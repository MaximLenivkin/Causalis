"""Verify downloaded B06 CI artifacts against an exact GitHub run snapshot."""
import argparse
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = [
    "tests/refutation/test_multi_sensitivity_benchmark.py",
    "tests/refutation/test_sensitivity_benchmark.py",
    "tests/refutation/test_sensitivity_combination.py",
    "tests/refutation/test_sensitivity_integration_irm.py",
    "tests/refutation/test_sensitivity_protocol.py",
    "tests/refutation/test_sensitivity_rv_signed_rr.py",
    "tests/refutation/test_trim_sensitivity_ate.py",
]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--source", required=True)
    parser.add_argument("--expected-tests", required=True, type=int)
    options = parser.parse_args()
    assert options.run_id > 0 and options.expected_tests > 0
    assert re.fullmatch(r"[a-f0-9]{40}", options.source)
    temp = ROOT / f"audit/block06_ci_test_temp/run-{options.run_id}"
    snapshot = json.loads((temp / "run_status.json").read_text(encoding="utf-8-sig"))
    assert snapshot["headSha"] == options.source
    assert snapshot["url"].endswith(f"/actions/runs/{options.run_id}")
    jobs = []
    issues = []
    for job in snapshot["jobs"]:
        match = re.fullmatch(r"Python (3\.(?:10|11|12|13|14)) / (latest|legacy) \(sensitivity deferred\)", job["name"])
        assert match, job["name"]
        minor, stack = match.groups()
        artifact = temp / f"correctness-py{minor}-{stack}"
        entry = {
            "job_id": job["databaseId"], "name": job["name"],
            "python_minor": minor, "stack": stack,
            "status": job["status"], "conclusion": job["conclusion"],
            "started_at": job["startedAt"], "completed_at": job["completedAt"],
            "artifact_name": artifact.name,
            "artifact_verified": False,
        }
        if (artifact / "result.json").is_file():
            selection = json.loads((artifact / "selection.json").read_text())
            result = json.loads((artifact / "result.json").read_text())
            assert selection["environment"]["commit"] == options.source
            assert selection["environment"]["python"].startswith(minor + ".")
            assert selection["scope"] == result["scope"] == "correctness"
            assert selection["selected_full_suite"] is result["selected_full_suite"] is False
            assert selection["collect_only"] is result["collect_only"] is False
            assert selection["excluded_modules"] == EXCLUDED
            suites = ET.parse(artifact / "junit.xml").getroot().findall(".//testsuite")
            totals = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
                      for key in ("tests", "failures", "errors", "skipped")}
            assert totals["tests"] > 0
            totals["passed"] = totals["tests"] - sum(totals[key] for key in ("failures", "errors", "skipped"))
            if job["conclusion"] == "success":
                assert totals["tests"] == options.expected_tests
                assert result["exit_code"] == 0
                assert totals["failures"] == totals["errors"] == 0
            entry.update({
                "artifact_verified": True,
                "environment": selection["environment"],
                "pytest_result": result,
                "junit": totals,
            })
        elif job["conclusion"] == "success":
            issues.append(f"Missing result artifact for successful job {job['name']}")
        jobs.append(entry)
    assert len(jobs) <= 6
    if snapshot["status"] == "completed" and len(jobs) != 6:
        issues.append(f"Expected six matrix jobs, found {len(jobs)}")
    verified = [job for job in jobs if job["artifact_verified"] and job["conclusion"] == "success"]
    result = {
        "run_id": options.run_id,
        "run_url": snapshot["url"],
        "tested_source_checkpoint": options.source,
        "expected_tests_per_job": options.expected_tests,
        "expected_jobs": 6,
        "jobs_created": len(jobs),
        "snapshot_observed_at": snapshot["observed_at"],
        "run_status": snapshot["status"], "run_conclusion": snapshot["conclusion"],
        "scope": "Repository suite excluding seven explicitly deferred sensitivity modules",
        "selected_full_suite": False,
        "excluded_modules": EXCLUDED,
        "verified_successful_jobs": len(verified),
        "failed_pytest_jobs": [job["name"] for job in jobs
                               if job.get("pytest_result", {}).get("exit_code", 0) != 0],
        "matrix_verified": len(verified) == 6 and snapshot["conclusion"] == "success" and not issues,
        "jobs": jobs,
        "issues": issues,
        "prior_run": {"run_id": 37371536543,
                      "overall_conclusion": "cancelled by newer source/config push",
                      "legacy_pytest_step": "53 real IV source failures before cancellation; see block06_ci_prior_legacy_result.json"},
        "before_fix_run": {"run_id": 37372133090,
                           "evidence_file": "audit/block06_ci_before_fix_result.json",
                           "status_note": "Earlier source checkpoint; partial successes retained separately, never mixed into this matrix."},
        "external_queue_incident": "https://www.githubstatus.com/incidents/3q1yb5m7ltvb",
        "limitations": ["Linux CI; representative dependency stacks, not every cross-product.",
                        "Sensitivity and full release validation are not claimed.",
                        "Raw downloaded JUnit and environment artifacts are retained in task-owned ignored temp files and on GitHub."],
    }
    (ROOT / "audit/block06_ci_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("run_id", "snapshot_observed_at", "verified_successful_jobs", "matrix_verified", "issues")}, indent=2))
