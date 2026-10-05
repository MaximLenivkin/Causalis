"""Inventory review surface; no package imports or repository mutations."""
import ast
import csv
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
rows = []
for path in sorted((root / "causalis").rglob("*.py")):
    if path.name == "_version.py":
        continue
    text = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)
    rel = path.relative_to(root).as_posix()
    if "/scenarios/unconfoundedness/" in rel or "/scenarios/multi_unconfoundedness/" in rel or any(x in rel for x in ["/scenarios/gate/", "/scenarios/uplift/"]) or rel.endswith("_orthogonal.py"):
        owner = "DML"
    elif "/scenarios/" in rel and not rel.endswith("__init__.py"):
        owner = "Other scenarios"
    else:
        owner = "Root contracts/shared/DGP"
    rows.append({"path": rel, "lines": len(text.splitlines()), "owner": owner,
                 "functions": sum(isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) for x in ast.walk(tree)),
                 "module_docstring": bool(ast.get_docstring(tree)), "syntax": "OK"})
with (root / "audit" / "MODULE_INVENTORY.csv").open("w", encoding="utf-8-sig", newline="") as out:
    writer = csv.DictWriter(out, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
notebooks = list((root / "notebooks").rglob("*.ipynb"))
stats = {"python_files": len(rows), "python_lines": sum(r["lines"] for r in rows),
         "test_files": len(list((root / "tests").rglob("test_*.py"))),
         "notebooks": len(notebooks), "notebook_cells": 0}
for path in notebooks:
    stats["notebook_cells"] += len(json.loads(path.read_text(encoding="utf-8"))["cells"])
(root / "audit" / "inventory_summary.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
print(json.dumps(stats, indent=2))
