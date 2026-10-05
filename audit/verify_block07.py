"""Verify committed B07 source, scope, doc-only paths and actual test evidence."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

from summarize_block07_ci import EXCLUDED

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
START = "c234e647e010f5d8bfb805af7ece61392e327537"
DOC_ONLY = ["causalis/scenarios/did/model.py", "causalis/scenarios/did/refutation/diagnostics.py",
            "causalis/dgp/multicausaldata/base.py", "causalis/scenarios/multi_unconfoundedness/dgp.py"]
ALLOWED_LIBRARY = set(DOC_ONLY + ["causalis/data_contracts/panel_data_did.py",
    "causalis/scenarios/unconfoundedness/_utils.py", "causalis/scenarios/unconfoundedness/model.py",
    "causalis/scenarios/multi_unconfoundedness/_utils.py", "causalis/scenarios/multi_unconfoundedness/model.py"])
NEW_TESTS = ["tests/scenarios/did/test_did_earliest_pre_period.py",
             "tests/inference/test_nuisance_prediction_contract.py"]
ALLOWED_FUNCTIONS = {
    "causalis/data_contracts/panel_data_did.py": {"PanelDataDID.att_gt_cells"},
    "causalis/scenarios/unconfoundedness/_utils.py": {"_predict_prob_or_value"},
    "causalis/scenarios/unconfoundedness/model.py": {"IRM._store_cross_fitted_predictions"},
    "causalis/scenarios/multi_unconfoundedness/_utils.py": {"_predict_propensity_matrix"},
    "causalis/scenarios/multi_unconfoundedness/model.py": {
        "MultiTreatmentIRM._store_cross_fitted_predictions",
        "MultiTreatmentIRM._predict_binary_outcome_probability",
        "MultiTreatmentIRM._fit_one_outcome_nuisance",
        "MultiTreatmentIRM._cross_fit_nuisances"},
}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8").strip()


class WithoutDocstrings(ast.NodeTransformer):
    def owner(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr):
            expression = node.body[0].value
            if isinstance(expression, ast.Constant) and isinstance(expression.value, str):
                node.body = node.body[1:]
        return node
    visit_Module = visit_ClassDef = visit_FunctionDef = visit_AsyncFunctionDef = owner


def executable_ast(source):
    return ast.dump(WithoutDocstrings().visit(ast.parse(source)), include_attributes=False)


class IgnoreAllowedBodies(ast.NodeTransformer):
    def __init__(self, allowed):
        self.allowed = allowed
        self.owners = []
    def visit_ClassDef(self, node):
        self.owners.append(node.name)
        self.generic_visit(node)
        self.owners.pop()
        return node
    def visit_FunctionDef(self, node):
        name = ".".join([*self.owners, node.name])
        if name in self.allowed:
            node.body = [ast.Pass()]
        else:
            self.generic_visit(node)
        return node
    visit_AsyncFunctionDef = visit_FunctionDef


def outside_allowed_ast(source, allowed):
    tree = WithoutDocstrings().visit(ast.parse(source))
    return ast.dump(IgnoreAllowedBodies(allowed).visit(tree), include_attributes=False)


def main():
    selection = json.loads((AUDIT / "block07_integration_selection.json").read_text(encoding="utf-8"))
    result = json.loads((AUDIT / "block07_integration_result.json").read_text(encoding="utf-8"))
    source = result["tested_source_checkpoint"]
    paths = set(git("diff", "--name-only", START).splitlines())
    paths.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    issues = []
    sensitive = sorted(path for path in paths if "sensitivity" in path.lower())
    if sensitive:
        issues.append({"error": "Deferred sensitivity paths changed", "paths": sensitive})
    source_drift = git("diff", source, "--name-only", "--", "causalis", "tests", "scripts")
    untracked_source = git("ls-files", "--others", "--exclude-standard", "--", "causalis", "tests", "scripts")
    if source_drift or untracked_source:
        issues.append({"error": "Source differs from tested checkpoint", "diff": source_drift,
                       "untracked": untracked_source})
    library_paths = sorted(path for path in paths if path.startswith("causalis/"))
    if set(library_paths) != ALLOWED_LIBRARY:
        issues.append({"error": "Unexpected library scope", "paths": library_paths})
    test_paths = sorted(path for path in paths if path.startswith("tests/"))
    if set(test_paths) != set(NEW_TESTS):
        issues.append({"error": "Unexpected test changes", "paths": test_paths})
    doc_only_verified = []
    for path in DOC_ONLY:
        if executable_ast(git("show", f"{START}:{path}")) != executable_ast((ROOT / path).read_text(encoding="utf-8")):
            issues.append({"error": "Doc-only path changed runtime", "path": path})
        else:
            doc_only_verified.append(path)
    function_scope_verified = []
    for path, functions in ALLOWED_FUNCTIONS.items():
        if outside_allowed_ast(git("show", f"{START}:{path}"), functions) != outside_allowed_ast(
                (ROOT / path).read_text(encoding="utf-8"), functions):
            issues.append({"error": "Runtime changed outside approved functions", "path": path})
        else:
            function_scope_verified.append(path)
    python_paths = sorted(path for path in paths if path.endswith(".py"))
    for path in python_paths:
        try:
            ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=path)
        except (OSError, SyntaxError) as error:
            issues.append({"error": str(error), "path": path})
    if selection["tested_source_checkpoint"] != source or selection["environment"]["commit"] != source:
        issues.append({"error": "Integration source provenance mismatch"})
    if (selection["scope"] != "correctness" or selection["selected_full_suite"]
            or selection["excluded_modules"] != EXCLUDED or selection["collect_only"]):
        issues.append({"error": "Unexpected integration scope"})
    junit = ET.parse(AUDIT / "block07_integration_test_temp/junit.xml")
    cases = junit.findall(".//testcase")
    failures = junit.findall(".//failure") + junit.findall(".//error")
    skipped = junit.findall(".//skipped")
    new_cases = {Path(path).stem: sum(case.attrib.get("classname", "").endswith(Path(path).stem)
                                     for case in cases) for path in NEW_TESTS}
    expected_tests = 1582 + sum(new_cases.values())
    if (result["exit_code"] != 0 or failures or skipped or len(cases) != expected_tests
            or result["passed"] != len(cases) or not all(new_cases.values())):
        issues.append({"error": "Unexpected local integration result", "cases": len(cases),
                       "expected": expected_tests, "failures": len(failures), "skipped": len(skipped)})
    matrix = json.loads((AUDIT / "block07_ci_result.json").read_text(encoding="utf-8"))
    if (matrix["tested_source_checkpoint"] != source or matrix["expected_tests_per_job"] != expected_tests
            or matrix["excluded_modules"] != EXCLUDED or matrix["issues"]
            or not matrix["matrix_verified"] or matrix["verified_successful_jobs"] != 6):
        issues.append({"error": "CI matrix incomplete or incompatible evidence"})
    for job in matrix["jobs"]:
        if (not job["artifact_verified"] or job["conclusion"] != "success"
                or job["junit"]["passed"] != expected_tests
                or job["environment"]["commit"] != source):
            issues.append({"error": "Invalid CI job evidence", "job": job["name"]})
    # The report links to this verifier's output. Create it before the local
    # link walk, then replace the temporary status with the complete evidence.
    (AUDIT / "block07_validation_checks.json").write_text(
        json.dumps({"status": "verification in progress", "tested_source_checkpoint": source}),
        encoding="utf-8")
    checked = 0
    for report in AUDIT.glob("*.md"):
        for target in re.findall(r"\]\((D:/[^)]+)\)", report.read_text(encoding="utf-8")):
            match = re.fullmatch(r"(.*?)(?::(\d+))?", target)
            path = Path(match[1])
            checked += 1
            if not path.exists():
                issues.append({"error": "Missing local artifact", "report": report.name, "target": target})
            elif match[2] and not 1 <= int(match[2]) <= len(path.read_text(encoding="utf-8").splitlines()):
                issues.append({"error": "Line out of bounds", "report": report.name, "target": target})
    evidence = dict(start_commit=START, tested_source_checkpoint=source,
                    python_files_parsed=len(python_paths), local_links_checked=checked,
                    library_paths_changed=library_paths, doc_only_runtime_verified=doc_only_verified,
                    runtime_function_scope_verified=function_scope_verified,
                    approved_runtime_functions={path: sorted(functions) for path, functions in ALLOWED_FUNCTIONS.items()},
                    sensitivity_paths_changed=sensitive, source_changes_after_integration=source_drift,
                    new_cases=new_cases, total_new_cases=sum(new_cases.values()), integration=result,
                    ci_run=matrix["run_id"], matrix_verified=matrix["matrix_verified"], issues=issues)
    (AUDIT / "block07_validation_checks.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return int(bool(issues))


if __name__ == "__main__":
    raise SystemExit(main())
