"""Reproducible timings for contracts, data extraction and matched IRM fits.

Run alone (no concurrent pytest/fits) from repository root.
Tracemalloc is a traced allocation peak, not OS peak RSS.
"""
from __future__ import annotations

import cProfile
import gc
import importlib.metadata
import json
import os
import platform
import pstats
import statistics
import time
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from threadpoolctl import threadpool_limits

from causalis.data_contracts import CausalData, RctCausalData
from causalis.scenarios.unconfoundedness import IRM
from causalis.scenarios.unconfoundedness._utils import _is_binary

OUT = Path(__file__).parent


class SampleScreenedCausalData(CausalData):
    """Audit-only optimization prototype; library source is unchanged."""
    def _check_duplicate_column_values(self, df):
        roles = self._get_roles()
        column_roles = {name: role for role, name in roles.items()}
        column_roles.update({name: "confounder" for name in self.confounders_names})
        RctCausalData._check_duplicate_values(df, column_roles)


def linear_binary(values):
    """Exact same numeric 0/1-and-both-classes criterion without sorting."""
    return bool(np.all((values == 0) | (values == 1)) and np.any(values == 0) and np.any(values == 1))


def owned_arrays(data, binary_check=_is_binary):
    y = data.df[data.outcome_name].to_numpy(dtype=float, copy=True)
    d = data.df[data.treatment_name].to_numpy(dtype=int, copy=True)
    if not binary_check(d):
        raise ValueError("Treatment must be binary 0/1 or boolean.")
    cols = list(data.confounders)
    if not cols:
        raise ValueError("CausalData must include non-empty confounders.")
    X = data.df[cols].to_numpy(dtype=float, copy=True)
    return X, y, d, binary_check(y)


def timing(fn, repeats=5):
    samples = []
    value = None
    for _ in range(repeats):
        value = None
        gc.collect()
        start = time.perf_counter()
        value = fn()
        samples.append(time.perf_counter() - start)
    return {"median_seconds": statistics.median(samples), "samples_seconds": samples}, value


def memory(fn):
    gc.collect()
    tracemalloc.start()
    value = fn()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"traced_peak_MiB": peak / 1024**2}, value


def frame(n, p):
    rng = np.random.default_rng(321)
    X = rng.normal(size=(n, p))
    pr = 1 / (1 + np.exp(-.4*X[:, 0]))
    d = rng.binomial(1, pr)
    y = 2*d + X[:, 0] + rng.normal(size=n)
    cols = [f"x{i}" for i in range(p)]
    return pd.DataFrame({"y": y, "d": d, **{c: X[:, i] for i, c in enumerate(cols)}}), cols


