"""Separation must remain visible in shared and weighted balance reports."""

import numpy as np
import pandas as pd
import pytest

from causalis.data_contracts.causal_diagnostic_data import (
    MultiUnconfoundednessDiagnosticData,
    UnconfoundednessDiagnosticData,
)
from causalis.data_contracts.causal_estimate import CausalEstimate
from causalis.data_contracts.causaldata import CausalData
from causalis.data_contracts.multicausal_estimate import MultiCausalEstimate
from causalis.data_contracts.multicausaldata import MultiCausalData
from causalis.scenarios.multi_unconfoundedness.refutation.unconfoundedness import (
    unconfoundedness_validation as multi,
)
from causalis.scenarios.unconfoundedness.refutation.unconfoundedness import (
    unconfoundedness_validation as binary,
)
from causalis.shared.confounders_balance import _compute_balance_table, confounders_balance


@pytest.mark.parametrize("treated_level", [5.0, 1.0])
def test_shared_balance_reports_signed_infinite_smd_for_separation(treated_level):
    d = np.repeat([0, 1], 4)
    data = CausalData(
        df=pd.DataFrame({"d": d, "y": np.arange(8), "x": np.where(d, treated_level, 3.0)}),
        treatment="d", outcome="y", confounders=["x"],
    )
    row = confounders_balance(data).iloc[0]
    assert row["smd"] == np.copysign(np.inf, treated_level - 3.0)
    assert row["abs_diff"] == 2.0


def test_shared_balance_identical_constants_have_zero_smd():
    # Globally constant confounders are rejected by the public data contract.
    table = _compute_balance_table(
        pd.DataFrame({"x": [3.0] * 4}), ["x"],
        np.array([True, True, False, False]), np.array([False, False, True, True]),
    )
    assert table.iloc[0]["smd"] == 0.0


def test_shared_balance_unavailable_moments_are_not_zero():
    table = _compute_balance_table(
        pd.DataFrame({"x": [np.nan] * 4}), ["x"],
        np.array([True, True, False, False]), np.array([False, False, True, True]),
    )
    assert np.isnan(table.iloc[0]["smd"])


def _separation_report(kind, *, score, normalize, mixed):
    n_arms = 2 if kind == "binary" else 3
    labels = np.repeat(np.arange(n_arms), 4)
    x = np.where(labels == 1, 5.0, 3.0)[:, None]
    names = ["separated"]
    if mixed:
        x = np.column_stack([x, np.tile([-1.0, 1.0, -1.0, 1.0], n_arms)])
        names.append("balanced")
    df = pd.DataFrame(x, columns=names)
    df["y"] = np.arange(len(labels), dtype=float)
    common = dict(
        estimand=score, model="manual oracle fixture", alpha=0.05,
        n_control=4, n_treated=4 * (n_arms - 1), outcome="y", confounders=names,
    )
    if kind == "binary":
        df["d"] = labels
        data = CausalData(df=df, treatment="d", outcome="y", confounders=names)
        diag = UnconfoundednessDiagnosticData(
            x=x, d=labels, m_hat=np.full(len(labels), 0.5),
            score=score, normalize_ipw=normalize,
        )
        estimate = CausalEstimate(
            **common, treatment="d", value=0.0, ci_lower_absolute=-1.0,
            ci_upper_absolute=1.0, is_significant=False,
            treatment_mean=0.0, control_mean=0.0, diagnostic_data=diag,
        )
        return binary.run_unconfoundedness_diagnostics(data, estimate)
    d = np.eye(n_arms)[labels]
    treatments = [f"d_{k}" for k in range(n_arms)]
    for k, name in enumerate(treatments):
        df[name] = d[:, k]
    data = MultiCausalData(
        df=df, outcome="y", treatment_names=treatments,
        confounders=names, control_treatment="d_0",
    )
    diag = MultiUnconfoundednessDiagnosticData(
        x=x, d=d, m_hat=np.full_like(d, 1.0 / n_arms),
        score=score, normalize_ipw=normalize,
    )
    estimate = MultiCausalEstimate(
        **common, treatment=treatments, value=np.zeros(2),
        ci_lower_absolute=-np.ones(2), ci_upper_absolute=np.ones(2),
        is_significant=[False, False], diagnostic_data=diag,
    )
    return multi.run_unconfoundedness_diagnostics(data, estimate)


@pytest.mark.parametrize("kind", ["binary", "multi"])
@pytest.mark.parametrize("score", ["ATE", "ATTE"])
@pytest.mark.parametrize("normalize", [False, True])
@pytest.mark.parametrize("mixed", [False, True])
def test_infinite_smd_fails_public_report_and_is_red(kind, score, normalize, mixed):
    report = _separation_report(kind, score=score, normalize=normalize, mixed=mixed)
    balance = report["balance"]
    assert balance["smd_max"] == np.inf
    assert balance["pass"] is False
    assert report["flags"]["balance_max_smd"] == "RED"
    assert report["overall_flag"] == "RED"
    # Binary: one separated feature. Multi: one separated comparison out of two.
    expected_fraction = (0.5 if kind == "multi" else 1.0) / (2 if mixed else 1)
    assert balance["frac_violations"] == pytest.approx(expected_fraction)
    assert balance["worst_features"].index[0] == "separated"
    if kind == "multi":
        failed, passed = balance["by_comparison"].to_dict("records")
        assert not failed["pass"] and failed["overall_flag"] == "RED"
        assert failed["smd_max"] == np.inf
        assert passed["pass"] and passed["overall_flag"] == "GREEN"
        assert passed["smd_max"] == 0.0
    summary = report["summary"]
    max_rows = summary[summary["metric"] == "balance_max_smd"]
    assert (max_rows.loc[max_rows["value"] == np.inf, "flag"] == "RED").all()


@pytest.mark.parametrize("kind", ["binary", "multi"])
def test_all_unavailable_smd_cannot_pass(kind):
    d = np.repeat([0.0, 1.0], 4)
    x = np.full((len(d), 1), np.nan)
    if kind == "binary":
        inputs = binary._BalanceInputs(
            x=x, d=d, m_hat=np.full_like(d, 0.5), w_bar=None,
            names=["x"], score="ATE", normalize=False,
        )
        balance = binary._balance_smd(inputs, threshold=0.1)
    else:
        inputs = multi._BalanceInputs(
            x=x, d=np.column_stack([1 - d, d]), m_hat=np.full((len(d), 2), 0.5),
            feature_names=["x"], treatment_names=["d0", "d1"], score="ATE", normalize=False,
        )
        balance = multi._balance_smd(inputs, threshold=0.1)
    assert balance["pass"] is False
    assert np.isnan(balance["smd_max"])
    assert np.isnan(balance["frac_violations"])
