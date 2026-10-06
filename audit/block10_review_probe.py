"""Independent B10 coordinate and exact numeric-only compatibility probes."""
from contextlib import contextmanager
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import types

import numpy as np
import pandas as pd
from scipy.stats import norm

import causalis.dgp.base as shared
from causalis.dgp.causaldata.base import CausalDatasetGenerator
from causalis.dgp.causaldata_instrumental.base import InstrumentalGenerator
from causalis.dgp.multicausaldata.base import MultiCausalDatasetGenerator


BASELINE = "83b63836dbd0c4793c24dd95ff7dc18c443792ad"
SPECS = [
    {"name": "numeric_a", "dist": "normal", "mu": 2., "sd": .7, "clip_min": -1., "clip_max": 5.},
    {"name": "numeric_b", "dist": "uniform", "a": -2., "b": 4.},
    {"name": "numeric_c", "dist": "bernoulli", "p": .37},
    {"name": "numeric_d", "dist": "lognormal", "mu": .2, "sigma": .4},
    {"name": "numeric_e", "dist": "gamma", "shape": 3., "mean": 2.},
    {"name": "numeric_f", "dist": "beta", "mean": .4, "kappa": 6.},
    {"name": "numeric_g", "dist": "poisson", "lam": 2.},
    {"name": "numeric_h", "dist": "negbin", "mu": 3., "alpha": .3},
]


def frozen_helper():
    module = types.ModuleType("block10_review_frozen_shared")
    sys.modules[module.__name__] = module
    source = subprocess.check_output(["git", "show", f"{BASELINE}:causalis/dgp/base.py"], text=True)
    exec(compile(source, f"{BASELINE}:causalis/dgp/base.py", "exec"), module.__dict__)
    return module._gaussian_copula


@contextmanager
def substitute_helper(helper):
    modules = [importlib.import_module("causalis.dgp.causaldata.base"),
               importlib.import_module("causalis.dgp.multicausaldata.base")]
    originals = [module._gaussian_copula for module in modules]
    try:
        for module in modules:
            module._gaussian_copula = helper
        yield
    finally:
        for module, original in zip(modules, originals):
            module._gaussian_copula = original


def numeric_only(frozen):
    entries = []
    correlations = {"identity": np.eye(8),
                    "toeplitz": .35 ** np.abs(np.arange(8)[:, None] - np.arange(8)),
                    "singular_repaired": np.ones((8, 8))}
    for seed in [1, 731, 999]:
        for n in [1, 30]:
            for label, corr in correlations.items():
                old_rng, new_rng = np.random.default_rng(seed), np.random.default_rng(seed)
                for generation in range(2):
                    old_x, old_names = frozen(old_rng, n, SPECS, corr)
                    new_x, new_names = shared._gaussian_copula(new_rng, n, SPECS, corr)
                    np.testing.assert_array_equal(old_x, new_x)
                    assert old_names == new_names
                    np.testing.assert_array_equal(old_rng.random(10), new_rng.random(10))
                entries.append({"seed": seed, "n": n, "correlation": label, "generations": 2,
                                "exact_values_names_next10rng": True})
    return entries


def public_frames(frozen):
    entries = []
    for generator in [CausalDatasetGenerator, MultiCausalDatasetGenerator, InstrumentalGenerator]:
        for outcome in ["continuous", "binary", "poisson", "gamma"]:
            for oracle in [False, True]:
                for seed in [4, 731]:
                    kwargs = dict(confounder_specs=SPECS, use_copula=True,
                                  copula_corr=.25 ** np.abs(np.arange(8)[:, None] - np.arange(8)),
                                  outcome_type=outcome, include_oracle=oracle, seed=seed)
                    old, new = generator(**kwargs), generator(**kwargs)
                    for generation in range(2):
                        with substitute_helper(frozen):
                            expected = old.generate(30)
                        actual = new.generate(30)
                        pd.testing.assert_frame_equal(expected, actual, check_exact=True)
                        if hasattr(old, "confounder_names_"):
                            assert old.confounder_names_ == new.confounder_names_
                        np.testing.assert_array_equal(old.rng.random(10), new.rng.random(10))
                    entries.append({"generator": generator.__name__, "outcome": outcome,
                                    "include_oracle": oracle, "seed": seed, "generations": 2,
                                    "exact_frame_schema_next10rng": True})
    return entries


