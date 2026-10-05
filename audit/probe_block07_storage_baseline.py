"""Run the final public-fit storage probes against the exact previous methods."""
import subprocess
import sys
import types

import pytest

from causalis.scenarios.unconfoundedness.model import IRM
from causalis.scenarios.multi_unconfoundedness.model import MultiTreatmentIRM


BASELINE = "c234e647e010f5d8bfb805af7ece61392e327537"
CASES = "tests/inference/test_nuisance_prediction_contract.py"


def previous_class(path, name, class_name):
    source = subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], encoding="utf-8")
    module = types.ModuleType(name)
    module.__file__ = f"git:{BASELINE}:{path}"
    sys.modules[name] = module
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return getattr(module, class_name)


def main():
    old_binary = previous_class("causalis/scenarios/unconfoundedness/model.py",
                                "causalis.scenarios.unconfoundedness._b07_legacy_probe", "IRM")
    old_multi = previous_class("causalis/scenarios/multi_unconfoundedness/model.py",
                               "causalis.scenarios.multi_unconfoundedness._b07_legacy_probe", "MultiTreatmentIRM")
    # Only the two storage methods use the exact prior code. Ordinary fit()
    # prepares metadata and the test bypasses the fold prediction helpers.
    IRM._store_cross_fitted_predictions = old_binary._store_cross_fitted_predictions
    MultiTreatmentIRM._store_cross_fitted_predictions = old_multi._store_cross_fitted_predictions
    return pytest.main([CASES, "-k", "cross_fit_storage", "-q", "-p", "no:cacheprovider",
                        "--basetemp=audit/block07_nuisance_test_temp/storage_baseline",
                        "--junitxml=audit/block07_nuisance_test_temp/storage_baseline.xml"])


if __name__ == "__main__":
    sys.exit(main())
