"""Revisit only the DiD probes from the historical audit; no other scenarios."""

import json
import os
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["MPLCONFIGDIR"] = str(ROOT / "audit/mplconfig")
    namespace = runpy.run_path(str(ROOT / "audit/repro_scenarios.py"))
    results = {name: namespace[name]() for name in ["did_shift", "did_pre_controls",
                                                    "did_dr_mle_influence", "did_aggregate_weight_influence"]}
    try:
        namespace["did_single_cluster_bootstrap"]()
    except ValueError as exc:
        assert "at least two clusters" in str(exc)
        results["did_single_cluster_bootstrap"] = {"status": "rejected", "reason": str(exc)}
    else:
        raise AssertionError("Single cluster bootstrap was accepted")
    serialized = json.dumps(results, indent=2, default=str)
    (ROOT / "audit/block04_correctness_result.json").write_text(serialized, encoding="utf-8")
    print(serialized)
