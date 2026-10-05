"""Documented IV model/result diagnostic equivalence and lifecycle guards."""

from types import SimpleNamespace

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.exceptions import NotFittedError

from causalis.data_contracts import IVCausalData
from causalis.scenarios.iv import IIVM
from causalis.scenarios.iv.refutation import (
    first_stage,
    instrument_overlap,
    instrument_overlap_plot,
    reduced_form,
)


TABLES = [instrument_overlap, first_stage, reduced_form]
ENTRYPOINTS = [*TABLES, instrument_overlap_plot]


def _make_model(*, threshold=0.01, seed=917):
    rng = np.random.default_rng(seed)
    n = 400
    x = rng.normal(size=n)
    z = rng.binomial(1, 0.5, size=n)
    d = rng.binomial(1, 0.15 + 0.65 * z, size=n)
    y = 2.0 * d + 0.7 * x + rng.normal(size=n)
    data = IVCausalData.from_df(
        pd.DataFrame({"x": x, "z": z, "d": d, "y": y}),
        treatment="d",
        outcome="y",
        instruments="z",
        confounders=["x"],
    )
    return IIVM(
        data,
        ml_g=LinearRegression(),
        ml_m=LogisticRegression(max_iter=1000),
        ml_r=LogisticRegression(max_iter=1000),
        n_folds=2,
        n_jobs=1,
        random_state=3,
        weak_iv_threshold=threshold,
    )


def _clear_payload_caches(diag):
    diag.instrument_overlap = None
    diag.first_stage = None
    diag.reduced_form = None
    diag.diagnostics = {}


@pytest.mark.parametrize("entrypoint", TABLES, ids=lambda fn: fn.__name__)
@pytest.mark.parametrize("cached", [True, False], ids=["cached", "lazy"])
def test_model_tables_equal_estimate_and_payload(entrypoint, cached):
    model = _make_model().fit()
    estimate = model.estimate()
    if not cached:
        _clear_payload_caches(estimate.diagnostic_data)
    expected = entrypoint(estimate)
    if not cached:
        _clear_payload_caches(estimate.diagnostic_data)
    actual = entrypoint(model)
    pd.testing.assert_frame_equal(actual, expected)
    pd.testing.assert_frame_equal(entrypoint(estimate.diagnostic_data), expected)


def test_model_overlap_plot_equals_estimate_plot():
    model = _make_model().fit()
    estimate = model.estimate()
    figures = []
    try:
        expected = instrument_overlap_plot(estimate, bins=7)
        figures.append(expected)
        actual = instrument_overlap_plot(model, bins=7)
        figures.append(actual)
        expected_ax, actual_ax = expected.axes[0], actual.axes[0]
        assert actual_ax.get_legend_handles_labels()[1] == expected_ax.get_legend_handles_labels()[1]
        assert len(actual_ax.patches) == len(expected_ax.patches) == 14
        for expected_patch, actual_patch in zip(expected_ax.patches, actual_ax.patches):
            np.testing.assert_allclose(
                [actual_patch.get_x(), actual_patch.get_width(), actual_patch.get_height()],
                [expected_patch.get_x(), expected_patch.get_width(), expected_patch.get_height()],
            )
        for expected_line, actual_line in zip(expected_ax.lines, actual_ax.lines):
            np.testing.assert_allclose(actual_line.get_xdata(), expected_line.get_xdata())
    finally:
        for fig in figures:
            plt.close(fig)


@pytest.mark.parametrize("fitted", [False, True], ids=["unfitted", "fit_without_estimate"])
@pytest.mark.parametrize("entrypoint", ENTRYPOINTS, ids=lambda fn: fn.__name__)
def test_model_without_estimate_has_actionable_error(entrypoint, fitted):
    model = _make_model()
    if fitted:
        model.fit()
    with pytest.raises(ValueError, match=r"call estimate\(\)"):
        entrypoint(model)


@pytest.mark.parametrize("entrypoint", ENTRYPOINTS, ids=lambda fn: fn.__name__)
def test_missing_estimate_payload_has_actionable_error(entrypoint):
    model = _make_model().fit()
    model.result_ = model.estimate().model_copy(update={"diagnostic_data": None})
    with pytest.raises(ValueError, match=r"diagnostic_data.*call estimate\(\)"):
        entrypoint(model)


@pytest.mark.parametrize("entrypoint", ENTRYPOINTS, ids=lambda fn: fn.__name__)
@pytest.mark.parametrize("nested", [False, True], ids=["direct", "model_result"])
def test_non_iv_diagnostic_payload_is_rejected(entrypoint, nested):
    invalid = SimpleNamespace(diagnostic_data={"z": [0, 1]})
    source = SimpleNamespace(result_=invalid) if nested else invalid
    with pytest.raises(TypeError, match="IVCausalEstimate.diagnostic_data"):
        entrypoint(source)


