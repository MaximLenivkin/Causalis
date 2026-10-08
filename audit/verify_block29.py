"""Verify B29's committed source, preserved tests, local docs and optional CI."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = 'd88299887f96bd032fe3533349b2e2eb28ecf4ef'
SOURCE = '2c63f8d73c5d6f3ca15c4ca17ab0c1beb296f720'
PATHS = {'README.md', 'causalis/scenarios/did/__init__.py',
         'causalis/scenarios/did/honest.py', 'tests/scenarios/did/test_honest_did.py'}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def cases(path):
    return {(c.attrib['classname'], c.attrib['name']) for c in ET.parse(path).getroot().iter('testcase')}


def totals(path):
    suites = ET.parse(path).getroot().findall('.//testsuite')
    return {k: sum(int(s.attrib.get(k, 0)) for s in suites)
            for k in ('tests', 'failures', 'errors', 'skipped')}


def read(name):
    return json.loads((ROOT/'audit'/name).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-ci', action='store_true')
    args = parser.parse_args()
    assert set(git('diff', '--name-only', BASE, SOURCE).splitlines()) == PATHS
    initial_source = 'd54269201e8ab6c9fd44e01a506d868d1b61f472'
    assert git('diff', '--name-only', initial_source, SOURCE) == 'tests/scenarios/did/test_honest_did.py'
    assert all(p.startswith('audit/') for p in git('diff', '--name-only', SOURCE).splitlines())
    assert all(p.startswith('audit/') for p in git('ls-files', '--others', '--exclude-standard').splitlines())
    files = git('ls-tree', '-r', '--name-only', BASE).splitlines()
    old_library = [p for p in files if (p.startswith(('causalis/', 'scripts/', '.github/workflows/'))
                                      and p.endswith(('.py', '.yml', '.yaml')) and p not in PATHS)]
    old_tests = [p for p in files if p.startswith('tests/') and p.endswith('.py')]
    assert not git('diff', '--name-only', BASE, SOURCE, '--', *old_library, *old_tests)
    for path in PATHS:
        if path.endswith('.py'):
            ast.parse((ROOT/path).read_text())
    focus = read('block29_focus_result.json')
    integration = read('block29_integration_result.json')
    selection = read('block29_integration_selection.json')
    assert focus['observed_head'] == integration['tested_source_checkpoint'] == SOURCE
    assert focus['passed'] == focus['tests'] == 420 and focus['new_cases'] == 190
    assert integration['passed'] == integration['tests'] == 4282
    assert focus['exit_code'] == integration['exit_code'] == 0
    assert not any(focus[k] or integration[k] for k in ('failures', 'errors', 'skipped'))
    assert focus['source_sha256'] == {p: digest(ROOT/p) for p in PATHS}
    assert focus['junit_sha256'] == digest(ROOT/'audit/block29_focus_test_temp/junit.xml')
    assert totals(ROOT/'audit/block29_integration_test_temp/junit.xml') == {
        k: integration[k] for k in ('tests', 'failures', 'errors', 'skipped')}
    assert selection['environment']['commit'] == SOURCE
    assert selection['scope'] == integration['scope'] == 'correctness'
    assert selection['selected_full_suite'] is integration['selected_full_suite'] is False
    previous = read('block28_integration_selection.json')
    assert selection['excluded_modules'] == previous['excluded_modules'] and len(selection['excluded_modules']) == 7
    old_cases = cases(ROOT/'audit/block28_integration_test_temp/junit.xml')
    full_cases = cases(ROOT/'audit/block29_integration_test_temp/junit.xml')
    focused = cases(ROOT/'audit/block29_focus_test_temp/junit.xml')
    assert len(old_cases) == 4092 and old_cases <= full_cases and focused <= full_cases
    added = full_cases-old_cases
    assert len(added) == 190 and all('test_honest_did' in name for name, _ in added)
    initial_ci = read('block29_initial_ci_result.json')
    assert initial_ci['tested_source_checkpoint'] == initial_source
    assert initial_ci['run_conclusion'] == 'failure' and not initial_ci['matrix_verified']
    assert len(initial_ci['jobs']) == 6 and initial_ci['verified_successful_jobs'] == 0
    initial_dir = ROOT/'audit/block29_ci_test_temp/run-37844628093'
    for job in initial_ci['jobs']:
        artifact = initial_dir/f"correctness-py{job['python_minor']}-{job['stack']}"
        assert job['artifact_verified'] and job['conclusion'] == 'failure'
        assert job['junit'] == dict(tests=4282, failures=1, errors=0, skipped=0, passed=4281)
        raw = artifact/'ci-tests'
        assert cases(raw/'junit.xml') == full_cases
        failed = [c for c in ET.parse(raw/'junit.xml').getroot().iter('testcase') if c.find('failure') is not None]
        assert len(failed) == 1
        assert failed[0].attrib['name'] == 'test_actual_csa_adapter_owns_inputs_matches_iid_covariance_and_never_calls_model'
        assert 'confidence_set' in failed[0].find('failure').text
        assert job['artifact_sha256'] == {n:digest(raw/n) for n in ('selection.json','result.json','junit.xml')}
        assert job['docs_artifact_sha256'] == {n:digest(artifact/'docs-check'/n) for n in ('result.json','build.log')}
        assert job['standalone_docs']['exit_code'] == 0
    assert read('block29_initial_focus_result.json')['observed_head'] == initial_source
    assert read('block29_initial_integration_result.json')['passed'] == 4282
    assert read('block29_initial_docs_result.json')['environment']['commit'] == initial_source
    for kind in ('focus', 'integration'):
        initial_result = read(f'block29_initial_{kind}_result.json')
        raw = ROOT/f'audit/block29_initial_{kind}_test_temp/junit.xml'
        assert totals(raw) == {key:initial_result[key] for key in ('tests','failures','errors','skipped')}
        assert initial_result['exit_code'] == 0
        assert cases(raw) == (focused if kind == 'focus' else full_cases)
    initial_docs = read('block29_initial_docs_result.json')
    assert initial_docs == read('block29_initial_docs_test_temp/result.json')
    assert initial_docs['log_sha256'] == digest(ROOT/'audit/block29_initial_docs_test_temp/build.log')
    for log in read('block29_initial_log_result.json'):
        assert log['excerpt_sha256'] == digest(ROOT/log['excerpt'])
        assert log['original_sha256'] == digest(ROOT/log['original'])
    docs = read('block29_docs_result.json')
    assert docs == read('block29_docs_test_temp/result.json')
    assert docs['environment']['commit'] == SOURCE and docs['exit_code'] == 0
    assert docs['warnings_are_errors'] is True and docs['publishes_html'] is False
    assert docs['log_sha256'] == digest(ROOT/'audit/block29_docs_test_temp/build.log')
    assert docs['generator_sha256'] == digest(ROOT/'scripts/generate_api_reference.py')
    handoff = read('handoff_validation.json')
    assert not handoff['issues'] and handoff['snapshot_links_checked'] == 167
    for tag, expected in [('development', (177, 1)), ('development_final', (177, 0)),
                          ('development_complete', (187, 1)), ('precommit', (190, 0))]:
        observed = totals(ROOT/f'audit/block29_{tag}_test_temp/junit.xml')
        assert observed['tests'] == expected[0] and observed['failures'] == expected[1]
        assert observed['errors'] == observed['skipped'] == 0
    cleanup = read('block29_cleanup_result.json')
    allowed = {f'audit/block29_{kind}_test_temp/pytest-temp' for kind in ('focus', 'integration')}
    assert set(cleanup['removed_owned_paths']) <= allowed
    assert all(not (ROOT/p).exists() for p in allowed)
    assert cleanup['junit_sha256'] == {k: digest(ROOT/f'audit/block29_{k}_test_temp/junit.xml')
                                      for k in ('focus', 'integration')}
    assert cleanup['client_records_downloaded'] is False
    report = (ROOT/'audit/BLOCK29_HONEST_DID.md').read_text()
    links = re.findall(r'\]\(([^)]+)\)', report)
    local_links = [p for p in links if not p.startswith(('https:', 'http:'))]
    name = 'block29_validation_result.json' if args.require_ci else 'block29_local_validation_result.json'
    # The report may link this invocation's output before it is generated.
    assert all(p == name or (ROOT/'audit'/p).exists() for p in local_links)
    evidence = dict(baseline=BASE, tested_source_checkpoint=SOURCE, source_paths=sorted(PATHS),
                    existing_source_workflow_files_unchanged=len(old_library),
                    existing_test_files_unchanged=len(old_tests), all_4092_previous_cases_preserved=True,
                    new_cases=190, focused_cases=420, integration_cases=4282,
                    strict_sphinx_exit_code=0, handoff_links=167, local_report_links=len(local_links),
                    cleanup_verified=True, requires_ci=args.require_ci, issues=[])
    evidence.update(initial_six_portability_failures_preserved=True,
                    library_unchanged_by_portability_fix=True)
    if args.require_ci:
        ci = read('block29_ci_result.json')
        command = [str(ROOT/'.venv/bin/python'), 'audit/summarize_block29_ci.py', '--run-id',
                   str(ci['run_id']), '--source', SOURCE, '--expected-tests', '4282']
        subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        assert read('block29_ci_result.json') == ci
        assert ci['matrix_verified'] and ci['verified_successful_jobs'] == 6 and not ci['issues']
        assert ci['tested_source_checkpoint'] == SOURCE
        evidence.update(ci_run=ci['run_id'], all_six_matrix_artifacts_verified=True)
    (ROOT/'audit'/name).write_text(json.dumps(evidence, indent=2)+'\n')
    assert all((ROOT/'audit'/p).exists() for p in local_links)
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
