"""Compare valid public fits and inference with the exact B18 implementation.

Synthetic rows remain in memory. Save counts, configs and code hashes only.
"""
import ast
from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".venv/matplotlib"))
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from tests.inference.test_nuisance_prediction_contract import dataset, estimator

BASELINE = "52cd6e2fbb1934edaa1191856f70424858a59f6f"
PATHS = ["causalis/scenarios/_numerics.py",
         "causalis/scenarios/unconfoundedness/_utils.py",
         "causalis/scenarios/unconfoundedness/model.py",
         "causalis/scenarios/multi_unconfoundedness/_utils.py",
         "causalis/scenarios/multi_unconfoundedness/model.py",
         "causalis/scenarios/iv/model.py", "tests/inference/test_extreme_score_arithmetic.py",
         "tests/inference/test_nuisance_prediction_contract.py",
         "causalis/scenarios/unconfoundedness/_score_utils.py",
         "causalis/scenarios/unconfoundedness/_diagnostic_utils.py"]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def old_module(name, path, substitutions=()):
    source = git("show", f"{BASELINE}:{path}")
    for old, new in substitutions:
        source = source.replace(old.encode(), new.encode())
    module = types.ModuleType(name)
    sys.modules[name] = module
    exec(compile(source, name, "exec"), module.__dict__)
    return module


def main():
    old_module("_b19_score_utils", PATHS[8])
    old_module("_b19_binary_utils", PATHS[1])
    old_module("_b19_multi_utils", PATHS[3])
    binary_sub = [("from causalis.scenarios.unconfoundedness._utils import", "from _b19_binary_utils import"),
                  ("from causalis.scenarios.unconfoundedness._score_utils import", "from _b19_score_utils import")]
    multi_sub = [("from causalis.scenarios.multi_unconfoundedness._utils import", "from _b19_multi_utils import")]
    old_classes = {
        "binary": old_module("_b19_binary", PATHS[2], binary_sub).IRM,
        "multi": old_module("_b19_multi", PATHS[4], multi_sub).MultiTreatmentIRM,
        "iv": old_module("_b19_iv", PATHS[5], binary_sub).IIVM}
    attributes = {
        "binary": ["g0_hat_", "g1_hat_", "m_hat_", "m_hat_raw_", "folds_", "_full_sample_folds_"],
        "multi": ["g_hat_", "m_hat_", "m_hat_raw_", "folds_"],
        "iv": ["g_hat0_", "g_hat1_", "r_hat0_", "r_hat1_", "m_hat_", "m_hat_raw_", "folds_"]}
    fits, estimates = [], 0
    for normalize in (False, True):
        for kind in old_classes:
            for binary in (False, True):
                for jobs in (1, 2):
                    for diagnostics in ((True,) if kind == "iv" else (False, True)):
                        data = dataset(kind, binary_outcome=binary)
                        frame = data.get_df()
                        kwargs = dict(n_jobs=jobs)
                        if binary:
                            kwargs["g"] = LogisticRegression(max_iter=500)
                        current = estimator(kind, data, **kwargs)
                        if kind != "iv":
                            current.set_params(store_diagnostics=diagnostics)
                        assert str(inspect.signature(type(current))) == str(inspect.signature(old_classes[kind]))
                        old = old_classes[kind](**current.get_params(deep=False))
                        current.normalize_ipw = normalize
                        old.normalize_ipw = normalize
                        current.fit()
                        old.fit()
                        for attribute in attributes[kind]:
                            np.testing.assert_array_equal(getattr(current, attribute), getattr(old, attribute))
                        if kind == "iv":
                            assert list(current.predictions_) == list(old.predictions_)
                        for score in (("LATE",) if kind == "iv" else ("ATE", "ATTE")):
                            actual, expected = current.estimate(score=score), old.estimate(score=score)
                            for attribute in ("coef_", "se_", "pval_", "confint_", "psi_", "psi_a_", "psi_b_"):
                                np.testing.assert_array_equal(getattr(current, attribute), getattr(old, attribute))
                            np.testing.assert_array_equal(actual.value, expected.value)
                            estimates += 1
                        pd.testing.assert_frame_equal(data.get_df(), frame)
                        fits.append(dict(kind=kind, binary_outcome=binary, n_jobs=jobs,
                                         store_diagnostics=diagnostics, normalize_ipw=normalize, exact=True))
    unchanged = []
    allowed = {PATHS[1]: set(),
               PATHS[2]: {"_compute_estimate_components", "_solve_moment_equation",
                          "_compute_relative_effect_stats", "estimate"},
               PATHS[3]: set(),
               PATHS[4]: {"_compute_score_terms", "_solve_moment_and_inference",
                          "_compute_relative_effect_inference"},
               PATHS[5]: {"_compute_ipw_terms", "estimate"},
               PATHS[8]: {"_compute_ipw_components", "_resolve_irm_weights"}}
    for path, changed_names in allowed.items():
        def methods(source):
            tree = ast.parse(source)
            return {node.name: ast.dump(node, include_attributes=False)
                    for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        before = methods(git("show", f"{BASELINE}:{path}"))
        after = methods((ROOT / path).read_bytes())
        for name, node in before.items():
            if name not in changed_names:
                assert node == after[name], (path, name)
                unchanged.append(f"{path}:{name}")
    result = dict(baseline=BASELINE, process_head=git("rev-parse", "HEAD").decode().strip(),
                  observed_at=datetime.now(timezone.utc).isoformat(), python=sys.version,
                  exact_fit_pairs=len(fits), exact_inference_pairs=estimates, fits=fits,
                  unchanged_functions=unchanged,
                  sha256={path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in PATHS})
    (ROOT / "audit/block19_probe_result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ("exact_fit_pairs", "exact_inference_pairs")}, indent=2))


if __name__ == "__main__":
    main()
