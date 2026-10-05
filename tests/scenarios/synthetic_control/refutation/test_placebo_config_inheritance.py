"""Refutations must change assignment/windows while preserving the fitted ASCM."""

from __future__ import annotations

import inspect
import json
from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from causalis.data_contracts import PanelDataSCM, PanelEstimate
from causalis.scenarios.synthetic_control import (
    ASCM,
    placebo_in_space_table,
    placebo_in_time_table,
    run_placebo_tests,
)
from causalis.scenarios.synthetic_control.dgp import generate_scm_gamma_26


SOURCE_OPTIONS = {
    "lambda_aug": 1e6,
    "lambda_sc": 0.03,
    "max_iter": 500,
    "tol": 1e-8,
    "enforce_sum_to_one_augmented": False,
    "alpha": 0.12,
    "conformal_grid_size": 17,
    "conformal_grid_min": -7.0,
    "conformal_grid_max": 7.0,
    "conformal_grid_scale_mult": 4.5,
    "average_att_n_folds": 2,
    "compute_average_att_ttest": False,
    "compute_pointwise_conformal": False,
}


@pytest.fixture(scope="module")
def panel():
    return generate_scm_gamma_26(
        n_donors=3, n_pre_periods=9, n_post_periods=3, seed=241
    )


def _fit(panel, options=None):
    return ASCM(**(SOURCE_OPTIONS if options is None else options)).fit(panel).estimate()


def _manual_panel(panel, treated_unit, *, start=None, end=None):
    """Construct assignment/windows independently of the refutation's helpers."""
    frame = panel.df_analysis()
    if treated_unit != panel.treated_unit:
        frame = frame.loc[frame[panel.unit_col] != panel.treated_unit].copy()
    else:
        frame = frame.copy()
    if end is not None:
        frame = frame.loc[frame[panel.time_col] <= end].copy()
    start = panel.treatment_start if start is None else start
    frame[panel.treated_time] = (
        (frame[panel.unit_col] == treated_unit) & (frame[panel.time_col] >= start)
    ).astype(int)
    return PanelDataSCM(
        df=frame,
        y=panel.y,
        unit_col=panel.unit_col,
        time_col=panel.time_col,
        treated_time=panel.treated_time,
    )


def _assert_space_row(row, direct):
    gap = direct.observed_outcome - direct.synthetic_outcome
    pre = gap.loc[list(direct.pre_times)].to_numpy()
    post = gap.loc[list(direct.post_times)].to_numpy()
    expected = [
        np.sqrt(np.mean(pre**2)),
        np.sqrt(np.mean(post**2)),
        np.mean(post),
        np.max(np.abs(post)),
    ]
    actual = row[["pre_rmse", "post_rmse", "average_post_gap", "max_abs_post_gap"]]
    np.testing.assert_allclose(actual.to_numpy(dtype=float), expected, rtol=1e-10, atol=1e-10)


def _assert_time_rows(table, panel, options):
    assert not table.empty
    pre = list(panel.pre_times())
    for row in table.itertuples(index=False):
        start = row.placebo_treatment_start
        end = pre[pre.index(start) + row.n_post_after_placebo - 1]
        direct = _fit(_manual_panel(panel, panel.treated_unit, start=start, end=end), options)
        diagnostics = direct.diagnostics
        avg = diagnostics["average_att_estimate"]
        if not np.isfinite(avg):
            avg = float(direct.effect_by_time.mean())
        assert row.average_att_placebo == pytest.approx(avg, rel=1e-10, abs=1e-10)
        assert row.pre_fit_metric == pytest.approx(diagnostics["pre_rmse_augmented"])
        for field, key in [
            ("ci_lower", "average_att_ci_lower"),
            ("ci_upper", "average_att_ci_upper"),
            ("p_value", "average_att_p_value"),
        ]:
            expected = diagnostics[key]
            observed = getattr(row, field)
            if np.isfinite(expected):
                assert observed == pytest.approx(expected, rel=1e-10, abs=1e-10)
            else:
                assert observed is None or pd.isna(observed)
        p = diagnostics["average_att_p_value"]
        assert row.rejects_zero == bool(np.isfinite(p) and p < options["alpha"])


def test_estimate_records_complete_serializable_constructor_configuration(panel):
    estimate = _fit(panel)
    assert estimate.model_options == SOURCE_OPTIONS
    assert set(estimate.model_options) == set(inspect.signature(ASCM).parameters)
    assert json.loads(json.dumps(estimate.model_options)) == SOURCE_OPTIONS
    restored = PanelEstimate.model_validate(estimate.model_dump())
    assert restored.model_options == SOURCE_OPTIONS


