"""Public studentization preserves units and distinguishes undefined inference."""

import re
import warnings

import numpy as np
import pandas as pd
import pytest

from causalis.data_contracts import PanelDataDID
from causalis.data_contracts.panel_did_estimate import CallawaySantAnnaDIDEstimate
from causalis.scenarios.did import (
    CallawaySantAnnaDID,
    did_post_inference_cell_table,
    run_did_post_inference_diagnostics,
)


def _reference_estimate(pre_pairs):
    rows = [
        dict(cell_id=idx, cohort=3, time=idx, event_time=idx - len(pre_pairs),
             is_post_treatment=False, att=att, se=se, n_treated=4)
        for idx, (att, se) in enumerate(pre_pairs)
    ]
    rows.append(dict(cell_id=len(rows), cohort=3, time=4, event_time=1,
                     is_post_treatment=True, att=2.0, se=1.0, n_treated=4))
    cells = pd.DataFrame(rows)
    simple = pd.DataFrame([dict(estimate=2.0, se=1.0, ci_lower=0.04,
                                ci_upper=3.96, p_value=0.0455, is_significant=True)])
    return CallawaySantAnnaDIDEstimate(
        model="hand-specified inference reference", estimator="dr", control_group="never_treated",
        anticipation=0, base_period="varying", include_pre_periods=True, alpha=0.05,
        att_gt=cells, aggregates=dict(simple=simple, cohort=pd.DataFrame(),
                                     calendar=pd.DataFrame(), event=pd.DataFrame()),
        support=cells.copy(), skipped_cells=pd.DataFrame(), outcome="y", treatment="d",
        unit_col="unit", time_col="time", inference="asymptotic",
    )


def _pre_check(estimate):
    report = run_did_post_inference_diagnostics(estimate, max_abs_pretrend_t_stat=2.0)
    assert list(report.columns) == ["test", "flag", "value", "threshold", "message"]
    return report.loc[report["test"] == "fitted_pre_period_placebo"].iloc[0]


@pytest.mark.parametrize("att,se,expected", [(1.0, 0.5, 2.0), (-1.0, 0.5, -2.0), (0.0, 0.25, 0.0)])
def test_public_cell_studentization_uses_the_signed_positive_se_ratio(att, se, expected):
    estimate = _reference_estimate([(att, se)])
    cells = did_post_inference_cell_table(estimate)
    assert cells.loc[0, "t_stat"] == expected
    assert cells.loc[0, "abs_t_stat"] == abs(expected)


@pytest.mark.parametrize("sign", [-1.0, 1.0])
@pytest.mark.parametrize("scale", [1e-120, 1e-20, 1.0, 1e20, 1e120])
def test_real_small_effects_with_positive_se_are_invariant_to_outcome_units(sign, scale):
    estimate = _reference_estimate([(sign * 0.75 * scale, 0.25 * scale)])
    cells = did_post_inference_cell_table(estimate)
    assert cells.loc[0, "t_stat"] == pytest.approx(sign * 3.0, rel=2e-15)
    row = _pre_check(estimate)
    assert row["flag"] == "YELLOW"
    assert row["value"] == pytest.approx(3.0, rel=2e-15)


@pytest.mark.parametrize("att", [0.0, 1e-30, -1e-30, 1.0, -1.0])
def test_zero_standard_error_has_no_defined_studentized_statistic(att):
    estimate = _reference_estimate([(att, 0.0)])
    cells = did_post_inference_cell_table(estimate)
    assert np.isnan(cells.loc[0, "t_stat"])
    assert np.isnan(cells.loc[0, "abs_t_stat"])
    row = _pre_check(estimate)
    assert row["flag"] == "YELLOW"
    assert row["value"] is None
    assert re.search("undefined|invalid|unavailable|non.?finite", row["message"], re.IGNORECASE)


INVALID_PAIRS = [
    (np.nan, 1.0), (np.inf, 1.0), (-np.inf, 1.0),
    (0.5, np.nan), (0.5, np.inf), (0.5, -np.inf), (0.5, -0.25),
]


