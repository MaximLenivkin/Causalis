"""Check B10's bounded scope and actual local/CI evidence, including known failure."""
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
BASELINE = "83b63836dbd0c4793c24dd95ff7dc18c443792ad"
LIBRARY = "causalis/dgp/base.py"
TEST = "tests/data/test_copula_categorical_coordinates.py"
DID_NODE = ("tests.scenarios.did.refutation.test_did_post_inference_diagnostics",
            "test_post_inference_report_accepts_panel_and_estimate")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def read(name):
    return json.loads((AUDIT / name).read_text())


def totals(path):
    suites = ET.parse(path).getroot().findall(".//testsuite")
    result = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
              for key in ("tests", "failures", "errors", "skipped")}
    result["passed"] = result["tests"] - sum(result[key] for key in ("failures", "errors", "skipped"))
    return result


def main():
    local = read("block10_integration_result.json")
    source = local["tested_source_checkpoint"]
    assert re.fullmatch("[a-f0-9]{40}", source)
    changed = git("diff", "--name-only", BASELINE, source, "--", "causalis", "tests", "scripts").decode().splitlines()
    assert set(changed) == {LIBRARY, TEST}, changed
    assert not git("diff", source, "--name-only", "--", "causalis", "tests", "scripts").strip()
    assert not git("ls-files", "--others", "--exclude-standard", "--", "causalis", "tests", "scripts").strip()
    old_tree = ast.parse(git("show", BASELINE + ":" + LIBRARY))
    new_tree = ast.parse(git("show", source + ":" + LIBRARY))
    old_nodes = {node.name: ast.dump(node) for node in old_tree.body if isinstance(node, ast.FunctionDef)}
    new_nodes = {node.name: ast.dump(node) for node in new_tree.body if isinstance(node, ast.FunctionDef)}
    assert {key for key in old_nodes.keys() | new_nodes.keys()
            if old_nodes.get(key) != new_nodes.get(key)} == {"_gaussian_copula"}
    focused = totals(AUDIT / "block10_copula_test_temp/current.xml")
    baseline = totals(AUDIT / "block10_copula_test_temp/baseline.xml")
    assert focused["tests"] == focused["passed"] > 0
    assert baseline["tests"] == focused["tests"] and baseline["failures"] > 0
    assert baseline["errors"] == baseline["skipped"] == 0
    for mode, junit_totals, checkpoint in (("focused", focused, source), ("baseline", baseline, BASELINE)):
        manifest = read(f"block10_copula_{mode}_test_result.json")
        assert manifest["counts"] == junit_totals
        assert manifest["source_sha256"] == hashlib.sha256(git("show", checkpoint + ":" + LIBRARY)).hexdigest()
        assert manifest["test_file_sha256"] == hashlib.sha256((ROOT / TEST).read_bytes()).hexdigest()
    review = read("block10_review_result.json")
    assert review["reviewed_head"] == source and review["issues"] == []
    assert review["current_library_sha256"] == hashlib.sha256((ROOT / LIBRARY).read_bytes()).hexdigest()
    assert review["current_test_module_sha256"] == hashlib.sha256((ROOT / TEST).read_bytes()).hexdigest()
    assert len(review["numeric_helper_reference"]) == 18
    assert all(row["generations"] == 2 and row["exact_values_names_next10rng"]
               for row in review["numeric_helper_reference"])
    assert len(review["public_numeric_fullframe_reference"]) == 48
    assert all(row["generations"] == 2 and row["exact_frame_schema_next10rng"]
               for row in review["public_numeric_fullframe_reference"])
    assert len(review["coordinate_reference"]) == 9 and len(review["boundary_reference"]) == 7
    expected = 2039 + focused["tests"]
    actual = totals(AUDIT / "block10_integration_test_temp/junit.xml")
    assert actual == {"tests": expected, "passed": expected - 1, "failures": 1, "errors": 0, "skipped": 0}
    assert all(local[key] == actual[key] for key in actual)
    assert local["exit_code"] == 1 and local["scoped_suite_clean"] is False
    assert local["full_suite_clean"] is local["sensitivity_validated"] is False
    cases = ET.parse(AUDIT / "block10_integration_test_temp/junit.xml").getroot().findall(".//testcase")
    failed = [case for case in cases if case.find("failure") is not None]
    assert [(case.attrib["classname"], case.attrib["name"]) for case in failed] == [DID_NODE]
    assert "YELLOW" in failed[0].find("failure").attrib["message"]
    selection = read("block10_integration_selection.json")
    ci = read("block10_ci_result.json")
    previous_selection = read("block09_integration_selection.json")
    assert selection["excluded_modules"] == ci["excluded_modules"] == previous_selection["excluded_modules"]
    assert len(selection["excluded_modules"]) == 7
    assert selection["environment"]["commit"] == source
    assert ci["tested_source_checkpoint"] == source and ci["expected_tests_per_job"] == expected
    assert ci["matrix_verified"] is True and ci["verified_successful_jobs"] == 6 and ci["issues"] == []
    assert all(job["junit"] == {"tests": expected, "passed": expected, "failures": 0, "errors": 0, "skipped": 0}
               for job in ci["jobs"])
    did = read("block10_did_provenance.json")
    assert did["fixture_unchanged"] and did["called_package_unchanged"] and did["cell_aggregates_equal_b09"]
    assert not did["changed_copula_path_called"] and did["overall_flag"] == "YELLOW"
    assert did["current_head"] == source
    for path, digest in did["called_package_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    python_paths = [ROOT / LIBRARY, ROOT / TEST] + list(AUDIT.glob("*block10*.py"))
    for path in python_paths:
        ast.parse(path.read_text())
    checked_links = 0
    for path in list(AUDIT.glob("B10_*.md")) + [AUDIT / "BLOCK10_COPULA.md"]:
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if "://" in target or target.startswith("#"):
                continue
            assert (path.parent / target.split("#")[0]).exists(), (path, target)
            checked_links += 1
    result = {"baseline_sha": BASELINE, "source": source, "changed_source_paths": changed,
              "new_cases": focused["tests"], "baseline": {"checkpoint": BASELINE, **baseline},
              "local": actual, "ci_jobs_verified": 6, "relative_links_checked": checked_links,
              "python_files_parsed": len(python_paths), "issues": []}
    (AUDIT / "block10_validation_checks.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
