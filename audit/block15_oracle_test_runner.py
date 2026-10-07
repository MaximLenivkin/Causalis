"""Run identical marginal-propensity tests on frozen or current public modules."""

from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import importlib.abc
import importlib.metadata
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


BASELINE = "71f6a619b04e0ab8fab388fb95b7d0f3d6631b96"
SOURCES = (
    "causalis/dgp/multicausaldata/base.py",
    "causalis/dgp/multicausaldata/functional.py",
)
DEPENDENCIES = (
    "causalis/dgp/base.py",
    "causalis/data_contracts/multicausaldata.py",
    "causalis/dgp/multicausaldata/__init__.py",
    "causalis/data_contracts/_duplicate_columns.py",
)
TEST = "tests/data/test_multicausal_marginal_propensity.py"


def _module_name(path):
    if path.endswith("/__init__.py"):
        return path[:-12].replace("/", ".")
    return path[:-3].replace("/", ".")


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
    dependency_sources = {
        path: subprocess.check_output(["git", "show", BASELINE + ":" + path])
        for path in DEPENDENCIES
    }
    for path, content in dependency_sources.items():
        assert (root / path).read_bytes() == content, path
    loaded_sources = frozen_sources if args.mode == "baseline" else {
        path: (root / path).read_bytes() for path in SOURCES
    }
    test_hash = hashlib.sha256((root / TEST).read_bytes()).hexdigest()
    temporary_root = root / "audit" / "block15_oracle_test_temp"
    temporary_root.mkdir(exist_ok=True)
    junit = temporary_root / ("baseline.xml" if args.mode == "baseline" else "current.xml")
    log = root / ("audit/block15_oracle_" + args.mode + "_tests.log")
    started = datetime.now(timezone.utc).isoformat()
    timer = time.perf_counter()
    with contextlib.ExitStack() as cleanup:
        if args.mode == "baseline":
            snapshot_root = Path(cleanup.enter_context(
                tempfile.TemporaryDirectory(prefix="b15-oracle-", dir=root / ".venv")
            ))
            snapshots = {}
            for path, content in frozen_sources.items():
                snapshot = snapshot_root / path
                snapshot.parent.mkdir(parents=True, exist_ok=True)
                snapshot.write_bytes(content)
                snapshots[_module_name(path)] = snapshot
            finder = FrozenModules(snapshots)
            sys.meta_path.insert(0, finder)
            cleanup.callback(sys.meta_path.remove, finder)
        import pytest
        assert all(_module_name(path) not in sys.modules for path in SOURCES)
        with log.open("w", encoding="utf-8") as output:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                exit_code = int(pytest.main([
                    "-q", "-p", "no:cacheprovider", TEST,
                    "--basetemp=" + str(root / ".venv" / ("block15-oracle-" + args.mode + "-temp")),
                    "--junitxml=" + str(junit),
                ]))
        for path, expected in {**loaded_sources, **dependency_sources}.items():
            module = sys.modules[_module_name(path)]
            assert Path(module.__file__).read_bytes() == expected, path
        base = sys.modules["causalis.dgp.multicausaldata.base"]
        functional = sys.modules["causalis.dgp.multicausaldata.functional"]
        public = sys.modules["causalis.dgp.multicausaldata"]
        shared = sys.modules["causalis.dgp.base"]
        contract = sys.modules["causalis.data_contracts.multicausaldata"]
        assert functional.MultiCausalDatasetGenerator is base.MultiCausalDatasetGenerator
        assert public.MultiCausalDatasetGenerator is base.MultiCausalDatasetGenerator
        assert public.generate_multitreatment is functional.generate_multitreatment
        assert functional.MultiCausalData is base.MultiCausalData is public.MultiCausalData is contract.MultiCausalData
        assert base._gaussian_copula is shared._gaussian_copula
        assert base._sigmoid is shared._sigmoid
    assert test_hash == hashlib.sha256((root / TEST).read_bytes()).hexdigest()
    suites = list(ET.parse(junit).getroot().iter("testsuite"))
    counts = {
        key: sum(int(suite.get(key, "0")) for suite in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }
    counts["passed"] = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    cases = [case.get("classname") + "::" + case.get("name") for suite in suites for case in suite.findall("testcase")]
    failure_types = {}
    for suite in suites:
        for case in suite.findall("testcase"):
            failure = case.find("failure")
            if failure is not None:
                kind = failure.get("message", "").split(":", 1)[0]
                failure_types[kind] = failure_types.get(kind, 0) + 1
    result = {
        "mode": args.mode,
        "baseline_sha": BASELINE,
        "head_at_start": head,
        "source_files": list(SOURCES),
        "source_sha256": {path: hashlib.sha256(data).hexdigest() for path, data in loaded_sources.items()},
        "unchanged_dependency_files": list(DEPENDENCIES),
        "unchanged_dependency_sha256": {path: hashlib.sha256(data).hexdigest() for path, data in dependency_sources.items()},
        "test_file": TEST,
        "test_file_sha256": test_hash,
        "collected_case_ids": cases,
        "counts": counts,
        "failure_exception_types": failure_types,
        "exit_code": exit_code,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.perf_counter() - timer,
        "python": sys.version,
        "platform": platform.platform(),
        "dependencies": {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "scipy", "pydantic")},
        "junit": str(junit.relative_to(root)),
        "log": str(log.relative_to(root)),
        "public_generator_and_wrapper_aliases_verified": True,
        "shared_helper_and_contract_bindings_verified": True,
        "non_target_tracked_package_paths_unchanged": True,
        "baseline_feature_absence_is_planned_not_a_numerical_bug": args.mode == "baseline",
        "full_suite_run": False,
        "sensitivity_validated": False,
    }
    result_path = root / ("audit/block15_oracle_" + args.mode + "_test_result.json")
    result_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"mode": args.mode, "exit_code": exit_code, "counts": counts}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
