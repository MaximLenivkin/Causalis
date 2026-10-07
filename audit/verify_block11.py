"""Verify B11's bounded source changes and recorded baseline/local/CI evidence."""
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
BASELINE = "4d6b8143db7a93c1a7eba371fcd144878d80c896"
LIBRARY = {
    "causalis/dgp/causaldata/base.py": "CausalDatasetGenerator",
    "causalis/dgp/causaldata_instrumental/base.py": "InstrumentalGenerator",
}
TEST = "tests/data/test_binary_iv_namespace_contract.py"
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
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
            return node.value.func.attr == "_validate_column_names"
    if isinstance(node, ast.Assign):
        return any(isinstance(t, ast.Name) and t.id == "x_shape" for t in node.targets)
    return isinstance(node, ast.If) and ast.unparse(node.test).startswith("len(names) !=")


def main():
    local = read("block11_integration_result.json")
    source = local["tested_source_checkpoint"]
    assert re.fullmatch(r"[a-f0-9]{40}", source)
    changed = git("diff", "--name-only", BASELINE, source, "--", "causalis", "tests", "scripts").decode().splitlines()
    assert set(changed) == set(LIBRARY) | {TEST}, changed
    assert not git("diff", source, "--name-only", "--", "causalis", "tests", "scripts").strip()
    assert not git("ls-files", "--others", "--exclude-standard", "--", "causalis", "tests", "scripts").strip()
    for path, cls in LIBRARY.items():
        old = methods(git("show", BASELINE + ":" + path), cls)
        new = methods(git("show", source + ":" + path), cls)
        altered = {key for key in old.keys() | new.keys()
                   if ast.dump(old.get(key, ast.Pass())) != ast.dump(new.get(key, ast.Pass()))}
        assert altered <= {"__post_init__", "generate", "_output_column_roles", "_validate_column_names"}, altered
        assert [ast.dump(n) for n in new["generate"].body if not guard_or_doc(n)] == [
            ast.dump(n) for n in old["generate"].body[1:]], path

    focused = totals(AUDIT / "block11_namespace_test_temp/current.xml")
    baseline = totals(AUDIT / "block11_namespace_test_temp/baseline.xml")
    assert focused == dict(tests=163, passed=163, failures=0, errors=0, skipped=0)
    assert baseline == dict(tests=163, passed=60, failures=103, errors=0, skipped=0)
    for mode, counts, checkpoint in (("focused", focused, source), ("baseline", baseline, BASELINE)):
        manifest = read(f"block11_namespace_{mode}_test_result.json")
        assert manifest["counts"] == counts
        assert manifest["wrapper_bindings_and_iv_inheritance_verified"]
        assert manifest["test_file_sha256"] == hashlib.sha256((ROOT / TEST).read_bytes()).hexdigest()
        for path, digest in manifest["source_sha256"].items():
            assert digest == hashlib.sha256(git("show", checkpoint + ":" + path)).hexdigest()
    old_cases = ET.parse(AUDIT / "block11_namespace_test_temp/baseline.xml").getroot().findall(".//testcase")
    new_cases = ET.parse(AUDIT / "block11_namespace_test_temp/current.xml").getroot().findall(".//testcase")
    assert [(c.attrib["classname"], c.attrib["name"]) for c in old_cases] == [
        (c.attrib["classname"], c.attrib["name"]) for c in new_cases]

    review = read("block11_review_probe.json")
    assert review["reviewed_head"] == source and not review["issues"]
    assert review["current_test_module_sha256"] == hashlib.sha256((ROOT / TEST).read_bytes()).hexdigest()
    for path, digest in review["library_sha256"].items():
        assert digest == hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    assert len(review["valid_configurations"]) == 80
    assert all(row["generations"] == 2 and row["exact_frame_dtypes_schema_next10rng"]
               for row in review["valid_configurations"])
    assert len(review["family_specific_available_names"]) == 6
    assert len(review["zero_confounder_containers"]) == 14
    assert all(row["exact_frame_next10rng"] for row in review["family_specific_available_names"])
    assert all(row["generations"] == 2 and row["exact_frame_schema_next10rng"]
               for row in review["zero_confounder_containers"])
    assert len(review["rejected_schemas"]) == 45 and len(review["mutation_checks"]) == 11
    assert all(row["baseline_returned_raw_frame"] and row["new_status"] == "ValueError"
               for row in review["rejected_schemas"])
    assert all(row["status"] == "ValueError" for row in review["mutation_checks"])

    current_junit = AUDIT / "block11_integration_test_temp/junit.xml"
    actual = totals(current_junit)
    assert actual["tests"] == 2072 + focused["tests"]
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

    selection = read("block11_integration_selection.json")
    ci = read("block11_ci_result.json")
    assert selection["environment"]["commit"] == source
    assert selection["excluded_modules"] == ci["excluded_modules"] == read("block10_integration_selection.json")["excluded_modules"]
    assert len(selection["excluded_modules"]) == 7
    assert ci["tested_source_checkpoint"] == source and ci["expected_tests_per_job"] == actual["tests"]
    assert ci["matrix_verified"] and ci["verified_successful_jobs"] == 6 and not ci["issues"]
    assert all(job["junit"] == dict(tests=actual["tests"], passed=actual["tests"], failures=0, errors=0, skipped=0)
               for job in ci["jobs"])

    python_paths = [ROOT / p for p in LIBRARY] + [ROOT / TEST] + list(AUDIT.glob("*block11*.py"))
    for path in python_paths:
        ast.parse(path.read_text(encoding="utf-8"))
    links = 0
    for path in list(AUDIT.glob("B11_*.md")) + [AUDIT / "BLOCK11_NAMESPACE.md"]:
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" not in target and not target.startswith("#"):
                assert (path.parent / target.split("#")[0]).exists(), (path, target)
                links += 1
    evidence = dict(baseline=BASELINE, source=source, changed_source_paths=changed,
                    new_cases=actual["tests"] - 2072, local=actual, ci_jobs_verified=6,
                    prior_did_runtime_source=prior["current_head"], did_called_closure_unchanged=True,
                    python_files_parsed=len(python_paths), relative_links_checked=links, issues=[])
    (AUDIT / "block11_validation_checks.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