@pytest.mark.parametrize("override", [None, {}, {"alpha": 0.2}, {"lambda_aug": 0.15}])
def test_actual_treated_row_matches_original_or_explicit_partial_override(panel, override):
    estimate = _fit(panel)
    options = {**SOURCE_OPTIONS, **(override or {})}
    table = placebo_in_space_table(estimate, panel, model_kwargs=override)
    direct = _fit(panel, options)
    _assert_space_row(table.loc[table.is_actual_treated].iloc[0], direct)
    assert table.attrs["model_options"] == options
    assert table.attrs["model_kwargs_overrides"] == (override or {})


@pytest.mark.parametrize("enforce", [False, True])
def test_donor_placebo_preserves_configuration_and_excludes_actual_treated(panel, enforce):
    options = {**SOURCE_OPTIONS, "enforce_sum_to_one_augmented": enforce}
    estimate = _fit(panel, options)
    table = placebo_in_space_table(estimate, panel)
    donor = panel.donor_pool()[0]
    independent_panel = _manual_panel(panel, donor)
    direct = _fit(independent_panel, options)
    assert panel.treated_unit not in direct.donor_weights_augmented
    _assert_space_row(table.loc[table.unit_id == donor].iloc[0], direct)


@pytest.mark.parametrize("enabled", [False, True])
def test_time_placebo_inherits_per_estimate_inference_overrides(panel, enabled):
    model = ASCM(**SOURCE_OPTIONS).fit(panel)
    overrides = {
        "alpha": 0.18,
        "average_att_n_folds": 4,
        "compute_average_att_ttest": enabled,
        "conformal_grid_size": 11,
        "conformal_grid_min": -5.0,
        "conformal_grid_max": 5.0,
        "conformal_grid_scale_mult": 3.0,
    }
    estimate = model.estimate(**overrides)
    options = {**SOURCE_OPTIONS, **overrides}
    table = placebo_in_time_table(estimate, panel)
    _assert_time_rows(table, panel, options)
    assert estimate.model_options == options
    assert table.attrs["model_options"] == options
    assert model.estimate().model_options == SOURCE_OPTIONS


def test_time_placebo_partial_override_and_runner_preserve_all_other_options(panel):
    estimate = _fit(panel)
    overrides = {"compute_average_att_ttest": True, "alpha": 0.2}
    options = {**SOURCE_OPTIONS, **overrides}
    result = run_placebo_tests(estimate, panel, model_kwargs=overrides)
    _assert_time_rows(result["placebo_in_time"], panel, options)
    for table in result.values():
        assert table.attrs["model_options"] == options
        assert table.attrs["model_kwargs_overrides"] == overrides


def test_fit_configuration_is_snapshotted_and_estimates_do_not_share_options(panel):
    model = ASCM(**SOURCE_OPTIONS).fit(panel)
    first = model.estimate()
    model.lambda_aug = 2.0
    first.model_options["lambda_aug"] = 123.0
    second = model.estimate()
    assert second.model_options == SOURCE_OPTIONS
    model.fit(panel)
    assert model.estimate().model_options == {**SOURCE_OPTIONS, "lambda_aug": 2.0}


@pytest.mark.parametrize("function", [placebo_in_space_table, placebo_in_time_table, run_placebo_tests])
@pytest.mark.parametrize("metadata", [{}, {"lambda_aug": 1e6}])
def test_legacy_or_partial_configuration_requires_complete_explicit_replacement(panel, function, metadata):
    legacy = _fit(panel).model_copy(update={"model_options": metadata})
    with pytest.raises(ValueError, match="Missing ASCM configuration.*re-estimate.*model_kwargs"):
        function(legacy, panel)


@pytest.mark.parametrize("function", [placebo_in_space_table, placebo_in_time_table])
def test_legacy_configuration_can_be_restored_with_full_explicit_kwargs(panel, function):
    legacy = _fit(panel).model_copy(update={"model_options": {}})
    table = function(legacy, panel, model_kwargs=SOURCE_OPTIONS)
    assert table.attrs["model_options"] == SOURCE_OPTIONS
    if function is placebo_in_space_table:
        _assert_space_row(table.loc[table.is_actual_treated].iloc[0], _fit(panel))
    else:
        _assert_time_rows(table, panel, SOURCE_OPTIONS)


def test_unrelated_metadata_is_ignored_without_mutating_inputs(panel):
    estimate = _fit(panel)
    estimate.model_options["release_metadata"] = {"version": "future"}
    before = deepcopy(estimate.model_options)
    frame = panel.df_analysis().copy(deep=True)
    overrides = {"lambda_aug": 0.15, "conformal_grid_min": None}
    saved_overrides = dict(overrides)
    table = placebo_in_space_table(estimate, panel, model_kwargs=overrides)
    expected = {**SOURCE_OPTIONS, **overrides}
    assert table.attrs["model_options"] == expected
    assert estimate.model_options == before
    assert overrides == saved_overrides
    pd.testing.assert_frame_equal(panel.df_analysis(), frame)
    _assert_space_row(table.loc[table.is_actual_treated].iloc[0], _fit(panel, expected))


