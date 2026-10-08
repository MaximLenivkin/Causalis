"""Verify exact B21 source, local/CI cases, docs and compatibility evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = '1780d8c715a15182137d51313e502280d6982dd9'
BASELINE = '2db4802b13d6a312ddb5109fa5d8a9beca30bac8'
PATHS = {
    '.github/workflows/ci.yml', '.github/workflows/release.yml', 'README.md',
    'scripts/generate_api_reference.py', 'scripts/run_docs_check.py',
    'tests/docs/test_generate_api_reference.py',
}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def read(name):
    return json.loads((ROOT / 'audit' / name).read_text())


def cases(path):
    return {(c.attrib['classname'].rsplit('.', 1)[-1], c.attrib['name'])
            for c in ET.parse(path).getroot().iter('testcase')}


def totals(path):
    suites = list(ET.parse(path).getroot().iter('testsuite'))
    return {key:sum(int(s.attrib.get(key,0)) for s in suites)
            for key in ('tests','failures','errors','skipped')}


def main():
    changed = set(git('diff','--name-only',BASELINE,SOURCE).splitlines())
    assert {p for p in changed if not p.startswith('audit/')} == PATHS
    assert not git('diff',BASELINE,SOURCE,'--name-only','--','causalis')
    assert not git('diff',SOURCE,'--name-only','--', *sorted(PATHS))
    hashes = {}
    for path in PATHS:
        committed = subprocess.check_output(['git','show',SOURCE+':'+path],cwd=ROOT)
        assert (ROOT/path).read_bytes() == committed
        hashes[path] = hashlib.sha256(committed).hexdigest()
    probe = read('block21_probe_result.json')
    assert probe['baseline_commit'] == probe['observed_head'] == BASELINE
    assert probe['same_html_page_set'] and probe['same_inventory']
    assert probe['baseline']['html_pages'] == probe['current']['html_pages']
    assert len(probe['current']['html_pages']) == 144
    assert probe['baseline']['inventory'] == probe['current']['inventory']
    assert len(probe['current']['inventory']) == 1296
    assert probe['regressions']['test_sha256'] == hashes['tests/docs/test_generate_api_reference.py']
    for label in ('baseline','current'):
        log = ROOT / f'audit/block21_{label}_build_checks.log'
        assert hashlib.sha256(log.read_bytes()).hexdigest() == probe[label]['log_sha256']
        assert probe[label]['warnings'] == probe[label]['exit_code'] == 0
    base = ROOT/'audit/block21_baseline_test_temp/junit.xml'
    focus = ROOT/'audit/block21_focus_test_temp/junit.xml'
    integration = ROOT/'audit/block21_integration_test_temp/junit.xml'
    assert totals(base) == dict(tests=8,failures=7,errors=0,skipped=0)
    assert totals(focus) == dict(tests=11,failures=0,errors=0,skipped=0)
    assert totals(integration) == dict(tests=3367,failures=0,errors=0,skipped=0)
    assert cases(base) <= cases(focus) <= cases(integration)
    selection = read('block21_integration_selection.json')
    assert selection['environment']['commit'] == selection['tested_source_checkpoint'] == SOURCE
    assert selection['environment']['docs_build_environment'] == 'false'
    assert len(selection['excluded_modules']) == 7
    local = read('block21_integration_result.json')
    assert local['tested_source_checkpoint'] == SOURCE and local['exit_code'] == 0
    docs = read('block21_docs_result.json')
    assert docs['environment']['commit'] == SOURCE and docs['exit_code'] == 0
    assert docs['warnings_are_errors'] and not docs['publishes_html']
    assert docs['command'][-1] == '--check'
    assert docs['generator_sha256'] == hashes['scripts/generate_api_reference.py']
    assert docs['log_sha256'] == hashlib.sha256((ROOT/'audit/block21_docs_test_temp/build.log').read_bytes()).hexdigest()
    ci = read('block21_ci_result.json')
    assert ci['tested_source_checkpoint'] == SOURCE and ci['matrix_verified']
    assert ci['verified_successful_jobs'] == 6 and not ci['issues']
    temp = ROOT / f"audit/block21_ci_test_temp/run-{ci['run_id']}"
    for job in ci['jobs']:
        folder = temp / f"correctness-py{job['python_minor']}-{job['stack']}"
        assert cases(folder/'ci-tests/junit.xml') == cases(integration)
        for subdir,key in (('ci-tests','artifact_sha256'),('docs-check','docs_artifact_sha256')):
            for name,digest in job[key].items():
                assert hashlib.sha256((folder/subdir/name).read_bytes()).hexdigest() == digest
    handoff = read('handoff_validation.json')
    assert handoff['snapshot_links_checked'] == 132 and not handoff['issues']
    links = re.findall(r'\]\(([^)]+)\)', (ROOT/'audit/BLOCK21_SPHINX_GATE.md').read_text())
    local_links = [link for link in links if not link.startswith(('https://','http://','#'))]
    for link in local_links:
        assert (ROOT/'audit'/link.split('#',1)[0]).is_file(), link
    result = dict(source=SOURCE,baseline=BASELINE,source_paths=sorted(PATHS),
                  library_source_changes=0,committed_hashes=hashes,
                  baseline_cases=8,baseline_failed=7,focus_passed=11,
                  local_passed=3367,verified_ci_jobs=6,
                  same_html_pages=144,same_inventory_records=1296,
                  handoff_links=132,report_local_links=len(local_links),
                  standalone_local_and_ci_verified=True,issues=[])
    (ROOT/'audit/block21_validation_result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
