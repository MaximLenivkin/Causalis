"""Independent date-pair and placebo references for the first observed DID period."""

import numpy as np
import pandas as pd
import pytest

from causalis.data_contracts import PanelDataDID
from causalis.scenarios.did import (
    CallawaySantAnnaDID,
    did_base_design_table,
    did_covariate_balance_table,
    did_support_table,
    raw_did_event_study_table,
)


def _panel(*, frequency="M", start=0, focal_first=3, missing=(), covariates=False):
    times = pd.period_range("2020-01", periods=7, freq=frequency)
    slopes = {"focal": [1.0, 2.0, 4.0], "future": [0.25, 0.75, 1.5],
              "never": [-0.5, 0.5, 1.0]}
    firsts = {"focal": focal_first, "future": 5, "never": None}
    rows = []
    for group, values in slopes.items():
        for j, slope in enumerate(values):
            unit = f"{group}{j}"
            for t, time in enumerate(times):
                if t < start or (unit, t) in missing:
                    continue
                treated = firsts[group] is not None and t >= firsts[group]
                rows.append({"unit": unit, "time": time, "d": int(treated),
                             "y": 10.0 + j + slope * t + 5.0 * treated,
                             "x": float(j) + (0.15 if group == "focal" else 0.0)})
    frame = pd.DataFrame(rows).sample(frac=1.0, random_state=918)
    frame.index = np.arange(len(frame)) % 3
    return PanelDataDID(df=frame, y="y", unit_col="unit", time_col="time",
                        treated_time="d", covariates=["x"] if covariates else [])


def _date_pairs(times, cohort, anticipation, base_period):
    """All contrasts with two observed dates, from their mathematical definition."""
    base_position = times.index(cohort) - anticipation - 1
    if base_position < 0:
        return []
    fixed_base = times[base_position]
    post = [(time, fixed_base) for time in times if time >= cohort]
    if base_period == "universal":
        pre = [(time, fixed_base) for time in times if time < fixed_base]
    else:
        unaffected_last = times[base_position]
        pre = [(later, earlier) for earlier, later in zip(times[:-1], times[1:])
               if later <= unaffected_last]
    return pre + post


def _row(table, cohort, time):
    selected = table.loc[(table.cohort == cohort) & (table.time == time)]
    assert len(selected) == 1, f"Expected one cell for {(cohort, time)}, found {len(selected)}"
    return selected.iloc[0]


@pytest.mark.parametrize("base_period", ["universal", "varying"])
@pytest.mark.parametrize("anticipation", [0, 1])
@pytest.mark.parametrize("frequency", ["M", "2M"])
@pytest.mark.parametrize("start", [0, 1])
def test_support_enumerates_all_defined_date_pairs_in_stable_order(
    base_period, anticipation, frequency, start,
):
    # Filtering an earlier source date changes the analysis axis, not calendar
    # frequency units: its new first date remains a valid universal target.
    panel = _panel(frequency=frequency, start=start)
    original = panel.df_analysis()
    times = list(panel.analysis_times())
    support = panel.att_gt_cells(base_period=base_period, anticipation=anticipation,
                                 include_pre_periods=True, include_unsupported=True)
    expected = [(cohort, time, base) for cohort in panel.cohorts
                for time, base in _date_pairs(times, cohort, anticipation, base_period)]
    actual = list(support[["cohort", "time", "base_time"]].itertuples(index=False, name=None))
    assert actual == expected
    assert not support.duplicated(["cohort", "time"]).any()
    if base_period == "varying":
        assert times[0] not in support.time.tolist()
    for row in support.itertuples():
        assert row.event_time == times.index(row.time) - times.index(row.cohort)
    pd.testing.assert_frame_equal(panel.df_analysis(), original)


@pytest.mark.parametrize("anticipation,focal_first", [(0, 1), (0, 2), (1, 2), (1, 3)])
def test_short_pre_window_has_a_placebo_exactly_when_fixed_base_is_later(
    anticipation, focal_first,
):
    panel = _panel(focal_first=focal_first)
    times = list(panel.analysis_times())
    cohort = times[focal_first]
    universal = panel.att_gt_cells(anticipation=anticipation, include_pre_periods=True)
    pre = universal.loc[(universal.cohort == cohort) & ~universal.is_post_treatment]
    expected_targets = times[:focal_first - anticipation - 1]
    assert pre.time.tolist() == expected_targets
    # The fixed base is a normalizing date, never a manufactured zero estimate.
    assert times[focal_first - anticipation - 1] not in pre.time.tolist()


