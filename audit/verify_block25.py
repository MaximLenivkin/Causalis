"""Check B25 source isolation, numerical regressions and local/CI provenance."""
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
AUDIT = ROOT / 'audit'
BASELINE = 'ebf940f76ec81317a2a59ff6a52880473a23f581'
PATHS = {'README.md', 'causalis/scenarios/uplift/learners.py',
         'causalis/scenarios/uplift/__init__.py', 'tests/scenarios/uplift/test_dr_r_learners.py'}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def read(name):
    return json.loads((AUDIT / name).read_text())


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
    # All existing library algorithms, sensitivity, guards, workflows and
    # test selections are byte-identical; only the uplift export list changes.
    existing = git('ls-tree', '-r', '--name-only', BASELINE, '--', 'causalis', 'scripts', '.github').decode().splitlines()
    unchanged = [n for n in existing if n != 'causalis/scenarios/uplift/__init__.py']
    assert all(git('show', BASELINE+':'+n) == git('show', args.source+':'+n) for n in unchanged)

    focus = read('block25_focus_result.json')
    assert focus['source_sha256'] == source_hashes
    assert focus['observed_head'] == BASELINE
    assert focus['exit_code'] == focus['failures'] == focus['errors'] == focus['skipped'] == 0
    assert focus['passed'] == focus['tests'] == 584 and focus['new_cases'] == 124
    focus_path = AUDIT/'block25_focus_test_temp/junit.xml'
    focus_cases, focus_totals = junit(focus_path)
    assert digest(focus_path) == focus['junit_sha256']
    assert all(focus_totals[k] == focus[k] for k in focus_totals)
    assert sum('test_dr_r_learners' in c[0] for c in focus_cases) == 124

    correction = read('block25_complex_baseline_result.json')
    assert correction['failed'] == 8 and correction['deselected'] == 116
    assert digest(AUDIT/'block25_complex_baseline_tests.log') == correction['log_sha256']
    assert correction['source_sha256']['tests/scenarios/uplift/test_dr_r_learners.py'] == source_hashes['tests/scenarios/uplift/test_dr_r_learners.py']
    assert correction['source_sha256']['causalis/scenarios/uplift/learners.py'] != source_hashes['causalis/scenarios/uplift/learners.py']

    selection, result = read('block25_integration_selection.json'), read('block25_integration_result.json')
    previous = read('block24_integration_selection.json')
    assert selection['excluded_modules'] == previous['excluded_modules'] and len(selection['excluded_modules']) == 7
    for payload in (selection, result):
        assert payload['tested_source_checkpoint'] == payload['environment']['commit'] == args.source
        assert payload['scope'] == 'correctness' and payload['selected_full_suite'] is False
        assert payload['collect_only'] is False and payload['sensitivity_validated'] is False
    assert result['exit_code'] == result['failures'] == result['errors'] == result['skipped'] == 0
    assert result['passed'] == result['tests'] == 3772
    full_cases, full_totals = junit(AUDIT/'block25_integration_test_temp/junit.xml')
    assert all(full_totals[k] == result[k] for k in full_totals)
    old_cases, _ = junit(AUDIT/'block24_integration_test_temp/junit.xml')
    assert old_cases < full_cases and len(full_cases-old_cases) == 124
    assert focus_cases <= full_cases

    docs = read('block25_docs_result.json')
    assert docs['environment']['commit'] == args.source and docs['exit_code'] == 0
    assert docs['warnings_are_errors'] is True and docs['publishes_html'] is False
    assert docs['log_sha256'] == digest(AUDIT/'block25_docs_test_temp/build.log')
    assert docs['generator_sha256'] == digest(ROOT/'scripts/generate_api_reference.py')
    assert docs == read('block25_docs_test_temp/result.json')
    cleanup = read('block25_cleanup_result.json')
    assert cleanup['source'] == args.source
    expected_removed = {'audit/block25_focus_test_temp/pytest-temp',
                        'audit/block25_focus_test_temp/first-pytest-temp',
                        'audit/block25_focus_test_temp/complex-pytest-temp',
                        'audit/block25_integration_test_temp/pytest-temp'}
    assert set(cleanup['removed_paths']) == expected_removed
    assert all(not (ROOT/name).exists() for name in expected_removed)
    assert cleanup['focus_junit_sha256'] == digest(focus_path)
    assert cleanup['integration_junit_sha256'] == digest(AUDIT/'block25_integration_test_temp/junit.xml')

    subprocess.run([sys.executable, 'audit/verify_handoff.py'], cwd=ROOT, check=True)
    handoff = read('handoff_validation.json')
    assert handoff['snapshot_links_checked'] == 149 and handoff['issues'] == []
    local_links = []
    for target in re.findall(r'\]\(([^)]+)\)', (AUDIT/'BLOCK25_DR_R_CATE.md').read_text()):
        if target.startswith(('https://', 'http://', '#')): continue
        assert (AUDIT/target).is_file(), target
        local_links.append(target)
    ci = None
    if args.require_ci:
        ci = read('block25_ci_result.json')
        before = (AUDIT/'block25_ci_result.json').read_bytes()
        subprocess.run([sys.executable, 'audit/summarize_block25_ci.py', '--run-id', str(ci['run_id']),
                        '--source', args.source, '--expected-tests', '3772'], cwd=ROOT, check=True)
        assert (AUDIT/'block25_ci_result.json').read_bytes() == before
        assert ci['matrix_verified'] is True and ci['issues'] == []
    payload = dict(baseline=BASELINE, implementation_checkpoint=args.source,
                   source_sha256=source_hashes, unchanged_existing_source_files=len(unchanged),
                   focused_passed=584, new_cases=124, integration_passed=3772,
                   prior_case_set_preserved=True, sensitivity_validated=False,
                   standalone_docs_exit=0, handoff_links=149, report_local_links=len(local_links),
                   ci_required=args.require_ci, ci_matrix_verified=bool(ci), issues=[])
    (AUDIT/'block25_validation_result.json').write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
