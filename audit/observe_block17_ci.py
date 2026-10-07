"""Observe one authorized personal-branch CI run and download final evidence."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
GH = "/Users/m.lenivkin/.local/bin/gh"
REPO = "MaximLenivkin/Causalis"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--expected-tests", required=True)
    args = parser.parse_args()
    folder = ROOT / f"audit/block17_ci_test_temp/run-{args.run_id}"
    folder.mkdir(parents=True, exist_ok=True)
    while True:
        data = json.loads(subprocess.check_output(
            [GH, "run", "view", args.run_id, "--repo", REPO, "--json",
             "headSha,url,status,conclusion,jobs"], text=True))
        assert data["headSha"] == args.source
        data["observed_at"] = datetime.now(timezone.utc).isoformat()
        (folder / "run_status.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(json.dumps({"observed_at": data["observed_at"], "status": data["status"],
                          "conclusion": data["conclusion"],
                          "jobs": [{"name": job["name"], "status": job["status"],
                                    "conclusion": job["conclusion"]} for job in data["jobs"]]}), flush=True)
        if data["status"] == "completed":
            break
        time.sleep(45)
    subprocess.run([GH, "run", "download", args.run_id, "--repo", REPO,
                    "--dir", str(folder)], check=True)
    return subprocess.run(
        [str(ROOT / ".venv/bin/python"), "audit/summarize_block17_ci.py", "--run-id", args.run_id,
         "--source", args.source, "--expected-tests", args.expected_tests], cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
