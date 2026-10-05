"""Regression properties for the comparison population of every DID cell."""

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


def _panel(*, unbalanced=False, covariates=False, include_never=True):
    times = pd.period_range("2020-01", periods=7, freq="M")
    groups = {"early": 2, "middle": 3, "focal": 4, "future": 6}
    if include_never:
        groups["never"] = None
    rows = []
    for group, first in groups.items():
        for j in range(3):
            unit = f"{group}{j}"
            for t, time in enumerate(times):
                if unbalanced and (
                    (unit == "future0" and t == 1)
                    or (unit == "never0" and t in {2, 3})
                ):
                    continue
                treated = first is not None and t >= first
                rows.append({
                    "unit": unit,
                    "time": time,
                    "y": 10.0 + j + (2.0 * t if group == "focal" else 0.0)
                    + (100.0 if treated else 0.0),
                    "d": int(treated),
                    "x": float(j) + (0.5 if group == "focal" else 0.0),
                })
    frame = pd.DataFrame(rows)
    # The long frame has a deliberately arbitrary duplicate index and unit order.
    frame = frame.sample(frac=1.0, random_state=41)
    frame.index = np.arange(len(frame)) % 4
    return PanelDataDID(
        df=frame, y="y", unit_col="unit", time_col="time", treated_time="d",
        covariates=["x"] if covariates else [],
    )


def _expected_units(panel, row, control_group, anticipation):
    """Independent sets from the formal treatment-date rule and observed pairs."""
    frame = panel.df_analysis()
    axis = panel.time_to_index()
    cutoff = max(axis[row["time"]], axis[row["base_time"]]) + anticipation
    firsts = panel.first_treatment_by_unit
    candidates = set()
    for unit, first in firsts.items():
        if first == row["cohort"]:
            continue
        if first is None:
            eligible = control_group != "not_yet_treated"
        else:
            eligible = control_group != "never_treated" and axis[first] > cutoff
        if eligible:
            candidates.add(unit)
    base_units = set(frame.loc[frame.time == row["base_time"], "unit"])
    target_units = set(frame.loc[frame.time == row["time"], "unit"])
    pair_units = base_units & target_units
    treated = {unit for unit, first in firsts.items() if first == row["cohort"]}
    return candidates, candidates & pair_units, treated & pair_units


@pytest.mark.parametrize("control_group", ["never_treated", "not_yet_treated", "not_yet_or_never"])
@pytest.mark.parametrize("base_period", ["universal", "varying"])
@pytest.mark.parametrize("anticipation", [0, 1])
@pytest.mark.parametrize("unbalanced", [False, True])
def test_support_estimator_and_refutations_share_disjoint_complete_unit_populations(
    control_group, base_period, anticipation, unbalanced,
):
    panel = _panel(unbalanced=unbalanced, covariates=True)
    original = panel.df_analysis()
    settings = dict(control_group=control_group, base_period=base_period,
                    anticipation=anticipation, include_pre_periods=True)
    support = panel.att_gt_cells(include_unsupported=True, **settings)
    ref_support = did_support_table(panel, **settings)
    raw = raw_did_event_study_table(panel, **settings)
    balance = did_covariate_balance_table(panel, post_only=False, **settings)
    design = did_base_design_table(panel, post_only=False, **settings)
    estimate = CallawaySantAnnaDID(diagnostic_data=True, **settings).fit(panel).estimate()
    unit_level = estimate.diagnostics["unit_level"]
    assert not unit_level.duplicated(["cell_id", "unit"]).any()

    for row in support.to_dict("records"):
        if pd.isna(row["time"]):
            continue
        available, control, treated = _expected_units(panel, row, control_group, anticipation)
        assert row["n_control_available"] == len(available)
        assert row["n_control_complete"] == len(control)
        assert row["n_treated_complete"] == len(treated)
        assert bool(row["is_supported"]) == bool(control and treated)
        key = (row["cohort"], row["time"])
        ref_row = ref_support.loc[
            (ref_support.cohort == key[0]) & (ref_support.time == key[1])
        ].iloc[0]
        assert ref_row["n_control_complete"] == len(control)
        if not row["is_supported"]:
            continue
        fitted = unit_level.loc[(unit_level.cohort == key[0]) & (unit_level.time == key[1])]
        assert set(fitted.loc[fitted.is_treated_cohort == 0, "unit"]) == control
        assert set(fitted.loc[fitted.is_treated_cohort == 1, "unit"]) == treated
        assert len(fitted) == len(control) + len(treated)
        for table in (raw, balance, design):
            matched = table.loc[(table.cohort == key[0]) & (table.time == key[1])]
            assert not matched.empty
            assert (matched.n_control == len(control)).all()
        raw_row = raw.loc[(raw.cohort == key[0]) & (raw.time == key[1])].iloc[0]
        wide = original.pivot(index="unit", columns="time", values="y")
        delta = wide[row["time"]] - wide[row["base_time"]]
        manual = delta.loc[list(treated)].mean() - delta.loc[list(control)].mean()
        assert raw_row.raw_did == pytest.approx(manual)

    pd.testing.assert_frame_equal(panel.df_analysis(), original)


