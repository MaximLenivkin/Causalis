"""Verify B05 source checkpoint, integration evidence, links and deferred scope."""
import ast
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
START = "c55909491c8c50d603a8bf348b4beca11b623e02"
SOURCE = "1b2477755c9b89bd2f69f260fd094002bdc26fe2"


def main():
    issues = []
    changed = subprocess.check_output(["git", "diff", "--name-only", START], cwd=ROOT, text=True).splitlines()
    untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], cwd=ROOT, text=True).splitlines()
    paths = sorted(set(changed + untracked))
    sensitive = [path for path in paths if "sensitivity" in path.lower()]
    if sensitive:
        issues.append(dict(error="Deferred sensitivity paths changed", paths=sensitive))
    source_diff = subprocess.check_output(["git", "diff", "--name-only", SOURCE, "--", "causalis", "tests"],
                                          cwd=ROOT, text=True).splitlines()
    if source_diff or any(path.startswith(("causalis/", "tests/")) for path in untracked):
        issues.append(dict(error="Source differs from tested checkpoint", paths=source_diff))
    python_paths = [path for path in paths if path.endswith(".py")]
    for path in python_paths:
        try:
            ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=path)
        except (OSError, SyntaxError) as exc:
            issues.append(dict(path=path, error=str(exc)))
    log = (AUDIT / "block05_integration_tests.log").read_text(encoding="utf-8")
    summary = re.search(r"^(\d+) passed(?:, (\d+) warnings)? in ([\d.]+)s", log, re.MULTILINE)
    failures = re.findall(r"^FAILED (\S+)", log, re.MULTILINE)
    if not summary or int(summary[1]) != 1376 or failures:
        issues.append(dict(error="Unexpected integration result", failure_nodes=failures))
    selection = json.loads((AUDIT / "block05_integration_selection.json").read_text(encoding="utf-8"))
    result = dict(scope=selection["scope"], tested_source_checkpoint=SOURCE,
                  passed=int(summary[1]) if summary else None, failed=0 if summary and not failures else None,
                  warnings=int(summary[2] or 0) if summary else None,
                  elapsed_seconds=float(summary[3]) if summary else None,
                  failure_nodes=failures, previous_baseline_failure="SC-12 fixed and original test retained",
                  excluded_modules=selection["excluded_modules"], sensitivity_validated=False,
                  docs_build=selection["docs_build"], full_suite_clean=False,
                  scoped_suite_clean=bool(summary and not failures),
                  new_test_cases=dict(names=24, stable_design=22, iv=60, scm=31, total=137))
    (AUDIT / "block05_integration_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    validation_path = AUDIT / "block05_validation_checks.json"
    validation_path.write_text(json.dumps(dict(start_commit=START, status="checking artifacts")), encoding="utf-8")
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
    evidence = dict(start_commit=START, local_links_checked=checked, python_files_parsed=len(python_paths),
                    library_paths_changed=[path for path in paths if path.startswith("causalis/")],
                    sensitivity_paths_changed=sensitive, integration_result=result, issues=issues)
    validation_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return bool(issues)


if __name__ == "__main__":
    raise SystemExit(main())