def coordinate_reference(frozen):
    entries = []
    patterns = [["categorical"], ["categorical", "categorical", "categorical"],
                ["normal", "categorical", "uniform", "categorical", "categorical", "normal"]]
    for pattern in patterns:
        for rho in [0., .6, -.2]:
            d = len(pattern)
            corr = np.full((d, d), rho)
            np.fill_diagonal(corr, 1.)
            specs = [{"name": f"x{j}", "dist": dist,
                      **({"categories": [0, 1, 2], "probs": [.2, .3, .5]} if dist == "categorical" else {})}
                     for j, dist in enumerate(pattern)]
            normal_specs = [{"name": f"z{j}", "dist": "normal"} for j in range(d)]
            normal_rng, current_rng = np.random.default_rng(731), np.random.default_rng(731)
            z, _ = frozen(normal_rng, 1000, normal_specs, corr)
            x, names = shared._gaussian_copula(current_rng, 1000, specs, corr)
            width = 0
            for j, dist in enumerate(pattern):
                if dist == "categorical":
                    # Independent latent Gaussian partition, using the quantiles
                    # rather than the categorical implementation's CDF/search.
                    q1, q2 = norm.ppf(.2), norm.ppf(.5)
                    expected_1 = (z[:, j] >= q1) & (z[:, j] < q2)
                    expected_2 = z[:, j] >= q2
                    np.testing.assert_array_equal(x[:, width], expected_1.astype(float))
                    np.testing.assert_array_equal(x[:, width + 1], expected_2.astype(float))
                    width += 2
                else:
                    width += 1
            np.testing.assert_array_equal(normal_rng.random(10), current_rng.random(10))
            entry = {"pattern": pattern, "rho": rho, "n": 1000,
                     "exact_current_coordinate_gaussian_partitions": True, "next10rng_equal": True}
            try:
                old_x, old_names = frozen(np.random.default_rng(731), 1000, specs, corr)
                entry["baseline_status"] = "returned"
                entry["baseline_matches_corrected_categories"] = bool(np.array_equal(old_x, x))
                numeric_names = [f"x{j}" for j, dist in enumerate(pattern) if dist != "categorical"]
                indices = [names.index(name) for name in numeric_names]
                np.testing.assert_array_equal(old_x[:, indices], x[:, indices])
                entry["numeric_columns_baseline_exact"] = True
            except UnboundLocalError:
                entry["baseline_status"] = "UnboundLocalError"
            entries.append(entry)
    return entries


class FixedRNG:
    def __init__(self, values):
        self.values = np.asarray(values, dtype=float)
        self.calls = 0

    def normal(self, size):
        assert size == self.values.shape
        self.calls += 1
        return self.values.copy()


def boundary_reference():
    entries = []
    for tail, weights, expected in [
        (10., [.5, .5, 0.], [1., 0.]),
        (10., [1., 0., 0.], [0., 0.]),
        (-100., [0., 1., 0.], [1., 0.]),
        (-100., [0., 0., 1.], [0., 1.]),
        (0., [.5, 0., .5], [0., 1.]),
        (10., [.2, .3, .5], [0., 1.]),
        (-8., [1e-15, 1. - 1e-15, 0.], [0., 0.]),
    ]:
        rng = FixedRNG([[0., tail]])
        x, names = shared._gaussian_copula(rng, 1,
            [{"name": "z", "dist": "normal"},
             {"name": "c", "dist": "categorical", "categories": [0, 1, 2], "probs": weights}])
        np.testing.assert_array_equal(x[0, 1:], expected)
        assert rng.calls == 1
        entries.append({"tail_z": tail, "probabilities": weights, "expected_nonbase_dummies": expected,
                        "actual_matches": True, "normal_calls": rng.calls})
    return entries


def main():
    frozen = frozen_helper()
    root = Path(__file__).resolve().parents[1]
    result = {"baseline_sha": BASELINE,
              "reviewed_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "working_library_diff_sha256": hashlib.sha256(subprocess.check_output(
                  ["git", "diff", "HEAD", "--", "causalis/dgp/base.py"])).hexdigest(),
              "current_library_sha256": hashlib.sha256((root / "causalis/dgp/base.py").read_bytes()).hexdigest(),
              "current_test_module_sha256": hashlib.sha256((root / "tests/data/test_copula_categorical_coordinates.py").read_bytes()).hexdigest(),
              "numeric_helper_reference": numeric_only(frozen),
              "public_numeric_fullframe_reference": public_frames(frozen),
              "coordinate_reference": coordinate_reference(frozen),
              "boundary_reference": boundary_reference(), "issues": []}
    Path(__file__).with_name("block10_review_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"numeric_helper_configs": len(result["numeric_helper_reference"]),
                      "public_fullframe_configs": len(result["public_numeric_fullframe_reference"]),
                      "coordinate_configs": len(result["coordinate_reference"]),
                      "boundary_cases": len(result["boundary_reference"]), "all_checks_passed": True}, indent=2))


if __name__ == "__main__":
    main()
