"""Verify that B10 does not enter or change the known synthetic DiD failure."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "83b63836dbd0c4793c24dd95ff7dc18c443792ad"
FIXTURE = "tests/scenarios/did/refutation/test_did_post_inference_diagnostics.py"
CHANGED = "causalis/dgp/base.py"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def main():
    os.chdir(ROOT)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = "1"
    os.environ.update(MPLBACKEND="Agg", MPLCONFIGDIR=str(ROOT / ".venv/matplotlib"))
    assert (ROOT / FIXTURE).read_bytes() == git("show", BASELINE + ":" + FIXTURE)
    spec = importlib.util.spec_from_file_location("block10_did_fixture", ROOT / FIXTURE)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    called = set()

    def profile(frame, event, arg):
        if event == "call":
            try:
                path = Path(frame.f_code.co_filename).resolve().relative_to(ROOT).as_posix()
            except ValueError:
                return
            if path.startswith("causalis/"):
                called.add(path)

    sys.setprofile(profile)
    try:
        panel, estimate = fixture._estimate()
        report = fixture._relaxed_report(panel, estimate)
        cells = fixture.did_post_inference_cell_table(estimate)
        fixture.did_influence_table(estimate)
        fixture.did_cluster_influence_table(panel, estimate)
    finally:
        sys.setprofile(None)
    hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
              for path in sorted(called)}
    unchanged = all((ROOT / path).read_bytes() == git("show", BASELINE + ":" + path)
                    for path in called)
    previous = json.loads((ROOT / "audit/block09_did_current_probe.json").read_text())
    previous_cells = {row["cell_id"]: row for row in previous["cell_aggregate_rows"]}
    keys = ["cell_id", "att", "se", "t_stat", "abs_t_stat"]
    current_cells = cells[keys].to_dict(orient="records")
    # Include all cell values, allowing identical NaN only where B09 serialized it.
    same = all(str(row[key]) == str(previous_cells[row["cell_id"]][key])
               for row in current_cells for key in keys)
    result = {
        "baseline": BASELINE,
        "current_head": git("rev-parse", "HEAD").decode().strip(),
        "fixture": FIXTURE,
        "fixture_sha256": hashlib.sha256((ROOT / FIXTURE).read_bytes()).hexdigest(),
        "fixture_unchanged": True,
        "called_package_sha256": hashes,
        "called_package_unchanged": unchanged,
        "changed_copula_path_called": CHANGED in called,
        "overall_flag": report.loc[0, "flag"],
        "cell_aggregates_equal_b09": same,
        "non_green_report_rows": report.loc[report["flag"] != "GREEN"].to_dict(orient="records"),
        "pre_cell_aggregates": [row for row in current_cells
                                if not bool(cells.loc[cells["cell_id"] == row["cell_id"],
                                                      "is_post_treatment"].iloc[0])],
        "individual_rows_saved": False,
    }
    assert unchanged and not result["changed_copula_path_called"] and same
    assert result["overall_flag"] == previous["overall_flag"] == "YELLOW"
    (ROOT / "audit/block10_did_provenance.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: result[key] for key in (
        "overall_flag", "called_package_unchanged", "changed_copula_path_called",
        "cell_aggregates_equal_b09")}))


if __name__ == "__main__":
    main()
