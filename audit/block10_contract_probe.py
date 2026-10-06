"""Read-only B10 categorical-copula coordinate and boundary contract probes."""
from __future__ import annotations

import ast
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import types

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".venv/matplotlib"))
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np
from scipy.special import ndtri

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "83b63836dbd0c4793c24dd95ff7dc18c443792ad"
PATH = "causalis/dgp/base.py"
sys.path.insert(0, str(ROOT))


def module_from_source(name, source):
    module = types.ModuleType(name)
    sys.modules[name] = module
    exec(compile(source, name, "exec"), module.__dict__)
    return module


def runtime_body(source):
    function = next(node for node in ast.parse(source).body
                    if isinstance(node, ast.FunctionDef) and node.name == "_gaussian_copula")
    return ast.dump(ast.Module(body=function.body[1:], type_ignores=[]), include_attributes=False)


class ControlledRNG:
    def __init__(self, values):
        self.values = np.asarray(values, dtype=float)
        self.calls = []

    def normal(self, size):
        assert tuple(size) == self.values.shape
        self.calls.append(list(size))
        return self.values.copy()


def main():
    source = subprocess.check_output(
        ["git", "show", f"{BASELINE}:{PATH}"], cwd=ROOT, text=True
    )
    old_line = 'draw = np.searchsorted(thr, u, side="right")'
    assert source.count(old_line) == 1
    candidate_source = source.replace(old_line, 'draw = np.searchsorted(thr, U[:, j], side="right")')
    old_guard = "draw[draw == len(cats)] = len(cats) - 1"
    assert candidate_source.count(old_guard) == 1
    candidate_source = candidate_source.replace(
        old_guard,
        "if np.any(draw == len(cats)):\n"
        "                draw[draw == len(cats)] = np.flatnonzero(probs > 0)[-1]",
    )
    assert runtime_body((ROOT / PATH).read_text(encoding="utf-8")) == runtime_body(candidate_source)
    baseline = module_from_source("_block10_contract_baseline", source)
    candidate = module_from_source("_block10_contract_candidate", candidate_source)
    gaussian_reference = []
    for rho in (0., .6, -.6):
        seed, n = 731, 20_000
        rng = np.random.default_rng(seed)
        innovations = rng.normal(size=(n, 2))
        diagonal = math.sqrt(1. + 1e-10)
        second = rho / diagonal * innovations[:, 0] + math.sqrt(
            1. + 1e-10 - rho ** 2 / (1. + 1e-10)
        ) * innovations[:, 1]
        # Gaussian-domain cutpoints are independent of the helper's cdf and
        # searchsorted. Known positive-definite C avoids shared PSD repair.
        cutpoints = ndtri(np.array([.2, .5]))
        classes = (second[:, None] >= cutpoints).sum(axis=1)
        expected = np.column_stack((classes == 1, classes == 2)).astype(float)
        settings = dict(
            n=n, specs=[{"name": "z", "dist": "normal"},
                        {"name": "cat", "dist": "categorical", "categories": [0, 1, 2],
                         "probs": [.2, .3, .5]}],
            corr=np.array([[1., rho], [rho, 1.]]),
        )
        old_rng, new_rng = np.random.default_rng(seed), np.random.default_rng(seed)
        old, old_names = baseline._gaussian_copula(old_rng, **settings)
        new, new_names = candidate._gaussian_copula(new_rng, **settings)
        np.testing.assert_array_equal(new[:, 1:], expected)
        np.testing.assert_array_equal(new[:, 0], old[:, 0])
        np.testing.assert_array_equal(new_rng.random(10), old_rng.random(10))
        assert old_names == new_names == ["z", "cat_1", "cat_2"]
        gaussian_reference.append({
            "rho": rho, "n": n, "seed": seed,
            "candidate_matches_independent_gaussian_domain_reference": True,
            "baseline_reference_mismatches": int(np.any(old[:, 1:] != expected, axis=1).sum()),
            "numeric_column_exact": True, "next_rng_draws_exact": True,
        })

    # The scores are deterministic probe inputs, not observed/client records.
    scores = np.array([-40., -9., -8., -7.5, 0., 7.5, 8., 9., 40.])
    raw_uniform = np.array([.5 * math.erfc(-z / math.sqrt(2.)) for z in scores])
    weights = np.array([.5e-12, 1. - 1e-12, .5e-12])
    cdf = np.cumsum(weights / weights.sum())
    raw_classes = np.array([sum(value >= threshold for threshold in cdf) for value in raw_uniform])
    raw_classes[raw_classes == 3] = 2
    clipped_uniform = np.clip(raw_uniform, 1e-12, 1. - 1e-12)
    clipped_classes = np.array([sum(value >= threshold for threshold in cdf) for value in clipped_uniform])
    clipped_classes[clipped_classes == 3] = 2
    innovations = (scores / math.sqrt(1. + 1e-10)).reshape(-1, 1)
    controlled = ControlledRNG(innovations)
    actual, names = candidate._gaussian_copula(
        controlled, len(scores), [{"name": "tail", "dist": "categorical",
                                  "categories": [0, 1, 2], "probs": weights}],
    )
    np.testing.assert_array_equal(actual, np.column_stack((raw_classes == 1, raw_classes == 2)).astype(float))
    assert names == ["tail_1", "tail_2"] and controlled.calls == [[len(scores), 1]]
    endpoint_cases = []
    for label, probabilities, expected in (
        ("leading_zero_at_U0", [0., .5, .5], [1, 2, 2]),
        ("middle_zero_at_Uhalf", [.5, 0., .5], [0, 2, 2]),
        ("trailing_zero_at_U1", [.5, .5, 0.], [0, 1, 1]),
        ("multiple_trailing_zeros_at_U1", [1., 0., 0.], [0, 0, 0]),
    ):
        test_rng = ControlledRNG(np.array([-40., 0., 40.]).reshape(3, 1) / math.sqrt(1. + 1e-10))
        values, _ = candidate._gaussian_copula(
            test_rng, 3, [{"name": "endpoint", "dist": "categorical",
                          "categories": [0, 1, 2], "probs": probabilities}],
        )
        expected = np.asarray(expected)
        np.testing.assert_array_equal(values, np.column_stack((expected == 1, expected == 2)).astype(float))
        endpoint_cases.append({"name": label, "expected_classes_at_U0_half_1": expected.tolist(),
                               "candidate_exact": True, "rng_normal_calls": test_rng.calls})

    numeric_specs = [
        {"name": "normal", "dist": "normal", "mu": 2., "sd": .7},
        {"name": "uniform", "dist": "uniform", "a": -2., "b": 3.},
        {"name": "bernoulli", "dist": "bernoulli", "p": .35},
        {"name": "lognormal", "dist": "lognormal", "mu": .2, "sigma": .5},
        {"name": "gamma", "dist": "gamma", "shape": 2., "mean": 3.},
        {"name": "beta", "dist": "beta", "mean": .3, "kappa": 7.},
        {"name": "poisson", "dist": "poisson", "lam": 4.},
        {"name": "negbin", "dist": "negbin", "mu": 3., "alpha": .4},
    ]
    old_rng, new_rng = np.random.default_rng(947), np.random.default_rng(947)
    old, old_names = baseline._gaussian_copula(old_rng, 512, numeric_specs)
    new, new_names = candidate._gaussian_copula(new_rng, 512, numeric_specs)
    np.testing.assert_array_equal(new, old)
    np.testing.assert_array_equal(new_rng.random(10), old_rng.random(10))
    assert old_names == new_names
    single_rng = ControlledRNG(np.array([[-40.], [0.], [40.]]))
    single, single_names = candidate._gaussian_copula(
        single_rng, 3, [{"name": "one", "dist": "categorical", "categories": ["only"]}],
    )
    np.testing.assert_array_equal(single, np.zeros((3, 1)))
    assert single_names == ["one__onlylevel"]
    payload = {
        "baseline": BASELINE,
        "observed_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "candidate_scope": "Frozen baseline helper patched in memory only; no library/test edits by this reviewer.",
        "working_tree_runtime_ast_matches_candidate": True,
        "working_tree_diff_sha256": hashlib.sha256(subprocess.check_output(
            ["git", "diff", BASELINE, "--", PATH], cwd=ROOT
        )).hexdigest(),
        "gaussian_reference": gaussian_reference,
        "tail_policy": {"gaussian_probe_scores": scores.tolist(), "weights": weights.tolist(),
                        "raw_classes": raw_classes.tolist(), "clipped_classes": clipped_classes.tolist(),
                        "raw_vs_clipped_disagreements": int(np.sum(raw_classes != clipped_classes)),
                        "candidate_matches_raw_reference": True},
        "endpoint_cases": endpoint_cases,
        "numeric_only_compatibility": {"n": 512, "seed": 947, "families": 8,
                                       "values_schema_exact": True, "next_rng_draws_exact": True},
        "first_single_level": {"values_schema_exact": True, "rng_normal_calls": single_rng.calls},
        "issues": [],
    }
    (ROOT / "audit/block10_contract_result.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({"gaussian_reference_configurations": len(gaussian_reference),
                      "tail_disagreements_if_clipped": payload["tail_policy"]["raw_vs_clipped_disagreements"],
                      "endpoint_cases": len(endpoint_cases), "issues": []}))


if __name__ == "__main__":
    main()
