"""Verify B15's source boundary, preserved default AST and final evidence."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
BASELINE = "71f6a619b04e0ab8fab388fb95b7d0f3d6631b96"
LIBRARY = ["causalis/dgp/multicausaldata/base.py", "causalis/dgp/multicausaldata/functional.py"]
TEST = "tests/data/test_multicausal_marginal_propensity.py"
OPTION = "include_marginal_propensity"


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ExistingBehavior(ast.NodeTransformer):
    """Remove only the precisely named additive API and validation branches."""

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return None
        if (isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == "_validate_marginal_propensity_option"):
            return None
        return self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module == "scipy.integrate" and [x.name for x in node.names] == ["quad_vec"]:
            return None
        return node

    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name) and node.target.id == OPTION:
            return None
        return self.generic_visit(node)

    def visit_If(self, node):
        if isinstance(node.test, ast.Attribute) and node.test.attr == OPTION:
            return None
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if node.name in {"_validate_marginal_propensity_option", "_gaussian_marginal_propensity"}:
            return None
        if node.args.args and node.args.args[-1].arg == OPTION:
            node.args.args.pop()
            node.args.defaults.pop()
        return self.generic_visit(node)

    def visit_Call(self, node):
        node.keywords = [x for x in node.keywords if x.arg != OPTION]
        return self.generic_visit(node)


def old_ast(source: bytes) -> str:
    return ast.dump(ExistingBehavior().visit(ast.parse(source)), include_attributes=False)


def case_ids(path: Path) -> set:
    return {(x.attrib["classname"], x.attrib["name"])
            for x in ET.parse(path).getroot().findall(".//testcase")}


def junit_counts(path: Path) -> dict:
    cases = ET.parse(path).getroot().findall(".//testcase")
    failures = sum(case.find("failure") is not None for case in cases)
    errors = sum(case.find("error") is not None for case in cases)
    skipped = sum(case.find("skipped") is not None for case in cases)
    return {"tests": len(cases), "failures": failures, "errors": errors,
            "skipped": skipped, "passed": len(cases) - failures - errors - skipped}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    assert re.fullmatch(r"[a-f0-9]{40}", args.source)
    assert git("diff", args.source, "--name-only", "--", "causalis", "tests", "scripts").strip() == b""
    changed = git("diff", BASELINE, args.source, "--name-only", "--", "causalis", "tests", "scripts").decode().splitlines()
    assert sorted(changed) == sorted(LIBRARY + [TEST]), changed
    hashes = {}
    for path in LIBRARY + [TEST]:
        committed = git("show", f"{args.source}:{path}")
        assert (ROOT / path).read_bytes() == committed, path
        hashes[path] = sha(committed)
    for path in LIBRARY:
        assert old_ast(git("show", f"{BASELINE}:{path}")) == old_ast((ROOT / path).read_bytes()), path

    baseline = json.loads((AUDIT / "block15_oracle_baseline_test_result.json").read_text())
    focus = json.loads((AUDIT / "block15_oracle_focused_test_result.json").read_text())
    assert baseline["baseline_sha"] == focus["baseline_sha"] == BASELINE
    assert baseline["test_file_sha256"] == focus["test_file_sha256"] == hashes[TEST]
    assert baseline["collected_case_ids"] == focus["collected_case_ids"]
    assert baseline["counts"] == {"tests": 79, "failures": 74, "errors": 0, "skipped": 0, "passed": 5}
    assert focus["counts"] == {"tests": 79, "failures": 0, "errors": 0, "skipped": 0, "passed": 79}
    assert focus["exit_code"] == 0 and baseline["exit_code"] == 1
    assert baseline["baseline_feature_absence_is_planned_not_a_numerical_bug"] is True
    for payload in (baseline, focus):
        assert payload["public_generator_and_wrapper_aliases_verified"] is True
        assert payload["shared_helper_and_contract_bindings_verified"] is True
        assert payload["non_target_tracked_package_paths_unchanged"] is True
        junit = AUDIT.parent / payload["junit"]
        assert len(case_ids(junit)) == 79
        assert junit_counts(junit) == payload["counts"]
        assert {classname + "::" + name for classname, name in case_ids(junit)} == set(payload["collected_case_ids"])
        for path, value in payload["unchanged_dependency_sha256"].items():
            assert sha(git("show", f"{args.source}:{path}")) == sha(git("show", f"{BASELINE}:{path}")) == value
    assert baseline["failure_exception_types"] == {"TypeError": 67, "AttributeError": 7}
    combined = json.loads((AUDIT / "block15_oracle_test_result.json").read_text())
    assert combined["source_commit_sha"] == combined["focused_matching_committed_source_sha"] == args.source
    assert combined["committed_source_and_test_bytes_match_focused_run"] is True
    assert combined["raw_junit_counts_and_case_ids_verified"] is True
    assert combined["committed_file_sha256"] == hashes
    assert combined["baseline_failures_are_planned_api_absence"] is True
    assert combined["focused_was_precommit_working_tree_run"] is True
    assert focus["source_sha256"] == {path: hashes[path] for path in LIBRARY}
    for path, value in baseline["source_sha256"].items():
        assert sha(git("show", f"{BASELINE}:{path}")) == value

    contract = json.loads((AUDIT / "block15_contract_result.json").read_text())
    review = json.loads((AUDIT / "block15_review_result.json").read_text())
    assert contract["baseline_sha"] == review["baseline"] == BASELINE
    assert contract["issues"] == review["issues"] == []
    assert contract["source_sha256"]["candidate_snapshot"] == review["source_sha256"] == focus["source_sha256"]
    assert contract["counts"]["propensity_reference_cases"] == 31
    assert contract["counts"]["public_generation_cases"] == 8
    assert contract["max_propensity_abs_error"] < 1e-10
    assert review["original_positional_parameters_preserved"] is True
    assert review["frozen_full_graph_bindings_verified"] is True
    bounded = review["bounded_policy_review"]
    assert bounded["issues"] == [] and len(bounded["projections"]) == 10 and len(bounded["failure_modes"]) == 8
    assert bounded["supplied_U_q_exact_invariance"] is True
    assert bounded["source_sha256"] == review["source_sha256"]
    final_tests = review["final_test_review"]
    assert final_tests["issues"] == [] and final_tests["tests_read"] == 79
    assert final_tests["actual_junit_counts_and_ids_verified"] is True
    assert final_tests["test_sha256"] == hashes[TEST]
    link = review["committed_source_linkage"]
    assert link["source_checkpoint"] == args.source and link["issues"] == []
    assert link["initial_reference_provenance_preserved"] is True
    assert link["full_runtime_references_repeated"] is False
    for path, value in link["committed_file_sha256"].items():
        assert sha(git("show", f"{args.source}:{path}")) == sha((ROOT / path).read_bytes()) == value
    for path, value in review["unchanged_dependency_sha256"].items():
        assert sha(git("show", f"{args.source}:{path}")) == sha(git("show", f"{BASELINE}:{path}")) == value
    provenance = json.loads((AUDIT / "block15_committed_provenance.json").read_text())
    assert provenance["source_checkpoint"] == args.source and provenance["baseline"] == BASELINE
    assert provenance["issues"] == [] and provenance["unique_paths"] == len(provenance["files"]) == 11
    assert provenance["original_runtime_provenance_preserved"] is True
    assert provenance["numerical_runs_repeated_for_linkage"] is False
    for entry in provenance["files"]:
        assert sha(git("show", f"{args.source}:{entry['path']}")) == entry["sha256"]
        assert sha((ROOT / entry["path"]).read_bytes()) == entry["sha256"]

    integration = json.loads((AUDIT / "block15_integration_result.json").read_text())
    selection = json.loads((AUDIT / "block15_integration_selection.json").read_text())
    assert integration["tested_source_checkpoint"] == selection["environment"]["commit"] == args.source
    assert integration["scoped_suite_clean"] is True and integration["full_suite_clean"] is False
    assert integration["failures"] == integration["errors"] == integration["skipped"] == integration["exit_code"] == 0
    assert integration["tests"] == integration["passed"] == 2618
    assert junit_counts(AUDIT / "block15_integration_test_temp/junit.xml") == {
        key: integration[key] for key in ("tests", "failures", "errors", "skipped", "passed")}
    assert integration["sensitivity_validated"] is selection["selected_full_suite"] is False
    local_cases = case_ids(AUDIT / "block15_integration_test_temp/junit.xml")
    assert len(local_cases) == integration["tests"]
    focused = {x for x in local_cases if x[0] == "tests.data.test_multicausal_marginal_propensity"}
    assert len(focused) == 79
    assert {classname + "::" + name for classname, name in focused} == set(focus["collected_case_ids"])

    ci = json.loads((AUDIT / "block15_ci_result.json").read_text())
    assert ci["tested_source_checkpoint"] == args.source
    assert ci["matrix_verified"] is True and ci["verified_successful_jobs"] == 6 and ci["issues"] == []
    configs = set()
    for job in ci["jobs"]:
        configs.add((job["python_minor"], job["stack"]))
        assert job["junit"]["tests"] == job["junit"]["passed"] == integration["tests"]
        assert job["environment"]["commit"] == args.source
        assert "Linux" in job["environment"]["platform"]
        folder = AUDIT / f"block15_ci_test_temp/run-{ci['run_id']}/correctness-py{job['python_minor']}-{job['stack']}"
        actual_selection = json.loads((folder / "selection.json").read_text())
        actual_result = json.loads((folder / "result.json").read_text())
        assert actual_selection["excluded_modules"] == selection["excluded_modules"] == ci["excluded_modules"]
        assert actual_selection["environment"] == job["environment"]
        assert actual_result["exit_code"] == 0
        assert junit_counts(folder / "junit.xml") == job["junit"]
        assert [actual_selection["pytest_args"][i + 1] for i, x in enumerate(actual_selection["pytest_args"]) if x == "--ignore"] == selection["excluded_modules"]
        assert not any(x in {"-k", "-m", "--deselect"} for x in actual_selection["pytest_args"])
        assert case_ids(folder / "junit.xml") == local_cases
    assert configs == {(f"3.{minor}", "latest") for minor in range(10, 15)} | {("3.10", "legacy")}

    ci_review = review["ci_review"]
    assert ci_review["issues"] == [] and ci_review["matrix_verified"] is True
    assert ci_review["source_checkpoint"] == args.source
    assert ci_review["run_id"] == ci["run_id"] and ci_review["verified_jobs"] == 6
    assert ci_review["all_full_case_sets_equal_local"] is True
    assert ci_review["all_79_new_case_ids_each_job"] is True
    assert ci_review["seven_exclusions_unchanged_from_B14"] is True
    assert ci_review["actual_ignore_arguments_verified"] is True
    assert ci_review["source_hashes_verified_against_checkpoint"] is True
    assert ci_review["local_junit_sha256"] == sha((AUDIT / "block15_integration_test_temp/junit.xml").read_bytes())
    assert ci_review["ci_summary_sha256"] == sha((AUDIT / "block15_ci_result.json").read_bytes())
    assert ci_review["run_status_sha256"] == sha((AUDIT / f"block15_ci_test_temp/run-{ci['run_id']}/run_status.json").read_bytes())
    reviewed_configs = set()
    for job in ci_review["jobs"]:
        config = (job["python_minor"], job["stack"])
        reviewed_configs.add(config)
        summary_job = next(item for item in ci["jobs"] if (item["python_minor"], item["stack"]) == config)
        assert job["environment"] == summary_job["environment"]
        assert job["junit"] == summary_job["junit"]
        assert job["complete_case_count"] == 2618 and job["new_case_count"] == 79
        assert job["full_case_set_equals_local"] is True
        folder = AUDIT / f"block15_ci_test_temp/run-{ci['run_id']}" / job["artifact"]
        for name, value in job["artifact_sha256"].items():
            assert sha((folder / name).read_bytes()) == value
        actual_selection = json.loads((folder / "selection.json").read_text())
        assert job["actual_pytest_args"] == actual_selection["pytest_args"]
    assert reviewed_configs == configs

    handoff = json.loads((AUDIT / "handoff_validation.json").read_text())
    assert handoff["snapshot_links_checked"] == 110 and handoff["issues"] == []

    python_paths = sorted(AUDIT.glob("*block15*.py")) + [ROOT / TEST]
    for path in python_paths:
        ast.parse(path.read_bytes(), filename=str(path))
    checked_links = 0
    for name in ["BLOCK15_GAUSSIAN_ORACLE.md", "B15_ORACLE_CONTRACT.md", "B15_ORACLE_IMPLEMENTATION.md", "B15_ORACLE_TESTS.md", "B15_ORACLE_REVIEW.md"]:
        content = (AUDIT / name).read_text()
        for target in re.findall(r"\]\(([^)]+)\)", content):
            if "://" in target or target.startswith("#"):
                continue
            assert (AUDIT / target.split("#", 1)[0]).exists(), (name, target)
            checked_links += 1
    result = {"baseline": BASELINE, "source_checkpoint": args.source,
              "source_hashes": hashes, "source_scope_verified": True,
              "default_executable_ast_preserved": True,
              "local_tests": integration["tests"], "new_cases": len(focused),
              "six_ci_full_case_sets_match_local": True,
              "independent_ci_review_and_artifact_hashes_verified": True,
              "review_failure_and_projection_boundaries_verified": True,
              "actual_focused_and_integration_junit_counts_verified": True,
              "handoff_snapshot_links_checked": handoff["snapshot_links_checked"],
              "python_files_parsed": len(python_paths), "relative_links_checked": checked_links,
              "sensitivity_validated": False, "issues": []}
    (AUDIT / "block15_validation_checks.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
