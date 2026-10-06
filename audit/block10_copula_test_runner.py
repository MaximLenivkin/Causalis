"""Run the same categorical copula tests on frozen baseline or working tree."""

from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET


BASELINE = "83b63836dbd0c4793c24dd95ff7dc18c443792ad"
SOURCE = "causalis/dgp/base.py"
TEST = "tests/data/test_copula_categorical_coordinates.py"


class FrozenSharedBase(importlib.abc.MetaPathFinder):
    def __init__(self, path):
        self.path = path

    def find_spec(self, fullname, path=None, target=None):
        if fullname == "causalis.dgp.base":
            return importlib.util.spec_from_file_location(fullname, self.path)
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("baseline", "focused"), required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = "1"
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["MPLCONFIGDIR"] = str(root / ".venv" / "matplotlib")
    os.environ["SKIP_DOCS_BUILD"] = "true"
    changed = subprocess.check_output([
        "git", "diff", "--name-only", BASELINE, "--", "causalis",
    ], text=True).splitlines()
    assert not (set(changed) - {SOURCE}), changed
    frozen_source = subprocess.check_output(["git", "show", BASELINE + ":" + SOURCE])
    source = frozen_source if args.mode == "baseline" else (root / SOURCE).read_bytes()
    test_hash = hashlib.sha256((root / TEST).read_bytes()).hexdigest()
    temp_root = root / "audit" / "block10_copula_test_temp"
    temp_root.mkdir(exist_ok=True)
    junit = temp_root / ("current.xml" if args.mode == "focused" else "baseline.xml")
    log = root / ("audit/block10_copula_" + args.mode + "_tests.log")
    started = datetime.now(timezone.utc).isoformat()
    timer = time.perf_counter()
    with contextlib.ExitStack() as cleanup:
        if args.mode == "baseline":
            snapshot_root = Path(cleanup.enter_context(
                tempfile.TemporaryDirectory(prefix="b10-copula-", dir=root / ".venv")
            ))
            snapshot = snapshot_root / "base.py"
            snapshot.write_bytes(frozen_source)
            finder = FrozenSharedBase(snapshot)
            sys.meta_path.insert(0, finder)
            cleanup.callback(sys.meta_path.remove, finder)
        import pytest
        assert "causalis.dgp.base" not in sys.modules, "baseline interception must precede package import"
        with log.open("w", encoding="utf-8") as output:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                exit_code = int(pytest.main([
                    "-q", "-p", "no:cacheprovider", TEST,
                    "--basetemp=" + str(root / ".venv" / ("block10-copula-" + args.mode + "-temp")),
                    "--junitxml=" + str(junit),
                ]))
        actual_module = sys.modules["causalis.dgp.base"]
        loaded_path = Path(actual_module.__file__)
        assert hashlib.sha256(loaded_path.read_bytes()).hexdigest() == hashlib.sha256(source).hexdigest()
    assert test_hash == hashlib.sha256((root / TEST).read_bytes()).hexdigest()
    suites = list(ET.parse(junit).getroot().iter("testsuite"))
    counts = {
        key: sum(int(suite.get(key, "0")) for suite in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }
    counts["passed"] = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    result = {
        "mode": args.mode,
        "baseline_sha": BASELINE,
        "head_at_start": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_file": SOURCE,
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "test_file": TEST,
        "test_file_sha256": test_hash,
        "counts": counts,
        "exit_code": exit_code,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.perf_counter() - timer,
        "python": sys.version,
        "platform": platform.platform(),
        "junit": str(junit.relative_to(root)),
        "log": str(log.relative_to(root)),
        "non_target_tracked_package_paths_unchanged": True,
        "full_suite_run": False,
        "sensitivity_validated": False,
    }
    output_json = root / ("audit/block10_copula_" + args.mode + "_test_result.json")
    output_json.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"mode": args.mode, "exit_code": exit_code, "counts": counts}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
