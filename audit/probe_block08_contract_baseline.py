"""Run new contract regressions against the exact B07 source checkpoint."""
from pathlib import Path
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
name = 'causalis.dgp.multicausaldata.base'
import causalis.dgp.multicausaldata.base

source = subprocess.check_output(
    ['git', 'show', 'b33922f1c0db8885ae9e8e071c45fc46de5205b6:causalis/dgp/multicausaldata/base.py'],
    cwd=ROOT,
).decode('utf-8')
module = types.ModuleType(name)
module.__file__ = str(ROOT / 'causalis/dgp/multicausaldata/base.py')
sys.modules[name] = module
exec(compile(source, module.__file__, 'exec'), module.__dict__)
import pytest

raise SystemExit(pytest.main([
    str(ROOT / 'tests/data/test_multicausal_generator_contracts.py'),
    '-q', '-p', 'no:cacheprovider',
    '--basetemp=' + str(ROOT / 'audit/block08_contract_before_test_temp'),
]))
