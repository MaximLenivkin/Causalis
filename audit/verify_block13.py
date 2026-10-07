"""Verify the bounded B13 change and its baseline, local and CI evidence."""
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
BASELINE = "9f0a63c42308ca886d92dc73d8d8d9611d5b2c31"
LIBRARY = "causalis/scenarios/classic_rct/dgp.py"
TEST = "tests/data/test_scenario_namespace_contract.py"
DID_NODE = ("tests.scenarios.did.refutation.test_did_post_inference_diagnostics",
            "test_post_inference_report_accepts_panel_and_estimate")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def read(name):
    return json.loads((AUDIT / name).read_text(encoding="utf-8"))


def totals(path):
    suites = ET.parse(path).getroot().findall(".//testsuite")
    counts = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
              for key in ("tests", "failures", "errors", "skipped")}
    counts["passed"] = counts["tests"] - sum(counts[key] for key in ("failures", "errors", "skipped"))
    return counts


def policy_statement(node):
    if isinstance(node, ast.Expr):
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return True
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            return node.value.func.id in {"_validate_scenario_pre_name", "_validate_new_columns"}
    if isinstance(node, ast.Assign):
        return any(isinstance(target, ast.Name) and target.id == "exclude" for target in node.targets)
    if isinstance(node, ast.If) and ast.dump(node.test) == ast.dump(ast.Name(id="include_oracle", ctx=ast.Load())):
        return (not node.orelse and len(node.body) == 1 and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Call)
                and isinstance(node.body[0].value.func, ast.Attribute)
                and isinstance(node.body[0].value.func.value, ast.Name)
                and node.body[0].value.func.value.id == "exclude"
                and node.body[0].value.func.attr == "update")
    return False


