"""Run alone in sequential fresh single-thread workers; do not change estimands.

Baseline imports an extracted git package. Constructor/input creation are
separate from extraction and fit timers. Tracemalloc peak is not process RSS.
"""
import argparse
import gc
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import sys
import time
import tracemalloc

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
ROOT = Path(__file__).resolve().parents[1]
source = args.source.resolve() if args.source else ROOT
sys.path.insert(0, str(source))

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from threadpoolctl import threadpool_limits
from causalis.data_contracts import CausalData, IVCausalData, MultiCausalData
from causalis.scenarios.unconfoundedness import IRM
from causalis.scenarios.unconfoundedness._utils import _is_binary
from causalis.shared.outcome_plots import _kde_unbounded, _silverman_bandwidth


def measured(fn, repeats=5, memory=True):
    fn()  # Shape-specific warmup, outside both measurements.
    samples = []
    for _ in range(repeats):
        gc.collect()
        start = time.perf_counter()
        value = fn()
        samples.append(time.perf_counter() - start)
        del value
    result = dict(samples_seconds=samples, median_seconds=float(np.median(samples)))
    if memory:
        gc.collect()
        tracemalloc.start()
        value = fn()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        del value
        result["peak_traced_MiB"] = peak / 1024**2
    return result


def fingerprint(array):
    array = np.ascontiguousarray(array)
    return dict(shape=list(array.shape), dtype=str(array.dtype),
                sha256=hashlib.sha256(array.tobytes()).hexdigest())


def frame(n, p):
    rng = np.random.default_rng(731)
    x = rng.normal(size=(n, p))
    z = rng.binomial(1, .5, n)
    d = rng.binomial(1, 1 / (1 + np.exp(-(.4 * x[:, 0] + .6 * z))))
    y = 10 + 2 * d + x[:, 0] + rng.normal(size=n)
    cols = [f"x{i}" for i in range(p)]
    df = pd.DataFrame(x, columns=cols, index=np.arange(n) // 2)
    df["y"], df["d"], df["z"] = y, d, z
    labels = rng.integers(0, 3, n)
    for k in range(3):
        df[f"d{k}"] = (labels == k).astype(int)
    return df, cols


def owned_candidate(data):
    """Audit-only fresh owned extraction, keeping validation before int cast."""
    df = data.df
    y = df[data.outcome_name].to_numpy(dtype=float, copy=True)
    d = df[data.treatment_name].to_numpy(copy=True)
    if not _is_binary(d):
        raise ValueError("Treatment must be binary 0/1 or boolean.")
    d = d.astype(int)
    cols = list(data.confounders)
    if not cols:
        raise ValueError("CausalData must include non-empty confounders.")
    x = df[cols].to_numpy(dtype=float, copy=True)
    return x, y, d, _is_binary(y)


def main():
    result = dict(source=str(source), library_file=sys.modules["causalis"].__file__,
                  environment=dict(python=platform.python_version(), platform=platform.platform(),
                                   packages={name: importlib.metadata.version(name) for name in
                                             ["numpy", "pandas", "scipy", "scikit-learn", "statsmodels", "pydantic"]}),
                  seed=731, native_threads=1, repeats=5, contracts=[], extraction=[], binary=[], kde=[])
    for n, p in [(100_000, 20), (500_000, 20), (1_000_000, 8)]:
        df, cols = frame(n, p)
        factories = dict(causal=lambda: CausalData.from_df(df, "d", "y", cols),
                         iv=lambda: IVCausalData.from_df(df, "d", "y", "z", cols),
                         multi=lambda: MultiCausalData(df=df, outcome="y",
                            treatment_names=["d0", "d1", "d2"], confounders=cols, control_treatment="d0"))
        for kind, factory in factories.items():
            data = factory()
            snapshot = data.get_df()
            identity = dict(columns=list(snapshot.columns), index=fingerprint(snapshot.index.to_numpy()),
                            values=fingerprint(snapshot.to_numpy()))
            result["contracts"].append(dict(n=n, p=p, kind=kind, timing=measured(factory), snapshot=identity))
            del data, snapshot
        data = factories["causal"]()
        model = IRM(data=data, ml_g=LinearRegression(), ml_m=LogisticRegression(max_iter=200),
                    n_folds=3, random_state=17, n_jobs=1)
        arrays = model._check_data()
        candidate = owned_candidate(data)
        for actual, expected in zip(candidate[:3], arrays[:3]):
            np.testing.assert_array_equal(actual, expected)
        assert candidate[3] == arrays[3]
        result["extraction"].append(dict(n=n, p=p, current=measured(model._check_data),
                    owned_candidate=measured(lambda: owned_candidate(data)),
                    arrays=[fingerprint(array) for array in arrays[:3]], binary_outcome=bool(arrays[3])))
        for outcome in ["continuous", "binary"]:
            values = df.y.to_numpy() if outcome == "continuous" else df.d.to_numpy(dtype=float)
            result["binary"].append(dict(n=n, outcome=outcome, timing=measured(lambda: _is_binary(values)),
                                         value=bool(_is_binary(values))))
        del df, data, model, arrays, candidate

    for n in [10_000, 30_000]:
        x = np.random.default_rng(992).normal(size=n)
        grid = np.linspace(-5, 5, 800)
        bandwidth = _silverman_bandwidth(x)
        density = _kde_unbounded(x, grid, bandwidth)
        # Preserve raw output for numeric comparison, small 800-element JSON.
        result["kde"].append(dict(n=n, grid=800, bandwidth=bandwidth,
                                  timing=measured(lambda: _kde_unbounded(x, grid, bandwidth), repeats=3),
                                  density=density.tolist()))

    df, cols = frame(20_000, 8)
    data = CausalData.from_df(df, "d", "y", cols)
    def fit():
        return IRM(data=data, ml_g=LinearRegression(), ml_m=LogisticRegression(max_iter=200),
                   n_folds=3, random_state=17, n_jobs=1).fit()
    model = fit()
    estimate = model.estimate()
    result["irm"] = dict(n=20_000, p=8, n_folds=3, n_jobs=1, score="ATE",
                         fit=measured(fit, repeats=3, memory=False), value=float(estimate.value),
                         se=float(np.asarray(model.se)[0]),
                         arrays={name: fingerprint(getattr(model, name)) for name in
                           ["folds_", "g0_hat_", "g1_hat_", "m_hat_", "psi_", "psi_a_", "psi_b_"]})
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key not in ["kde", "contracts"]}, indent=2))


if __name__ == "__main__":
    with threadpool_limits(limits=1):
        main()
