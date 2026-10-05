"""Check B06 artifacts, real integration result and unchanged executable source."""
import ast
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
START = "bf2ea87534e4eaf82266cb61d905b7e876cc2e1d"
SOURCE = "09e00de5a9d3dc915c6d59627f8b0ebc875dd4e9"
BENCHMARK_SOURCE = "d292b3c2f83ec94ef75652a17f3e34436c71902f"


class WithoutDocstrings(ast.NodeTransformer):
    def visit_Module(self, node):
        return self._visit_owner(node)

    def visit_ClassDef(self, node):
        return self._visit_owner(node)

    def visit_FunctionDef(self, node):
        return self._visit_owner(node)

    def visit_AsyncFunctionDef(self, node):
        return self._visit_owner(node)

    def _visit_owner(self, node):
        self.generic_visit(node)
        if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            node.body = node.body[1:]
        return node


def executable_ast(text):
    return ast.dump(WithoutDocstrings().visit(ast.parse(text)), include_attributes=False)


def git_output(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8")


def main():
    issues = []
    paths = sorted(set(git_output("diff", "--name-only", START).splitlines()
                       + git_output("ls-files", "--others", "--exclude-standard").splitlines()))
    sensitive = [path for path in paths if "sensitivity" in path.lower()]
    if sensitive:
        issues.append(dict(error="Deferred sensitivity paths changed", paths=sensitive))
    source_diff = git_output("diff", "--name-only", SOURCE, "--", "causalis", "tests").splitlines()
    prose_changes = []
    for path in source_diff:
        original = git_output("show", f"{SOURCE}:{path}")
        current = (ROOT / path).read_text(encoding="utf-8")
        if not path.startswith("causalis/") or executable_ast(original) != executable_ast(current):
            issues.append(dict(error="Executable source differs from tested checkpoint", path=path))
        else:
            prose_changes.append(path)
    python_paths = [path for path in paths if path.endswith(".py")]
    for path in python_paths:
        try:
            ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=path)
        except (OSError, SyntaxError) as error:
            issues.append(dict(path=path, error=str(error)))
    for path in git_output("ls-files", "--others", "--exclude-standard").splitlines():
        if path.startswith(("causalis/", "tests/")):
            issues.append(dict(error="Untested untracked source", path=path))
    measured_paths = [
        "causalis/data_contracts/causaldata.py", "causalis/data_contracts/iv_causal_data.py",
        "causalis/data_contracts/multicausaldata.py", "causalis/data_contracts/rct_causal_data.py",
        "causalis/data_contracts/_duplicate_columns.py",
        "causalis/scenarios/unconfoundedness/_utils.py",
        "causalis/scenarios/multi_unconfoundedness/_utils.py",
        "causalis/scenarios/unconfoundedness/model.py", "causalis/shared/outcome_plots.py",
    ]
    unchanged_measured_paths = []
    for path in measured_paths:
        if executable_ast(git_output("show", f"{BENCHMARK_SOURCE}:{path}")) != executable_ast(
                (ROOT / path).read_text(encoding="utf-8")):
            issues.append(dict(error="Measured benchmark path changed", path=path))
        else:
            unchanged_measured_paths.append(path)

    selection = json.loads((AUDIT / "block06_integration_selection.json").read_text())
    result = json.loads((AUDIT / "block06_integration_result.json").read_text())
    log = (AUDIT / "block06_integration_tests.log").read_text(encoding="utf-8")
    summary = re.search(r"^(\d+) passed(?:, (\d+) warnings)? in ([\d.]+)s", log, re.MULTILINE)
    junit = ET.parse(AUDIT / "block06_integration_test_temp/final-junit.xml")
    tests = junit.findall(".//testcase")
    failures = junit.findall(".//failure") + junit.findall(".//error")
    skipped = junit.findall(".//skipped")
    if not summary or int(summary[1]) != 1582 or result["exit_code"] != 0 or failures or skipped:
        issues.append(dict(error="Unexpected integration result", summary=summary[0] if summary else None,
                           exit_code=result["exit_code"], failures=len(failures), skipped=len(skipped)))
    if len(tests) != 1582 or len(selection["excluded_modules"]) != 7 or selection["selected_full_suite"]:
        issues.append(dict(error="Unexpected integration selection", cases=len(tests)))
    result.update(passed=int(summary[1]) if summary else None, failed=len(failures), skipped=len(skipped),
                  warnings=int(summary[2] or 0) if summary else None,
                  pytest_elapsed_seconds=float(summary[3]) if summary else None,
                  full_suite_clean=False, scoped_suite_clean=not failures and result["exit_code"] == 0,
                  new_cases=dict(ci=11, duplicates=71, binary=74, kde=37, iv_compat=13, total=206))
    (AUDIT / "block06_integration_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    matrix = json.loads((AUDIT / "block06_ci_result.json").read_text(encoding="utf-8"))
    if matrix["tested_source_checkpoint"] != SOURCE:
        issues.append(dict(error="CI used a different source checkpoint"))
    verified_jobs = [job for job in matrix["jobs"]
                     if job["conclusion"] == "success" and job["artifact_verified"]]
    if matrix["issues"] or len(verified_jobs) != matrix["verified_successful_jobs"]:
        issues.append(dict(error="CI artifact summary inconsistent", details=matrix["issues"]))
    for job in verified_jobs:
        if (job["junit"]["passed"] != 1582 or job["junit"]["failures"]
                or job["junit"]["errors"] or job["junit"]["skipped"]):
            issues.append(dict(error="Unexpected CI success coverage", job=job["name"]))
    if matrix["matrix_verified"] and (len(verified_jobs) != 6 or matrix["run_conclusion"] != "success"):
        issues.append(dict(error="False matrix completion claim"))

    checked = 0
    for report in AUDIT.glob("*.md"):
        for target in re.findall(r"\]\((D:/[^)]+)\)", report.read_text(encoding="utf-8")):
            match = re.fullmatch(r"(.*?)(?::(\d+))?", target)
            path = Path(match[1])
            checked += 1
            if not path.exists():
                issues.append(dict(report=report.name, target=target, error="Missing local artifact"))
            elif match[2] and not 1 <= int(match[2]) <= len(path.read_text(encoding="utf-8").splitlines()):
                issues.append(dict(report=report.name, target=target, error="Line out of bounds"))
    evidence = dict(start_commit=START, tested_executable_checkpoint=SOURCE,
                    source_prose_only_changes_after_checkpoint=prose_changes,
                    python_files_parsed=len(python_paths), local_links_checked=checked,
                    library_paths_changed=[path for path in paths if path.startswith("causalis/")],
                    sensitivity_paths_changed=sensitive, integration=result,
                    benchmark_measured_source=BENCHMARK_SOURCE,
                    benchmark_measured_paths_unchanged=unchanged_measured_paths,
                    matrix_validation=dict(run_id=matrix["run_id"], source=matrix["tested_source_checkpoint"],
                                           verified_successful_jobs=len(verified_jobs),
                                           all_six_jobs_verified=matrix["matrix_verified"],
                                           pending_is_not_pass=True), issues=issues)
    (AUDIT / "block06_validation_checks.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return bool(issues)


if __name__ == "__main__":
    raise SystemExit(main())
