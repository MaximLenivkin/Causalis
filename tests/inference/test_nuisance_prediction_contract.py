"""Reject undefined learner outputs before probability repair or inference."""
import numpy as np
import pandas as pd
import pytest
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin, is_classifier
from sklearn.linear_model import LinearRegression, LogisticRegression

from causalis.data_contracts import CausalData, IVCausalData, MultiCausalData
from causalis.scenarios.unconfoundedness import IRM
from causalis.scenarios.iv import IIVM
from causalis.scenarios.multi_unconfoundedness.model import MultiTreatmentIRM
import causalis.scenarios.unconfoundedness._utils as binary_utils
import causalis.scenarios.multi_unconfoundedness._utils as multi_utils
import causalis.scenarios.unconfoundedness.model as binary_model
import causalis.scenarios.multi_unconfoundedness.model as multi_model
import causalis.scenarios.iv.model as iv_model


class ConstantRegressor(RegressorMixin, BaseEstimator):
    def __init__(self, value=0.5):
        self.value = value

    def fit(self, X, y):
        return self

    def predict(self, X):
        return np.full(len(X), self.value)


class ProbabilityClassifier(ClassifierMixin, BaseEstimator):
    """Expose bad raw probabilities even in a column not selected for P(Y=1)."""
    def __init__(self, value=0.5, bad_column=0, classes=None):
        self.value = value
        self.bad_column = bad_column
        self.classes = classes

    def fit(self, X, y):
        self.classes_ = np.unique(y) if self.classes is None else np.asarray(self.classes)
        return self

    def predict_proba(self, X):
        probabilities = np.full((len(X), len(self.classes_)), 0.25)
        probabilities[:, self.bad_column] = self.value
        return probabilities


class UnlabelledSingleColumnClassifier(ClassifierMixin, BaseEstimator):
    """Legacy supported API without reliable classes_, requiring predict() fallback."""
    def __init__(self, value=0.5):
        self.value = value

    def fit(self, X, y):
        return self

    def predict_proba(self, X):
        return np.ones((len(X), 1))

    def predict(self, X):
        return np.full(len(X), self.value)


