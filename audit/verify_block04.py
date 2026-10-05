"""Check B04 integration evidence, artifact links, syntax and deferred scope."""

import ast
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
START = "f57f2d32d232e5ab0b358153f6ac564e615d19c3"
SOURCE = "57dbba1e2ecc0c1cab413b1da7f40cfdd8b22131"


def main():
    issues = []
    changed = subprocess.check_output(["git", "diff", "--name-only", START], cwd=ROOT, text=True).splitlines()
    untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], cwd=ROOT, text=True).splitlines()
    paths = sorted(set(changed + untracked))
    sensitive = [path for path in paths if "sensitivity" in path.lower()]
    if sensitive:
        issues.append(dict(error="Deferred sensitivity paths changed", paths=sensitive))
    python_paths = [path for path in paths if path.endswith(".py")]
    for relative in python_paths:
        try:
            ast.parse((ROOT / relative).read_text(encoding="utf-8"), filename=relative)
        except (OSError, SyntaxError) as exc:
            issues.append(dict(path=relative, error=str(exc)))
    log = (AUDIT / "block04_integration_tests.log").read_text(encoding="utf-8")
    summary = re.search(r"(\d+) failed, (\d+) passed, (\d+) warnings in ([\d.]+)s", log)
    failures = re.findall(r"^FAILED (\S+)", log, re.MULTILINE)
    known = "tests/statistics/test_cuped_rct.py::test_shared_design_and_input_unchanged"
    if not summary or int(summary[1]) != 1 or failures != [known]:
        issues.append(dict(error="Unexpected integration result", failure_nodes=failures))
    selection = json.loads((AUDIT / "block04_integration_selection.json").read_text(encoding="utf-8"))
    result = dict(scope=selection["scope"], tested_source_checkpoint=SOURCE,
                  passed=int(summary[2]) if summary else None,
                  failed=int(summary[1]) if summary else None,
                  warnings=int(summary[3]) if summary else None,
                  elapsed_seconds=float(summary[4]) if summary else None,
                  failure_nodes=failures, baseline_failure_id="SC-12",
                  new_failures=[node for node in failures if node != known],
                  excluded_modules=selection["excluded_modules"], full_suite_clean=False)
    (AUDIT / "block04_integration_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    # Reports may link to this runner's own output. Materialize it before
    # checking links, then replace the interim record with complete evidence.
    validation_path = AUDIT / "block04_validation_checks.json"
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
    evidence = dict(start_commit=START, local_links_checked=checked,
                    python_files_parsed=len(python_paths),
                    library_paths_changed=[path for path in paths if path.startswith("causalis/")],
                    sensitivity_paths_changed=sensitive, integration_result=result, issues=issues)
    validation_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return bool(issues)


if __name__ == "__main__":
    raise SystemExit(main())
