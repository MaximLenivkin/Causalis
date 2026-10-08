"""Record B26 synthetic held-out and adjacent regression checks."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PATHS = ['README.md', 'causalis/scenarios/uplift/validation.py',
         'causalis/scenarios/uplift/__init__.py', 'tests/scenarios/uplift/test_held_out_validation.py']
TESTS = ['tests/scenarios/uplift', 'tests/inference/test_irm_external_oof.py',
         'tests/inference/test_irm_cluster_crossfit.py', 'tests/inference/test_irm_repeated_crossfit.py',
         'tests/inference/test_data_snapshot_contracts.py', 'tests/inference/test_irm_estimator.py',
         'tests/inference/test_irm_score_identities.py', 'tests/test_no_tests_imports_in_causalis.py']


def main():
    output = ROOT / 'audit/block26_focus_test_temp'
    output.mkdir(exist_ok=True)
    command = [sys.executable, '-m', 'pytest', *TESTS, '-q',
               '--junitxml=' + str(output/'junit.xml'), '--basetemp=' + str(output/'pytest-temp')]
    hashes = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in PATHS}
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               SKIP_DOCS_BUILD='true', MPLBACKEND='Agg', PYTEST_ADDOPTS='')
    log_path = ROOT/'audit/block26_focus_tests.log'
    with log_path.open('w') as log:
        status = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    suites = ET.parse(output/'junit.xml').getroot().findall('.//testsuite')
    totals = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
              for key in ('tests', 'failures', 'errors', 'skipped')}
    cases = list(ET.parse(output/'junit.xml').getroot().iter('testcase'))
    summary = next(line for line in reversed(log_path.read_text().splitlines()) if re.search(r'\d+ passed', line))
    payload = dict(observed_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                   source_state='working tree before source commit', command=command,
                   source_sha256=hashes, exit_code=status, **totals,
                   new_cases=sum('test_held_out_validation' in c.attrib['classname'] for c in cases),
                   passed=totals['tests']-totals['failures']-totals['errors']-totals['skipped'],
                   warnings=int(re.search(r'(\d+) warnings', summary)[1]) if re.search(r'(\d+) warnings', summary) else 0,
                   pytest_elapsed_seconds=float(re.search(r' in ([\d.]+)s', summary)[1]),
                   junit_sha256=hashlib.sha256((output/'junit.xml').read_bytes()).hexdigest())
    assert hashes == {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in PATHS}
    (ROOT/'audit/block26_focus_result.json').write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return status


if __name__ == '__main__':
    raise SystemExit(main())
