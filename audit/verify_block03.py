"""Check B03 artifacts and scope, preserving historical audit evidence."""

import ast
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
START = "790c8aba17b004e08061949f5e9e45de2ad3ab43"


def main():
    issues = []
    links_checked = 0
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", START], cwd=ROOT, text=True
    ).splitlines()
    sensitive = [path for path in changed if "sensitivity" in path.lower()]
    if sensitive:
        issues.append({"error": "sensitivity paths changed", "paths": sensitive})
    python_paths = {path for path in changed if path.endswith(".py")}
    python_paths.update(
        subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard", "--", "*.py"],
            cwd=ROOT, text=True,
        ).splitlines()
    )
    for relative in sorted(python_paths):
        try:
            ast.parse((ROOT / relative).read_text(encoding="utf-8"), filename=relative)
        except (OSError, SyntaxError) as error:
            issues.append({"path": relative, "error": str(error)})
    integration_log = (AUDIT / "block03_integration_tests.log").read_text(encoding="utf-8")
    summary = re.search(r"(\d+) failed, (\d+) passed, (\d+) warnings in ([\d.]+)s", integration_log)
    failures = re.findall(r"^FAILED (\S+)", integration_log, re.MULTILINE)
    known_failure = "tests/statistics/test_cuped_rct.py::test_shared_design_and_input_unchanged"
    if not summary or failures != [known_failure] or int(summary[1]) != 1:
        issues.append({"error": "unexpected integration result", "failures": failures})
    selection = json.loads((AUDIT / "block03_integration_selection.json").read_text(encoding="utf-8"))
    integration = {
        "scope": selection["scope"],
        "tested_source_checkpoint": "113c693a0dd721c6e77dfe84bc647d2ffb4c7841",
        "passed": int(summary[2]) if summary else None,
        "failed": int(summary[1]) if summary else None,
        "warnings": int(summary[3]) if summary else None,
        "elapsed_seconds": float(summary[4]) if summary else None,
        "failure_nodes": failures,
        "baseline_failure_id": "SC-12",
        "new_failures": [node for node in failures if node != known_failure],
        "excluded_modules": selection["excluded_modules"],
        "full_suite_clean": False,
    }
    (AUDIT / "block03_integration_result.json").write_text(
        json.dumps(integration, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Check artifact links after generating the result JSON they may reference.
    for report in sorted(AUDIT.glob("*.md")):
        content = report.read_text(encoding="utf-8")
        for target in re.findall(r"\]\((D:/[^)]+)\)", content):
            match = re.fullmatch(r"(.*?)(?::(\d+))?", target)
            path = Path(match[1])
            links_checked += 1
            if not path.exists():
                issues.append({"report": report.name, "target": target, "error": "missing"})
            elif match[2] and not 1 <= int(match[2]) <= len(path.read_text(encoding="utf-8").splitlines()):
                issues.append({"report": report.name, "target": target, "error": "line out of bounds"})
    result = {
        "start_commit": START,
        "local_links_checked": links_checked,
        "python_files_parsed": len(python_paths),
        "library_paths_changed": [path for path in changed if path.startswith("causalis/")],
        "sensitivity_paths_changed": sensitive,
        "integration_result": integration,
        "issues": issues,
    }
    (AUDIT / "block03_validation_checks.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return bool(issues)


if __name__ == "__main__":
    raise SystemExit(main())
