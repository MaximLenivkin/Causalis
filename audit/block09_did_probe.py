"""Read-only aggregate probe of the pre-existing synthetic DiD fixture."""

from __future__ import annotations

import argparse
from collections import Counter
import contextlib
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import warnings


BASELINE = "74145665127f8fa5a0bf038d769697ab880854b8"
TEST = "tests/scenarios/did/refutation/test_did_post_inference_diagnostics.py"
TARGETS = (
    "causalis/dgp/multicausaldata/base.py",
    "causalis/dgp/multicausaldata/functional.py",
)


def scalar_safe(value):
    if isinstance(value, dict):
        return {str(key): scalar_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [scalar_safe(item) for item in value]
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("current", "baseline"), required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = "1"
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["MPLCONFIGDIR"] = str(root / ".venv" / "matplotlib")
    os.environ["SKIP_DOCS_BUILD"] = "true"
    changed_package = subprocess.check_output(
        ["git", "diff", "--name-only", BASELINE, "--", "causalis"], text=True
    ).splitlines()
    assert not (set(changed_package) - set(TARGETS)), changed_package
    assert (root / TEST).read_bytes() == subprocess.check_output(
        ["git", "show", BASELINE + ":" + TEST]
    )

    with contextlib.ExitStack() as cleanup:
        test_path = root / TEST
        if args.mode == "baseline":
            temporary = Path(cleanup.enter_context(
                tempfile.TemporaryDirectory(prefix="b09-did-", dir=root / ".venv")
            ))
            import causalis.dgp.multicausaldata as package
            for source_path in TARGETS:
                snapshot = temporary / Path(source_path).name
                snapshot.write_bytes(subprocess.check_output([
                    "git", "show", BASELINE + ":" + source_path,
                ]))
                leaf = snapshot.stem
                module = load_module("causalis.dgp.multicausaldata." + leaf, snapshot)
                setattr(package, leaf, module)
            test_path = temporary / "test_fixture.py"
            test_path.write_bytes(subprocess.check_output([
                "git", "show", BASELINE + ":" + TEST,
            ]))
        fixture = load_module("block09_did_fixture", test_path)
        called = set()

        def profile(frame, event, arg):
            if event == "call":
                file_path = Path(frame.f_code.co_filename)
                try:
                    relative = file_path.resolve().relative_to(root)
                except ValueError:
                    return
                if str(relative).startswith("causalis/"):
                    called.add(str(relative))

        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            sys.setprofile(profile)
            try:
                panel, estimate = fixture._estimate()
                report = fixture._relaxed_report(panel, estimate)
                cells = fixture.did_post_inference_cell_table(estimate)
                fixture.did_influence_table(estimate)
                fixture.did_cluster_influence_table(panel, estimate)
            finally:
                sys.setprofile(None)
        columns = [
            "cell_id", "event_time", "is_post_treatment", "att", "se",
            "t_stat", "abs_t_stat", "control_design_rank", "n_parameters",
            "condition_number", "control_weight_ess", "propensity_clip_share",
            "diagnostic_status", "diagnostic_flags",
        ]
        columns = [name for name in columns if name in cells.columns]
        called_hashes = {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in sorted(called)
        }
        unchanged = all(
            (root / name).read_bytes() == subprocess.check_output([
                "git", "show", BASELINE + ":" + name,
            ]) for name in called
        )
        result = {
            "mode": args.mode,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "baseline_sha": BASELINE,
            "current_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "python": sys.version,
            "platform": platform.platform(),
            "dependencies": {
                name: importlib.metadata.version(name)
                for name in ("numpy", "pandas", "scipy", "statsmodels", "scikit-learn", "pydantic")
            },
            "fixture": TEST,
            "fixture_sha256": hashlib.sha256((root / TEST).read_bytes()).hexdigest(),
            "fixture_unchanged_from_baseline": True,
            "changed_package_paths": changed_package,
            "called_package_paths_sha256": called_hashes,
            "called_package_paths_unchanged_from_baseline": unchanged,
            "changed_dgp_paths_called": sorted(set(called) & set(TARGETS)),
            "overall_flag": report.loc[0, "flag"],
            "report_rows": scalar_safe(report.to_dict(orient="records")),
            "cell_aggregate_rows": scalar_safe(cells[columns].to_dict(orient="records")),
            "simple_aggregate": scalar_safe(estimate.aggregates["simple"].to_dict(orient="records")),
            "warning_counts": dict(Counter(type(item.message).__name__ for item in recorded)),
            "warnings": sorted(set(str(item.message) for item in recorded)),
            "individual_rows_saved": False,
        }
        output = root / ("audit/block09_did_" + args.mode + "_probe.json")
        output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        print(json.dumps({
            "mode": args.mode, "overall_flag": result["overall_flag"],
            "non_green": [row for row in result["report_rows"][1:] if row["flag"] != "GREEN"],
            "changed_dgp_paths_called": result["changed_dgp_paths_called"],
            "called_paths_unchanged": unchanged,
        }, allow_nan=False))


if __name__ == "__main__":
    main()
