"""Verify exact B17 committed scope, baseline/final tests, local and CI evidence."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'aaeadd8'
SOURCE = 'e2fced5f476a8567bee2cc0bbda062ad62124eae'


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


def totals(path):
    suites = ET.parse(ROOT/'audit'/path).getroot().findall('.//testsuite')
    counts = {k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    counts['passed'] = counts['tests']-sum(counts[k] for k in ('failures','errors','skipped'))
    return counts


def cases(path):
    return {(n.attrib['classname'],n.attrib['name']) for n in ET.parse(ROOT/'audit'/path).getroot().iter('testcase')}


def methods(data):
    return {n.name:ast.dump(n,include_attributes=False) for cls in ast.parse(data).body
            if isinstance(cls,ast.ClassDef) for n in cls.body if isinstance(n,ast.FunctionDef)}


def main():
    expected = {'causalis/dgp/_gaussian_joint.py','causalis/dgp/causaldata/base.py',
        'causalis/dgp/causaldata_instrumental/base.py','tests/data/test_gaussian_propensity_joint_means.py',
        'tests/data/test_gaussian_joint_accuracy_policy.py'}
    assert set(git('diff','--name-only',BASELINE,SOURCE,'--','causalis','tests','scripts').decode().splitlines()) == expected
    assert not git('diff',SOURCE,'--name-only','--','causalis','tests','scripts').strip()
    allowed = {'causalis/dgp/causaldata/base.py':{'generate','oracle_nuisance'},
               'causalis/dgp/causaldata_instrumental/base.py':{'_r_by_z','_g_by_z'}}
    unchanged = 0
    for path,names in allowed.items():
        before,after = methods(git('show',f'{BASELINE}:{path}')),methods(git('show',f'{SOURCE}:{path}'))
        assert before.keys() == after.keys()
        for name in before.keys()-names:
            assert before[name] == after[name], (path,name)
            unchanged += 1
    probe = json.loads((ROOT/'audit/block17_probe_result.json').read_text())
    assert probe['baseline'] == git('rev-parse',BASELINE).decode().strip()
    for path,digest in probe['source_hashes'].items():
        data = (ROOT/path).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest
        assert data == git('show',f'{SOURCE}:{path}')
    for path in ('causalis/dgp/_gaussian_outcome.py','causalis/dgp/base.py','causalis/dgp/multicausaldata/base.py'):
        assert git('show',f'{BASELINE}:{path}') == git('show',f'{SOURCE}:{path}')
    assert len(probe['unchanged_methods']) == unchanged
    assert len(probe['compatibility']) == 90 and probe['compatibility_frame_rng_pairs'] == 180
    assert len(probe['references']) == 52 and len(probe['repairs']) == 4
    b = json.loads((ROOT/'audit/block17_baseline_result.json').read_text())
    assert b['baseline'] == probe['baseline'] and b['exit_code'] == 1
    assert b['test_sha256'] == probe['source_hashes'][b['test_path']]
    assert b['shared_helper_sha256'] == probe['source_hashes']['causalis/dgp/_gaussian_outcome.py']
    for path,digest in b['baseline_sha256'].items():
        assert hashlib.sha256(git('show',f'{BASELINE}:{path}')).hexdigest() == digest
    baseline,focus,neighbors,integration = [totals(p) for p in ('block17_baseline.xml','block17_focus.xml',
        'block17_neighbors.xml','block17_integration_test_temp/junit.xml')]
    assert baseline == dict(tests=57,failures=45,errors=0,skipped=0,passed=12)
    for count,res in ((90,focus),(1449,neighbors),(2829,integration)):
        assert res == dict(tests=count,failures=0,errors=0,skipped=0,passed=count)
    final_cases = cases('block17_focus.xml')
    assert cases('block17_baseline.xml') == {c for c in final_cases if c[0].endswith('test_gaussian_propensity_joint_means')}
    assert final_cases <= cases('block17_neighbors.xml') <= cases('block17_integration_test_temp/junit.xml')
    selection = json.loads((ROOT/'audit/block17_integration_selection.json').read_text())
    result = json.loads((ROOT/'audit/block17_integration_result.json').read_text())
    old = json.loads((ROOT/'audit/block16_integration_selection.json').read_text())
    assert selection['excluded_modules'] == old['excluded_modules'] and len(selection['excluded_modules']) == 7
    assert selection['tested_source_checkpoint'] == result['tested_source_checkpoint'] == selection['environment']['commit'] == SOURCE
    assert result['exit_code'] == 0 and result['scoped_suite_clean'] is True
    assert result['sensitivity_validated'] is result['full_suite_clean'] is False
    ci = json.loads((ROOT/'audit/block17_ci_result.json').read_text())
    assert ci['matrix_verified'] is True and ci['verified_successful_jobs'] == 6 and ci['issues'] == []
    assert ci['tested_source_checkpoint'] == SOURCE and ci['expected_tests_per_job'] == 2829
    assert ci['excluded_modules'] == selection['excluded_modules']
    for job in ci['jobs']:
        assert job['case_sets_verified'] and job['artifact_verified']
        artifact = ROOT/f"audit/block17_ci_test_temp/run-{ci['run_id']}"/f"correctness-py{job['python_minor']}-{job['stack']}"
        for path,digest in job['artifact_sha256'].items():
            assert hashlib.sha256((artifact/path).read_bytes()).hexdigest() == digest
        assert totals(str((artifact/'junit.xml').relative_to(ROOT/'audit'))) == integration
        assert cases(str((artifact/'junit.xml').relative_to(ROOT/'audit'))) == cases('block17_integration_test_temp/junit.xml')
    ast_count = 0
    for path in (ROOT/'audit').glob('*block17*.py'):
        ast.parse(path.read_text())
        ast_count += 1
    links = 0
    report = (ROOT/'audit/BLOCK17_GAUSSIAN_PROPENSITY_JOINT_MEANS.md').read_text()
    for target in re.findall(r'\]\(([^)]+)\)',report):
        if not target.startswith(('https://','http://','#')):
            assert (ROOT/'audit'/target).exists(),target
            links += 1
    payload = dict(source_checkpoint=SOURCE,baseline=probe['baseline'],
        original_probe_process_head=probe['process_head'],original_probe_time=probe['observed_at_utc'],
        committed_hash_paths=len(probe['source_hashes']),unchanged_methods=unchanged,
        baseline_tests=baseline,focus_tests=focus,neighbors_tests=neighbors,integration=integration,
        ci_run=ci['run_id'],ci_verified=True,sensitivity_validated=False,
        ast_checks=ast_count,local_report_links=links,issues=[])
    (ROOT/'audit/block17_validation_result.json').write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(payload,indent=2))

if __name__ == '__main__':
    main()