@pytest.mark.parametrize("att,se", INVALID_PAIRS)
def test_invalid_cell_inputs_are_not_reported_as_a_valid_t_statistic(att, se):
    cells = did_post_inference_cell_table(_reference_estimate([(att, se)]))
    assert np.isnan(cells.loc[0, "t_stat"])
    assert np.isnan(cells.loc[0, "abs_t_stat"])


@pytest.mark.parametrize("att,se", INVALID_PAIRS + [(0.0, 0.0), (1e-30, 0.0)])
def test_a_valid_pre_cell_cannot_hide_another_undefined_pre_cell(att, se):
    estimate = _reference_estimate([(0.25, 0.5), (att, se)])
    row = _pre_check(estimate)
    assert row["flag"] == "YELLOW"
    assert row["value"] == pytest.approx(0.5)
    assert re.search("undefined|invalid|unavailable|non.?finite", row["message"], re.IGNORECASE)


@pytest.mark.parametrize("sign", [-1.0, 1.0])
def test_finite_inputs_with_overflowing_ratio_remain_visible_and_cautious(sign):
    estimate = _reference_estimate([(0.25, 0.5), (sign * 1e308, 1e-308)])
    cells = did_post_inference_cell_table(estimate)
    assert cells.loc[1, "t_stat"] == sign * np.inf
    assert cells.loc[1, "abs_t_stat"] == np.inf
    row = _pre_check(estimate)
    assert row["flag"] == "YELLOW"
    assert row["value"] == np.inf
    assert re.search("overflow|undefined|non.?finite", row["message"], re.IGNORECASE)


def test_all_valid_small_pre_statistics_can_pass_the_pre_period_check():
    row = _pre_check(_reference_estimate([(0.0, 0.5), (-0.25, 0.5), (0.75, 0.5)]))
    assert row["flag"] == "GREEN"
    assert row["value"] == 1.5


@pytest.mark.parametrize("missing", ["att", "se"])
def test_cached_zero_statistics_cannot_hide_missing_pre_inputs(missing):
    estimate = _reference_estimate([(0.0, 0.5)])
    estimate.att_gt["t_stat"] = 0.0
    estimate.att_gt["abs_t_stat"] = 0.0
    estimate.att_gt.drop(columns=missing, inplace=True)
    cells = did_post_inference_cell_table(estimate)
    assert cells["t_stat"].isna().all()
    assert cells["abs_t_stat"].isna().all()
    row = _pre_check(estimate)
    assert row["flag"] == "YELLOW"
    assert row["value"] is None


def test_absent_pre_cells_cannot_pass_the_pre_period_check():
    row = _pre_check(_reference_estimate([]))
    assert row["flag"] == "YELLOW"
    assert row["value"] is None


def _two_period_panel(
    control_delta, treated_delta, *, matching_x=False, rank_deficient=False, covariates=True
):
    control_x = np.array([0.5, 0.7, 0.9, 1.1])
    treated_x = control_x.copy() if matching_x else np.array([-0.1, 0.1, 0.3, 0.5])
    if rank_deficient:
        control_x = np.zeros(4)
    rows = []
    periods = pd.period_range("2020-01", periods=2, freq="M")
    for treated, x_values, response in ((False, control_x, control_delta), (True, treated_x, treated_delta)):
        changes = np.broadcast_to(response, (4,))
        for idx, (x, change) in enumerate(zip(x_values, changes)):
            for idx_period, (period, outcome) in enumerate(zip(periods, (0.0, change))):
                rows.append(dict(unit=f'{"treated" if treated else "control"}_{idx}', time=period,
                                 y=outcome, d=int(treated and idx_period == 1), x=x))
    return PanelDataDID(df=pd.DataFrame(rows), y="y", unit_col="unit", time_col="time",
                        treated_time="d", covariates=["x"] if covariates else [])


def _fit(panel, estimator="dr"):
    return CallawaySantAnnaDID(
        estimator=estimator, control_group="never_treated", min_treated_per_cell=1,
        min_control_per_cell=1, min_control_ess=1.0, max_propensity_clip_share=1.0,
        max_condition_number=1e12, diagnostic_data=True,
    ).fit(panel).estimate(diagnostic_data=True)