@pytest.mark.parametrize("invalid", [[], "lambda_aug", 1])
def test_invalid_explicit_configuration_type_has_clear_error(panel, invalid):
    with pytest.raises(TypeError, match="model_kwargs must be a mapping"):
        placebo_in_space_table(_fit(panel), panel, model_kwargs=invalid)


def test_unknown_explicit_override_is_rejected(panel):
    with pytest.raises(TypeError, match="Unknown ASCM model_kwargs.*lambda_aug_typo"):
        placebo_in_space_table(_fit(panel), panel, model_kwargs={"lambda_aug_typo": 2.0})


def test_invalid_legacy_configuration_type_has_clear_error(panel):
    estimate = _fit(panel).model_copy(update={"model_options": [1.0]})
    with pytest.raises(TypeError, match="estimate.model_options must be a mapping"):
        placebo_in_space_table(estimate, panel)


def test_explicit_options_record_canonical_constructor_types(panel):
    overrides = {"lambda_aug": "0.15", "max_iter": 500.0}
    table = placebo_in_space_table(_fit(panel), panel, model_kwargs=overrides)
    expected = {**SOURCE_OPTIONS, "lambda_aug": 0.15}
    assert table.attrs["model_options"] == expected
    assert type(table.attrs["model_options"]["lambda_aug"]) is float
    assert type(table.attrs["model_options"]["max_iter"]) is int
    assert table.attrs["model_kwargs_overrides"] == overrides
    _assert_space_row(table.loc[table.is_actual_treated].iloc[0], _fit(panel, expected))


def test_partial_legacy_metadata_can_be_completed_explicitly(panel):
    legacy = _fit(panel).model_copy(update={"model_options": {"lambda_aug": 1e6}})
    missing = {key: value for key, value in SOURCE_OPTIONS.items() if key != "lambda_aug"}
    table = placebo_in_time_table(legacy, panel, model_kwargs=missing)
    assert table.attrs["model_options"] == SOURCE_OPTIONS
    _assert_time_rows(table, panel, SOURCE_OPTIONS)


def test_empty_time_table_retains_configuration_and_validates_overrides(panel):
    estimate = _fit(panel)
    table = placebo_in_time_table(estimate, panel, pseudo_post_horizon=100)
    assert table.empty
    assert table.attrs["model_options"] == SOURCE_OPTIONS
    with pytest.raises(ValueError, match="alpha must be finite"):
        placebo_in_time_table(
            estimate, panel, model_kwargs={"alpha": 1.0}, pseudo_post_horizon=100
        )


def test_pointwise_configuration_is_inherited_and_can_be_explicitly_disabled(panel):
    options = {
        **SOURCE_OPTIONS,
        "alpha": 0.2,
        "compute_pointwise_conformal": True,
        "conformal_grid_size": 3,
    }
    estimate = _fit(panel, options)
    assert estimate.model_options == options
    table = placebo_in_space_table(
        estimate, panel, model_kwargs={"compute_pointwise_conformal": False}
    )
    expected = {**options, "compute_pointwise_conformal": False}
    assert table.attrs["model_options"] == expected
    _assert_space_row(table.loc[table.is_actual_treated].iloc[0], _fit(panel, expected))


def test_failed_refit_cannot_expose_stale_configuration(panel):
    model = ASCM(**SOURCE_OPTIONS).fit(panel)
    with pytest.raises(ValueError, match="PanelDataSCM"):
        model.fit(None)
    with pytest.raises(RuntimeError, match="fitted"):
        model.estimate()
    model.lambda_aug = 2.0
    model.fit(panel)
    assert model.estimate().model_options == {**SOURCE_OPTIONS, "lambda_aug": 2.0}


def test_inference_override_uses_fitted_configuration_after_attribute_changes(panel):
    model = ASCM(**SOURCE_OPTIONS).fit(panel)
    inference = {"compute_average_att_ttest": True, "alpha": 0.2}
    expected = model.estimate(**inference)
    changed = {
        "lambda_aug": 0.01,
        "lambda_sc": 2.0,
        "max_iter": 250,
        "tol": 1e-6,
        "enforce_sum_to_one_augmented": True,
    }
    for key, value in changed.items():
        setattr(model, key, value)
    actual = model.estimate(**inference)
    assert actual.model_options == expected.model_options == {**SOURCE_OPTIONS, **inference}
    for key in [
        "average_att_estimate", "average_att_ci_lower", "average_att_ci_upper",
        "average_att_p_value", "average_att_standard_error", "pre_rmse_augmented",
    ]:
        assert actual.diagnostics[key] == pytest.approx(expected.diagnostics[key])
    for key, value in changed.items():
        assert getattr(model, key) == value
