"""Run B10's recorded non-sensitivity integration on committed source."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
OUTPUT = AUDIT / "block10_integration_test_temp"


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()


def main() -> int:
    source = git("rev-parse", "HEAD")
    changed = git("diff", "HEAD", "--name-only", "--", "causalis", "tests", "scripts")
    untracked = git("ls-files", "--others", "--exclude-standard", "--", "causalis", "tests", "scripts")
    if changed or untracked:
        raise RuntimeError("Commit source/tests before integration: " + changed + untracked)
    env = os.environ.copy()
    env.update(MPLBACKEND="Agg", MPLCONFIGDIR=str(ROOT / ".venv/matplotlib"),
               SKIP_DOCS_BUILD="true", PYTEST_ADDOPTS="",
               PYTHONIOENCODING="utf-8",
               OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    command = [sys.executable, "scripts/run_tests.py", "--scope", "correctness",
               "--output-dir", str(OUTPUT)]
    log_path = AUDIT / "block10_integration_tests.log"
    print(f"Testing committed source {source}; log: {log_path}", flush=True)
    with log_path.open("w", encoding="utf-8") as log:
        status = subprocess.run(command, cwd=ROOT, env=env, stdout=log,
                                stderr=subprocess.STDOUT, check=False).returncode
    for name in ("selection", "result"):
        payload = json.loads((OUTPUT / f"{name}.json").read_text(encoding="utf-8"))
        payload.update(tested_source_checkpoint=source, sensitivity_validated=False)
        if name == "result":
            suites = ET.parse(OUTPUT / "junit.xml").getroot().findall(".//testsuite")
            totals = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
                      for key in ("tests", "failures", "errors", "skipped")}
            payload.update(totals)
            payload["passed"] = totals["tests"] - sum(
                totals[key] for key in ("failures", "errors", "skipped"))
            lines = log_path.read_text(encoding="utf-8").splitlines()
            summary = next((line for line in reversed(lines)
                            if " in " in line and re.search(r"\d+ (passed|failed)", line)), None)
            warning_match = re.search(r"(\d+) warnings", summary) if summary else None
            time_match = re.search(r" in ([\d.]+)s", summary) if summary else None
            payload["warnings"] = int(warning_match[1]) if warning_match else (0 if summary else None)
            payload["pytest_elapsed_seconds"] = float(time_match[1]) if time_match else None
            payload["scoped_suite_clean"] = status == 0 and totals["failures"] == totals["errors"] == 0
            payload["full_suite_clean"] = False
            print(json.dumps(payload, indent=2), flush=True)
        (AUDIT / f"block10_integration_{name}.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8")
    if git("diff", source, "--name-only", "--", "causalis", "tests", "scripts"):
        raise RuntimeError("Source/tests changed during integration.")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
