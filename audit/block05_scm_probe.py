"""SC-08 placebo-only probe; deliberately never calls LOO/sensitivity."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "audit" / "mplconfig"))

from causalis.scenarios.synthetic_control import ASCM, placebo_in_space_table
from causalis.scenarios.synthetic_control.dgp import generate_scm_gamma_26


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    panel = generate_scm_gamma_26(
        n_donors=3, n_pre_periods=9, n_post_periods=3, seed=241
    )
    kwargs = {"lambda_aug": 1e6, "compute_average_att_ttest": False}
    estimate = ASCM(**kwargs).fit(panel).estimate()
    rows = {}
    for name, overrides in [("inherited", None), ("explicit_partial_matching", kwargs)]:
        table = placebo_in_space_table(estimate, panel, model_kwargs=overrides)
        actual = table.loc[table.is_actual_treated].iloc[0]
        rows[name] = {
            "average_post_gap": float(actual.average_post_gap),
            "pre_rmse": float(actual.pre_rmse),
            "post_rmse": float(actual.post_rmse),
            "model_options": table.attrs.get("model_options"),
        }
    result = {
        "scope": "ASCM placebo only; LOO sensitivity deferred",
        "source_kwargs": kwargs,
        "source_model_options": getattr(estimate, "model_options", None),
        "original_post_gap": float(estimate.effect_by_time.mean()),
        "actual_placebo_rows": rows,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
