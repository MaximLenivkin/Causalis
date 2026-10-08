"""Verify B27's source isolation and raw local/documentation/CI evidence."""
from __future__ import annotations

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
BASELINE = '750354b51896f0d775b3eb73c1cebaec1b882f17'
PATHS = {'README.md', 'causalis/__init__.py', 'causalis/inference/family.py',
         'causalis/inference/__init__.py', 'tests/inference/test_inference_family.py'}


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
    unchanged = [n for n in existing if n != 'causalis/__init__.py']
    assert all(git('show', BASELINE+':'+n) == git('show', args.source+':'+n) for n in unchanged)

    old_root = ast.parse(git('show', BASELINE+':causalis/__init__.py').decode())
    new_root = ast.parse(git('show', args.source+':causalis/__init__.py').decode())
    functions = lambda tree: {n.name: ast.dump(n, include_attributes=False)
                             for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert functions(old_root) == functions(new_root)
    initial_docs = read('block27_initial_docs_result.json')
    assert initial_docs['environment']['commit'] == 'f71863483c59df3d740a4984981998bfcb0da627'
    assert initial_docs['exit_code'] == 1
    assert initial_docs['log_sha256'] == digest(AUDIT/'block27_initial_docs_test_temp/build.log')
    initial_result = read('block27_initial_integration_result.json')
    assert initial_result['tested_source_checkpoint'] == initial_docs['environment']['commit']
    assert initial_result['tests'] == 3980 and initial_result['failures'] == 1
    _, initial_totals = junit(AUDIT/'block27_initial_integration_test_temp/junit.xml')
    assert all(initial_totals[k] == initial_result[k] for k in initial_totals)

    focus = read('block27_focus_result.json')
    assert focus['source_sha256'] == source_hashes and focus['observed_head'] == args.source
    assert focus['exit_code'] == focus['failures'] == focus['errors'] == focus['skipped'] == 0
    assert focus['passed'] == focus['tests'] == 793 and focus['new_cases'] == 107
    focus_path = AUDIT/'block27_focus_test_temp/junit.xml'
    focus_cases, focus_totals = junit(focus_path)
    assert digest(focus_path) == focus['junit_sha256']
    assert all(focus_totals[k] == focus[k] for k in focus_totals)
    assert sum('test_inference_family' in c[0] for c in focus_cases) == 107

    selection, result = read('block27_integration_selection.json'), read('block27_integration_result.json')
    previous = read('block26_integration_selection.json')
    assert selection['excluded_modules'] == previous['excluded_modules'] and len(selection['excluded_modules']) == 7
    for payload in (selection, result):
        assert payload['tested_source_checkpoint'] == args.source
        assert payload['scope'] == 'correctness' and payload['selected_full_suite'] is False
        assert payload['collect_only'] is False and payload['sensitivity_validated'] is False
    assert selection['environment']['commit'] == args.source
    assert result['exit_code'] == result['failures'] == result['errors'] == result['skipped'] == 0
    assert result['passed'] == result['tests'] == 3981
    full_cases, full_totals = junit(AUDIT/'block27_integration_test_temp/junit.xml')
    assert all(full_totals[k] == result[k] for k in full_totals)
    old_cases, _ = junit(AUDIT/'block26_integration_test_temp/junit.xml')
    assert old_cases < full_cases and len(full_cases-old_cases) == 107
    assert focus_cases <= full_cases

    docs = read('block27_docs_result.json')
    assert docs['environment']['commit'] == args.source and docs['exit_code'] == 0
    assert docs['warnings_are_errors'] is True and docs['publishes_html'] is False
    assert docs['log_sha256'] == digest(AUDIT/'block27_docs_test_temp/build.log')
    assert docs['generator_sha256'] == digest(ROOT/'scripts/generate_api_reference.py')
    assert docs == read('block27_docs_test_temp/result.json')
    cleanup = read('block27_cleanup_result.json')
    assert cleanup['source'] == args.source
    expected_removed = {'audit/block27_focus_test_temp/pytest-temp',
                        'audit/block27_integration_test_temp/pytest-temp'}
    assert set(cleanup['removed_paths']) == expected_removed
    assert all(not (ROOT/name).exists() for name in expected_removed)
    assert cleanup['focus_junit_sha256'] == digest(focus_path)
    assert cleanup['integration_junit_sha256'] == digest(AUDIT/'block27_integration_test_temp/junit.xml')

    subprocess.run([sys.executable, 'audit/verify_handoff.py'], cwd=ROOT, check=True)
    handoff = read('handoff_validation.json')
    assert not handoff['issues']
    if args.require_ci:
        ci = read('block27_ci_result.json')
        assert ci['implementation_checkpoint'] == ci['tested_source_checkpoint'] == args.source
        assert ci['matrix_verified'] is True and ci['verified_successful_jobs'] == 6
        assert not ci['issues']
        manifest_before = ci
        subprocess.run([sys.executable, 'audit/summarize_block27_ci.py', '--run-id', str(ci['run_id']),
                        '--source', args.source, '--expected-tests', '3981'], cwd=ROOT, check=True)
        assert read('block27_ci_result.json') == manifest_before
        assert all(job['junit']['passed'] == 3981 and job['standalone_docs']['exit_code'] == 0 for job in ci['jobs'])
    report = (AUDIT/'BLOCK27_INFERENCE_FAMILIES.md').read_text()
    links = re.findall(r'\]\(([^)]+)\)', report)
    local_links = [link for link in links if not link.startswith(('https://', 'http://'))]
    assert all((AUDIT/link.split('#')[0]).is_file() for link in local_links)
    payload = dict(source=args.source, baseline=BASELINE, issues=[],
                   changed_non_audit_paths=sorted(PATHS), unchanged_existing_source_files=len(unchanged),
                   source_sha256=source_hashes, focused_cases=len(focus_cases), new_cases=107,
                   integration_cases=len(full_cases), previous_cases_preserved=len(old_cases),
                   sensitivity_validated=False, standalone_sphinx_exit_code=0,
                   handoff_links_checked=handoff['snapshot_links_checked'], report_local_links_checked=len(local_links),
                   ci_required=args.require_ci)
    (AUDIT/'block27_validation_result.json').write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
