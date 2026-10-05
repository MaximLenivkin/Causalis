"""Build API in an isolated audit copy; preserve checked-in published artifacts."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / "audit" / "docs_build_check" / "repo"
if "--build-only" not in sys.argv:
    target.mkdir(parents=True, exist_ok=False)
    shutil.copy2(root / "pyproject.toml", target / "pyproject.toml")
    for name in ["causalis", "scripts"]:
        shutil.copytree(root / name, target / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (target / "notebooks").mkdir()
    shutil.copytree(root / "notebooks" / "api", target / "notebooks" / "api")
elif not (target / "scripts" / "generate_api_reference.py").is_file():
    raise SystemExit("Missing isolated audit copy; run without --build-only first.")
tmp = root / "audit" / "docs_build_temp"
tmp.mkdir(exist_ok=True)
env = dict(os.environ, TEMP=str(tmp), TMP=str(tmp), MPLCONFIGDIR=str(root / "audit" / "mplconfig"))
result = subprocess.run([sys.executable, "scripts/generate_api_reference.py"], cwd=target,
                        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
(root / "audit" / "docs_build.log").write_text(result.stdout, encoding="utf-8")
print(f"exit_code={result.returncode}")
print(result.stdout[-3500:])
print(f"html_modules={len(list((target / 'notebooks/api/html/apidocs/causalis').glob('*.html')))}")
raise SystemExit(result.returncode)
