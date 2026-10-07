"""Verify B14's committed scope and original local/CI evidence."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
BASELINE = "dbded76ecf8a207aad2094903b8f015fed8ae5d6"
LIBRARY = ["causalis/scenarios/did/model.py", "causalis/scenarios/did/refutation/post_inference.py"]
TESTS = ["tests/scenarios/did/refutation/test_did_post_inference_diagnostics.py",
         "tests/scenarios/did/refutation/test_did_studentization_contract.py"]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def read(name):
    return json.loads((AUDIT / name).read_text(encoding="utf-8"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def totals(path):
    suites = ET.parse(path).getroot().findall(".//testsuite")
    out = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
           for key in ("tests", "failures", "errors", "skipped")}
    out["passed"] = out["tests"] - sum(out[k] for k in ("failures", "errors", "skipped"))
    return out


def case_ids(path):
    return {(c.attrib["classname"], c.attrib["name"])
            for c in ET.parse(path).getroot().findall(".//testcase")}


def definitions(data):
    tree = ast.parse(data)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                node.body = node.body[1:]
    return {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}


def main():
    local = read("block14_integration_result.json")
    source = local["tested_source_checkpoint"]
    assert re.fullmatch(r"[0-9a-f]{40}", source)
    expected = set(LIBRARY + TESTS)
    assert set(git("diff", "--name-only", BASELINE, source, "--", "causalis", "tests", "scripts").decode().splitlines()) == expected
    assert not git("diff", source, "--name-only", "--", "causalis", "tests", "scripts").strip()
    assert not git("ls-files", "--others", "--exclude-standard", "--", "causalis", "tests", "scripts").strip()
    scope = read("block14_source_scope.json")
    assert scope["baseline"] == BASELINE
    for record in scope["records"]:
        path = record["path"]
        previous = git("show", BASELINE + ":" + path)
        current = git("show", source + ":" + path)
        assert digest(previous) == record["baseline_sha256"]
        assert digest(current) == record["current_sha256"] == digest((ROOT / path).read_bytes())
        old, new = definitions(previous), definitions(current)
        assert old.keys() == new.keys()
        changed = [name for name in old if ast.dump(old[name]) != ast.dump(new[name])]
        assert changed == record["changed_runtime_functions"]
        allowed = (["_normal_p_value", "_fit_outcome_regression", "_add_inference"] if path == LIBRARY[0]
                   else ["_safe_t_stat", "did_post_inference_cell_table", "run_did_post_inference_diagnostics"])
        assert changed == allowed
        for name in old:
            if isinstance(old[name], ast.FunctionDef):
                assert ast.dump(old[name].args) == ast.dump(new[name].args)

    old, new = definitions(git("show", BASELINE + ":" + TESTS[0])), definitions(git("show", source + ":" + TESTS[0]))
    for helper in ("_estimate", "_relaxed_report"):
        assert ast.dump(old[helper]) == ast.dump(new[helper])
    original_assertions = [ast.dump(n) for n in ast.walk(old["test_post_inference_report_accepts_panel_and_estimate"]) if isinstance(n, ast.Assert)]
    final_assertions = [ast.dump(n) for n in ast.walk(new["test_post_inference_report_accepts_panel_and_estimate"]) if isinstance(n, ast.Assert)]
    assert all(n in final_assertions for n in original_assertions)

    baseline_path = AUDIT / "block14_did_test_temp/baseline.xml"
    focused_path = AUDIT / "block14_did_test_temp/current.xml"
    baseline_counts, focused_counts = totals(baseline_path), totals(focused_path)
    assert baseline_counts["failures"] > 0 and baseline_counts["errors"] == baseline_counts["skipped"] == 0
    assert focused_counts["passed"] == focused_counts["tests"] and focused_counts["failures"] == focused_counts["errors"] == focused_counts["skipped"] == 0
    assert baseline_counts["tests"] == focused_counts["tests"]
    assert case_ids(baseline_path) == case_ids(focused_path)
    assert baseline_counts == dict(tests=56, passed=28, failures=28, errors=0, skipped=0)
    assert focused_counts == dict(tests=56, passed=56, failures=0, errors=0, skipped=0)
    for mode, counts, checkpoint in (("baseline", baseline_counts, BASELINE), ("focused", focused_counts, source)):
        manifest = read(f"block14_did_{mode}_test_result.json")
        assert manifest["counts"] == counts and manifest["baseline_sha"] == BASELINE
        assert manifest["public_class_and_refutation_aliases_verified"] and manifest["plot_influence_bindings_verified"]
        assert manifest["non_target_tracked_package_paths_unchanged"]
        assert manifest["test_module_case_counts"] == {
            "tests.scenarios.did.refutation.test_did_studentization_contract": 51,
            "tests.scenarios.did.refutation.test_did_post_inference_diagnostics": 5,
        }
        for path, value in manifest["source_sha256"].items():
            assert value == digest(git("show", checkpoint + ":" + path))
        for path, value in manifest["test_sha256"].items():
            assert value == digest(git("show", source + ":" + path))
        for path, value in manifest["unchanged_dependency_sha256"].items():
            assert value == digest(git("show", BASELINE + ":" + path)) == digest(git("show", source + ":" + path))
    combined = read("block14_did_test_result.json")
    assert combined["source_commit_sha"] == combined["focused_matching_committed_source_sha"] == source
    for key in ("committed_source_and_test_bytes_match_focused_run", "committed_dependency_bytes_match_baseline_and_focused_run",
                "baseline_and_focused_collection_identical", "raw_junit_counts_and_case_ids_verified"):
        assert combined[key], key
    assert combined["baseline_warnings"] == 4 and combined["focused_warnings"] == 0
    provenance = read("block14_committed_provenance.json")
    assert provenance["source_checkpoint"] == source and provenance["baseline"] == BASELINE
    assert provenance["all_recorded_bytes_match_committed_source"]
    for path, value in provenance["committed_file_sha256"].items():
        assert value == digest(git("show", source + ":" + path)) == digest((ROOT / path).read_bytes())

    contract = read("block14_contract_result.json")
    assert contract["baseline_sha"] == BASELINE and contract["imports_verified"] and contract["fixture_always_frozen"]
    assert not contract["global_package_overlays"] and not contract["individual_rows_saved"]
    for path, value in contract["baseline_source_sha256"].items():
        assert value == digest(git("show", BASELINE + ":" + path))
    for path, value in contract["current_source_sha256"].items():
        assert value == digest(git("show", source + ":" + path))
    assert len(contract["regression_references"]) == 11
    assert contract["original_fixture"]["baseline"]["overall_flag"] == contract["original_fixture"]["current"]["overall_flag"] == "YELLOW"

    review = read("block14_review_probe.json")
    assert review["baseline"] == BASELINE and not review["issues"] and not review["warnings"]
    assert review["public_signatures_unchanged"] and review["nonmutation_verified"]
    assert len(review["fitted_references"]) == 16 and all(row["estimate_calls"] == 2 for row in review["fitted_references"])
    assert len(review["regression"]["unchanged"]) == 27 and len(review["regression"]["analytical_constant_cases"]) == 7
    delta = review["delta_verification"]
    assert delta["proof"]["normal_runtime_bytes_unchanged"] and not delta["warnings_outside_expected_baseline_bootstrap"]
    for path, value in review["current_source_sha256"].items():
        assert value == digest(git("show", source + ":" + path))
    for path, value in review["unchanged_dependency_sha256"].items():
        assert value == digest(git("show", BASELINE + ":" + path)) == digest(git("show", source + ":" + path))
    assert review["committed_source_linkage"]["source_checkpoint"] == source

    actual_local = totals(AUDIT / "block14_integration_test_temp/junit.xml")
    assert actual_local["passed"] == actual_local["tests"] and actual_local["tests"] > 2488
    assert all(local[k] == actual_local[k] for k in actual_local)
    assert local["exit_code"] == 0 and local["scoped_suite_clean"] and not local["full_suite_clean"] and not local["sensitivity_validated"]
    assert case_ids(focused_path).issubset(case_ids(AUDIT / "block14_integration_test_temp/junit.xml"))
    ci = read("block14_ci_result.json")
    assert ci["matrix_verified"] and ci["verified_successful_jobs"] == 6 and not ci["issues"]
    assert ci["tested_source_checkpoint"] == source and ci["expected_tests_per_job"] == actual_local["tests"]
    independent_ci = review["ci_review"]
    assert independent_ci["source_checkpoint"] == source and independent_ci["run_id"] == ci["run_id"]
    assert independent_ci["verified_jobs"] == 6 and independent_ci["matrix_verified"] and not independent_ci["issues"]
    for key in ("all_56_focused_case_ids_each_job", "all_51_new_case_ids_each_job", "seven_exclusions_unchanged_from_B13",
                "actual_ignore_arguments_verified", "all_six_full_junit_case_sets_identical"):
        assert independent_ci[key], key
    previous_exclusions = read("block13_integration_selection.json")["excluded_modules"]
    assert ci["excluded_modules"] == read("block14_integration_selection.json")["excluded_modules"] == previous_exclusions
    configurations = set()
    full_ci_cases = None
    for job in ci["jobs"]:
        configurations.add((job["python_minor"], job["stack"]))
        artifact = AUDIT / f"block14_ci_test_temp/run-{ci['run_id']}" / f"correctness-py{job['python_minor']}-{job['stack']}"
        result = json.loads((artifact / "result.json").read_text())
        selection = json.loads((artifact / "selection.json").read_text())
        assert totals(artifact / "junit.xml") == actual_local == job["junit"]
        assert selection["environment"]["commit"] == source
        assert selection["environment"]["python"].startswith(job["python_minor"] + ".")
        assert selection["environment"]["platform"].startswith("Linux")
        assert selection["scope"] == result["scope"] == "correctness" and result["exit_code"] == 0
        assert selection["excluded_modules"] == previous_exclusions
        assert not selection["collect_only"] and not selection["selected_full_suite"] and not result["selected_full_suite"]
        assert case_ids(focused_path).issubset(case_ids(artifact / "junit.xml"))
        actual_cases = case_ids(artifact / "junit.xml")
        if full_ci_cases is None:
            full_ci_cases = actual_cases
        assert actual_cases == full_ci_cases == case_ids(AUDIT / "block14_integration_test_temp/junit.xml")
    assert configurations == {(f"3.{m}", "latest") for m in range(10, 15)} | {("3.10", "legacy")}

    parsed = []
    for path in sorted(set(AUDIT.glob("*block14*.py")) | set(ROOT / p for p in LIBRARY + TESTS)):
        ast.parse(path.read_text(encoding="utf-8")); parsed.append(str(path.relative_to(ROOT)))
    links = []
    for path in list(AUDIT.glob("B14_*.md")) + [AUDIT / "BLOCK14_DID_NUMERICAL_ZERO.md"]:
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" in link:
                continue
            destination = (path.parent / link.split("#")[0]).resolve()
            assert destination.exists(), (path, link)
            links.append({"report": path.name, "target": link})
    output = dict(baseline_sha=BASELINE, source_checkpoint=source, changed_source_test_paths=sorted(expected),
                  changed_runtime_functions_verified=True, original_api_assertions_and_thresholds_preserved=True,
                  baseline=baseline_counts, focused=focused_counts, local=actual_local,
                  verified_ci_jobs=6, final_cases_in_every_ci_artifact=True, sensitivity_validated=False,
                  independent_ci_review_verified=True, full_ci_and_local_case_sets_identical=True,
                  parsed_python_files=parsed, checked_relative_links=links, issues=[])
    (AUDIT / "block14_validation_checks.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source": source, "focused": focused_counts, "local": actual_local, "ci_jobs": 6,
                      "python_files": len(parsed), "relative_links": len(links), "issues": []}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
