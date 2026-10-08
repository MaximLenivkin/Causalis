"""Verify B23 CI jobs and their downloaded source/selection/JUnit evidence."""
from __future__ import annotations

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
CONFIGS = {(f"3.{minor}", "latest") for minor in range(10, 15)} | {("3.10", "legacy")}
IMPLEMENTATION = "b1adeb291870c965825c60712144d23ea4c31ce9"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--source", required=True)
    parser.add_argument("--expected-tests", required=True, type=int)
    options = parser.parse_args()
    assert re.fullmatch(r"[a-f0-9]{40}", options.source)
    subprocess = __import__('subprocess')
    changed = subprocess.check_output(
        ['git', 'diff', '--name-only', IMPLEMENTATION, options.source], cwd=ROOT, text=True).splitlines()
    assert all(path.startswith('audit/') for path in changed), changed
    temp = ROOT / f"audit/block23_ci_test_temp/run-{options.run_id}"
    snapshot = json.loads((temp / "run_status.json").read_text(encoding="utf-8-sig"))
    assert snapshot["headSha"] == options.source
    assert snapshot["url"].endswith(f"/actions/runs/{options.run_id}")
    local_selection = json.loads((ROOT/'audit/block23_integration_selection.json').read_text())
    def cases(path):
        return {(c.attrib['classname'],c.attrib['name']) for c in ET.parse(path).getroot().iter('testcase')}
    local_cases = cases(ROOT/'audit/block23_integration_test_temp/junit.xml')
    focused_cases = cases(ROOT/'audit/block23_focus_test_temp/junit.xml')
    issues, jobs, configs = [], [], set()
    for job in snapshot["jobs"]:
        match = re.fullmatch(r"Python (3\.(?:10|11|12|13|14)) / (latest|legacy) \(sensitivity deferred\)", job["name"])
        assert match, job["name"]
        minor, stack = match.groups()
        config = (minor, stack)
        assert config in CONFIGS and config not in configs
        configs.add(config)
        artifact_root = temp / f"correctness-py{minor}-{stack}"
        artifact = artifact_root / "ci-tests"
        docs = artifact_root / "docs-check"
        entry = {"job_id": job["databaseId"], "name": job["name"],
                 "python_minor": minor, "stack": stack, "status": job["status"],
                 "conclusion": job["conclusion"], "artifact_verified": False,
                 "started_at": job["startedAt"], "completed_at": job["completedAt"]}
        if (artifact / "result.json").is_file():
            selection = json.loads((artifact / "selection.json").read_text(encoding="utf-8"))
            result = json.loads((artifact / "result.json").read_text(encoding="utf-8"))
            assert selection["environment"]["commit"] == options.source
            assert selection["environment"]["python"].startswith(minor + ".")
            assert selection["scope"] == result["scope"] == "correctness"
            assert selection["selected_full_suite"] is result["selected_full_suite"] is False
            assert selection["collect_only"] is result["collect_only"] is False
            assert selection["excluded_modules"] == EXCLUDED == local_selection['excluded_modules']
            # Basetemp/JUnit output directories differ by machine; all other args must match.
            def normalized_args(args):
                return [a.split('=',1)[0] if a.startswith(('--basetemp=','--junitxml=')) else a for a in args]
            assert normalized_args(selection['pytest_args']) == normalized_args(local_selection['pytest_args'])
            assert cases(artifact/'junit.xml') == local_cases
            assert focused_cases <= cases(artifact/'junit.xml')
            suites = ET.parse(artifact / "junit.xml").getroot().findall(".//testsuite")
            totals = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
                      for key in ("tests", "failures", "errors", "skipped")}
            totals["passed"] = totals["tests"] - sum(
                totals[key] for key in ("failures", "errors", "skipped"))
            assert totals["tests"] > 0
            if job["conclusion"] == "success":
                assert totals["tests"] == totals["passed"] == options.expected_tests
                assert result["exit_code"] == 0
            docs_result = json.loads((docs / 'result.json').read_text())
            assert docs_result['environment']['commit'] == options.source
            assert docs_result['environment']['python'] == selection['environment']['python']
            assert docs_result['exit_code'] == 0
            assert docs_result['warnings_are_errors'] is True and docs_result['publishes_html'] is False
            assert docs_result['command'][-1] == '--check'
            sha256 = __import__('hashlib').sha256
            assert docs_result['log_sha256'] == sha256((docs / 'build.log').read_bytes()).hexdigest()
            generator_bytes = __import__('subprocess').check_output(
                ['git','show',options.source + ':scripts/generate_api_reference.py'],cwd=ROOT)
            assert docs_result['generator_sha256'] == sha256(generator_bytes).hexdigest()
            entry.update(standalone_docs=docs_result,
                         docs_artifact_sha256={name:sha256((docs/name).read_bytes()).hexdigest()
                                               for name in ('result.json','build.log')})
            entry.update(artifact_verified=True, environment=selection["environment"],
                         pytest_result=result, junit=totals, case_sets_verified=True,
                         artifact_sha256={name:__import__('hashlib').sha256((artifact/name).read_bytes()).hexdigest()
                             for name in ('selection.json','result.json','junit.xml')})
        elif job["conclusion"] == "success":
            issues.append("Missing artifacts for " + job["name"])
        jobs.append(entry)
    if snapshot["status"] == "completed" and configs != CONFIGS:
        issues.append("Missing matrix configurations")
    verified = [job for job in jobs if job["artifact_verified"] and job["conclusion"] == "success"]
    evidence = dict(run_id=options.run_id, run_url=snapshot["url"],
                    tested_source_checkpoint=options.source,
                    implementation_checkpoint=IMPLEMENTATION,
                    only_audit_changes_from_implementation=True,
                    expected_tests_per_job=options.expected_tests,
                    snapshot_observed_at=snapshot["observed_at"],
                    run_status=snapshot["status"], run_conclusion=snapshot["conclusion"],
                    excluded_modules=EXCLUDED, selected_full_suite=False,
                    verified_successful_jobs=len(verified),
                    matrix_verified=len(verified) == 6 and snapshot["conclusion"] == "success" and not issues,
                    jobs=jobs, issues=issues,
                    limitations=["Linux; six representative stacks, not all dependency combinations.",
                                 "Sensitivity methods, RST migration, notebook execution, hosted website and release are not validated."])
    (ROOT / "audit/block23_ci_result.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({key: evidence[key] for key in (
        "run_id", "run_status", "verified_successful_jobs", "matrix_verified", "issues")}, indent=2))
    return int(bool(issues) or not evidence["matrix_verified"])


if __name__ == "__main__":
    raise SystemExit(main())
