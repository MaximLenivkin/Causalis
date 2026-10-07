"""Validate B20 source provenance, baseline/focus and committed local/CI evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

from probe_block20 import BASELINE, PATHS, functions

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'audit'


def read(name):
    return json.loads((AUDIT/name).read_text())


def junit(path):
    tree = ET.parse(path).getroot()
    suites = tree.findall('.//testsuite')
    counts = {key:sum(int(s.attrib.get(key,0)) for s in suites)
              for key in ['tests','failures','errors','skipped']}
    counts['passed'] = counts['tests'] - sum(counts[k] for k in ['failures','errors','skipped'])
    cases = {(c.attrib['classname'],c.attrib['name']) for c in tree.iter('testcase')}
    assert len(cases) == counts['tests']
    return counts,cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--run-id', required=True)
    options = parser.parse_args()
    assert re.fullmatch('[a-f0-9]{40}', options.source)
    scope = subprocess.check_output(['git','diff','--name-only',BASELINE,options.source,'--',
                                     'causalis','tests','scripts'],cwd=ROOT,text=True).splitlines()
    assert set(scope) == set(PATHS), scope
    probe = read('block20_probe_result.json')
    assert probe['baseline'] == probe['original_head'] == BASELINE
    assert probe['exact_fit_pairs'] == 20 and probe['exact_inference_pairs'] == 36
    assert probe['input_frames_unchanged'] and probe['synthetic_in_memory_only']
    for path,digest in probe['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest, path
        committed = subprocess.check_output(['git','show',options.source+':'+path],cwd=ROOT)
        assert hashlib.sha256(committed).hexdigest() == digest, path
    for item in probe['unchanged_functions']:
        path,key = item.split(':',1)
        old = subprocess.check_output(['git','show',BASELINE+':'+path],cwd=ROOT,text=True)
        new = subprocess.check_output(['git','show',options.source+':'+path],cwd=ROOT,text=True)
        assert functions(old)[key] == functions(new)[key], item
    assert len(probe['unchanged_functions']) == 132
    collisions = read('block20_collision_result.json')
    assert collisions['source'] == options.source
    assert collisions['source_sha256'] == probe['source_sha256']['causalis/data_contracts/causaldata.py']
    assert len(collisions['checks']) == 8 and not collisions['individual_data_saved']
    assert {(c['kind'],c['n']) for c in collisions['checks']} == {(k,n) for k in ['binary','multi','iv','rct'] for n in [12,129]}
    assert all(c['rounded_fingerprints_equal'] and c['distinct_exact_values_accepted'] and c['input_unchanged'] for c in collisions['checks'])
    baseline = read('block20_baseline_result.json')
    assert baseline['baseline'] == BASELINE and baseline['isolated_baseline_import_verified']
    assert baseline['test_sha256'] == probe['source_sha256'][baseline['test_path']]
    before,new_cases = junit(AUDIT/'block20_baseline.xml')
    assert before == {key:baseline[key] for key in before}
    assert before == dict(tests=107, failures=86, errors=0, skipped=0, passed=21)
    focus,focus_cases = junit(AUDIT/'block20_focus.xml')
    assert focus == dict(tests=2106,failures=0,errors=0,skipped=0,passed=2106)
    assert new_cases <= focus_cases
    integration = read('block20_integration_result.json')
    local,local_cases = junit(AUDIT/'block20_integration_test_temp/junit.xml')
    assert local == dict(tests=3359,failures=0,errors=0,skipped=0,passed=3359)
    assert local == {k:integration[k] for k in local}
    assert integration['tested_source_checkpoint'] == options.source
    assert integration['exit_code'] == 0 and integration['scoped_suite_clean']
    assert not integration['sensitivity_validated'] and not integration['full_suite_clean']
    assert focus_cases <= local_cases
    ci = read('block20_ci_result.json')
    assert ci['tested_source_checkpoint'] == options.source
    assert ci['run_id'] == int(options.run_id)
    assert ci['matrix_verified'] and ci['verified_successful_jobs'] == 6 and not ci['issues']
    selection = read('block20_integration_selection.json')
    assert ci['excluded_modules'] == selection['excluded_modules']
    assert len(ci['excluded_modules']) == 7
    artifacts = AUDIT/f'block20_ci_test_temp/run-{options.run_id}'
    for job in ci['jobs']:
        assert job['artifact_verified'] and job['case_sets_verified'] and job['conclusion'] == 'success'
        assert job['junit'] == local
        folder = artifacts/f"correctness-py{job['python_minor']}-{job['stack']}"
        for name,digest in job['artifact_sha256'].items():
            assert hashlib.sha256((folder/name).read_bytes()).hexdigest() == digest
        assert junit(folder/'junit.xml')[1] == local_cases
    handoff = read('handoff_validation.json')
    assert handoff['snapshot_links_checked'] == 127 and not handoff['issues']
    report = (AUDIT/'BLOCK20_DATA_SNAPSHOT_CONTRACTS.md').read_text()
    links = []
    for link in re.findall(r'\]\(([^)]+)\)',report):
        if link.startswith('https://'):
            continue
        path = (AUDIT/link.split('#')[0]).resolve()
        if path.name != 'block20_validation_result.json':
            assert path.is_file(), link
        links.append(link)
    result = dict(source=options.source,baseline=BASELINE,changed_source_test_paths=scope,
                  committed_hashes_verified=len(probe['source_sha256']),
                  unchanged_executable_functions=132,baseline_counts=before,focus_counts=focus,
                  integration_counts=local,ci_jobs_verified=6,complete_case_sets_verified=True,
                  local_report_links_verified=len(links),handoff_links_verified=127,issues=[])
    (AUDIT/'block20_validation_result.json').write_text(json.dumps(result,indent=2))
    for link in links:
        assert (AUDIT/link.split('#')[0]).resolve().is_file()
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
