"""Replay sampling regressions against exact B07 generator and wrapper source."""
from pathlib import Path
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import causalis.dgp.multicausaldata as package

for suffix in ("base", "functional"):
    name = "causalis.dgp.multicausaldata." + suffix
    path = "causalis/dgp/multicausaldata/" + suffix + ".py"
    source = subprocess.check_output([
        "git", "show", "b33922f1c0db8885ae9e8e071c45fc46de5205b6:" + path
    ], cwd=ROOT).decode("utf-8")
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / path)
    sys.modules[name] = module
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    setattr(package, suffix, module)
    if suffix == "base":
        package.MultiCausalDatasetGenerator = module.MultiCausalDatasetGenerator
    else:
        package.generate_multitreatment = module.generate_multitreatment

import pytest
raise SystemExit(pytest.main([
    "tests/data/test_multicausal_assignment_policy.py", "-q", "-p", "no:cacheprovider",
    "--basetemp=" + str(ROOT / "audit/block08_sampling_exact_before_test_temp")
]))
