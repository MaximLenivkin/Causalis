"""Run the final B19 public regressions in an owned exact-baseline worktree."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "52cd6e2fbb1934edaa1191856f70424858a59f6f"
TEST = "tests/inference/test_extreme_score_arithmetic.py"


def main():
    env = os.environ.copy()
    env.update(MPLBACKEND="Agg", MPLCONFIGDIR=str(ROOT / ".venv/matplotlib"),
               SKIP_DOCS_BUILD="true", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               MKL_NUM_THREADS="1", PYTEST_ADDOPTS="")
    with tempfile.TemporaryDirectory(prefix="causalis-b19-", dir="/private/tmp") as temp:
        checkout = Path(temp) / "baseline"
        subprocess.run(["git", "worktree", "add", "--detach", str(checkout), BASELINE],
                       cwd=ROOT, check=True, capture_output=True)
        try:
            shutil.copyfile(ROOT / TEST, checkout / TEST)
            env["PYTHONPATH"] = str(checkout)
            code = ("import pathlib, causalis, pytest; "
                    "assert pathlib.Path(causalis.__file__).resolve().is_relative_to(pathlib.Path.cwd()); "
                    "raise SystemExit(pytest.main())")
            command = [str(ROOT / ".venv/bin/python"), "-c", code, TEST,
                       "--junitxml=" + str(ROOT / "audit/block19_baseline.xml")]
            with (ROOT / "audit/block19_baseline_tests.log").open("w") as log:
                status = subprocess.run(command, cwd=checkout, env=env, stdout=log,
                                        stderr=subprocess.STDOUT).returncode
            suites = ET.parse(ROOT / "audit/block19_baseline.xml").getroot().findall(".//testsuite")
            counts = {k: sum(int(s.attrib.get(k, 0)) for s in suites)
                      for k in ("tests", "failures", "errors", "skipped")}
            counts["passed"] = counts["tests"] - sum(counts[k] for k in ("failures", "errors", "skipped"))
            result = dict(baseline=BASELINE, observed_at=datetime.now(timezone.utc).isoformat(),
                          interpreter=str(ROOT / ".venv/bin/python"), test_path=TEST,
                          test_sha256=hashlib.sha256((ROOT / TEST).read_bytes()).hexdigest(),
                          isolated_baseline_import_verified=True, exit_code=status, **counts)
            (ROOT / "audit/block19_baseline_result.json").write_text(json.dumps(result, indent=2))
            print(json.dumps(result, indent=2))
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(checkout)], cwd=ROOT, check=True)
    return 0 if status == 1 and counts["failures"] > 0 and counts["errors"] == counts["skipped"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
