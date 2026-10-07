"""Run final B17 public regression file against exact frozen B16 classes."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from probe_block17 import git, load, BASELINE
import causalis.dgp.causaldata.base as binary
import causalis.dgp.causaldata_instrumental.base as iv
import pytest

paths = ['causalis/dgp/causaldata/base.py','causalis/dgp/causaldata_instrumental/base.py']
old_binary = load('_b17_test_old_binary',git('show',f'{BASELINE}:{paths[0]}')).CausalDatasetGenerator
old_iv = load('_b17_test_old_iv',git('show',f'{BASELINE}:{paths[1]}').replace(
    b'from causalis.dgp.causaldata.base import CausalDatasetGenerator',
    b'from _b17_test_old_binary import CausalDatasetGenerator')).InstrumentalGenerator
assert old_iv.__bases__ == (old_binary,)
binary.CausalDatasetGenerator = old_binary
iv.InstrumentalGenerator = old_iv
test_path = 'tests/data/test_gaussian_propensity_joint_means.py'
metadata = dict(baseline=git('rev-parse',BASELINE).decode().strip(),
    process_head=git('rev-parse','HEAD').decode().strip(),
    baseline_sha256={p:hashlib.sha256(git('show',f'{BASELINE}:{p}')).hexdigest() for p in paths},
    test_path=test_path,test_sha256=hashlib.sha256((ROOT/test_path).read_bytes()).hexdigest(),
    shared_helper_sha256=hashlib.sha256((ROOT/'causalis/dgp/_gaussian_outcome.py').read_bytes()).hexdigest())
code = pytest.main([test_path,'-q','--junitxml=audit/block17_baseline.xml'])
metadata['exit_code'] = int(code)
(ROOT/'audit/block17_baseline_result.json').write_text(json.dumps(metadata,indent=2)+'\n')
raise SystemExit(code)