def main():
    local = read("block13_integration_result.json")
    source = local["tested_source_checkpoint"]
    assert re.fullmatch(r"[a-f0-9]{40}", source)
    changed = git("diff", "--name-only", BASELINE, source, "--", "causalis", "tests", "scripts").decode().splitlines()
    assert set(changed) == {LIBRARY, TEST}, changed
    assert not git("diff", source, "--name-only", "--", "causalis", "tests", "scripts").strip()
    assert not git("ls-files", "--others", "--exclude-standard", "--", "causalis", "tests", "scripts").strip()
    old = {n.name: n for n in ast.parse(git("show", BASELINE + ":" + LIBRARY)).body if isinstance(n, ast.FunctionDef)}
    new = {n.name: n for n in ast.parse(git("show", source + ":" + LIBRARY)).body if isinstance(n, ast.FunctionDef)}
    for name in ("generate_classic_rct_26", "classic_rct_gamma_26"):
        assert ast.dump(old[name].args) == ast.dump(new[name].args), name
        assert [ast.dump(n) for n in old[name].body if not policy_statement(n)] == [
            ast.dump(n) for n in new[name].body if not policy_statement(n)], name

    focused = totals(AUDIT / "block13_scenario_test_temp/current.xml")
    baseline = totals(AUDIT / "block13_scenario_test_temp/baseline.xml")
    assert focused == dict(tests=91, passed=91, failures=0, errors=0, skipped=0)
    assert baseline == dict(tests=91, passed=63, failures=28, errors=0, skipped=0)
    for mode, counts, checkpoint in (("focused", focused, source), ("baseline", baseline, BASELINE)):
        manifest = read(f"block13_scenario_{mode}_test_result.json")
        assert manifest["counts"] == counts
        for key in ("public_scenario_aliases_verified", "wrapper_bindings_and_iv_inheritance_verified",
                    "shared_helper_bindings_verified", "b12_dependencies_and_control_scenarios_unchanged",
                    "non_target_tracked_package_paths_unchanged"):
            assert manifest[key], key
        assert manifest["test_file_sha256"] == hashlib.sha256((ROOT / TEST).read_bytes()).hexdigest()
        for path, digest in manifest["source_sha256"].items():
            assert digest == hashlib.sha256(git("show", checkpoint + ":" + path)).hexdigest()
        for path, digest in manifest["unchanged_dependency_sha256"].items():
            assert digest == hashlib.sha256(git("show", BASELINE + ":" + path)).hexdigest()
            assert digest == hashlib.sha256(git("show", source + ":" + path)).hexdigest()
    combined = read("block13_scenario_test_result.json")
    assert combined["source_commit_sha"] == combined["focused_matching_committed_source_sha"] == source
    assert combined["committed_source_and_test_bytes_match_focused_run"]
    assert combined["committed_dependency_bytes_match_baseline_and_focused_run"]
    assert combined["baseline_and_focused_collection_identical"]
    old_cases = ET.parse(AUDIT / "block13_scenario_test_temp/baseline.xml").getroot().findall(".//testcase")
    new_cases = ET.parse(AUDIT / "block13_scenario_test_temp/current.xml").getroot().findall(".//testcase")
    assert [(c.attrib["classname"], c.attrib["name"]) for c in old_cases] == [
        (c.attrib["classname"], c.attrib["name"]) for c in new_cases]
    contract = read("block13_contract_result.json")
    assert contract["baseline_sha"] == BASELINE and contract["evidence_kind"] == "frozen_baseline_only"
    assert contract["bindings_verified"] and contract["records_count"] == len(contract["records"]) == 100
    for path, digest in contract["baseline_source_sha256"].items():
        assert digest == hashlib.sha256(git("show", BASELINE + ":" + path)).hexdigest()
    review = read("block13_review_probe.json")
    assert review["baseline"] == BASELINE and not review["issues"] and not review["warnings"]
    assert review["current_test_module_sha256"] == hashlib.sha256((ROOT / TEST).read_bytes()).hexdigest()
    assert review["public_constructor_signatures_unchanged"]
    assert len(review["valid_configs"]) == 116
    assert all(row["exact_frame_dtypes_schema_metadata_state_next10rng"] for row in review["valid_configs"])
    assert len(review["namespace_rejections"]) == 13
    assert len(review["permitted_names"]) == 40
    for path, digest in review["current_library_sha256"].items():
        assert digest == hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        assert digest == hashlib.sha256(git("show", source + ":" + path)).hexdigest()
    assert review["reviewed_head"] == review["source_commit_sha"] == source
    assert review["committed_source_and_test_bytes_match_reviewed_outputs"]
    assert len(review["committed_file_sha256"]) == 13
    for path, digest in review["committed_file_sha256"].items():
        assert digest == hashlib.sha256(git("show", source + ":" + path)).hexdigest()

    actual = totals(AUDIT / "block13_integration_test_temp/junit.xml")
    assert all(local[key] == actual[key] for key in actual)
    assert actual["tests"] == read("block12_integration_result.json")["tests"] + focused["tests"]
    assert actual["failures"] == 1 and actual["errors"] == actual["skipped"] == 0
    assert local["exit_code"] == 1 and local["scoped_suite_clean"] is False
    assert local["full_suite_clean"] is local["sensitivity_validated"] is False
    failed = [c for c in ET.parse(AUDIT / "block13_integration_test_temp/junit.xml").getroot().findall(".//testcase")
              if c.find("failure") is not None]
    assert [(c.attrib["classname"], c.attrib["name"]) for c in failed] == [DID_NODE]
    assert "YELLOW" in failed[0].find("failure").attrib["message"]

    # This is a static linkage to the preceding numerical-zero runtime evidence.
    prior = read("block10_did_provenance.json")
    assert hashlib.sha256((ROOT / prior["fixture"]).read_bytes()).hexdigest() == prior["fixture_sha256"]
    assert LIBRARY not in prior["called_package_sha256"]
    for path, digest in prior["called_package_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest

    selection = read("block13_integration_selection.json")
    ci = read("block13_ci_result.json")
    assert selection["environment"]["commit"] == source
    assert selection["excluded_modules"] == ci["excluded_modules"] == read("block12_integration_selection.json")["excluded_modules"]
    assert len(selection["excluded_modules"]) == 7
    assert ci["tested_source_checkpoint"] == source and ci["expected_tests_per_job"] == actual["tests"]
    assert ci["matrix_verified"] and ci["verified_successful_jobs"] == 6 and not ci["issues"]
    artifact_root = AUDIT / f"block13_ci_test_temp/run-{ci['run_id']}"
    expected_scenario_cases = {(c.attrib["classname"], c.attrib["name"]) for c in new_cases}
    independent_ci = review["ci_review"]
    assert independent_ci["source_checkpoint"] == source and independent_ci["run_id"] == ci["run_id"]
    assert independent_ci["all_six_actual_artifacts_verified"] and not independent_ci["issues"]
    assert independent_ci["all_91_final_scenario_case_ids_present_per_job"]
    for job in ci["jobs"]:
        artifact = artifact_root / f"correctness-py{job['python_minor']}-{job['stack']}"
        downloaded = json.loads((artifact / "selection.json").read_text(encoding="utf-8"))
        result = json.loads((artifact / "result.json").read_text(encoding="utf-8"))
        assert downloaded["environment"] == job["environment"]
        assert downloaded["environment"]["commit"] == source
        assert downloaded["excluded_modules"] == selection["excluded_modules"]
        assert result == job["pytest_result"] and result["exit_code"] == 0
        counts = totals(artifact / "junit.xml")
        assert counts == job["junit"]
        assert counts == dict(tests=actual["tests"], passed=actual["tests"], failures=0, errors=0, skipped=0)
        cases = ET.parse(artifact / "junit.xml").getroot().findall(".//testcase")
        scenario_cases = {(c.attrib["classname"], c.attrib["name"]) for c in cases
                          if c.attrib["classname"] == "tests.data.test_scenario_namespace_contract"}
        assert scenario_cases == expected_scenario_cases

    python_paths = [ROOT / LIBRARY, ROOT / TEST] + sorted(AUDIT.glob("*block13*.py"))
    for path in python_paths:
        ast.parse(path.read_bytes(), filename=str(path))
    report_paths = [AUDIT / "BLOCK13_SCENARIO_NAMESPACE.md"] + sorted(AUDIT.glob("B13_*.md"))
    links = 0
    for path in report_paths:
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if not target.startswith(("https://", "http://")):
                assert (path.parent / target.split("#")[0]).exists(), (path, target)
                links += 1
    evidence = dict(baseline=BASELINE, source_checkpoint=source,
                    bounded_paths=changed, public_signatures_unchanged=True,
                    numeric_runtime_ast_unchanged_apart_from_namespace_and_projection=True,
                    focused_junit=focused, baseline_junit=baseline,
                    baseline_only_contract_records=100, exact_reference_configs=116,
                    independent_review_source_hashes_verified=True,
                    local_junit=actual, known_did_failure_static_linkage_verified=True,
                    ci_artifacts_verified=6, all_new_cases_present_in_each_ci_artifact=True,
                    independent_ci_review_verified=True, sensitivity_validated=False,
                    python_ast_files=len(python_paths), report_links_checked=links, issues=[])
    (AUDIT / "block13_validation_checks.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
