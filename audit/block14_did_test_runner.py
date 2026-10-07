"""Run identical public DiD zero-studentization and API tests on selected source."""

from __future__ import annotations

import argparse
from collections import Counter
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


BASELINE = "dbded76ecf8a207aad2094903b8f015fed8ae5d6"
SOURCES = (
    "causalis/scenarios/did/model.py",
    "causalis/scenarios/did/refutation/post_inference.py",
)
DEPENDENCIES = (
    "causalis/data_contracts/panel_data_did.py",
    "causalis/data_contracts/panel_did_estimate.py",
    "causalis/scenarios/did/__init__.py",
    "causalis/scenarios/did/refutation/__init__.py",
    "causalis/scenarios/did/refutation/post_inference_plots.py",
)
TESTS = (
    "tests/scenarios/did/refutation/test_did_studentization_contract.py",
    "tests/scenarios/did/refutation/test_did_post_inference_diagnostics.py",
)


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
    test_hashes = {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in TESTS}
    temporary_root = root / "audit" / "block14_did_test_temp"
    temporary_root.mkdir(exist_ok=True)
    junit = temporary_root / ("baseline.xml" if args.mode == "baseline" else "current.xml")
    log = root / ("audit/block14_did_" + args.mode + "_tests.log")
    started = datetime.now(timezone.utc).isoformat()
    timer = time.perf_counter()
    with contextlib.ExitStack() as cleanup:
        if args.mode == "baseline":
            snapshot_root = Path(cleanup.enter_context(
                tempfile.TemporaryDirectory(prefix="b14-did-", dir=root / ".venv")
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
                    "-q", "-p", "no:cacheprovider", *TESTS,
                    "--basetemp=" + str(root / ".venv" / ("block14-did-" + args.mode + "-temp")),
                    "--junitxml=" + str(junit),
                ]))
        for path, expected in {**loaded_sources, **dependency_sources}.items():
            module = sys.modules[_module_name(path)]
            assert Path(module.__file__).read_bytes() == expected, path
        model = sys.modules["causalis.scenarios.did.model"]
        post = sys.modules["causalis.scenarios.did.refutation.post_inference"]
        did = sys.modules["causalis.scenarios.did"]
        refutation = sys.modules["causalis.scenarios.did.refutation"]
        assert did.CallawaySantAnnaDID is model.CallawaySantAnnaDID
        assert model.CallawaySantAnnaDIDEstimate is post.CallawaySantAnnaDIDEstimate
        for name in (
            "did_post_inference_cell_table", "run_did_post_inference_diagnostics",
            "run_did_inference_diagnostics",
        ):
            assert getattr(did, name) is getattr(post, name)
            assert getattr(refutation, name) is getattr(post, name)
        plots = sys.modules["causalis.scenarios.did.refutation.post_inference_plots"]
        assert plots.did_influence_table is post.did_influence_table
    assert test_hashes == {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in TESTS}
    suites = list(ET.parse(junit).getroot().iter("testsuite"))
    counts = {
        key: sum(int(suite.get(key, "0")) for suite in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }
    counts["passed"] = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    cases = [case.get("classname") + "::" + case.get("name") for suite in suites for case in suite.findall("testcase")]
    module_counts = dict(Counter(case.split("::")[0] for case in cases))
    result = {
        "mode": args.mode,
        "baseline_sha": BASELINE,
        "head_at_start": head,
        "source_files": list(SOURCES),
        "source_sha256": {path: hashlib.sha256(data).hexdigest() for path, data in loaded_sources.items()},
        "unchanged_dependency_files": list(DEPENDENCIES),
        "unchanged_dependency_sha256": {path: hashlib.sha256(data).hexdigest() for path, data in dependency_sources.items()},
        "test_files": list(TESTS),
        "test_sha256": test_hashes,
        "test_module_case_counts": module_counts,
        "collected_case_ids": cases,
        "counts": counts,
        "exit_code": exit_code,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.perf_counter() - timer,
        "python": sys.version,
        "platform": platform.platform(),
        "dependencies": {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "scipy", "pydantic")},
        "junit": str(junit.relative_to(root)),
        "log": str(log.relative_to(root)),
        "public_class_and_refutation_aliases_verified": True,
        "plot_influence_bindings_verified": True,
        "non_target_tracked_package_paths_unchanged": True,
        "full_suite_run": False,
        "sensitivity_validated": False,
    }
    result_path = root / ("audit/block14_did_" + args.mode + "_test_result.json")
    result_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"mode": args.mode, "exit_code": exit_code, "counts": counts, "modules": module_counts}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
