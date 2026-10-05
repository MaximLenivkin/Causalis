"""Record the standalone population-share oracle experiment used by B04 tests."""

import json
import os
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["MPLCONFIGDIR"] = str(ROOT / "audit/mplconfig")
    namespace = runpy.run_path(str(ROOT / "tests/scenarios/did/test_did_aggregate_influence.py"))
    result = namespace["_oracle_share_simulation"]()
    result["scope"] = "IID known deterministic cell effects; random cohort shares only; not nuisance pipeline"
    result["se_to_sd_ratio"] = result["rms_se"] / result["empirical_sd"]
    (ROOT / "audit/block04_aggregate_oracle_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
