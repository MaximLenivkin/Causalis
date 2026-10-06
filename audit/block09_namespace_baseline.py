"""Reproduce namespace regressions against the frozen pre-B09 generator."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
import xml.etree.ElementTree as ET


BASELINE = "74145665127f8fa5a0bf038d769697ab880854b8"
TARGETS = (
    "causalis/dgp/multicausaldata/base.py",
    "causalis/dgp/multicausaldata/functional.py",
)
TEST = "tests/data/test_multicausal_namespace_contract.py"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default=BASELINE)
    parser.add_argument("--output-stem", default="audit/block09_namespace_baseline_reproduction")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    sha = subprocess.check_output(["git", "rev-parse", args.baseline], text=True).strip()
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", sha, "--", "causalis"], text=True
    ).splitlines()
    other_changes = sorted(set(changed) - set(TARGETS))
    if other_changes:
        raise RuntimeError(
            "This scoped loader needs unchanged non-target package paths: "
            + ", ".join(other_changes)
        )
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = "1"
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["MPLCONFIGDIR"] = str(root / ".venv" / "matplotlib")
    os.environ["SKIP_DOCS_BUILD"] = "true"
    import pytest
    import causalis.dgp.multicausaldata as package

    stem = root / args.output_stem
    stem.parent.mkdir(parents=True, exist_ok=True)
    retained_junit = root / ".venv" / (stem.name + "_junit.xml")
    source_hashes = {}
    started = datetime.now(timezone.utc).isoformat()
    clock_start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="b09-baseline-", dir=root / ".venv") as temp:
        temp_path = Path(temp)
        for path in TARGETS:
            content = subprocess.check_output(["git", "show", sha + ":" + path])
            source = temp_path / Path(path).name
            source.write_bytes(content)
            source_hashes[path] = hashlib.sha256(content).hexdigest()
            leaf = source.stem
            module_name = "causalis.dgp.multicausaldata." + leaf
            spec = importlib.util.spec_from_file_location(module_name, source)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            setattr(package, leaf, module)
        junit = temp_path / "junit.xml"
        pytest_args = [
            "-q", "-p", "no:cacheprovider", "--basetemp=" + str(temp_path / "pytest-temp"),
            "--junitxml=" + str(junit), TEST,
        ]
        with stem.with_suffix(".log").open("w", encoding="utf-8") as output:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                exit_code = int(pytest.main(pytest_args))
        suites = list(ET.parse(junit).getroot().iter("testsuite"))
        counts = {
            key: sum(int(suite.get(key, "0")) for suite in suites)
            for key in ("tests", "failures", "errors", "skipped")
        }
        counts["passed"] = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
        shutil.copyfile(junit, retained_junit)
    report = {
        "baseline_sha": sha,
        "mode": "git-show loader for frozen target modules; all other tracked package paths unchanged",
        "source_sha256": source_hashes,
        "test_file": TEST,
        "test_file_sha256": hashlib.sha256((root / TEST).read_bytes()).hexdigest(),
        "python": sys.version,
        "interpreter": sys.executable,
        "platform": platform.platform(),
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.perf_counter() - clock_start,
        "exit_code": exit_code,
        "counts": counts,
        "junit": str(retained_junit.relative_to(root)),
        "log": str(stem.with_suffix(".log").relative_to(root)),
        "scope": {"full_suite_run": False, "sensitivity_validated": False},
    }
    stem.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"baseline_sha": sha, "exit_code": exit_code, "counts": counts}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