def test_lazy_model_diagnostics_use_estimate_options_snapshot_and_late():
    model = _make_model(threshold=0.9).fit()
    with pytest.warns(RuntimeWarning, match="estimated first stage is weak"):
        estimate = model.estimate()
    expected = first_stage(estimate)
    assert expected.loc[expected.metric == "weak_iv_flag", "value"].item() == "RED"
    model.weak_iv_threshold = 0.01
    _clear_payload_caches(estimate.diagnostic_data)

    actual = first_stage(model)
    pd.testing.assert_frame_equal(actual, expected)
    assert estimate.diagnostic_data.first_stage["weak_iv_threshold"] == 0.9
    reduced_form(model)
    assert estimate.diagnostic_data.reduced_form["late_value"] == estimate.value


@pytest.mark.parametrize("entrypoint", TABLES, ids=lambda fn: fn.__name__)
def test_model_uses_newest_successful_estimate(entrypoint):
    model = _make_model().fit()
    old_estimate = model.estimate(alpha=0.05)
    old_expected = entrypoint(old_estimate)
    model.fit(_make_model(seed=918).data)
    new_estimate = model.estimate(alpha=0.1)

    assert model.result_ is new_estimate
    assert new_estimate is not old_estimate
    pd.testing.assert_frame_equal(entrypoint(model), entrypoint(new_estimate))
    pd.testing.assert_frame_equal(entrypoint(old_estimate), old_expected)
    assert not entrypoint(new_estimate).equals(old_expected)


@pytest.mark.parametrize("failed", [False, True], ids=["successful_refit", "failed_refit"])
@pytest.mark.parametrize("entrypoint", ENTRYPOINTS, ids=lambda fn: fn.__name__)
def test_refit_requires_new_estimate_and_preserves_saved_result(entrypoint, failed):
    model = _make_model().fit()
    saved_estimate = model.estimate()
    saved_data = saved_estimate.diagnostic_data
    if failed:
        with pytest.raises(TypeError, match="IVCausalData"):
            model.fit(pd.DataFrame())
    else:
        model.fit(_make_model(seed=918).data)

    with pytest.raises(ValueError, match=r"call estimate\(\)"):
        entrypoint(model)
    assert saved_estimate.diagnostic_data is saved_data
    if entrypoint is instrument_overlap_plot:
        figure = entrypoint(saved_estimate)
        plt.close(figure)
    else:
        pd.testing.assert_frame_equal(entrypoint(saved_estimate), entrypoint(saved_data))


def _fail_refit(model, stage):
    if stage == "input":
        with pytest.raises(TypeError, match="IVCausalData"):
            model.fit(pd.DataFrame())
    else:
        model.ml_m = LogisticRegression(C=-1, max_iter=1000)
        with pytest.raises(ValueError, match="parameter"):
            model.fit()


def _access_fitted_attribute(model, name):
    attribute = getattr(model, name)
    return attribute() if callable(attribute) else attribute


@pytest.mark.parametrize("stage", ["input", "learner"])
@pytest.mark.parametrize("attribute", ["estimate", "diagnostics_", "coef", "se", "pvalues", "summary", "confint"])
def test_failed_refit_cannot_reuse_old_fit_or_inference(stage, attribute):
    model = _make_model().fit()
    saved_estimate = model.estimate()
    saved_summary = saved_estimate.summary()
    _fail_refit(model, stage)

    with pytest.raises(NotFittedError):
        _access_fitted_attribute(model, attribute)
    pd.testing.assert_frame_equal(saved_estimate.summary(), saved_summary)


@pytest.mark.parametrize("stage", ["input", "learner"])
def test_successful_fit_after_failed_refit_matches_fresh_model(stage):
    model = _make_model().fit()
    model.estimate()
    _fail_refit(model, stage)
    fresh = _make_model(seed=918)
    model.ml_m = LogisticRegression(max_iter=1000)
    actual = model.fit(fresh.data).estimate()
    expected = fresh.fit().estimate()

    assert actual.value == pytest.approx(expected.value, abs=1e-12)
    assert actual.std_error == pytest.approx(expected.std_error, abs=1e-12)
    np.testing.assert_allclose(model.predictions_["g_hat0"], fresh.predictions_["g_hat0"])
    for entrypoint in TABLES:
        pd.testing.assert_frame_equal(entrypoint(model), entrypoint(fresh))


@pytest.mark.parametrize("attribute", ["coef", "se", "pvalues", "summary", "confint"])
def test_successful_refit_requires_new_inference(attribute):
    model = _make_model().fit()
    model.estimate()
    model.fit(_make_model(seed=918).data)

    with pytest.raises(NotFittedError):
        _access_fitted_attribute(model, attribute)
    assert model.diagnostics_["m_hat"].shape == (400,)
    model.estimate()
    _access_fitted_attribute(model, attribute)