def main():
    results = {"environment": {"python": platform.python_version(), "platform": platform.platform(),
                               "cpu": platform.processor(), "logical_cpu_count": os.cpu_count(),
                               "packages": {p: importlib.metadata.version(p) for p in
                                            ["numpy", "pandas", "scipy", "scikit-learn", "pydantic", "doubleml"]}},
               "contracts": [], "matched_irm": {}}
    with threadpool_limits(limits=1):
        for vals in [[], [0], [1], [0, 1], [0., 1., np.nan], [-1, 0, 1], [0, 1, np.inf]]:
            assert linear_binary(np.asarray(vals)) == _is_binary(np.asarray(vals))
        for n, p in [(100_000, 20), (500_000, 20), (1_000_000, 8)]:
            df, cols = frame(n, p)
            row = {"n": n, "p": p, "input_MiB": df.memory_usage(deep=True).sum()/1024**2}
            functions = {
                "CausalData": lambda: CausalData.from_df(df, "d", "y", cols),
                "RctCausalData_single_outcome": lambda: RctCausalData.from_df(df, "d", "y", cols),
                "sample_screening_prototype": lambda: SampleScreenedCausalData.from_df(df, "d", "y", cols),
                "selected_frame_copy_only": lambda: df[["y", "d"]+cols].copy(),
            }
            for name, fn in functions.items():
                values, value = timing(fn, repeats=5)
                values.update(memory(fn)[0])
                row[name] = values
                del value
            data = CausalData.from_df(df, "d", "y", cols)
            row["get_df_copy"], _ = timing(data.get_df)
            row["X_property_copy"], _ = timing(lambda: data.X)
            proto = IRM(data=data, ml_g=LinearRegression(), ml_m=LogisticRegression(max_iter=100), n_folds=3, random_state=17)
            row["IRM_extract_arrays"], _ = timing(proto._check_data)
            row["owned_arrays_same_checks"], extracted = timing(lambda: owned_arrays(data))
            reference = proto._check_data()
            for actual, expected in zip(extracted[:3], reference[:3]):
                np.testing.assert_array_equal(actual, expected)
            assert extracted[3] == reference[3]
            row["owned_arrays_linear_binary_checks"], optimized = timing(lambda: owned_arrays(data, linear_binary))
            for actual, expected in zip(optimized[:3], reference[:3]):
                np.testing.assert_array_equal(actual, expected)
            assert optimized[3] == reference[3]
            results["contracts"].append(row)
            del proto, df, data

        # Matched sample splits, same learners, one native thread and one job.
        import doubleml as dml
        df, cols = frame(20_000, 8)
        data = CausalData.from_df(df, "d", "y", cols)
        ml_g = LinearRegression()
        ml_m = LogisticRegression(max_iter=100)
        models = []
        def causalis_fit():
            model = IRM(data=data, ml_g=ml_g, ml_m=ml_m, n_folds=3, random_state=17, n_jobs=1)
            model.fit()
            return model
        times, model = timing(causalis_fit, repeats=3)
        estimate = model.estimate(score="ATE")
        splits = model.smpls_ if hasattr(model, "smpls_") else None
        if splits is None:
            from sklearn.model_selection import StratifiedKFold
            splits = list(StratifiedKFold(n_splits=3, shuffle=True, random_state=17).split(df[cols], df.d))
        other_data = dml.DoubleMLData(df, y_col="y", d_cols="d", x_cols=cols)
        def doubleml_fit():
            other = dml.DoubleMLIRM(other_data, ml_g=ml_g, ml_m=ml_m, n_folds=3, score="ATE", normalize_ipw=False, draw_sample_splitting=False)
            other.set_sample_splitting(splits)
            other.fit(n_jobs_cv=1)
            return other
        other_times, other = timing(doubleml_fit, repeats=3)
        # Actual split equality verified by predictions, rather than assumed from seeds.
        pred = other.predictions
        results["matched_irm"] = {"n": 20_000, "p": 8, "folds": 3,
                                  "Causalis_fit": times, "DoubleML_fit": other_times,
                                  "Causalis_ATE": estimate.value, "DoubleML_ATE": float(other.coef[0]),
                                  "DoubleML_SE": float(other.se[0]),
                                  "Causalis_SE_from_IF": float(np.sqrt(np.mean(model.psi_**2)/len(df))) if hasattr(model, "psi_") else None,
                                  "max_m_hat_difference": float(np.max(np.abs(model.m_hat_ - pred["ml_m"][:, 0, 0]))),
                                  "max_g0_hat_difference": float(np.max(np.abs(model.g0_hat_ - pred["ml_g0"][:, 0, 0]))),
                                  "max_g1_hat_difference": float(np.max(np.abs(model.g1_hat_ - pred["ml_g1"][:, 0, 0])))}
        profile = cProfile.Profile()
        profile.enable()
        causalis_fit()
        profile.disable()
        with (OUT / "profile_irm.txt").open("w", encoding="utf-8") as stream:
            pstats.Stats(profile, stream=stream).sort_stats("cumulative").print_stats(35)
        profile = cProfile.Profile()
        profile.enable()
        CausalData.from_df(df, "d", "y", cols)
        profile.disable()
        with (OUT / "profile_contract.txt").open("w", encoding="utf-8") as stream:
            pstats.Stats(profile, stream=stream).sort_stats("cumulative").print_stats(30)
    (OUT / "benchmark_data_path.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