@pytest.mark.parametrize("estimator", ["dr", "aipw"])
def test_full_rank_constant_changes_have_exact_zero_effect_and_variance(estimator):
    # With an intercept and full control rank, the unique OLS fit to a constant
    # response is that constant. Every unit then has exactly zero residual.
    panel = _two_period_panel(1.0, 1.0)
    before = panel.df.copy(deep=True)
    estimate = _fit(panel, estimator)
    row = estimate.att_gt.iloc[0]
    assert row["control_design_rank"] == row["n_parameters"] == 2
    assert row["att"] == 0.0
    assert row["se"] == 0.0
    assert row["p_value"] == 1.0
    assert np.isnan(did_post_inference_cell_table(estimate).iloc[0]["t_stat"])
    np.testing.assert_array_equal(estimate.diagnostics["unit_level"]["outcome_regression"], np.ones(8))
    pd.testing.assert_frame_equal(panel.df, before)


@pytest.mark.parametrize("effect", [2.0 ** -80, -(2.0 ** -80), 0.5, -0.5])
def test_constant_control_changes_preserve_real_treated_departures_at_zero_se(effect):
    panel = _two_period_panel(0.0, effect, matching_x=True)
    before = panel.df.copy(deep=True)
    estimate = _fit(panel)
    row = estimate.att_gt.iloc[0]
    assert row["att"] == effect
    assert row["se"] == 0.0
    assert np.isnan(row["p_value"])
    assert np.isnan(did_post_inference_cell_table(estimate).iloc[0]["t_stat"])
    pd.testing.assert_frame_equal(panel.df, before)


@pytest.mark.parametrize("background", [0.0, 2.0 ** -40])
def test_nearly_constant_control_changes_retain_their_actual_slope(background):
    slope = 2.0 ** -80
    control_x = np.array([0.5, 0.7, 0.9, 1.1])
    treated_x = np.array([-0.1, 0.1, 0.3, 0.5])
    panel = _two_period_panel(background + slope * control_x, background + slope * treated_x)
    before = panel.df.copy(deep=True)
    estimate = _fit(panel)
    units = estimate.diagnostics["unit_level"]
    expected = background + slope * units["x"].to_numpy()
    tolerance = 64.0 * np.finfo(float).eps * max(abs(expected))
    np.testing.assert_allclose(units["outcome_regression"], expected, rtol=0.0, atol=tolerance)
    controls = units.loc[units["is_treated_cohort"] == 0]
    assert np.ptp(controls["outcome_regression"].to_numpy()) > 0.5 * slope * np.ptp(control_x)
    pd.testing.assert_frame_equal(panel.df, before)


def test_constant_changes_do_not_hide_rank_deficient_control_design():
    estimate = _fit(_two_period_panel(1.0, 1.0, rank_deficient=True))
    row = estimate.att_gt.iloc[0]
    assert row["control_design_rank"] == 1
    assert row["n_parameters"] == 2
    assert row["diagnostic_status"] == "red"
    assert "rank_deficient_control_design" in row["diagnostic_flags"]


@pytest.mark.parametrize("covariates", [False, True])
def test_all_zero_score_bootstrap_has_undefined_bands_without_runtime_warning(covariates):
    panel = _two_period_panel(0.0, 0.0, covariates=covariates)
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        model = CallawaySantAnnaDID(
            control_group="never_treated", min_treated_per_cell=1, min_control_per_cell=1,
            min_control_ess=1.0, max_propensity_clip_share=1.0, max_condition_number=1e12,
            bootstrap_replications=31, random_state=731,
        ).fit(panel)
        estimate = model.estimate()
    assert not any(issubclass(item.category, RuntimeWarning) for item in recorded)
    for table in (estimate.att_gt, estimate.aggregates["event"]):
        assert (table["se"] == 0.0).all()
        assert table["simultaneous_critical_value"].isna().all()
        assert table["sim_ci_lower"].isna().all()
        assert table["sim_ci_upper"].isna().all()
