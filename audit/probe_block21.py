"""Compare baseline/current standalone docs using owned disposable copies.

Archive only project code. Save hashes, page names, and logs, never HTML trees.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '2db4802b13d6a312ddb5109fa5d8a9beca30bac8'


def inventory(html):
    data = (html / 'objects.inv').read_bytes().split(b'\n', 4)[4]
    # Inventory records carry names, domains, URLs and human labels; no source paths.
    return sorted(zlib.decompress(data).decode().splitlines())


def main():
    records = {}
    with tempfile.TemporaryDirectory(prefix='causalis-b21-evidence-') as temp:
        parent = Path(temp)
        for label in ('baseline', 'current'):
            repo = parent / label
            repo.mkdir()
            if label == 'baseline':
                archive = subprocess.check_output(
                    ['git', 'archive', BASELINE, 'causalis', 'scripts'], cwd=ROOT)
                with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                    tar.extractall(repo, filter='data')
                # Editable installs generate this ignored module. Match the
                # installed source tree on both sides of the comparison.
                version = ROOT / 'causalis/_version.py'
                if version.exists():
                    shutil.copy2(version, repo / 'causalis/_version.py')
            else:
                for name in ('causalis', 'scripts'):
                    shutil.copytree(ROOT / name, repo / name,
                                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            started = time.perf_counter()
            run = subprocess.run([sys.executable, 'scripts/generate_api_reference.py'],
                                 cwd=repo, capture_output=True, text=True)
            log = run.stdout + run.stderr
            (ROOT / f'audit/block21_{label}_build_checks.log').write_text(log)
            if run.returncode:
                raise RuntimeError(f'{label} build failed; see log')
            html = repo / 'notebooks/api/html'
            records[label] = {
                'exit_code': run.returncode,
                'elapsed_seconds': time.perf_counter() - started,
                'html_pages': sorted(p.relative_to(html).as_posix() for p in html.rglob('*.html')),
                'inventory': inventory(html),
                'warnings': log.count('WARNING'),
                'log_sha256': hashlib.sha256(log.encode()).hexdigest(),
            }
        # Execute the identical final regression file against the baseline code.
        repo = parent / 'baseline'
        (repo / 'tests/docs').mkdir(parents=True)
        test = ROOT / 'tests/docs/test_generate_api_reference.py'
        shutil.copy2(test, repo / 'tests/docs/test_generate_api_reference.py')
        command = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                   'tests/docs/test_generate_api_reference.py',
                   f'--junitxml={ROOT / "audit/block21_baseline_test_temp/junit.xml"}']
        run = subprocess.run(command, cwd=repo, capture_output=True, text=True)
        (ROOT / 'audit/block21_baseline_tests.log').write_text(run.stdout + run.stderr)
        records['regressions'] = {'baseline_exit_code': run.returncode,
                                 'test_sha256': hashlib.sha256(test.read_bytes()).hexdigest()}
    records['baseline_commit'] = BASELINE
    version = ROOT / 'causalis/_version.py'
    records['matched_generated_version_sha256'] = (
        hashlib.sha256(version.read_bytes()).hexdigest() if version.exists() else None)
    records['observed_head'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'],cwd=ROOT,text=True).strip()
    records['same_html_page_set'] = records['baseline']['html_pages'] == records['current']['html_pages']
    records['same_inventory'] = records['baseline']['inventory'] == records['current']['inventory']
    records['temporary_copies_removed'] = True
    (ROOT / 'audit/block21_probe_result.json').write_text(json.dumps(records, indent=2)+'\n')
    print({key:value for key,value in records.items() if key not in ('baseline','current')})
    assert records['same_html_page_set'] and records['same_inventory']
    assert records['regressions']['baseline_exit_code'] != 0


if __name__ == '__main__':
    main()
