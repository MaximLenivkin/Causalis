"""Verify B26's source isolation and raw local/documentation/CI evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT/'audit'
BASELINE = '48761037fcbceae8d3aaaf2cc5595d481e63eca6'
PATHS = {'README.md', 'causalis/scenarios/uplift/validation.py',
         'causalis/scenarios/uplift/__init__.py', 'tests/scenarios/uplift/test_held_out_validation.py'}


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
    source_hashes = {n: hashlib.sha256(git('show', args.source+':'+n)).hexdigest() for n in sorted(PATHS)}
    assert source_hashes == {n: digest(ROOT/n) for n in sorted(PATHS)}
    existing = git('ls-tree', '-r', '--name-only', BASELINE, '--', 'causalis', 'scripts', '.github').decode().splitlines()
    unchanged = [n for n in existing if n != 'causalis/scenarios/uplift/__init__.py']
    assert all(git('show', BASELINE+':'+n) == git('show', args.source+':'+n) for n in unchanged)

    focus = read('block26_focus_result.json')
    assert focus['source_sha256'] == source_hashes and focus['observed_head'] == BASELINE
    assert focus['exit_code'] == focus['failures'] == focus['errors'] == focus['skipped'] == 0
    assert focus['passed'] == focus['tests'] == 686 and focus['new_cases'] == 102
    focus_path = AUDIT/'block26_focus_test_temp/junit.xml'
    focus_cases, focus_totals = junit(focus_path)
    assert digest(focus_path) == focus['junit_sha256']
    assert all(focus_totals[k] == focus[k] for k in focus_totals)
    assert sum('test_held_out_validation' in c[0] for c in focus_cases) == 102

    selection, result = read('block26_integration_selection.json'), read('block26_integration_result.json')
    previous = read('block25_integration_selection.json')
    assert selection['excluded_modules'] == previous['excluded_modules'] and len(selection['excluded_modules']) == 7
    for payload in (selection, result):
        assert payload['tested_source_checkpoint'] == args.source
        assert payload['scope'] == 'correctness' and payload['selected_full_suite'] is False
        assert payload['collect_only'] is False and payload['sensitivity_validated'] is False
    assert selection['environment']['commit'] == args.source
    assert result['exit_code'] == result['failures'] == result['errors'] == result['skipped'] == 0
    assert result['passed'] == result['tests'] == 3874
    full_cases, full_totals = junit(AUDIT/'block26_integration_test_temp/junit.xml')
    assert all(full_totals[k] == result[k] for k in full_totals)
    old_cases, _ = junit(AUDIT/'block25_integration_test_temp/junit.xml')
    assert old_cases < full_cases and len(full_cases-old_cases) == 102
    assert focus_cases <= full_cases

    docs = read('block26_docs_result.json')
    assert docs['environment']['commit'] == args.source and docs['exit_code'] == 0
    assert docs['warnings_are_errors'] is True and docs['publishes_html'] is False
    assert docs['log_sha256'] == digest(AUDIT/'block26_docs_test_temp/build.log')
    assert docs['generator_sha256'] == digest(ROOT/'scripts/generate_api_reference.py')
    assert docs == read('block26_docs_test_temp/result.json')
    cleanup = read('block26_cleanup_result.json')
    assert cleanup['source'] == args.source
    expected_removed = {'audit/block26_focus_test_temp/pytest-temp',
                        'audit/block26_integration_test_temp/pytest-temp'}
    assert cleanup['requested_but_not_created_paths'] == ['audit/block26_focus_test_temp/development-pytest-temp']
    assert not (ROOT/cleanup['requested_but_not_created_paths'][0]).exists()
    assert set(cleanup['removed_paths']) == expected_removed
    assert all(not (ROOT/name).exists() for name in expected_removed)
    assert cleanup['focus_junit_sha256'] == digest(focus_path)
    assert cleanup['integration_junit_sha256'] == digest(AUDIT/'block26_integration_test_temp/junit.xml')

    subprocess.run([sys.executable, 'audit/verify_handoff.py'], cwd=ROOT, check=True)
    handoff = read('handoff_validation.json')
    assert not handoff['issues']
    if args.require_ci:
        ci = read('block26_ci_result.json')
        assert ci['implementation_checkpoint'] == ci['tested_source_checkpoint'] == args.source
        assert ci['matrix_verified'] is True and ci['verified_successful_jobs'] == 6
        assert not ci['issues']
        manifest_before = ci
        subprocess.run([sys.executable, 'audit/summarize_block26_ci.py', '--run-id', str(ci['run_id']),
                        '--source', args.source, '--expected-tests', '3874'], cwd=ROOT, check=True)
        assert read('block26_ci_result.json') == manifest_before
        assert all(job['junit']['passed'] == 3874 and job['standalone_docs']['exit_code'] == 0 for job in ci['jobs'])
    report = (AUDIT/'BLOCK26_HELD_OUT_VALIDATION.md').read_text()
    links = re.findall(r'\]\(([^)]+)\)', report)
    local_links = [link for link in links if not link.startswith(('https://', 'http://'))]
    assert all((AUDIT/link.split('#')[0]).is_file() for link in local_links)
    payload = dict(source=args.source, baseline=BASELINE, issues=[],
                   changed_non_audit_paths=sorted(PATHS), unchanged_existing_source_files=len(unchanged),
                   source_sha256=source_hashes, focused_cases=len(focus_cases), new_cases=102,
                   integration_cases=len(full_cases), previous_cases_preserved=len(old_cases),
                   sensitivity_validated=False, standalone_sphinx_exit_code=0,
                   handoff_links_checked=handoff['snapshot_links_checked'], report_local_links_checked=len(local_links),
                   ci_required=args.require_ci)
    (AUDIT/'block26_validation_result.json').write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
