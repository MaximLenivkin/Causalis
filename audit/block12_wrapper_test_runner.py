"""Run identical wrapper namespace tests with six frozen or current modules."""

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


BASELINE = "eb6dfe23f0a97991b6e3d6109febc1b0170e128d"
SOURCES = (
    "causalis/dgp/base.py",
    "causalis/dgp/causaldata/preperiod.py",
    "causalis/dgp/causaldata/base.py",
    "causalis/dgp/causaldata/functional.py",
    "causalis/dgp/causaldata_instrumental/base.py",
    "causalis/dgp/causaldata_instrumental/functional.py",
)
TEST = "tests/data/test_wrapper_namespace_contract.py"


class FrozenModules(importlib.abc.MetaPathFinder):
    def __init__(self, paths):
        self.paths = paths

    def find_spec(self, fullname, path=None, target=None):
        if fullname in self.paths:
            return importlib.util.spec_from_file_location(fullname, self.paths[fullname])
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("baseline", "focused"), required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["MPLCONFIGDIR"] = str(root / ".venv" / "matplotlib")
    os.environ["SKIP_DOCS_BUILD"] = "true"
    os.environ["PYTEST_ADDOPTS"] = ""
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    changed = subprocess.check_output([
        "git", "diff", "--name-only", BASELINE, "--", "causalis",
    ], text=True).splitlines()
    assert not (set(changed) - set(SOURCES)), changed
    frozen_sources = {
        path: subprocess.check_output(["git", "show", BASELINE + ":" + path])
        for path in SOURCES
    }
    loaded_sources = frozen_sources if args.mode == "baseline" else {
        path: (root / path).read_bytes() for path in SOURCES
    }
    test_hash = hashlib.sha256((root / TEST).read_bytes()).hexdigest()
    temporary_root = root / "audit" / "block12_wrapper_test_temp"
    temporary_root.mkdir(exist_ok=True)
    junit = temporary_root / ("baseline.xml" if args.mode == "baseline" else "current.xml")
    log = root / ("audit/block12_wrapper_" + args.mode + "_tests.log")
    started = datetime.now(timezone.utc).isoformat()
    timer = time.perf_counter()
    with contextlib.ExitStack() as cleanup:
        if args.mode == "baseline":
            snapshot_root = Path(cleanup.enter_context(
                tempfile.TemporaryDirectory(prefix="b12-wrappers-", dir=root / ".venv")
            ))
            snapshots = {}
            for path, content in frozen_sources.items():
                snapshot = snapshot_root / path
                snapshot.parent.mkdir(parents=True, exist_ok=True)
                snapshot.write_bytes(content)
                snapshots[path[:-3].replace("/", ".")] = snapshot
            finder = FrozenModules(snapshots)
            sys.meta_path.insert(0, finder)
            cleanup.callback(sys.meta_path.remove, finder)
        import pytest
        assert all(path[:-3].replace("/", ".") not in sys.modules for path in SOURCES)
        with log.open("w", encoding="utf-8") as output:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                exit_code = int(pytest.main([
                    "-q", "-p", "no:cacheprovider", TEST,
                    "--basetemp=" + str(root / ".venv" / ("block12-wrapper-" + args.mode + "-temp")),
                    "--junitxml=" + str(junit),
                ]))
        for path in SOURCES:
            module = sys.modules[path[:-3].replace("/", ".")]
            assert Path(module.__file__).read_bytes() == loaded_sources[path]
        shared = sys.modules["causalis.dgp.base"]
        pre = sys.modules["causalis.dgp.causaldata.preperiod"]
        binary = sys.modules["causalis.dgp.causaldata.base"].CausalDatasetGenerator
        iv = sys.modules["causalis.dgp.causaldata_instrumental.base"].InstrumentalGenerator
        binary_wrapper = sys.modules["causalis.dgp.causaldata.functional"]
        iv_wrapper = sys.modules["causalis.dgp.causaldata_instrumental.functional"]
        assert iv.__bases__[0] is binary
        assert binary_wrapper.CausalDatasetGenerator is binary
        assert iv_wrapper.InstrumentalGenerator is iv
        assert binary_wrapper._add_ancillary_info is shared._add_ancillary_info
        assert iv_wrapper._add_ancillary_info is shared._add_ancillary_info
        assert binary_wrapper.add_preperiod_covariate is pre.add_preperiod_covariate
    assert test_hash == hashlib.sha256((root / TEST).read_bytes()).hexdigest()
    suites = list(ET.parse(junit).getroot().iter("testsuite"))
    counts = {
        key: sum(int(suite.get(key, "0")) for suite in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }
    counts["passed"] = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    cases = [case.get("classname") + "::" + case.get("name") for suite in suites for case in suite.findall("testcase")]
    result = {
        "mode": args.mode,
        "baseline_sha": BASELINE,
        "head_at_start": head,
        "source_files": list(SOURCES),
        "source_sha256": {path: hashlib.sha256(data).hexdigest() for path, data in loaded_sources.items()},
        "test_file": TEST,
        "test_file_sha256": test_hash,
        "collected_case_ids": cases,
        "counts": counts,
        "exit_code": exit_code,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.perf_counter() - timer,
        "python": sys.version,
        "platform": platform.platform(),
        "junit": str(junit.relative_to(root)),
        "log": str(log.relative_to(root)),
        "wrapper_bindings_and_iv_inheritance_verified": True,
        "shared_augmentation_bindings_verified": True,
        "non_target_tracked_package_paths_unchanged": True,
        "full_suite_run": False,
        "sensitivity_validated": False,
    }
    result_path = root / ("audit/block12_wrapper_" + args.mode + "_test_result.json")
    result_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"mode": args.mode, "exit_code": exit_code, "counts": counts}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
