"""Deterministic audit probes; run from repository root with .venv Python."""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from causalis.data_contracts import CausalData, PanelDataSCM
from causalis.shared.confounders_balance import confounders_balance
from causalis.shared.outcome_outliers import outcome_outliers
from causalis.shared.rct_design.split import assign_variants_df
from causalis.scenarios.classic_rct import DiffInMeans


def main():
    results = {}
    d = np.tile([0, 1], 20)
    y = np.arange(40, dtype=float) + .25
    for bad, label in [(np.inf, "inf"), (2 + 7j, "complex")]:
        values = y.astype(complex) if label == "complex" else y.copy()
        values[3] = bad
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            data = CausalData.from_df(pd.DataFrame({"d": d, "y": values}), "d", "y")
            try:
                estimate = DiffInMeans().fit(data).estimate()
                result = {"value": estimate.value, "p_value": estimate.p_value,
                          "ci_lower": estimate.ci_lower_absolute,
                          "ci_upper": estimate.ci_upper_absolute}
            except Exception as exc:
                result = {"exception": type(exc).__name__, "message": str(exc)}
            results[f"causaldata_{label}"] = {"accepted": True, "dtype": str(data.df.y.dtype),
                                                "estimate": result,
                                                "warnings": [str(w.message) for w in caught]}

    data = CausalData.from_df(pd.DataFrame({"d": d, "y": y, "x": 3 + 2*d}), "d", "y", ["x"])
    balance = confounders_balance(data).iloc[0]
    assert balance.smd == 0 and balance.abs_diff == 2
    results["balance_zero_variance"] = balance.to_dict()

    values = np.tile(np.arange(10, dtype=float), 2)
    values[9] = 100
    frame = pd.DataFrame({"d": np.repeat([0, 1], 10), "y": values})
    frame.index = list(range(9)) + [0] + list(range(10, 20))
    data = CausalData.from_df(frame, "d", "y")
    summary, outliers = outcome_outliers(data, return_rows=True)
    assert summary.outlier_count.sum() == 1 and len(outliers) == 2
    results["duplicate_index_outliers"] = {"flag_count": int(summary.outlier_count.sum()),
                                            "returned_rows": len(outliers),
                                            "returned_values": outliers.y.tolist()}

    assigned = assign_variants_df(pd.DataFrame({"id": range(10)}), "id", "audit",
                                  {"control": np.nan, "treated": .5})
    assert assigned.variant.isna().all()
    results["nan_assignment_weight"] = {"accepted": True, "assigned_count": int(assigned.variant.notna().sum())}

    panel = pd.DataFrame([{"unit": u, "time": t, "d": int(u == "T" and i >= 3),
                          "y": float(i + k)}
                         for k, u in enumerate(["T", "A", "B"])
                         for i, t in enumerate(pd.period_range("2020-01", periods=6, freq="M"))])
    panel.loc[1, "y"] = np.inf
    contract = PanelDataSCM(df=panel, y="y", unit_col="unit", time_col="time", treated_time="d")
    results["scm_infinite_outcome"] = {"accepted": True, "has_inf": bool(np.isinf(contract.df.y).any())}
    target = Path(__file__).parent / "results_contracts_shared.json"
    target.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