@pytest.mark.parametrize("estimator", ["dr", "ipw"])
@pytest.mark.parametrize("control_group", ["not_yet_treated", "not_yet_or_never"])
def test_universal_pre_placebo_excludes_own_cohort_and_controls_treated_by_base(
    estimator, control_group,
):
    panel = _panel()
    estimate = CallawaySantAnnaDID(
        estimator=estimator, control_group=control_group,
        include_pre_periods=True, diagnostic_data=True,
    ).fit(panel).estimate()
    # Focal April->February placebo: treated slope=2, eligible controls slope=0.
    cell = estimate.att_gt.loc[
        (estimate.att_gt.cohort == pd.Period("2020-05", freq="M"))
        & (estimate.att_gt.time == pd.Period("2020-02", freq="M"))
    ].iloc[0]
    assert cell.base_time == pd.Period("2020-04", freq="M")
    assert cell.att == pytest.approx(-4.0, abs=1e-9)
    units = estimate.diagnostics["unit_level"]
    units = units.loc[units.cell_id == cell.cell_id]
    assert units.unit.is_unique
    expected_controls = {f"future{i}" for i in range(3)}
    if control_group == "not_yet_or_never":
        expected_controls |= {f"never{i}" for i in range(3)}
    assert set(units.loc[units.is_treated_cohort == 0, "unit"]) == expected_controls


def test_last_cohort_has_no_pre_support_when_only_own_cohort_is_untreated():
    panel = _panel(include_never=False)
    support = panel.att_gt_cells(
        control_group="not_yet_treated", base_period="varying",
        include_pre_periods=True, include_unsupported=True,
    )
    own = support.loc[support.cohort == pd.Period("2020-07", freq="M")]
    # Earlier cohorts can be valid controls for early varying placebo cells,
    # but at June all other cohorts are already treated.
    last_pre = own.loc[own.time == pd.Period("2020-06", freq="M")].iloc[0]
    assert last_pre.n_control_available == 0
    assert not last_pre.is_supported
    assert last_pre.unsupported_reason == "no_complete_control_units"


def test_public_post_comparison_api_preserves_guard_and_accepts_anticipation():
    panel = _panel()
    focal = pd.Period("2020-05", freq="M")
    with pytest.raises(ValueError, match="at or after"):
        panel.comparison_units(focal, "2020-02")
    default = set(panel.comparison_units(focal, focal))
    assert default == {f"future{i}" for i in range(3)} | {f"never{i}" for i in range(3)}
    assert set(panel.comparison_units(focal, "2020-09")) == {f"never{i}" for i in range(3)}
    # Adoption in July is disallowed when June's comparisons may anticipate it.
    actual = set(panel.comparison_units(focal, "2020-06", anticipation=1))
    assert actual == {f"never{i}" for i in range(3)}
    support = panel.att_gt_cells(anticipation=1)
    row = support.loc[(support.cohort == focal) & (support.time == pd.Period("2020-06", freq="M"))].iloc[0]
    assert row.n_control_available == len(actual)


@pytest.mark.parametrize("frequency", ["M", "2M"])
def test_public_comparison_dates_share_period_units_and_later_base_rule(frequency):
    panel = _panel()
    frame = panel.df_analysis()
    old_times = panel.analysis_times()
    times = pd.period_range("2020-01", periods=7, freq=frequency)
    frame["time"] = frame["time"].map(dict(zip(old_times, times)))
    panel = PanelDataDID(df=frame, y="y", unit_col="unit", time_col="time", treated_time="d")
    never = {f"never{i}" for i in range(3)}
    future = {f"future{i}" for i in range(3)}
    assert set(panel.comparison_units(times[4], times[5])) == never | future
    assert set(panel.comparison_units(times[4], times[5], anticipation=1)) == never
    assert set(panel.comparison_units(times[4], times[4], base_time=times[6])) == never
    # Extending the query axis retains the original post-period API behavior.
    beyond = times[-1] + 2
    assert set(panel.comparison_units(times[4], beyond)) == never
