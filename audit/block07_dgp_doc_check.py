"""Check that the bounded B07 DGP corrections only change docstrings."""

import ast
import hashlib
import json
from pathlib import Path
import subprocess


BASE = "c234e647e010f5d8bfb805af7ece61392e327537"
ROOT = Path(__file__).resolve().parents[1]
PATHS = [
    "causalis/dgp/multicausaldata/base.py",
    "causalis/scenarios/multi_unconfoundedness/dgp.py",
]


def executable_ast(text):
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0], ast.Expr):
                value = node.body[0].value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    node.body.pop(0)
    return ast.dump(tree, include_attributes=False)


def main():
    checks = []
    for path in PATHS:
        before = subprocess.check_output(
            ["git", "show", f"{BASE}:{path}"], cwd=ROOT
        ).decode("utf-8")
        after = (ROOT / path).read_text(encoding="utf-8")
        old_ast = executable_ast(before)
        new_ast = executable_ast(after)
        checks.append(
            {
                "path": path,
                "executable_ast_equal": old_ast == new_ast,
                "executable_ast_sha256": hashlib.sha256(new_ast.encode("utf-8")).hexdigest(),
            }
        )
    result = {
        "baseline": BASE,
        "checks": checks,
        "issues": [item["path"] for item in checks if not item["executable_ast_equal"]],
    }
    serialized = json.dumps(result, indent=2)
    Path(__file__).with_name("block07_dgp_doc_checks.json").write_text(
        serialized + "\n", encoding="utf-8"
    )
    print(serialized)
    if result["issues"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