@pytest.mark.parametrize("control_group", ["never_treated", "not_yet_treated", "not_yet_or_never"])
@pytest.mark.parametrize("anticipation", [0, 1])
@pytest.mark.parametrize("unbalanced", [False, True])
def test_first_cell_is_shared_by_support_model_raw_balance_and_design(
    control_group, anticipation, unbalanced,
):
    missing = [("focal0", 0), ("future0", 0), ("never1", 0)] if unbalanced else []
    panel = _panel(missing=missing, covariates=True)
    original = panel.df_analysis()
    times = list(panel.analysis_times())
    settings = dict(control_group=control_group, anticipation=anticipation,
                    base_period="universal", include_pre_periods=True)
    focal, target, base = times[3], times[0], times[2 - anticipation]
    expected_treated = {f"focal{i}" for i in range(3)}
    expected_control = set()
    if control_group != "never_treated":
        expected_control |= {f"future{i}" for i in range(3)}
    if control_group != "not_yet_treated":
        expected_control |= {f"never{i}" for i in range(3)}
    available_controls = len(expected_control)
    if unbalanced:
        expected_treated -= {"focal0"}
        expected_control -= {"future0", "never1"}
    support = panel.att_gt_cells(include_unsupported=True, **settings)
    first = _row(support, focal, target)
    assert first.base_time == base
    assert first.event_time == -3
    assert first.n_treated_available == 3
    assert first.n_control_available == available_controls
    assert first.n_treated_complete == len(expected_treated)
    assert first.n_control_complete == len(expected_control)
    assert first.is_supported
    ref_support = _row(did_support_table(panel, **settings), focal, target)
    assert ref_support.n_treated_complete == len(expected_treated)
    assert ref_support.n_control_complete == len(expected_control)
    estimate = CallawaySantAnnaDID(diagnostic_data=True, **settings).fit(panel).estimate()
    cell = _row(estimate.att_gt, focal, target)
    assert cell.base_time == base
    local = estimate.diagnostics["unit_level"]
    local = local.loc[local.cell_id == cell.cell_id]
    assert local.unit.is_unique
    assert set(local.loc[local.is_treated_cohort == 1, "unit"]) == expected_treated
    assert set(local.loc[local.is_treated_cohort == 0, "unit"]) == expected_control
    wide = original.pivot(index="unit", columns="time", values="y")
    delta = wide[target] - wide[base]
    expected_raw = delta.loc[sorted(expected_treated)].mean() - delta.loc[sorted(expected_control)].mean()
    raw = _row(raw_did_event_study_table(panel, **settings), focal, target)
    assert raw.raw_did == pytest.approx(expected_raw)
    balance = _row(did_covariate_balance_table(panel, post_only=False, **settings), focal, target)
    assert balance.base_time == base
    assert balance.n_treated == len(expected_treated)
    assert balance.n_control == len(expected_control)
    design = _row(did_base_design_table(panel, post_only=False, **settings), focal, target)
    assert design.base_time == base
    assert design.n_control == len(expected_control)
    control_x = original.loc[(original.time == base) & original.unit.isin(expected_control), "x"]
    reference_design = np.column_stack([np.ones(len(control_x)), control_x])
    assert design.control_design_rank == np.linalg.matrix_rank(reference_design)
    pd.testing.assert_frame_equal(panel.df_analysis(), original)


