"""Verify B28 source isolation, retained regression cases and raw gate evidence."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT/'audit'
BASELINE = 'ab789bff3d03f6d2b20023c7d259adcdd8cc7019'
PATHS = {'README.md', 'causalis/scenarios/iv/__init__.py', 'causalis/scenarios/iv/model.py',
         'causalis/scenarios/iv/weak.py', 'tests/inference/test_iivm_weak.py'}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def read(name):
    return json.loads((AUDIT/name).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def junit(path):
    tree = ET.parse(path).getroot()
    cases = {(c.attrib['classname'], c.attrib['name']) for c in tree.iter('testcase')}
    totals = {key: sum(int(s.attrib.get(key, 0)) for s in tree.findall('.//testsuite'))
              for key in ('tests', 'failures', 'errors', 'skipped')}
    assert len(cases) == totals['tests']
    return cases, totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--require-ci', action='store_true')
    args = parser.parse_args()
    assert re.fullmatch('[a-f0-9]{40}', args.source)
    changed = set(git('diff', '--name-only', BASELINE, args.source).decode().splitlines())
    assert {n for n in changed if not n.startswith('audit/')} == PATHS
    assert all(n.startswith('audit/') for n in git('diff', '--name-only', args.source, 'HEAD').decode().splitlines())
    assert not git('diff', 'HEAD', '--name-only', '--', 'causalis', 'tests', 'scripts', 'README.md').strip()
    assert not git('ls-files', '--others', '--exclude-standard', '--', 'causalis', 'tests', 'scripts').strip()
    hashes = {n: hashlib.sha256(git('show', args.source+':'+n)).hexdigest() for n in sorted(PATHS)}
    assert hashes == {n: digest(ROOT/n) for n in sorted(PATHS)}
    existing = git('ls-tree', '-r', '--name-only', BASELINE, '--', 'causalis', 'scripts', '.github').decode().splitlines()
    unchanged = [n for n in existing if n not in PATHS]
    assert not git('diff', '--name-only', BASELINE, args.source, '--', *unchanged).strip()
    old_tests = git('ls-tree', '-r', '--name-only', BASELINE, '--', 'tests').decode().splitlines()
    assert not git('diff', '--name-only', BASELINE, args.source, '--', *old_tests).strip()
    def iv_methods(source):
        tree = ast.parse(git('show', source+':causalis/scenarios/iv/model.py').decode())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'IIVM')
        return {n.name: ast.dump(n, include_attributes=False) for n in cls.body if isinstance(n, ast.FunctionDef)}
    old, new = iv_methods(BASELINE), iv_methods(args.source)
    assert set(new)-set(old) == {'estimate_weak_iv'}
    assert all(new[key] == value for key, value in old.items())

    initial_cases, initial_totals = junit(AUDIT/'block28_development_test_temp/junit.xml')
    assert initial_totals == dict(tests=102, failures=2, errors=0, skipped=0)
    probe = read('block28_initial_discriminant_probe.json')
    assert probe['status'] == 'returned' and probe['set_type'] == 'singleton'
    assert probe['source'] == '856b05ca78a7127bdd342eb79cd9fda961aa6873'
    assert read('block28_final_discriminant_probe.json')['status'] == 'rejected'
    assert read('block28_final_discriminant_probe.json')['source'] == args.source
    pre_statistic = read('block28_pre_statistic_ci_result.json')
    assert pre_statistic['matrix_verified'] and pre_statistic['verified_successful_jobs'] == 6
    assert pre_statistic['implementation_checkpoint'] == '8aad3a07b96d174151bd7ef39bcaba05f7d98bfe'
    assert pre_statistic['expected_tests_per_job'] == 4091
    prior_cases, prior_totals = junit(AUDIT/'block28_pre_statistic_integration_test_temp/junit.xml')
    assert prior_totals == dict(tests=4091, failures=0, errors=0, skipped=0)
    prior_ci_root = AUDIT/f"block28_ci_test_temp/run-{pre_statistic['run_id']}"
    for job in pre_statistic['jobs']:
        folder = prior_ci_root/f"correctness-py{job['python_minor']}-{job['stack']}"
        assert job['junit']['passed'] == 4091 and job['standalone_docs']['exit_code'] == 0
        for name, recorded in job['artifact_sha256'].items():
            assert digest(folder/'ci-tests'/name) == recorded
        for name, recorded in job['docs_artifact_sha256'].items():
            assert digest(folder/'docs-check'/name) == recorded
        assert junit(folder/'ci-tests/junit.xml')[0] == prior_cases
    first = read('block28_initial_integration_result.json')
    assert first['tested_source_checkpoint'] == probe['source']
    assert first['tests'] == first['passed'] == 4089 and first['exit_code'] == 0
    _, first_totals = junit(AUDIT/'block28_initial_integration_test_temp/junit.xml')
    assert all(first_totals[k] == first[k] for k in first_totals)

    focus = read('block28_focus_result.json')
    assert focus['source_sha256'] == hashes and focus['observed_head'] == args.source
    assert focus['exit_code'] == focus['failures'] == focus['errors'] == focus['skipped'] == 0
    focus_path = AUDIT/'block28_focus_test_temp/junit.xml'
    focus_cases, focus_totals = junit(focus_path)
    assert digest(focus_path) == focus['junit_sha256']
    assert all(focus_totals[k] == focus[k] for k in focus_totals)
    new_cases = sum('test_iivm_weak' in c[0] for c in focus_cases)
    assert new_cases == focus['new_cases'] == 111
    selection, result = read('block28_integration_selection.json'), read('block28_integration_result.json')
    previous = read('block27_integration_selection.json')
    assert selection['excluded_modules'] == previous['excluded_modules'] and len(selection['excluded_modules']) == 7
    for payload in (selection, result):
        assert payload['tested_source_checkpoint'] == args.source
        assert payload['scope'] == 'correctness' and payload['selected_full_suite'] is False
        assert payload['collect_only'] is False and payload['sensitivity_validated'] is False
    assert selection['environment']['commit'] == args.source
    assert result['exit_code'] == result['failures'] == result['errors'] == result['skipped'] == 0
    assert result['passed'] == result['tests'] == 4092
    full_cases, totals = junit(AUDIT/'block28_integration_test_temp/junit.xml')
    assert all(totals[k] == result[k] for k in totals)
    old_cases, _ = junit(AUDIT/'block27_integration_test_temp/junit.xml')
    assert old_cases < full_cases and len(full_cases-old_cases) == new_cases
    assert focus_cases <= full_cases
    assert prior_cases < full_cases and len(full_cases-prior_cases) == 1
    docs = read('block28_docs_result.json')
    assert docs['environment']['commit'] == args.source and docs['exit_code'] == 0
    assert docs['warnings_are_errors'] is True and docs['publishes_html'] is False
    assert docs['log_sha256'] == digest(AUDIT/'block28_docs_test_temp/build.log')
    assert docs['generator_sha256'] == digest(ROOT/'scripts/generate_api_reference.py')
    assert docs == read('block28_docs_test_temp/result.json')
    cleanup = read('block28_cleanup_result.json')
    assert cleanup['source'] == args.source and cleanup['client_records_downloaded'] is False
    expected_removed = {'audit/block28_integration_test_temp/pytest-temp'}
    assert set(cleanup['removed_paths']) == expected_removed
    assert all(not (ROOT/name).exists() for name in expected_removed)
    assert set(cleanup['basetemp_not_created']) == {'audit/block28_focus_test_temp/pytest-temp'}
    assert cleanup['focus_junit_sha256'] == digest(focus_path)
    assert cleanup['integration_junit_sha256'] == digest(AUDIT/'block28_integration_test_temp/junit.xml')
    subprocess.run([sys.executable, 'audit/verify_handoff.py'], cwd=ROOT, check=True)
    handoff = read('handoff_validation.json')
    assert not handoff['issues']
    if args.require_ci:
        ci = read('block28_ci_result.json')
        assert ci['implementation_checkpoint'] == ci['tested_source_checkpoint'] == args.source
        assert ci['matrix_verified'] is True and ci['verified_successful_jobs'] == 6 and not ci['issues']
        subprocess.run([sys.executable, 'audit/summarize_block28_ci.py', '--run-id', str(ci['run_id']),
                        '--source', args.source, '--expected-tests', str(len(full_cases))], cwd=ROOT, check=True)
        assert read('block28_ci_result.json') == ci
    report = (AUDIT/'BLOCK28_WEAK_IV.md').read_text()
    local_links = [link for link in re.findall(r'\]\(([^)]+)\)', report)
                   if not link.startswith(('https://', 'http://'))]
    assert all((AUDIT/link.split('#')[0]).is_file() for link in local_links)
    payload = dict(source=args.source, baseline=BASELINE, issues=[], changed_non_audit_paths=sorted(PATHS),
                   unchanged_existing_source_files=len(unchanged), unchanged_existing_test_files=len(old_tests),
                   unchanged_iivm_methods=len(old), source_sha256=hashes, focused_cases=len(focus_cases),
                   new_cases=new_cases, integration_cases=len(full_cases), previous_cases_preserved=len(old_cases),
                   sensitivity_validated=False, standalone_sphinx_exit_code=0,
                   handoff_links_checked=handoff['snapshot_links_checked'], report_local_links_checked=len(local_links),
                   ci_required=args.require_ci)
    (AUDIT/'block28_validation_result.json').write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
