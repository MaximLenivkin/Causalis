"""Verify B23 local source, unchanged methods and aggregate evidence; CI optional."""
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
BASELINE = '1409e95cf0cfb0cb1f9ab8541eefc25b3cbe1342'
SOURCE = 'b1adeb291870c965825c60712144d23ea4c31ce9'
CI_SOURCE = 'b1adeb291870c965825c60712144d23ea4c31ce9'
PATHS = {'README.md', 'causalis/scenarios/gate/model.py',
         'causalis/scenarios/uplift/model.py',
         'causalis/scenarios/unconfoundedness/model.py',
         'causalis/scenarios/unconfoundedness/_repeated.py',
         'causalis/scenarios/unconfoundedness/_cluster.py',
         'tests/inference/test_irm_cluster_crossfit.py'}


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
    changed_methods = {'__init__', '_cross_fit_nuisances', 'fit', 'estimate',
                       '_solve_moment_equation', '_compute_relative_effect_stats',
                       'predict_cate', '_sensitivity_element_est', 'sensitivity_analysis'}
    unchanged = []
    for name, original in before.items():
        if name not in changed_methods:
            assert ast.dump(original) == ast.dump(after[name]), name
            unchanged.append(name)
    # Sensitivity methods differ only by the explicit cluster-fit entry guard.
    for name in ('_sensitivity_element_est', 'sensitivity_analysis'):
        candidate = after[name]
        guards = [node for node in candidate.body if isinstance(node, ast.If)
                  and ast.unparse(node.test) == "self._fit_cluster_codes_ is not None"]
        assert len(guards) == 1
        expected_guard = ast.parse('''if self._fit_cluster_codes_ is not None:
    raise NotImplementedError("Cluster IRM sensitivity inference is unavailable")''').body[0]
        assert ast.dump(guards[0]) == ast.dump(expected_guard)
        candidate.body.remove(guards[0])
        assert ast.dump(before[name]) == ast.dump(candidate), name
    probe = read('block23_probe_result.json')
    assert probe['baseline'] == probe['observed_head'] == BASELINE
    assert probe['temporary_copies_removed'] is True
    assert probe['exact_iid_fit_configuration_pairs'] == 32
    assert probe['exact_iid_estimate_pairs'] == 48
    assert probe['exact_unsupported_weighted_atte_rejections'] == 16
    assert probe['baseline_feature']['status'] == 'unsupported'
    assert probe['current_feature']['status'] == 'supported'
    for name, value in probe['source_sha256'].items():
        assert digest(ROOT / name) == value
    focus = read('block23_focus_result.json')
    focused_cases = cases(ROOT / 'audit/block23_focus_test_temp/junit.xml')
    assert len(focused_cases) == focus['passed'] == 364
    assert sum(name.endswith('test_irm_cluster_crossfit') for name, _ in focused_cases) == focus['new_cases'] == 87
    assert focus['junit_sha256'] == digest(ROOT / 'audit/block23_focus_test_temp/junit.xml')
    assert focus['source_sha256'] == hashes
    local = read('block23_integration_result.json')
    selection = read('block23_integration_selection.json')
    integration_cases = cases(ROOT / 'audit/block23_integration_test_temp/junit.xml')
    assert focused_cases <= integration_cases
    assert len(integration_cases) == local['passed'] == 3521
    assert local['exit_code'] == 0
    assert local['tested_source_checkpoint'] == SOURCE
    assert selection['environment']['commit'] == SOURCE
    assert local['selected_full_suite'] is selection['selected_full_suite'] is False
    baseline_selection = read('block22_integration_selection.json')
    assert selection['excluded_modules'] == baseline_selection['excluded_modules']
    assert len(selection['excluded_modules']) == 7
    docs = read('block23_docs_result.json')
    assert docs['environment']['commit'] == SOURCE
    assert docs['exit_code'] == 0 and docs['warnings_are_errors'] is True
    assert docs['publishes_html'] is False and docs['command'][-1] == '--check'
    assert docs['log_sha256'] == digest(ROOT / 'audit/block23_docs_test_temp/build.log')
    assert docs['generator_sha256'] == digest(ROOT / 'scripts/generate_api_reference.py')
    sampling = read('block23_sampling_result.json')
    assert sampling['observed_head'] == BASELINE
    assert sampling['synthetic_samples'] == 400 and sampling['clusters_per_sample'] == 80
    assert sampling['truth'] == 0.7
    assert set(sampling['scores']) == {'ATE_rep1', 'ATE_rep3', 'ATTE_rep1', 'ATTE_rep3'}
    assert {name:value['covered'] for name,value in sampling['scores'].items()} == {
        'ATE_rep1':378, 'ATE_rep3':378, 'ATTE_rep1':381, 'ATTE_rep3':377}
    for name, value in sampling['source_sha256'].items():
        assert digest(ROOT / name) == value
    for path, name in [('causalis/scenarios/gate/model.py', '_validate_gate_inputs'),
                       ('causalis/scenarios/uplift/model.py', '_validate_fitted_irm')]:
        original = ast.parse(git('show', BASELINE + ':' + path))
        candidate = ast.parse((ROOT / path).read_text())
        a = next(n for n in original.body if isinstance(n, ast.FunctionDef) and n.name == name)
        b = next(n for n in candidate.body if isinstance(n, ast.FunctionDef) and n.name == name)
        assert isinstance(b.body[1], ast.If) and 'Cluster IRM' in ast.dump(b.body[1])
        b.body.pop(1)
        assert ast.dump(a) == ast.dump(b)
        # Every other function/class, imports and module documentation match.
        assert ast.dump(original) == ast.dump(candidate)
    support = read('block23_support_result.json')
    assert support['tested_source_checkpoint'] == SOURCE
    assert support['training_arm_support_verified'] is True
    assert len(support['rejected_before_fitting']) == 2
    assert {item['n_rep'] for item in support['rejected_before_fitting']} == {1, 3}
    assert support['pytest_cases_added'] == 0
    if options.require_ci:
        ci = read('block23_ci_result.json')
        assert ci['tested_source_checkpoint'] == CI_SOURCE and ci['matrix_verified'] is True
        assert ci['implementation_checkpoint'] == SOURCE
        changed_from_implementation = git('diff', '--name-only', SOURCE, CI_SOURCE).splitlines()
        assert all(path.startswith('audit/') for path in changed_from_implementation)
        ci_root = ROOT / f"audit/block23_ci_test_temp/run-{ci['run_id']}"
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
    report = ROOT / 'audit/BLOCK23_GROUP_CROSSFIT.md'
    links = re.findall(r'\]\(([^)]+)\)', report.read_text())
    local_links = [link.split('#')[0] for link in links if '://' not in link]
    generated_manifest = ROOT / 'audit/block23_validation_result.json'
    assert all((report.parent / link).is_file() or report.parent / link == generated_manifest
               for link in local_links)
    payload = dict(source=SOURCE, baseline=BASELINE, source_sha256=hashes,
                   unchanged_irm_method_count=len(unchanged), unchanged_irm_methods=unchanged,
                   sensitivity_methods_only_entry_guard=True, focused_cases=364, new_cases=87,
                   local_cases=3521, sensitivity_exclusions=7, docs_exit_code=0,
                   ci_verified=options.require_ci,
                   ci_source=CI_SOURCE if options.require_ci else None,
                   handoff_links=handoff['snapshot_links_checked'],
                   report_local_links=len(local_links), issues=[])
    (ROOT / 'audit/block23_validation_result.json').write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
