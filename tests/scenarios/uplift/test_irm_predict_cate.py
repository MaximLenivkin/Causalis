import numpy as np
import pandas as pd
import pytest
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin
from sklearn.linear_model import LogisticRegression

from causalis.dgp.causaldata import CausalData
from causalis.scenarios.unconfoundedness import IRM


class CountingRegressor(RegressorMixin, BaseEstimator):
    fit_calls = 0

    @classmethod
    def reset(cls):
        cls.fit_calls = 0

    def fit(self, X, y):
        type(self).fit_calls += 1
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        X_design = np.column_stack([np.ones(X.shape[0]), X])
        self.coef_ = np.linalg.pinv(X_design) @ y
        return self

    def predict(self, X):
        X = np.asarray(X, dtype=float)
        X_design = np.column_stack([np.ones(X.shape[0]), X])
        return X_design @ self.coef_


class CountingClassifier(ClassifierMixin, BaseEstimator):
    fit_calls = 0

    @classmethod
    def reset(cls):
        cls.fit_calls = 0

    def fit(self, X, y):
        type(self).fit_calls += 1
        y = np.asarray(y, dtype=int)
        self.classes_ = np.array([0, 1])
        self.p_ = float(np.clip(np.mean(y), 1e-3, 1.0 - 1e-3))
        return self

    def predict_proba(self, X):
        n = np.asarray(X).shape[0]
        return np.column_stack(
            [
                np.full(n, 1.0 - self.p_, dtype=float),
                np.full(n, self.p_, dtype=float),
            ]
        )

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)


def _make_continuous_causal_data(n=180, seed=123):
    rng = np.random.default_rng(seed)
    user_id = np.array([f"u_{i:04d}" for i in range(n)])
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    p = 1.0 / (1.0 + np.exp(-(0.5 * x1 - 0.3 * x2)))
    d = rng.binomial(1, p)
    tau = 0.4 + 0.3 * (x1 > 0.0)
    y = 1.0 + 0.5 * x1 - 0.25 * x2 + tau * d + rng.normal(scale=0.2, size=n)
    df = pd.DataFrame({"user_id": user_id, "y": y, "d": d, "x1": x1, "x2": x2})
    return CausalData(
        df=df, outcome="y", treatment="d", confounders=["x1", "x2"], user_id="user_id"
    )


def _make_binary_causal_data(n=220, seed=456):
    rng = np.random.default_rng(seed)
    user_id = np.array([f"u_{i:04d}" for i in range(n)])
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    d = rng.binomial(1, 0.5, size=n)
    logits = -0.4 + 0.6 * x1 - 0.2 * x2 + 0.7 * d
    y = rng.binomial(1, 1.0 / (1.0 + np.exp(-logits)))
    df = pd.DataFrame({"user_id": user_id, "y": y, "d": d, "x1": x1, "x2": x2})
    return CausalData(
        df=df, outcome="y", treatment="d", confounders=["x1", "x2"], user_id="user_id"
    )


def _groups(data):
    df = data.get_df(include_user_id=True)
    return pd.Series(
        np.where(df["x1"] >= 0.0, "high_x1", "low_x1"),
        index=pd.Index(df["user_id"], name="user_id"),
        name="segment",
    )


def test_fit_atte_and_gate_do_not_train_or_store_uplift_models():
    CountingRegressor.reset()
    CountingClassifier.reset()
    causaldata = _make_continuous_causal_data()
    model = IRM(
        ml_g=CountingRegressor(),
        ml_m=CountingClassifier(),
        n_folds=3,
        n_jobs=1,
        random_state=42,
    ).fit(causaldata)

    fit_g_calls = CountingRegressor.fit_calls
    fit_m_calls = CountingClassifier.fit_calls
    assert fit_g_calls == 2 * model.n_folds
    assert fit_m_calls == model.n_folds
    assert not hasattr(model, "_uplift_g0_model_")
    assert not hasattr(model, "_uplift_g1_model_")

    model.estimate(score="ATTE")
    assert CountingRegressor.fit_calls == fit_g_calls
    assert CountingClassifier.fit_calls == fit_m_calls
    assert not hasattr(model, "_uplift_g0_model_")
    assert not hasattr(model, "_uplift_g1_model_")

    model.estimate(score="GATE", groups=_groups(causaldata))
    assert CountingRegressor.fit_calls == fit_g_calls
    assert CountingClassifier.fit_calls == fit_m_calls
    assert not hasattr(model, "_uplift_g0_model_")
    assert not hasattr(model, "_uplift_g1_model_")


