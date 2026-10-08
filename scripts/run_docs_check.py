"""Run the standalone strict Sphinx check and preserve CI evidence.

This gate is independent of pytest and ignores SKIP_DOCS_BUILD. It checks
rendering/build compatibility, not the scientific correctness of docstrings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from run_tests import ROOT, environment_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('build/docs-check'))
    options = parser.parse_args(argv)
    output = options.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(ROOT / 'scripts/generate_api_reference.py'), '--check']
    environment = environment_manifest()
    started = time.perf_counter()
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    log = run.stdout + run.stderr
    (output / 'build.log').write_text(log, encoding='utf-8')
    result = {
        'command': command,
        'environment': environment,
        'warnings_are_errors': True,
        'publishes_html': False,
        'exit_code': run.returncode,
        'elapsed_seconds': time.perf_counter() - started,
        'log_sha256': hashlib.sha256(log.encode('utf-8')).hexdigest(),
        'generator_sha256': hashlib.sha256(
            (ROOT / 'scripts/generate_api_reference.py').read_bytes()
        ).hexdigest(),
    }
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(log, end='')
    print(json.dumps(result, indent=2))
    return run.returncode


if __name__ == '__main__':
    raise SystemExit(main())
