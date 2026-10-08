"""Verify B22 local source, unchanged methods and aggregate evidence; CI optional."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '357e16e8d1faf37e221b92b7e1f83ee5fba3c2dc'
SOURCE = 'ede6deda2eb82c518ed3d7f5b48780d39cdfe5f0'
CI_SOURCE = 'd99ea8ffea853e48f750ca642a3918769cc38004'
PATHS = {'README.md', 'causalis/data_contracts/__init__.py',
         'causalis/data_contracts/repeated_causal_estimate.py',
         'causalis/scenarios/unconfoundedness/model.py',
         'causalis/scenarios/unconfoundedness/_repeated.py',
         'tests/inference/test_irm_repeated_crossfit.py'}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((ROOT / 'audit' / name).read_text())


def cases(path):
    document = ET.parse(path).getroot()
    assert not any(list(document.iter(key)) for key in ('failure', 'error', 'skipped'))
    return {(case.attrib['classname'], case.attrib['name']) for case in document.iter('testcase')}


def functions(source):
    module = ast.parse(source)
    klass = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == 'IRM')
    return {node.name: node for node in klass.body if isinstance(node, ast.FunctionDef)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-ci', action='store_true')
    options = parser.parse_args()
    changed = set(git('diff', '--name-only', BASELINE, SOURCE).splitlines())
    assert {path for path in changed if not path.startswith('audit/')} == PATHS
    assert not git('diff', SOURCE, '--name-only', '--', 'causalis', 'tests', 'scripts', 'README.md')
    hashes = {}
    for name in sorted(PATHS):
        content = subprocess.check_output(['git', 'show', SOURCE + ':' + name], cwd=ROOT)
        assert content == (ROOT / name).read_bytes()
        hashes[name] = digest(ROOT / name)
    path = 'causalis/scenarios/unconfoundedness/model.py'
    before = functions(git('show', BASELINE + ':' + path))
    after = functions((ROOT / path).read_text())
    changed_methods = {'__init__', '_validate_fit_config', 'fit', 'estimate',
                       'diagnostics_', 'orth_signal', 'predict_cate', '__repr__',
                       '_sensitivity_element_est', 'sensitivity_analysis'}
    unchanged = []
    for name, original in before.items():
        if name not in changed_methods:
            assert ast.dump(original) == ast.dump(after[name]), name
            unchanged.append(name)
    # Sensitivity methods differ only by the explicit repeated-fit entry guard.
    for name in ('_sensitivity_element_est', 'sensitivity_analysis'):
        candidate = after[name]
        guards = [node for node in candidate.body if isinstance(node, ast.If)
                  and ast.unparse(node.test) == "hasattr(self, '_fit_repetitions_')"]
        assert len(guards) == 1
        expected_guard = ast.parse('''if hasattr(self, "_fit_repetitions_"):
    raise NotImplementedError("Repeated IRM sensitivity aggregation is unavailable")''').body[0]
        assert ast.dump(guards[0]) == ast.dump(expected_guard)
        candidate.body.remove(guards[0])
        assert ast.dump(before[name]) == ast.dump(candidate), name
    probe = read('block22_probe_result.json')
    assert probe['baseline'] == probe['observed_head'] == BASELINE
    assert probe['temporary_copies_removed'] is True
    assert probe['exact_single_partition_fit_pairs'] == 16
    assert probe['exact_single_partition_estimate_pairs'] == 24
    assert probe['exact_unsupported_weighted_atte_rejections'] == 8
    assert probe['baseline_feature']['status'] == 'unsupported'
    assert probe['current_feature']['status'] == 'supported'
    for name, value in probe['source_sha256'].items():
        assert hashes[name] == value
    focus = read('block22_focus_result.json')
    focused_cases = cases(ROOT / 'audit/block22_focus_test_temp/junit.xml')
    assert len(focused_cases) == focus['passed'] == 221
    assert sum(name.endswith('test_irm_repeated_crossfit') for name, _ in focused_cases) == focus['new_cases'] == 67
    assert focus['junit_sha256'] == digest(ROOT / 'audit/block22_focus_test_temp/junit.xml')
    assert focus['test_sha256'] == hashes['tests/inference/test_irm_repeated_crossfit.py']
    local = read('block22_integration_result.json')
    selection = read('block22_integration_selection.json')
    integration_cases = cases(ROOT / 'audit/block22_integration_test_temp/junit.xml')
    assert focused_cases <= integration_cases
    assert len(integration_cases) == local['passed'] == 3434
    assert local['exit_code'] == 0
    assert local['tested_source_checkpoint'] == SOURCE
    assert selection['environment']['commit'] == SOURCE
    assert local['selected_full_suite'] is selection['selected_full_suite'] is False
    baseline_selection = read('block21_integration_selection.json')
    assert selection['excluded_modules'] == baseline_selection['excluded_modules']
    assert len(selection['excluded_modules']) == 7
    docs = read('block22_docs_result.json')
    assert docs['environment']['commit'] == SOURCE
    assert docs['exit_code'] == 0 and docs['warnings_are_errors'] is True
    assert docs['publishes_html'] is False and docs['command'][-1] == '--check'
    assert docs['log_sha256'] == digest(ROOT / 'audit/block22_docs_test_temp/build.log')
    assert docs['generator_sha256'] == digest(ROOT / 'scripts/generate_api_reference.py')
    sampling = read('block22_sampling_result.json')
    assert sampling['synthetic_samples'] == 200 and sampling['rows_per_sample'] == 600
    assert sampling['truth'] == 0.7 and sampling['split_repetitions'] == 3
    assert set(sampling['scores']) == {'ATE', 'ATTE'}
    assert all(score['covered'] == 193 and score['coverage_95'] == 0.965
               for score in sampling['scores'].values())
    if options.require_ci:
        ci = read('block22_ci_result.json')
        assert ci['tested_source_checkpoint'] == CI_SOURCE and ci['matrix_verified'] is True
        assert ci['implementation_checkpoint'] == SOURCE
        changed_from_implementation = git('diff', '--name-only', SOURCE, CI_SOURCE).splitlines()
        assert all(path.startswith('audit/') for path in changed_from_implementation)
        ci_root = ROOT / f"audit/block22_ci_test_temp/run-{ci['run_id']}"
        snapshot = json.loads((ci_root / 'run_status.json').read_text())
        assert snapshot['headSha'] == CI_SOURCE
        assert snapshot['status'] == 'completed' and snapshot['conclusion'] == 'success'
        assert ci['verified_successful_jobs'] == 6 and ci['issues'] == []
        configs = set()
        for job in ci['jobs']:
            config = (job['python_minor'], job['stack'])
            assert config not in configs
            configs.add(config)
            artifact = ci_root / f"correctness-py{config[0]}-{config[1]}"
            for name, value in job['artifact_sha256'].items():
                assert digest(artifact / 'ci-tests' / name) == value
            for name, value in job['docs_artifact_sha256'].items():
                assert digest(artifact / 'docs-check' / name) == value
            assert cases(artifact / 'ci-tests/junit.xml') == integration_cases
            remote_selection = json.loads((artifact / 'ci-tests/selection.json').read_text())
            assert remote_selection['environment']['commit'] == CI_SOURCE
            assert remote_selection['excluded_modules'] == selection['excluded_modules']
            remote_docs = json.loads((artifact / 'docs-check/result.json').read_text())
            assert remote_docs['environment']['commit'] == CI_SOURCE
            assert remote_docs['exit_code'] == 0
            assert remote_docs['log_sha256'] == digest(artifact / 'docs-check/build.log')
            assert remote_docs['generator_sha256'] == docs['generator_sha256']
        assert configs == {(f'3.{minor}', 'latest') for minor in range(10, 15)} | {('3.10', 'legacy')}
    handoff = read('handoff_validation.json')
    assert handoff['issues'] == []
    report = ROOT / 'audit/BLOCK22_REPEATED_CROSSFIT.md'
    links = re.findall(r'\]\(([^)]+)\)', report.read_text())
    local_links = [link.split('#')[0] for link in links if '://' not in link]
    generated_manifest = ROOT / 'audit/block22_validation_result.json'
    assert all((report.parent / link).is_file() or report.parent / link == generated_manifest
               for link in local_links)
    payload = dict(source=SOURCE, baseline=BASELINE, source_sha256=hashes,
                   unchanged_irm_method_count=len(unchanged), unchanged_irm_methods=unchanged,
                   sensitivity_methods_only_entry_guard=True, focused_cases=221, new_cases=67,
                   local_cases=3434, sensitivity_exclusions=7, docs_exit_code=0,
                   ci_verified=options.require_ci,
                   ci_source=CI_SOURCE if options.require_ci else None,
                   handoff_links=handoff['snapshot_links_checked'],
                   report_local_links=len(local_links), issues=[])
    (ROOT / 'audit/block22_validation_result.json').write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