def test_predict_cate_trains_final_outcome_models_once_and_reuses_cache():
    CountingRegressor.reset()
    CountingClassifier.reset()
    causaldata = _make_continuous_causal_data()
    model = IRM(
        ml_g=CountingRegressor(),
        ml_m=CountingClassifier(),
        n_folds=3,
        random_state=42,
    ).fit(causaldata)
    fit_g_calls = CountingRegressor.fit_calls
    fit_m_calls = CountingClassifier.fit_calls

    X_new = causaldata.X.iloc[:7].copy()
    cate_first = model.predict_cate(X_new)

    assert cate_first.shape == (7,)
    assert np.all(np.isfinite(cate_first))
    assert CountingRegressor.fit_calls == fit_g_calls + 2
    assert CountingClassifier.fit_calls == fit_m_calls
    assert hasattr(model, "_uplift_g0_model_")
    assert hasattr(model, "_uplift_g1_model_")

    cate_second = model.predict_cate(X_new)
    np.testing.assert_allclose(cate_second, cate_first)
    assert CountingRegressor.fit_calls == fit_g_calls + 2
    assert CountingClassifier.fit_calls == fit_m_calls


def test_predict_cate_binary_outcome_is_probability_uplift():
    causaldata = _make_binary_causal_data()
    model = IRM(
        ml_g=CountingClassifier(),
        ml_m=LogisticRegression(max_iter=1000),
        n_folds=3,
        random_state=42,
    ).fit(causaldata)

    cate = model.predict_cate(causaldata.X.iloc[:20])

    assert cate.shape == (20,)
    assert np.all(np.isfinite(cate))
    assert np.all(cate >= -1.0)
    assert np.all(cate <= 1.0)


def test_predict_cate_requires_fitted_feature_columns():
    causaldata = _make_continuous_causal_data()
    model = IRM(
        ml_g=CountingRegressor(),
        ml_m=CountingClassifier(),
        n_folds=3,
        random_state=42,
    ).fit(causaldata)

    with pytest.raises(ValueError, match="missing required feature"):
        model.predict_cate(causaldata.X.drop(columns=["x2"]))


def test_estimate_cate_points_to_predict_cate():
    causaldata = _make_continuous_causal_data()
    model = IRM(
        ml_g=CountingRegressor(),
        ml_m=CountingClassifier(),
        n_folds=3,
        random_state=42,
    ).fit(causaldata)

    with pytest.raises(NotImplementedError, match="predict_cate"):
        model.estimate(score="CATE")


@pytest.mark.parametrize("change", ["outcome", "features", "learner"])
def test_successful_refit_rebuilds_lazy_cate_cache_and_matches_fresh_model(change):
    from sklearn.dummy import DummyRegressor

    CountingRegressor.reset()
    data = _make_continuous_causal_data()
    model = IRM(data, ml_g=CountingRegressor(), ml_m=CountingClassifier(), n_folds=3, random_state=42).fit()
    old = model.predict_cate(data.X.iloc[:8])
    old_g0, old_g1 = model._uplift_g0_model_, model._uplift_g1_model_
    frame = data.df.copy(deep=True)
    if change == "outcome":
        frame["y"] += 4.0 * frame["d"]
    elif change == "features":
        frame.rename(columns={"x1": "z1", "x2": "z2"}, inplace=True)
    else:
        model.ml_g = DummyRegressor()
    names = ["z1", "z2"] if change == "features" else ["x1", "x2"]
    new_data = CausalData(df=frame, outcome="y", treatment="d", confounders=names, user_id="user_id")
    model.fit(new_data)
    for name in ("_uplift_g0_model_", "_uplift_g1_model_", "_uplift_feature_names_", "_uplift_y_is_binary_"):
        assert not hasattr(model, name)
    scoring = new_data.X.iloc[:8].copy()
    result = model.predict_cate(scoring)
    fresh = IRM(new_data, ml_g=model.ml_g, ml_m=CountingClassifier(), n_folds=3, random_state=42).fit()
    np.testing.assert_allclose(result, fresh.predict_cate(scoring), rtol=1e-12, atol=1e-12)
    assert model._uplift_g0_model_ is not old_g0
    assert model._uplift_g1_model_ is not old_g1
    if change == "outcome":
        np.testing.assert_allclose(result, old + 4.0, atol=1e-12)
    cached_calls = CountingRegressor.fit_calls
    np.testing.assert_array_equal(model.predict_cate(scoring), result)
    assert CountingRegressor.fit_calls == cached_calls