def dataset(kind, binary_outcome=False):
    rng = np.random.default_rng(7331)
    n = 180
    x = rng.normal(size=n)
    z = np.tile([0, 1], n // 2)
    d = rng.binomial(1, 0.2 + 0.6 * z)
    y = rng.binomial(1, 0.5, n) if binary_outcome else 8 + x + d + rng.normal(size=n)
    frame = pd.DataFrame(dict(y=y, d=d, z=z, x=x), index=np.arange(n) // 2)
    if kind == "binary":
        return CausalData.from_df(frame, "d", "y", ["x"])
    if kind == "iv":
        return IVCausalData.from_df(frame, "d", "y", "z", ["x"])
    labels = np.tile([0, 1, 2], n // 3)
    for k in range(3):
        frame[f"d{k}"] = (labels == k).astype(int)
    return MultiCausalData.from_df(
        frame, outcome="y", treatment_names=["d0", "d1", "d2"],
        confounders=["x"], control_treatment="d0")


def estimator(kind, data, *, g=None, m=None, r=None, n_jobs=1):
    options = dict(data=data, ml_g=g if g is not None else LinearRegression(),
                   ml_m=m if m is not None else LogisticRegression(max_iter=500),
                   n_folds=3, random_state=19, n_jobs=n_jobs, store_diagnostics=False)
    if kind == "binary":
        return IRM(**options)
    if kind == "iv":
        options.pop("store_diagnostics")
        return IIVM(ml_r=r if r is not None else LogisticRegression(max_iter=500), **options)
    return MultiTreatmentIRM(**options)


@pytest.mark.parametrize("kind", ["binary", "multi", "iv"])
@pytest.mark.parametrize("role", ["g_continuous", "g_binary", "m"])
@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("n_jobs", [1, 2])
def test_fit_rejects_nonfinite_raw_nuisance_predictions(kind, role, value, n_jobs):
    data = dataset(kind, binary_outcome=role == "g_binary")
    bad = ProbabilityClassifier(value=value) if role == "m" and kind == "multi" else ConstantRegressor(value)
    options = {"m": bad} if role == "m" else {"g": bad}
    model = estimator(kind, data, n_jobs=n_jobs, **options)
    with pytest.raises(RuntimeError, match="non-finite"):
        model.fit()


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("n_jobs", [1, 2])
def test_iv_shared_helper_rejects_invalid_treatment_nuisance(value, n_jobs):
    model = estimator("iv", dataset("iv"), r=ConstantRegressor(value), n_jobs=n_jobs)
    with pytest.raises(RuntimeError, match="non-finite"):
        model.fit()


@pytest.mark.parametrize("kind", ["binary", "iv"])
@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_public_fit_rejects_nonfinite_hard_label_probability_fallback(kind, value):
    model = estimator(kind, dataset(kind), m=UnlabelledSingleColumnClassifier(value))
    with pytest.raises(RuntimeError, match="non-finite"):
        model.fit()


@pytest.mark.parametrize("value", [0.0, 1.0, -0.3, 1.3])
def test_finite_hard_label_probability_fallback_keeps_existing_mapping(value):
    X = np.ones((6, 1))
    classifier = UnlabelledSingleColumnClassifier(value)
    actual = binary_utils._predict_prob_or_value(classifier, X, True)
    np.testing.assert_array_equal(actual, np.full(6, float(np.isclose(value, 1.0))))


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("kind", ["binary", "multi"])
def test_validate_complete_probability_output_before_selecting_class_one(kind, value):
    X = np.arange(5).reshape(-1, 1)
    classifier = ProbabilityClassifier(value=value, classes=[0, 1]).fit(X, [0, 1])
    with pytest.raises(RuntimeError, match="non-finite"):
        if kind == "binary":
            binary_utils._predict_prob_or_value(classifier, X)
        else:
            MultiTreatmentIRM()._predict_binary_outcome_probability(classifier, X)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("kind,role", [
    ("binary", "g0"), ("binary", "g1"), ("binary", "m"),
    ("multi", "g"), ("multi", "m")])
def test_cross_fit_storage_rejects_nonfinite_values_even_if_fold_helper_is_bypassed(monkeypatch, kind, role, value):
    model = estimator(kind, dataset(kind))
    n = len(model.data.df)
    if kind == "binary":
        predictions = dict(g0_hat=np.ones(n), g1_hat=np.ones(n), m_hat=np.full(n, .5))
        predictions[{"g0": "g0_hat", "g1": "g1_hat", "m": "m_hat"}[role]][2] = value
        outputs = (predictions["g0_hat"], predictions["g1_hat"], predictions["m_hat"],
                   np.arange(n) % 3, None)
    else:
        predictions = dict(g_hat=np.ones((n, 3)), m_hat=np.full((n, 3), 1 / 3))
        predictions["g_hat" if role == "g" else "m_hat"][2, 1] = value
        outputs = (predictions["g_hat"], predictions["m_hat"], np.arange(n) % 3)
    monkeypatch.setattr(model, "_cross_fit_nuisances", lambda **kwargs: outputs)
    with pytest.raises(RuntimeError, match="non-finite"):
        model.fit()
    assert not hasattr(model, "m_hat_")


@pytest.mark.parametrize("value", [-0.3, 1.3])
def test_finite_out_of_range_binary_propensity_keeps_warning_and_clip_policy(value):
    with pytest.warns(RuntimeWarning, match="outside"):
        actual = binary_utils._predict_prob_or_value(ConstantRegressor(value), np.ones((6, 1)), True)
    np.testing.assert_array_equal(actual, np.full(6, np.clip(value, 0, 1)))


def test_finite_multiclass_probabilities_keep_clipping_and_normalization():
    X = np.ones((6, 1))
    classifier = ProbabilityClassifier(value=1.3, classes=[2, 0, 1]).fit(X, [0, 1, 2])
    with pytest.warns(RuntimeWarning):
        actual = multi_utils._predict_propensity_matrix(classifier, X, 3)
    np.testing.assert_array_equal(actual, np.tile([1 / 6, 1 / 6, 2 / 3], (6, 1)))


@pytest.mark.parametrize("kind", ["binary", "multi"])
@pytest.mark.parametrize("label", [0, 1])
def test_finite_single_class_binary_probabilities_keep_existing_class_semantics(kind, label):
    X = np.ones((6, 1))
    classifier = ProbabilityClassifier(value=1.0, classes=[label]).fit(X, [label])
    actual = (binary_utils._predict_prob_or_value(classifier, X) if kind == "binary" else
              MultiTreatmentIRM()._predict_binary_outcome_probability(classifier, X))
    np.testing.assert_array_equal(actual, np.full(6, label))


def reference_binary_predictions(model, X, is_propensity=False):
    """Independent finite sklearn API adapter, without rejection/repair of invalid outputs."""
    if is_classifier(model):
        result = model.predict_proba(X)[:, list(model.classes_).index(1)]
    else:
        result = model.predict(X)
    result = np.asarray(result, dtype=float).ravel()
    return np.clip(result, 0, 1) if is_propensity else result


def reference_multi_predictions(model, X, n_treatments):
    raw = model.predict_proba(X)
    aligned = raw[:, [list(model.classes_).index(k) for k in range(n_treatments)]]
    clipped = np.clip(aligned, 0, 1)
    return clipped / clipped.sum(axis=1, keepdims=True)


@pytest.mark.parametrize("kind", ["binary", "multi", "iv"])
@pytest.mark.parametrize("binary_outcome", [False, True])
def test_finite_sklearn_cross_fit_predictions_and_inference_match_independent_adapter(monkeypatch, kind, binary_outcome):
    data = dataset(kind, binary_outcome=binary_outcome)
    before = data.get_df()
    g = LogisticRegression(max_iter=500) if binary_outcome else LinearRegression()
    actual = estimator(kind, data, g=g).fit()
    result = actual.estimate()
    module = {"binary": binary_model, "multi": multi_model, "iv": iv_model}[kind]
    with monkeypatch.context() as patch:
        patch.setattr(module, "_predict_propensity_matrix" if kind == "multi" else "_predict_prob_or_value",
                      reference_multi_predictions if kind == "multi" else reference_binary_predictions)
        expected = estimator(kind, data, g=g).fit()
        expected_result = expected.estimate()
    attributes = {
        "binary": ["g0_hat_", "g1_hat_", "m_hat_", "psi_", "psi_a_", "psi_b_", "_full_sample_folds_"],
        "multi": ["g_hat_", "m_hat_", "psi_", "psi_a_", "psi_b_"],
        "iv": ["g_hat0_", "g_hat1_", "r_hat0_", "r_hat1_", "m_hat_", "psi_", "phi_y_", "phi_d_"]}
    for attribute in attributes[kind]:
        np.testing.assert_array_equal(getattr(actual, attribute), getattr(expected, attribute))
    for attribute in ["coef_", "se_", "confint_", "pval_"]:
        np.testing.assert_array_equal(getattr(actual, attribute), getattr(expected, attribute))
    np.testing.assert_array_equal(result.value, expected_result.value)
    pd.testing.assert_frame_equal(data.get_df(), before)
