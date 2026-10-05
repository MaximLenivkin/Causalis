"""Check B02 artifacts and scope without rewriting historical audit evidence."""

import ast
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
START = "d092e8d42f384118c316fb36ecd4b452d7d030ef"


def main():
    issues = []
    links_checked = 0
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

    changed = subprocess.check_output(
        ["git", "diff", "--name-only", START], cwd=ROOT, text=True
    ).splitlines()
    sensitive = [path for path in changed if "sensitivity" in path.lower()]
    if sensitive:
        issues.append({"error": "sensitivity paths changed", "paths": sensitive})
    library_paths = [path for path in changed if path.startswith("causalis/")]
    # Include new, not-yet-staged Python evidence scripts/tests as well.
    python_paths = set(path for path in changed if path.endswith(".py"))
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

    result = {
        "start_commit": START,
        "local_links_checked": links_checked,
        "python_files_parsed": len(python_paths),
        "library_paths_changed": library_paths,
        "sensitivity_paths_changed": sensitive,
        "issues": issues,
    }
    (AUDIT / "block02_validation_checks.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return bool(issues)


if __name__ == "__main__":
    raise SystemExit(main())
