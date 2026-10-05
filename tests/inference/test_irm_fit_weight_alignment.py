"""Fit-time weights retain the same rows and order as cross-fitted scores."""

import warnings

import numpy as np
import pandas as pd
import pytest
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import LinearRegression

from causalis.data_contracts.causaldata import CausalData
from causalis.scenarios.unconfoundedness import IRM


class FeaturePropensity(ClassifierMixin, BaseEstimator):
    fit_calls = 0

    def fit(self, X, y):
        type(self).fit_calls += 1
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X):
        p = np.asarray(X)[:, 0]
        return np.column_stack([1 - p, p])


def _data():
    p = np.tile([0.02, 0.15, 0.35, 0.65, 0.85, 0.98], 20)
    d = np.tile([0, 1, 1, 0, 1, 0], 20)
    x = np.linspace(-1, 1, p.size)
    y = 4 + 0.3 * p + x + d * (0.5 + 0.7 * x) + 0.1 * np.sin(np.arange(p.size))
    frame = pd.DataFrame({"uid": [f"u{i}" for i in range(p.size)], "p": p, "x": x, "d": d, "y": y})
    frame.index = pd.Index(np.tile(["duplicate", "row"], p.size // 2), name="row")
    return CausalData(df=frame, outcome="y", treatment="d", confounders=["p", "x"], user_id="uid")


def _fit(data, weights, **kwargs):
    return IRM(
        data, weights=weights, ml_g=LinearRegression(), ml_m=FeaturePropensity(),
        n_folds=3, overlap_policy="drop", overlap_threshold=0.1,
        random_state=7, **kwargs,
    ).fit()


def _estimate(model):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return model.estimate(score="ATE")


@pytest.mark.parametrize("shape", ["array", "array_col", "array_row", "dict", "dict_col", "dict_row", "dict_multi"])
@pytest.mark.parametrize("store_diagnostics", [False, True])
def test_drop_weights_match_manual_retained_score_and_preserve_inputs(shape, store_diagnostics):
    data = _data()
    original = data.df.copy(deep=True)
    n = len(original)
    raw_w = np.linspace(0.3, 2.0, n)
    raw_bar = np.linspace(2.5, 0.8, n)
    if shape.startswith("array"):
        weights = raw_w.copy()
        if shape == "array_col":
            weights = weights[:, None]
        elif shape == "array_row":
            weights = weights[None, :]
        raw_bar = raw_w
    else:
        bar = raw_bar.copy()
        if shape == "dict_col":
            bar = bar[:, None]
        elif shape == "dict_row":
            bar = bar[None, :]
        elif shape == "dict_multi":
            bar = np.column_stack([bar, np.full(n, 999)])
        weights = {"weights": raw_w.copy(), "weights_bar": bar}
    originals = {key: value.copy() for key, value in weights.items()} if isinstance(weights, dict) else weights.copy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        model = _fit(data, weights, store_diagnostics=store_diagnostics)
        result = _estimate(model)

    for snapshots in (model._fit_weights_full_, model._fit_weights_):
        for values in snapshots.values():
            assert not values.flags.writeable
            with pytest.raises(ValueError):
                values[0] = 999.0

    mask = (original["p"].to_numpy() > 0.1) & (original["p"].to_numpy() < 0.9)
    w = raw_w[mask] / raw_w[mask].mean()
    w_bar = raw_bar[mask] / raw_w[mask].mean()
    y, d, p = original["y"].to_numpy()[mask], original["d"].to_numpy()[mask], model.m_hat_
    signal = w * (model.g1_hat_ - model.g0_hat_) + w_bar * (
        d * (y - model.g1_hat_) / p - (1 - d) * (y - model.g0_hat_) / (1 - p)
    )
    assert result.value == pytest.approx(signal.mean(), rel=1e-13)
    assert model.se_[0] == pytest.approx(signal.std(ddof=1) / np.sqrt(mask.sum()), rel=1e-13)
    np.testing.assert_array_equal(model._fit_index_, original["uid"].to_numpy()[mask])
    pd.testing.assert_frame_equal(data.df, original)
    if isinstance(weights, dict):
        for key, expected in originals.items():
            np.testing.assert_array_equal(weights[key], expected)
    else:
        np.testing.assert_array_equal(weights, originals)
    if store_diagnostics:
        np.testing.assert_allclose(result.diagnostic_data.w, w)
        np.testing.assert_allclose(result.diagnostic_data.w_bar, w_bar)
        np.testing.assert_array_equal(result.diagnostic_data.score_plot_cache["row_index"], np.flatnonzero(mask))
    else:
        assert result.diagnostic_data is None


@pytest.mark.parametrize("policy", ["clip", "drop"])
def test_weights_snapshot_survives_mutation_and_refit_uses_full_sample(policy):
    data = _data()
    original = data.df.copy(deep=True)
    w = np.linspace(0.3, 2.0, len(data.df))
    w_bar = np.linspace(2.5, 0.8, len(data.df))
    weights = {"weights": w, "weights_bar": w_bar}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        model = IRM(data, weights=weights, ml_g=LinearRegression(), ml_m=FeaturePropensity(), n_folds=3,
                    overlap_policy=policy, overlap_threshold=0.1, random_state=7).fit()
    first = _estimate(model)
    first_psi = model.psi_.copy()
    w[:] = w[::-1].copy()
    w_bar[:] = w_bar[::-1].copy()
    model.weights = None
    second = _estimate(model)
    assert second.value == pytest.approx(first.value)
    np.testing.assert_array_equal(model.psi_, first_psi)
    assert second.model_options["se_approx_weight_norm"] is True

    model.weights = weights
    model.fit()
    refit = _estimate(model)
    fresh = IRM(data, weights=weights, ml_g=LinearRegression(), ml_m=FeaturePropensity(), n_folds=3,
                overlap_policy=policy, overlap_threshold=0.1, random_state=7).fit()
    fresh_result = _estimate(fresh)
    assert refit.value == pytest.approx(fresh_result.value, rel=1e-13)
    np.testing.assert_allclose(model.psi_, fresh.psi_, rtol=1e-13)
    assert abs(refit.value - first.value) > 0.01
    pd.testing.assert_frame_equal(data.df, original)


@pytest.mark.parametrize("invalid", ["length", "bar_length", "nonfinite", "bar_nonfinite", "zero_mean", "missing_key"])
def test_invalid_full_sample_weights_fail_before_nuisance_fitting(invalid):
    data = _data()
    n = len(data.df)
    weights = {"weights": np.ones(n), "weights_bar": np.ones(n)}
    if invalid == "length":
        weights["weights"] = np.ones(n - 1)
    elif invalid == "bar_length":
        weights["weights_bar"] = np.ones(n - 1)
    elif invalid == "nonfinite":
        weights["weights"][0] = np.inf
    elif invalid == "bar_nonfinite":
        weights["weights_bar"][0] = np.nan
    elif invalid == "zero_mean":
        weights["weights"][:] = 0
    else:
        del weights["weights"]
    FeaturePropensity.fit_calls = 0
    with pytest.raises(ValueError, match="weights"):
        _fit(data, weights)
    assert FeaturePropensity.fit_calls == 0


def test_invalid_weight_config_does_not_replace_existing_fit_snapshot():
    data = _data()
    model = _fit(data, np.linspace(0.3, 2.0, len(data.df)))
    expected = _estimate(model)
    expected_psi = model.psi_.copy()
    model.weights = np.ones(len(data.df) - 1)
    with pytest.raises(ValueError, match="weights"):
        model.fit()
    assert _estimate(model).value == pytest.approx(expected.value)
    np.testing.assert_array_equal(model.psi_, expected_psi)
