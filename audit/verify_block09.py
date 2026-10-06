"""Check B09's bounded source scope, exact-source evidence and portable links."""
from __future__ import annotations

import ast
from collections import Counter
import hashlib
from itertools import product
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from summarize_block09_ci import CONFIGS, EXCLUDED

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
START = "74145665127f8fa5a0bf038d769697ab880854b8"
SOURCE = "1e2b544f7f91a57ad3e049572915a4b3891b084a"
LIBRARY = {
    "causalis/dgp/multicausaldata/base.py",
    "causalis/dgp/multicausaldata/functional.py",
}
TESTS = {"tests/data/test_multicausal_namespace_contract.py"}
PREVIOUS_CASES = 1916
NEW_CASES = 123
LOCAL_BASELINE_FAILURE = (
    "tests/scenarios/did/refutation/test_did_post_inference_diagnostics.py"
    "::test_post_inference_report_accepts_panel_and_estimate"
)


def git(*args):
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()


def read_json(name):
    return json.loads((AUDIT / name).read_text(encoding="utf-8"))


def blob_sha256(revision, path):
    content = subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)
    return hashlib.sha256(content).hexdigest()


def junit(path):
    suites = ET.parse(path).getroot().findall(".//testsuite")
    cases = [case for suite in suites for case in suite.findall("testcase")]
    totals = {key: sum(int(suite.attrib.get(key, 0)) for suite in suites)
              for key in ("tests", "failures", "errors", "skipped")}
    totals["passed"] = totals["tests"] - sum(
        totals[key] for key in ("failures", "errors", "skipped")
    )
    return cases, totals


def nodeid(case):
    return case.attrib.get("classname", "").replace(".", "/") + ".py::" + case.attrib.get("name", "")


