"""Verify B12's bounded source changes and recorded baseline/local/CI evidence."""
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
BASELINE = "eb6dfe23f0a97991b6e3d6109febc1b0170e128d"
LIBRARY = {
    "causalis/dgp/causaldata/base.py": "CausalDatasetGenerator",
    "causalis/dgp/causaldata_instrumental/base.py": "InstrumentalGenerator",
    "causalis/dgp/base.py": None,
    "causalis/dgp/causaldata/preperiod.py": None,
    "causalis/dgp/causaldata/functional.py": None,
    "causalis/dgp/causaldata_instrumental/functional.py": None,
}
TEST = "tests/data/test_wrapper_namespace_contract.py"
DID_NODE = ("tests.scenarios.did.refutation.test_did_post_inference_diagnostics",
            "test_post_inference_report_accepts_panel_and_estimate")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def read(name):
    return json.loads((AUDIT / name).read_text(encoding="utf-8"))


def totals(path):
    suites = ET.parse(path).getroot().findall(".//testsuite")
    result = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
              for key in ("tests", "failures", "errors", "skipped")}
    result["passed"] = result["tests"] - sum(result[key] for key in ("failures", "errors", "skipped"))
    return result


def methods(data, cls):
    tree = ast.parse(data)
    return {node.name: node for c in tree.body if isinstance(c, ast.ClassDef) and c.name == cls
            for node in c.body if isinstance(node, ast.FunctionDef)}


def guard_or_doc(node):
    if isinstance(node, ast.Expr):
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return True
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            return node.value.func.id == "_validate_new_columns"
    if isinstance(node, ast.Assign):
        target = node.targets[0]
        return (isinstance(target, ast.Name) and target.id in {"output_roles", "generated_names", "column_roles"}
                or isinstance(target, ast.Attribute) and target.attr in {
                    "_generated_confounder_names", "_generated_column_roles"})
    return False


def function(data, cls, name):
    tree = ast.parse(data)
    nodes = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == cls).body if cls else tree.body
    return next(node for node in nodes if isinstance(node, ast.FunctionDef) and node.name == name)


