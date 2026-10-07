"""Compare valid public fits and inference with the exact B17 implementation.

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

BASELINE = "b7cbec9ead7c589fa6d4570c0e8f188d349c95be"
PATHS = ["causalis/scenarios/_prediction.py",
         "causalis/scenarios/unconfoundedness/_utils.py",
         "causalis/scenarios/unconfoundedness/model.py",
         "causalis/scenarios/multi_unconfoundedness/_utils.py",
         "causalis/scenarios/multi_unconfoundedness/model.py",
         "causalis/scenarios/iv/model.py", "tests/inference/test_learner_output_shapes.py",
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
    old_module("_b18_binary_utils", PATHS[1])
    old_module("_b18_multi_utils", PATHS[3])
    binary_sub = [("from causalis.scenarios.unconfoundedness._utils import", "from _b18_binary_utils import")]
    multi_sub = [("from causalis.scenarios.multi_unconfoundedness._utils import", "from _b18_multi_utils import")]
    old_classes = {
        "binary": old_module("_b18_binary", PATHS[2], binary_sub).IRM,
        "multi": old_module("_b18_multi", PATHS[4], multi_sub).MultiTreatmentIRM,
        "iv": old_module("_b18_iv", PATHS[5], binary_sub).IIVM}
    attributes = {
        "binary": ["g0_hat_", "g1_hat_", "m_hat_", "m_hat_raw_", "folds_", "_full_sample_folds_"],
        "multi": ["g_hat_", "m_hat_", "m_hat_raw_", "folds_"],
        "iv": ["g_hat0_", "g_hat1_", "r_hat0_", "r_hat1_", "m_hat_", "m_hat_raw_", "folds_"]}
    fits, estimates = [], 0
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
                                     store_diagnostics=diagnostics, exact=True))
    unchanged = []
    allowed = {PATHS[1]: {"_predict_prob_or_value"}, PATHS[2]: set(),
               PATHS[3]: {"_predict_propensity_matrix"},
               PATHS[4]: {"_predict_binary_outcome_probability", "_fit_one_outcome_nuisance"},
               PATHS[5]: {"_cross_fit_nuisances", "fit"}}
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
    (ROOT / "audit/block18_probe_result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ("exact_fit_pairs", "exact_inference_pairs")}, indent=2))


if __name__ == "__main__":
    main()
