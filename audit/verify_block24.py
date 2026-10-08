"""Root-only B24 source, AST, test and exact CI evidence verification."""
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

from run_block24_focus import PATHS

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '3668eec10a5cc794dd16be26d8ade6c284277bf4'
PRE_FIX = '2652d9faeb027da871cd2cc4d1cea5f518485fcd'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()


def read(name):
    return json.loads((ROOT/'audit'/name).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(node):
    return ast.dump(node, include_attributes=False)


def methods(tree):
    return {method.name: method for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'IRM'
            for method in node.body if isinstance(method, ast.FunctionDef)}


def cases(path):
    return {(case.attrib['classname'], case.attrib['name']) for case in ET.parse(path).getroot().iter('testcase')}


def totals(path):
    return {name: sum(int(s.attrib.get(name, 0)) for s in ET.parse(path).getroot().iter('testsuite'))
            for name in ('tests', 'failures', 'errors', 'skipped')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--require-ci', action='store_true')
    args = parser.parse_args()
    changed = git('diff', '--name-only', BASELINE, args.source).splitlines()
    assert set(name for name in changed if not name.startswith('audit/')) == set(PATHS)
    assert all(name.startswith('audit/') for name in git('diff', '--name-only', args.source, 'HEAD').splitlines())
    source_hashes = {}
    for name in PATHS:
        committed = subprocess.check_output(['git', 'show', args.source+':'+name], cwd=ROOT)
        assert committed == (ROOT/name).read_bytes(), name
        source_hashes[name] = sha(ROOT/name)
    model = 'causalis/scenarios/unconfoundedness/model.py'
    before = methods(ast.parse(git('show', BASELINE+':'+model)))
    after = methods(ast.parse((ROOT/model).read_text()))
    modified = {name for name in before if dump(before[name]) != dump(after[name])}
    assert modified == {'fit', 'estimate', 'predict_cate', '_sensitivity_element_est', 'sensitivity_analysis'}
    assert set(after)-set(before) == {'make_oof_manifest', '_validate_external_oof_config'}
    for name in ('_sensitivity_element_est', 'sensitivity_analysis'):
        # Only the first guard after the unchanged docstring is new.
        guard = after[name].body.pop(1)
        assert isinstance(guard, ast.If) and '_fit_external_oof_' in ast.unparse(guard.test)
        assert dump(after[name]) == dump(before[name])
    for path, function in [('causalis/scenarios/gate/model.py', '_validate_gate_inputs'),
                           ('causalis/scenarios/uplift/model.py', '_validate_fitted_irm')]:
        before_module = ast.parse(git('show', BASELINE+':'+path))
        after_module = ast.parse((ROOT/path).read_text())
        target = next(node for node in after_module.body if isinstance(node, ast.FunctionDef) and node.name == function)
        guard = target.body.pop(1)
        assert isinstance(guard, ast.If) and '_fit_external_oof_' in ast.unparse(guard.test)
        assert dump(before_module) == dump(after_module)
    repeated = 'causalis/scenarios/unconfoundedness/_repeated.py'
    repeated_after = ast.parse((ROOT/repeated).read_text())
    aggregate = next(node for node in repeated_after.body if isinstance(node, ast.FunctionDef) and node.name == 'aggregate_estimates')
    aggregate.body = [node for node in aggregate.body if ast.unparse(node) != "options.pop('oof_split_seed', None)"]
    assert dump(repeated_after) == dump(ast.parse(git('show', BASELINE+':'+repeated)))
    probe = read('block24_probe_result.json')
    assert probe['baseline'] == BASELINE and probe['observed_head'] == PRE_FIX
    assert probe['exact_internal_fit_configuration_pairs'] == 64
    assert probe['exact_internal_estimate_pairs'] == 96
    assert probe['exact_unsupported_weighted_atte_rejections'] == 32
    assert probe['temporary_copies_removed'] is True
    assert probe['baseline_feature']['status'] == 'unsupported' and probe['current_feature']['status'] == 'supported'
    for name, expected in probe['source_sha256'].items(): assert sha(ROOT/name) == expected
    focus = read('block24_focus_result.json')
    assert focus['observed_head'] == PRE_FIX and focus['source_sha256'] == source_hashes
    focus_path = ROOT/'audit/block24_focus_test_temp/junit.xml'
    assert focus['junit_sha256'] == sha(focus_path)
    assert totals(focus_path) == {key: focus[key] for key in ('tests', 'failures', 'errors', 'skipped')}
    assert focus['exit_code'] == focus['failures'] == focus['errors'] == focus['skipped'] == 0
    assert focus['new_cases'] == 127 and focus['passed'] == focus['tests'] == 491
    local = read('block24_integration_result.json')
    selection = read('block24_integration_selection.json')
    local_path = ROOT/'audit/block24_integration_test_temp/junit.xml'
    assert local['tested_source_checkpoint'] == selection['tested_source_checkpoint'] == args.source
    assert selection['environment']['commit'] == args.source and selection['selected_full_suite'] is False
    assert local['exit_code'] == 0 and local['tests'] == local['passed'] == 3648
    assert totals(local_path) == {key: local[key] for key in ('tests', 'failures', 'errors', 'skipped')}
    assert local['failures'] == local['errors'] == local['skipped'] == 0
    assert cases(focus_path) <= cases(local_path)
    initial = read('block24_initial_ci_result.json')
    assert initial['tested_source_checkpoint'] == PRE_FIX
    assert initial['matrix_verified'] and initial['verified_successful_jobs'] == 6
    initial_path = ROOT/'audit/block24_initial_integration_test_temp/junit.xml'
    initial_local = read('block24_initial_integration_result.json')
    assert initial_local['tested_source_checkpoint'] == PRE_FIX
    assert initial_local['passed'] == 3646 and initial_local['exit_code'] == 0
    initial_cases = cases(initial_path)
    assert len(initial_cases) == 3646 and initial_cases < cases(local_path)
    for job in initial['jobs']:
        folder = ROOT/'audit'/f"block24_ci_test_temp/run-{initial['run_id']}"/f"correctness-py{job['python_minor']}-{job['stack']}"
        assert cases(folder/'ci-tests/junit.xml') == initial_cases
        for name, expected in job['artifact_sha256'].items(): assert sha(folder/'ci-tests'/name) == expected
        for name, expected in job['docs_artifact_sha256'].items(): assert sha(folder/'docs-check'/name) == expected
    docs_path = ROOT/'audit/block24_docs_test_temp'
    docs = read('block24_docs_result.json')
    assert docs == json.loads((docs_path/'result.json').read_text())
    assert docs['environment']['commit'] == args.source and docs['exit_code'] == 0
    assert docs['warnings_are_errors'] is True and docs['publishes_html'] is False
    assert docs['log_sha256'] == sha(docs_path/'build.log')
    assert docs['generator_sha256'] == sha(ROOT/'scripts/generate_api_reference.py')
    cleanup = read('block24_cleanup_result.json')
    assert cleanup['tested_source_checkpoint'] == args.source
    assert cleanup['integration_selection_sha256'] == sha(ROOT/'audit/block24_integration_selection.json')
    expected_temp = [str(ROOT/'audit'/f'block24_{name}_test_temp/pytest-temp') for name in ('integration', 'focus')]
    assert cleanup['owned_exact_pytest_temporary_directories_removed'] == expected_temp
    assert all(not Path(path).exists() for path in expected_temp)
    report = ROOT/'audit/BLOCK24_EXTERNAL_OOF.md'
    local_links = []
    for link in re.findall(r'\]\(([^)]+)\)', report.read_text()):
        if '://' in link or link.startswith('#'):
            continue
        assert (report.parent/link.split('#')[0]).is_file(), link
        local_links.append(link)
    handoff = subprocess.run([sys.executable, 'audit/verify_handoff.py'], cwd=ROOT, capture_output=True, text=True, check=True)
    handoff_result = json.loads(handoff.stdout)
    assert not handoff_result['issues']
    ci_jobs = 0
    if args.require_ci:
        ci = read('block24_ci_result.json')
        path = ROOT/'audit/block24_ci_result.json'
        original = path.read_bytes()
        subprocess.run([sys.executable, 'audit/summarize_block24_ci.py', '--run-id', str(ci['run_id']),
                        '--source', args.source, '--expected-tests', '3648'], cwd=ROOT, capture_output=True, check=True)
        assert original == path.read_bytes()
        assert ci['tested_source_checkpoint'] == args.source and ci['matrix_verified'] is True
        assert ci['verified_successful_jobs'] == 6 and not ci['issues']
        ci_jobs = 6
    result = dict(baseline=BASELINE, source=args.source, source_sha256=source_hashes,
                  unchanged_irm_method_asts=len(before)-len(modified),
                  sensitivity_algorithms_unchanged_except_two_entry_guards=True,
                  gate_uplift_algorithms_unchanged_except_entry_guards=True,
                  internal_fit_pairs=64, internal_estimate_pairs=96, weighted_atte_rejections=32,
                  focused_cases=491, new_cases=127, local_correctness_passed=3648,
                  local_junit_sha256=sha(local_path), verified_ci_jobs=ci_jobs,
                  report_local_links_checked=len(local_links), owned_pytest_temp_removed=True,
                  initial_ci_and_local_3646_cases_retained=True,
                  handoff=handoff_result, sensitivity_validated=False, issues=[])
    (ROOT/'audit/block24_validation_result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
