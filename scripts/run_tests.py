"""Run an explicit CI test scope and preserve selection/result evidence.

The release gate uses ``full`` (the default). The development compatibility
matrix uses ``correctness`` while upstream rewrites sensitivity analysis.
That scope lists every excluded module and never represents a full-suite pass.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
DEFERRED_SENSITIVITY_MODULES = (
    "tests/refutation/test_multi_sensitivity_benchmark.py",
    "tests/refutation/test_sensitivity_benchmark.py",
    "tests/refutation/test_sensitivity_combination.py",
    "tests/refutation/test_sensitivity_integration_irm.py",
    "tests/refutation/test_sensitivity_protocol.py",
    "tests/refutation/test_sensitivity_rv_signed_rr.py",
    "tests/refutation/test_trim_sensitivity_ate.py",
)


def build_selection(scope: str, root: Path, output: Path, collect_only: bool = False) -> dict:
    """Describe the exact selection; fail if the deferred scope has drifted."""
    if scope not in {"full", "correctness"}:
        raise ValueError(f"Unknown test scope: {scope!r}")
    excluded = []
    if scope == "correctness":
        discovered = {
            path.relative_to(root).as_posix()
            for path in (root / "tests").rglob("test_*.py")
            if "sensitivity" in path.relative_to(root).as_posix().lower()
        }
        unexpected = discovered.difference(DEFERRED_SENSITIVITY_MODULES)
        if unexpected:
            raise ValueError(
                "New sensitivity modules require an explicit CI scope review: "
                + ", ".join(sorted(unexpected))
            )
        excluded = sorted(discovered)
    args = [
        "-q", "-p", "no:cacheprovider",
        f"--basetemp={output / 'pytest-temp'}",
        f"--junitxml={output / 'junit.xml'}", "tests",
    ]
    for module in excluded:
        args.extend(["--ignore", module])
    if collect_only:
        args.append("--collect-only")
    return {
        "scope": scope,
        "selected_full_suite": scope == "full",
        "collect_only": collect_only,
        "excluded_modules": excluded,
        "pytest_args": args,
    }


def environment_manifest() -> dict:
    versions = {}
    for name in (
        "causalis", "numpy", "pandas", "scipy", "statsmodels", "scikit-learn",
        "pydantic", "catboost", "matplotlib", "pytest", "sphinx",
        "myst-parser", "sphinx-autodoc2",
    ):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
        check=False,
    )
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "executable": sys.executable,
        "commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "packages": versions,
        "docs_build_environment": os.environ.get("SKIP_DOCS_BUILD"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("full", "correctness"), default="full")
    parser.add_argument("--output-dir", type=Path, default=Path("build/ci-tests"))
    parser.add_argument("--collect-only", action="store_true")
    options = parser.parse_args(argv)
    if os.environ.get("PYTEST_ADDOPTS", "").strip():
        parser.error("PYTEST_ADDOPTS must be empty so the recorded scope remains explicit.")
    output = options.output_dir.resolve() if options.output_dir.is_absolute() else ROOT / options.output_dir
    output.mkdir(parents=True, exist_ok=True)
    selection = build_selection(options.scope, ROOT, output, options.collect_only)
    selection["environment"] = environment_manifest()
    (output / "selection.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")
    print(json.dumps(selection, indent=2), flush=True)
    if options.scope == "correctness":
        print("Scoped correctness run: sensitivity modules listed above are deferred.", flush=True)
    os.chdir(ROOT)
    import pytest

    started = time.perf_counter()
    exit_code = int(pytest.main(selection["pytest_args"]))
    result = {
        "scope": options.scope,
        "selected_full_suite": selection["selected_full_suite"],
        "collect_only": options.collect_only,
        "exit_code": exit_code,
        "elapsed_seconds": time.perf_counter() - started,
    }
    (output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
