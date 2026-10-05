"""Run only the historical SC-09 IV reproducer, without other scenario probes."""

from __future__ import annotations

import json
from pathlib import Path
import runpy


AUDIT = Path(__file__).resolve().parent


if __name__ == "__main__":
    namespace = runpy.run_path(str(AUDIT / "repro_scenarios.py"))
    result = namespace["iv_fit_and_diagnostics"]()
    assert result["first_stage_result_works"] == (7, 5)
    assert result["first_stage_model"] == "accepted"
    output = {
        "finding": "SC-09",
        "scope": "IV diagnostic API resolution; historical probe only",
        "result": result,
    }
    (AUDIT / "block05_iv_probe_result.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(output, indent=2))