@pytest.mark.parametrize("estimator", ["dr", "ipw"])
@pytest.mark.parametrize("anticipation", [0, 1])
def test_first_placebo_matches_hand_computed_difference_and_nonzero_influence_se(
    estimator, anticipation,
):
    panel = _panel()
    model = CallawaySantAnnaDID(estimator=estimator, anticipation=anticipation,
                              include_pre_periods=True).fit(panel)
    estimate = model.estimate()
    times = list(panel.analysis_times())
    cell = _row(estimate.att_gt, times[3], times[0])
    distance = -(2 - anticipation)
    treated_delta = distance * np.array([1.0, 2.0, 4.0])
    control_delta = distance * np.array([0.25, 0.75, 1.5, -0.5, 0.5, 1.0])
    expected_att = treated_delta.mean() - control_delta.mean()
    # Intercept-only DID is a difference of empirical group means. Its exact
    # contamination derivatives give an independent, nondegenerate IF oracle.
    derivatives = {f"focal{i}": 9 / 3 * (value - treated_delta.mean())
                   for i, value in enumerate(treated_delta)}
    for prefix, values in [("future", control_delta[:3]), ("never", control_delta[3:])]:
        derivatives.update({f"{prefix}{i}": -9 / 6 * (value - control_delta.mean())
                            for i, value in enumerate(values)})
    expected_se = np.sqrt(sum(value ** 2 for value in derivatives.values())) / 9
    assert expected_se > 0
    assert cell.att == pytest.approx(expected_att, abs=1e-12)
    assert cell.se == pytest.approx(expected_se, abs=1e-12)
    local = estimate.diagnostics["unit_level"]
    local = local.loc[local.cell_id == cell.cell_id].set_index("unit")
    for unit, derivative in derivatives.items():
        assert local.loc[unit, "influence_score"] == pytest.approx(derivative, abs=1e-12)
    score_column = model._att_gt.index[(model._att_gt.cohort == times[3])
                                     & (model._att_gt.time == times[0])][0]
    expected_scores = [derivatives[unit] for unit in model._prepared.unit_ids]
    np.testing.assert_allclose(model._score_matrix[:, score_column], expected_scores, atol=1e-12)


@pytest.mark.parametrize("missing_group,reason", [
    ("focal", "no_complete_treated_units"),
    ("control", "no_complete_control_units"),
])
def test_missing_first_pairs_report_unsupported_cell_without_fabricating_estimate(missing_group, reason):
    groups = ["focal"] if missing_group == "focal" else ["future", "never"]
    missing = [(f"{group}{i}", 0) for group in groups for i in range(3)]
    panel = _panel(missing=missing)
    times = list(panel.analysis_times())
    settings = dict(include_pre_periods=True)
    support = panel.att_gt_cells(include_unsupported=True, **settings)
    first = _row(support, times[3], times[0])
    assert not first.is_supported
    assert first.unsupported_reason == reason
    assert first.n_treated_available == 3
    assert first.n_control_available == 6
    supported = panel.att_gt_cells(**settings)
    assert supported.loc[(supported.cohort == times[3]) & (supported.time == times[0])].empty
    result = CallawaySantAnnaDID(**settings).fit(panel).estimate()
    assert result.att_gt.loc[(result.att_gt.cohort == times[3]) & (result.att_gt.time == times[0])].empty


def test_first_universal_target_without_eligible_future_controls_is_reported_unsupported():
    panel = _panel()
    times = list(panel.analysis_times())
    support = panel.att_gt_cells(control_group="not_yet_treated", include_pre_periods=True,
                                 include_unsupported=True)
    first = _row(support, times[5], times[0])
    assert first.n_control_available == 0
    assert first.n_control_complete == 0
    assert first.unsupported_reason == "no_complete_control_units"
    assert not first.is_supported


@pytest.mark.parametrize("anticipation", [0, 1])
@pytest.mark.parametrize("unbalanced", [False, True])
def test_enabling_pre_cells_preserves_post_estimates_scores_and_post_only_aggregates(
    anticipation, unbalanced,
):
    panel = _panel(missing=[("focal0", 0), ("future0", 0)] if unbalanced else [])
    models = [CallawaySantAnnaDID(anticipation=anticipation, include_pre_periods=include,
                                 bootstrap_replications=0).fit(panel) for include in [False, True]]
    results = [model.estimate() for model in models]
    posts = [result.att_gt.loc[result.att_gt.is_post_treatment].reset_index(drop=True)
             for result in results]
    # Cell IDs shift when pre contrasts are added; simultaneous bands and pre
    # tests also intentionally have a larger family and are not invariant.
    columns = ["cohort", "time", "base_time", "att", "se", "ci_lower", "ci_upper", "p_value"]
    pd.testing.assert_frame_equal(posts[0][columns], posts[1][columns])
    for row in posts[0].itertuples():
        score_columns = [model._att_gt.index[(model._att_gt.cohort == row.cohort)
                                            & (model._att_gt.time == row.time)][0] for model in models]
        np.testing.assert_array_equal(models[0]._score_matrix[:, score_columns[0]],
                                      models[1]._score_matrix[:, score_columns[1]])
    for kind in ["simple", "cohort", "calendar"]:
        pd.testing.assert_frame_equal(results[0].aggregates[kind], results[1].aggregates[kind])
    event_posts = [
        result.aggregates["event"].loc[result.aggregates["event"].event_time >= 0].reset_index(drop=True)
        for result in results
    ]
    pd.testing.assert_frame_equal(event_posts[0], event_posts[1])