def main():
    result = read_json("block09_integration_result.json")
    selection = read_json("block09_integration_selection.json")
    ci = read_json("block09_ci_result.json")
    reference = read_json("block09_finite_reference_result.json")
    untracked = set(git("ls-files", "--others", "--exclude-standard").splitlines())
    paths = set(git("diff", START, "--name-only").splitlines()) | untracked
    added = set(git("diff", START, "--diff-filter=A", "--name-only").splitlines()) | untracked
    issues = []

    def check(condition, message):
        if not condition:
            issues.append(message)

    source = result["tested_source_checkpoint"]
    check(bool(re.fullmatch(r"[a-f0-9]{40}", source)), "Invalid tested source SHA")
    check(source == SOURCE, "Unexpected B09 tested source SHA")
    check(not git("diff", source, "--name-only", "--", "causalis", "tests", "scripts"),
          "Source drift after integration")
    check(not git("ls-files", "--others", "--exclude-standard", "--", "causalis", "tests", "scripts"),
          "Untracked source/tests")
    check({p for p in paths if p.startswith("causalis/")} == LIBRARY,
          "Unexpected library paths")
    check({p for p in paths if p.startswith("tests/")} == TESTS,
          "Unexpected test paths")
    check(not any(p not in LIBRARY | TESTS and not p.startswith("audit/") for p in paths),
          "Unexpected changes outside the bounded source/tests/audit paths")
    check(not any("sensitivity" in p.lower() for p in paths),
          "Deferred sensitivity paths changed")

    check(selection["excluded_modules"] == EXCLUDED, "Wrong exclusions")
    check(selection["tested_source_checkpoint"] == selection["environment"]["commit"] == source,
          "Local provenance mismatch")
    check(selection["scope"] == result["scope"] == "correctness"
          and selection["selected_full_suite"] is result["selected_full_suite"] is False
          and selection["collect_only"] is result["collect_only"] is False,
          "Incorrect local suite selection")
    check(result["scoped_suite_clean"] is False
          and result["full_suite_clean"] is False
          and result["sensitivity_validated"] is False
          and selection["sensitivity_validated"] is False
          and result["exit_code"] == 1,
          "Incorrect scope/result claim")
    cases, totals = junit(AUDIT / "block09_integration_test_temp/junit.xml")
    check(len(cases) == totals["tests"] == result["tests"] == PREVIOUS_CASES + NEW_CASES
          and totals["passed"] == result["passed"] == 2038,
          "Local JUnit count mismatch")
    failures = [case for case in cases if case.find("failure") is not None]
    check(result["failures"] == totals["failures"] == len(failures) == 1
          and {nodeid(case) for case in failures} == {LOCAL_BASELINE_FAILURE},
          "Unexpected local failure(s)")
    check(all(result[key] == totals[key] == 0 for key in ("errors", "skipped"))
          and not any(case.find(tag) is not None for case in cases for tag in ("error", "skipped")),
          "Local errors/skips")
    new_cases = [case for case in cases
                 if any(Path(p).stem in case.attrib.get("classname", "") for p in TESTS)]
    check(len(new_cases) == NEW_CASES and result["tests"] == PREVIOUS_CASES + len(new_cases),
          "Previous/new case total mismatch")
    check(not any(case.find(tag) is not None for case in new_cases
                  for tag in ("failure", "error", "skipped")),
          "New namespace tests did not all pass")
    summary = re.search(
        r"^(\d+) failed, (\d+) passed, (\d+) warnings in ([\d.]+)s",
        (AUDIT / "block09_integration_tests.log").read_text(encoding="utf-8"), re.MULTILINE,
    )
    check(summary is not None and int(summary[1]) == result["failures"]
          and int(summary[2]) == result["passed"]
          and int(summary[3]) == result["warnings"] == 80
          and float(summary[4]) == result["pytest_elapsed_seconds"] == 117.46,
          "Local raw pytest summary/result mismatch")

    # The local failure stays a failure. Acceptance requires an exact-baseline
    # reproduction, unchanged called source, and retained matching raw JUnit.
    did_baseline = read_json("block09_did_baseline_probe.json")
    did_current = read_json("block09_did_current_probe.json")
    fixture = LOCAL_BASELINE_FAILURE.split("::", 1)[0]
    fixture_hash = blob_sha256(START, fixture)
    check(hashlib.sha256((ROOT / fixture).read_bytes()).hexdigest() == fixture_hash,
          "The local failing DiD fixture changed from baseline")
    for mode, probe in (("baseline", did_baseline), ("current", did_current)):
        check(probe["mode"] == mode and probe["baseline_sha"] == START
              and probe["current_head"] == source and probe["fixture"] == fixture
              and probe["fixture_sha256"] == fixture_hash
              and probe["fixture_unchanged_from_baseline"] is True,
              f"DiD {mode} probe provenance mismatch")
        check(set(probe["changed_package_paths"]) == LIBRARY
              and probe["called_package_paths_unchanged_from_baseline"] is True
              and probe["changed_dgp_paths_called"] == []
              and probe["individual_rows_saved"] is False,
              f"DiD {mode} probe source closure mismatch")
        called = probe["called_package_paths_sha256"]
        check(bool(called) and not set(called) & LIBRARY,
              f"DiD {mode} probe unexpectedly called changed DGP source")
        for path, digest in called.items():
            check(digest == blob_sha256(START, path)
                  == hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
                  f"DiD {mode} called source differs from baseline: {path}")
        check(probe["overall_flag"] == "YELLOW",
              f"DiD {mode} probe did not reproduce the observed flag")
    check(all(did_baseline[key] == did_current[key] for key in (
        "dependencies", "called_package_paths_sha256", "report_rows",
        "cell_aggregate_rows", "simple_aggregate",
    )), "DiD baseline/current probe results differ")
    did_summary = read_json("block09_did_probe_result.json")
    check(did_summary["nodeid"] == LOCAL_BASELINE_FAILURE
          and did_summary["baseline_sha"] == START and did_summary["current_sha"] == source
          and did_summary["fixture_unchanged_from_baseline"] is True
          and did_summary["fixture_sha256"] == fixture_hash
          and did_summary["called_package_paths_unchanged_from_baseline"] is True
          and did_summary["called_package_paths_count"] == len(did_current["called_package_paths_sha256"])
          and did_summary["changed_dgp_paths_called"] == []
          and did_summary["reports_equal"] is True
          and did_summary["cell_aggregate_rows_equal"] is True
          and did_summary["overall_flag"] == "YELLOW",
          "DiD reproduction summary provenance/result mismatch")
    messages = [failures[0].find("failure").attrib.get("message") if len(failures) == 1 else None]
    for mode, revision in (("baseline", START), ("current", source)):
        evidence = did_summary[mode]
        expected_junit = f"audit/block09_did_{mode}_case.xml"
        expected_log = f"audit/block09_did_{mode}_case.log"
        check(evidence["source_sha"] == revision and evidence["exit_code"] == 1
              and evidence["junit_relative_path"] == expected_junit
              and evidence["log_relative_path"] == expected_log,
              f"DiD {mode} single-case provenance mismatch")
        reproduced, reproduced_totals = junit(ROOT / expected_junit)
        expected_totals = {"tests": 1, "failures": 1, "errors": 0, "skipped": 0, "passed": 0}
        check(reproduced_totals == expected_totals
              and all(evidence[key] == value for key, value in expected_totals.items())
              and len(reproduced) == 1
              and {nodeid(case) for case in reproduced} == {LOCAL_BASELINE_FAILURE}
              and all(case.find("failure") is not None and case.find("error") is None
                      and case.find("skipped") is None for case in reproduced),
              f"DiD {mode} single-case raw JUnit mismatch")
        raw_message = reproduced[0].find("failure").attrib.get("message") if (
            len(reproduced) == 1 and reproduced[0].find("failure") is not None
        ) else None
        messages.append(raw_message)
        check(raw_message == evidence["failure_message"],
              f"DiD {mode} failure message differs from retained raw JUnit")
        check(re.search(r"^1 failed(?:, \d+ warnings)? in [\d.]+s",
                        (ROOT / expected_log).read_text(encoding="utf-8"), re.MULTILINE) is not None,
              f"DiD {mode} raw single-case log mismatch")
    check(messages[0] is not None and messages[0].startswith(
        "AssertionError: assert 'YELLOW' == 'GREEN'"
    ) and len(set(messages)) == 1, "DiD integration/baseline/current failures differ")

    check(ci["matrix_verified"] is True
          and ci["verified_successful_jobs"] == 6 and not ci["issues"],
          "CI matrix not verified")
    check(ci["tested_source_checkpoint"] == source, "CI/local source mismatch")
    check(ci["expected_tests_per_job"] == result["tests"], "CI/local test count mismatch")
    check(ci["excluded_modules"] == EXCLUDED and ci["selected_full_suite"] is False,
          "Incorrect CI suite selection")
    check(ci["run_status"] == "completed" and ci["run_conclusion"] == "success",
          "CI run is not successfully completed")
    jobs = ci["jobs"]
    check(len(jobs) == 6
          and {(job["python_minor"], job["stack"]) for job in jobs} == CONFIGS,
          "Wrong CI matrix configurations")
    check(all(job["status"] == "completed" and job["conclusion"] == "success"
              and job["artifact_verified"] is True
              and job["environment"]["commit"] == source
              and job["junit"]["tests"] == job["junit"]["passed"] == result["tests"]
              and all(job["junit"][key] == 0 for key in ("failures", "errors", "skipped"))
              for job in jobs),
          "CI job evidence mismatch")

    rows = reference["configurations"]
    check(reference["baseline"] == START and reference["tested_source_checkpoint"] == source
          and reference["verified"] == len(rows) == 128 and not reference["issues"],
          "Finite reference provenance/count mismatch")
    keys = [(row["family"], row["include_oracle"], row["custom_callbacks"],
             row["schema"], row["generation"]) for row in rows]
    expected = set(product(
        ("continuous", "binary", "poisson", "gamma"), (False, True), (False, True),
        ("default", "categorical", "copula", "custom_sampler"), (1, 2),
    ))
    counts = Counter(keys)
    check(set(counts) == expected and all(count == 1 for count in counts.values()),
          "Finite reference configuration/generation coverage mismatch")
    check(all(row["schema_equal"] is True and row["values_exact"] is True
              and row["next_rng_draws_exact"] is True for row in rows),
          "Finite reference mismatch")

    python_paths = sorted(p for p in paths if p.endswith(".py"))
    for path in python_paths:
        try:
            ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=path)
        except (OSError, SyntaxError) as error:
            issues.append(f"{path}: {error}")

    # Check only Markdown files new or changed in B09. Historical Windows links
    # in existing audit notes are provenance, not paths on this computer.
    markdown_paths = sorted(p for p in paths if p.startswith("audit/") and p.endswith(".md"))
    links, ignored_historical_links = 0, 0
    for path in markdown_paths:
        text = (ROOT / path).read_text(encoding="utf-8")
        for raw_target in re.findall(r"\]\(([^)]+)\)", text):
            target = raw_target.strip()
            if target.startswith("<"):
                target = target[1:].split(">", 1)[0]
            else:
                target = target.split(maxsplit=1)[0]
            if re.match(r"^[A-Za-z]:[/\\]", target) or target.startswith("/"):
                if path in added:
                    issues.append(f"Nonportable local link in {path}: {target}")
                else:
                    ignored_historical_links += 1
                continue
            parsed = urlsplit(target)
            if parsed.scheme or not parsed.path:
                continue
            relative = re.sub(r":\d+$", "", unquote(parsed.path))
            resolved = (ROOT / path).parent.joinpath(relative).resolve()
            links += 1
            check(resolved.is_relative_to(ROOT), f"Local link escapes repository in {path}: {target}")
            check(resolved.exists(), f"Missing local link in {path}: {target}")

    payload = {
        "source_checkpoint": source,
        "source_baseline": START,
        "previous_cases": PREVIOUS_CASES,
        "new_cases": len(new_cases),
        "local_tests": result["tests"],
        "local_passed": result["passed"],
        "local_warnings": result["warnings"],
        "local_pytest_elapsed_seconds": result["pytest_elapsed_seconds"],
        "local_scoped_suite_clean": result["scoped_suite_clean"],
        "local_baseline_failures": result["failures"],
        "local_baseline_failure_node": LOCAL_BASELINE_FAILURE,
        "baseline_failure_proof": "block09_did_probe_result.json",
        "ci_verified_jobs": ci["verified_successful_jobs"],
        "library_paths": sorted(LIBRARY),
        "test_paths": sorted(TESTS),
        "python_files_checked": len(python_paths),
        "markdown_files_checked": markdown_paths,
        "local_links_checked": links,
        "ignored_historical_machine_links": ignored_historical_links,
        "finite_reference_configurations": len({key[:-1] for key in keys}),
        "finite_reference_generation_records": len(rows),
        "sensitivity_paths": [],
        "issues": issues,
    }
    (AUDIT / "block09_validation_checks.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2))
    return bool(issues)


if __name__ == "__main__":
    raise SystemExit(main())
