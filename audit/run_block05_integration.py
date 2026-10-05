"""Run B05 integration, excluding explicitly deferred sensitivity modules."""
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "1b2477755c9b89bd2f69f260fd094002bdc26fe2"

if __name__ == "__main__":
    os.chdir(ROOT)
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["MPLCONFIGDIR"] = str(ROOT / "audit/mplconfig")
    os.environ["SKIP_DOCS_BUILD"] = "true"
    excluded = sorted(str(path.relative_to(ROOT)).replace("\\", "/")
                      for path in (ROOT / "tests").rglob("test_*.py")
                      if "sensitivity" in str(path.relative_to(ROOT)).lower())
    args = ["-q", "-p", "no:cacheprovider", "--basetemp=audit/block05_integration_test_temp", "tests"]
    for path in excluded:
        args.extend(["--ignore", path])
    manifest = dict(scope="Repository suite excluding deferred sensitivity test modules",
                    tested_source_checkpoint=SOURCE, excluded_modules=excluded,
                    pytest_args=args, docs_build="SKIP_DOCS_BUILD=true")
    (ROOT / "audit/block05_integration_selection.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)
    raise SystemExit(pytest.main(args))