def main():
    local = read("block12_integration_result.json")
    source = local["tested_source_checkpoint"]
    assert re.fullmatch(r"[a-f0-9]{40}", source)
    changed = git("diff", "--name-only", BASELINE, source, "--", "causalis", "tests", "scripts").decode().splitlines()
    assert set(changed) == set(LIBRARY) | {TEST}, changed
    assert not git("diff", source, "--name-only", "--", "causalis", "tests", "scripts").strip()
    assert not git("ls-files", "--others", "--exclude-standard", "--", "causalis", "tests", "scripts").strip()
    runtime_checks = [
        ("causalis/dgp/causaldata/base.py", "CausalDatasetGenerator", "generate"),
        ("causalis/dgp/causaldata_instrumental/base.py", "InstrumentalGenerator", "generate"),
        ("causalis/dgp/base.py", None, "_add_ancillary_info"),
        ("causalis/dgp/causaldata/preperiod.py", None, "add_preperiod_covariate"),
        ("causalis/dgp/causaldata/functional.py", None, "_add_tweedie_pre"),
    ]
    for path, cls, name in runtime_checks:
        old = function(git("show", BASELINE + ":" + path), cls, name)
        new = function(git("show", source + ":" + path), cls, name)
        assert ast.dump(old.args) == ast.dump(new.args), (path, name)
        assert [ast.dump(n) for n in new.body if not guard_or_doc(n)] == [
            ast.dump(n) for n in old.body if not guard_or_doc(n)], (path, name)

    focused = totals(AUDIT / "block12_wrapper_test_temp/current.xml")
    baseline = totals(AUDIT / "block12_wrapper_test_temp/baseline.xml")
    assert focused == dict(tests=162, passed=162, failures=0, errors=0, skipped=0)
    assert baseline == dict(tests=162, passed=26, failures=136, errors=0, skipped=0)
    for mode, counts, checkpoint in (("focused", focused, source), ("baseline", baseline, BASELINE)):
        manifest = read(f"block12_wrapper_{mode}_test_result.json")
        assert manifest["counts"] == counts
        assert manifest["wrapper_bindings_and_iv_inheritance_verified"]
        assert manifest["shared_augmentation_bindings_verified"]
        assert manifest["test_file_sha256"] == hashlib.sha256((ROOT / TEST).read_bytes()).hexdigest()
        for path, digest in manifest["source_sha256"].items():
            assert digest == hashlib.sha256(git("show", checkpoint + ":" + path)).hexdigest()
    old_cases = ET.parse(AUDIT / "block12_wrapper_test_temp/baseline.xml").getroot().findall(".//testcase")
    new_cases = ET.parse(AUDIT / "block12_wrapper_test_temp/current.xml").getroot().findall(".//testcase")
    assert [(c.attrib["classname"], c.attrib["name"]) for c in old_cases] == [
        (c.attrib["classname"], c.attrib["name"]) for c in new_cases]

    combined = read("block12_wrapper_test_result.json")
    assert combined["source_commit_sha"] == combined["focused_matching_committed_source_sha"] == source
    assert combined["committed_source_and_test_bytes_match_focused_run"]
    assert combined["baseline_and_focused_collection_identical"]
    review = read("block12_review_probe.json")
    assert review["reviewed_head"] == source and not review["issues"]
    assert review["current_test_module_sha256"] == hashlib.sha256((ROOT / TEST).read_bytes()).hexdigest()
    for path, digest in review["current_library_sha256"].items():
        assert digest == hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        assert digest == hashlib.sha256(git("show", source + ":" + path)).hexdigest()
    assert len(review["valid_wrapper_configs"]) == 300
    assert len(review["valid_core_conversion_configs"]) == 80
    assert all(row["exact_frame_schema_dtypes_metadata_next10rng"] for row in review["valid_wrapper_configs"])
    assert all(row["generations"] == 2 and row["exact_frame_schema_dtypes_metadata_next10rng"]
               for row in review["valid_core_conversion_configs"])
    assert len(review["namespace_rejections"]) >= 45
    assert all(row["status"] == "ValueError" for row in review["namespace_rejections"])
    assert len(review["permitted_names_and_conversion"]) >= 34
    assert len(review["callback_and_snapshot_checks"]) == 6
    assert len(review["wrapper_callback_and_helper_checks"]) == 5
    assert len(review["constructor_checks"]) == 2
    assert review["committed_source_and_test_bytes_match_reviewed_outputs"]
    assert len(review["residual_checks"]) == 1 and review["residual_checks"][0]["out_of_scope"]

    current_junit = AUDIT / "block12_integration_test_temp/junit.xml"
    actual = totals(current_junit)
    assert actual["tests"] == 2235 + focused["tests"]
    assert all(local[key] == actual[key] for key in actual)
    assert actual["failures"] == 1 and actual["errors"] == actual["skipped"] == 0
    assert local["exit_code"] == 1 and local["scoped_suite_clean"] is False
    assert local["full_suite_clean"] is local["sensitivity_validated"] is False
    cases = ET.parse(current_junit).getroot().findall(".//testcase")
    failed = [c for c in cases if c.find("failure") is not None]
    assert [(c.attrib["classname"], c.attrib["name"]) for c in failed] == [DID_NODE]
    assert "YELLOW" in failed[0].find("failure").attrib["message"]

    # The prior runtime probe recorded the entire called package closure.
    # Recheck that closure statically; do not present its values as a new run.
    prior = read("block10_did_provenance.json")
    fixture = prior["fixture"]
    assert hashlib.sha256((ROOT / fixture).read_bytes()).hexdigest() == prior["fixture_sha256"]
    assert not set(LIBRARY) & set(prior["called_package_sha256"])
    for path, digest in prior["called_package_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest

    selection = read("block12_integration_selection.json")
    ci = read("block12_ci_result.json")
    assert selection["environment"]["commit"] == source
    assert selection["excluded_modules"] == ci["excluded_modules"] == read("block10_integration_selection.json")["excluded_modules"]
    assert len(selection["excluded_modules"]) == 7
    assert ci["tested_source_checkpoint"] == source and ci["expected_tests_per_job"] == actual["tests"]
    assert ci["matrix_verified"] and ci["verified_successful_jobs"] == 6 and not ci["issues"]
    assert all(job["junit"] == dict(tests=actual["tests"], passed=actual["tests"], failures=0, errors=0, skipped=0)
               for job in ci["jobs"])

    # Inspect the downloaded artifact payloads as well as the aggregate manifest.
    for job in ci["jobs"]:
        artifact = AUDIT / f"block12_ci_test_temp/run-{ci['run_id']}" / (
            f"correctness-py{job['python_minor']}-{job['stack']}")
        job_selection = json.loads((artifact / "selection.json").read_text(encoding="utf-8"))
        job_result = json.loads((artifact / "result.json").read_text(encoding="utf-8"))
        assert job_selection["environment"]["commit"] == source
        assert job_selection["excluded_modules"] == selection["excluded_modules"]
        assert job_result["exit_code"] == 0
        assert totals(artifact / "junit.xml") == job["junit"]

    python_paths = [ROOT / p for p in LIBRARY] + [ROOT / TEST] + list(AUDIT.glob("*block12*.py"))
    for path in python_paths:
        ast.parse(path.read_text(encoding="utf-8"))
    links = 0
    for path in list(AUDIT.glob("B12_*.md")) + [AUDIT / "BLOCK11_NAMESPACE.md"]:
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" not in target and not target.startswith("#"):
                assert (path.parent / target.split("#")[0]).exists(), (path, target)
                links += 1
    evidence = dict(baseline=BASELINE, source=source, changed_source_paths=changed,
                    new_cases=actual["tests"] - 2235, local=actual, ci_jobs_verified=6,
                    prior_did_runtime_source=prior["current_head"], did_called_closure_unchanged=True,
                    numeric_runtime_bodies_preserved=len(runtime_checks), exact_reference_comparisons=460,
                    python_files_parsed=len(python_paths), relative_links_checked=links, issues=[])
    (AUDIT / "block12_validation_checks.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
