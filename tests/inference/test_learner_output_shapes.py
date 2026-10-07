"""Public-fit regressions for real, row-aligned nuisance predictions."""
import numpy as np
import pytest
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin

from tests.inference.test_nuisance_prediction_contract import dataset, estimator
from causalis.scenarios.unconfoundedness._utils import _predict_prob_or_value
from causalis.scenarios.multi_unconfoundedness.model import MultiTreatmentIRM
from causalis.scenarios.multi_unconfoundedness._utils import _predict_propensity_matrix


def output(values, mode):
    if mode == "scalar":
        return values.flat[0]
    if mode == "short":
        return values[:1]
    if mode == "long":
        return np.concatenate([values, values[:1]])
    if mode == "row":
        return values.reshape(1, -1)
    if mode == "column":
        return values.reshape(-1, 1)
    if mode == "matrix":
        return np.column_stack([values, values])
    if mode == "tensor":
        return values[..., None, None]
    if mode in {"complex", "zero_imaginary", "object_complex"}:
        result = values.astype(complex)
        if mode != "zero_imaginary":
            result.flat[0] += 2j
        return result.astype(object) if mode == "object_complex" else result
    return values


class ShapedRegressor(RegressorMixin, BaseEstimator):
    def __init__(self, mode="vector"):
        self.mode = mode

    def fit(self, X, y):
        self.mean_ = float(np.mean(y))
        return self

    def predict(self, X):
        return output(np.full(len(X), self.mean_), self.mode)


class ShapedClassifier(ClassifierMixin, BaseEstimator):
    def __init__(self, mode="valid", labelled=True, hard_mode="vector"):
        self.mode = mode
        self.labelled = labelled
        self.hard_mode = hard_mode

    def fit(self, X, y):
        self.labels_ = np.unique(y)
        if self.labelled:
            self.classes_ = self.labels_
        return self

    def predict_proba(self, X):
        k = len(self.labels_) if self.labelled else 1
        p = np.full((len(X), k), 1 / k)
        if self.mode == "extra_column":
            return np.column_stack([p, p[:, 0]])
        return output(p, self.mode)

    def predict(self, X):
        return output(np.ones(len(X)), self.hard_mode)


REGRESSOR_ROLES = [("binary", "g"), ("binary", "m"), ("multi", "g"),
                   ("iv", "g"), ("iv", "m"), ("iv", "r")]
CLASSIFIER_ROLES = REGRESSOR_ROLES + [("multi", "m")]
BAD_VECTORS = ["scalar", "short", "long", "row", "matrix", "tensor",
               "complex", "zero_imaginary", "object_complex"]
BAD_PROBABILITIES = ["scalar", "short", "long", "row", "tensor",
                     "extra_column", "complex", "zero_imaginary", "object_complex"]


@pytest.mark.parametrize("kind,role", REGRESSOR_ROLES)
@pytest.mark.parametrize("mode", BAD_VECTORS)
@pytest.mark.parametrize("n_jobs", [1, 2])
def test_public_fit_rejects_malformed_regressor_outputs(kind, role, mode, n_jobs):
    model = estimator(kind, dataset(kind), n_jobs=n_jobs, **{role: ShapedRegressor(mode)})
    with pytest.raises(ValueError, match="shape|real"):
        model.fit()
    assert not hasattr(model, "m_hat_")


@pytest.mark.parametrize("kind", ["binary", "multi"])
@pytest.mark.parametrize("labels", [[0], [1], [0, 1], [1, 0]])
@pytest.mark.parametrize("n", [0, 1, 4])
def test_binary_probability_mapping_preserves_single_class_and_column_order(kind, labels, n):
    classifier = ShapedClassifier().fit(np.ones((2, 1)), labels)
    classifier.labels_ = classifier.classes_ = np.asarray(labels)
    X = np.ones((n, 1))
    actual = (_predict_prob_or_value(classifier, X) if kind == "binary" else
              MultiTreatmentIRM()._predict_binary_outcome_probability(classifier, X))
    np.testing.assert_array_equal(actual, np.full(n, 0 if labels == [0] else 1 / len(labels)))
    assert actual.shape == (n,)


@pytest.mark.parametrize("kind", ["binary", "multi"])
@pytest.mark.parametrize("n", [0, 1, 4])
def test_direct_positive_class_probability_vector_is_supported(kind, n):
    classifier = ShapedClassifier().fit(np.ones((2, 1)), [0, 1])
    classifier.predict_proba = lambda X: np.full(len(X), .3)
    X = np.ones((n, 1))
    actual = (_predict_prob_or_value(classifier, X) if kind == "binary" else
              MultiTreatmentIRM()._predict_binary_outcome_probability(classifier, X))
    np.testing.assert_array_equal(actual, np.full(n, .3))


@pytest.mark.parametrize("kind", ["binary", "multi"])
@pytest.mark.parametrize("metadata", [None, [], [[0, 1]], [0], [0, 1, 2]])
def test_binary_probability_column_metadata_is_checked(kind, metadata):
    classifier = ShapedClassifier().fit(np.ones((2, 1)), [0, 1])
    classifier.classes_ = metadata
    X = np.ones((4, 1))
    call = (lambda: _predict_prob_or_value(classifier, X)) if kind == "binary" else (
        lambda: MultiTreatmentIRM()._predict_binary_outcome_probability(classifier, X))
    if metadata is None or metadata == []:
        np.testing.assert_array_equal(call(), np.full(4, .5))
    else:
        with pytest.raises(ValueError, match="column"):
            call()


@pytest.mark.parametrize("metadata", [[[0, 1, 2]], [0, 1], [0, 0, 2]])
def test_multi_probability_columns_require_matching_distinct_class_metadata(metadata):
    classifier = ShapedClassifier().fit(np.ones((3, 1)), [0, 1, 2])
    classifier.classes_ = metadata
    with pytest.raises(ValueError, match="column|duplicate"):
        _predict_propensity_matrix(classifier, np.ones((4, 1)), 3)


@pytest.mark.parametrize("kind,role", CLASSIFIER_ROLES)
@pytest.mark.parametrize("mode", BAD_PROBABILITIES)
@pytest.mark.parametrize("n_jobs", [1, 2])
def test_public_fit_rejects_malformed_probability_outputs(kind, role, mode, n_jobs):
    model = estimator(kind, dataset(kind, binary_outcome=role == "g"), n_jobs=n_jobs,
                      **{role: ShapedClassifier(mode)})
    with pytest.raises(ValueError, match="shape|real|column"):
        model.fit()
    assert not hasattr(model, "m_hat_")


@pytest.mark.parametrize("kind", ["binary", "iv"])
@pytest.mark.parametrize("mode", ["scalar", "row", "short", "complex", "object_complex"])
def test_public_fit_validates_hard_label_fallback(kind, mode):
    model = estimator(kind, dataset(kind), m=ShapedClassifier(labelled=False, hard_mode=mode))
    with pytest.raises(ValueError, match="shape|real"):
        model.fit()


@pytest.mark.parametrize("kind,role", REGRESSOR_ROLES)
@pytest.mark.parametrize("n_jobs", [1, 2])
def test_column_predictions_preserve_vector_fit_and_inference(kind, role, n_jobs):
    data = dataset(kind)
    actual = estimator(kind, data, n_jobs=n_jobs, **{role: ShapedRegressor("column")}).fit()
    expected = estimator(kind, data, n_jobs=n_jobs, **{role: ShapedRegressor()}).fit()
    actual_result, expected_result = actual.estimate(), expected.estimate()
    for attribute in ["coef_", "se_", "pval_", "confint_", "psi_", "psi_a_", "psi_b_"]:
        np.testing.assert_array_equal(getattr(actual, attribute), getattr(expected, attribute))
    np.testing.assert_array_equal(actual_result.value, expected_result.value)


IV_FIELDS = ["g_hat0", "g_hat1", "r_hat0", "r_hat1", "m_hat_raw", "m_hat"]


@pytest.mark.parametrize("field", IV_FIELDS)
@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf, "complex", "row", "column", "short"])
def test_iv_validates_assembled_predictions_before_storing_failed_refit(monkeypatch, field, bad):
    model = estimator("iv", dataset("iv")).fit()
    old_estimate = model.estimate()
    predictions = {key: values.copy() for key, values in model.predictions_.items()}
    folds = model.folds_.copy()
    if isinstance(bad, str):
        predictions[field] = output(predictions[field], bad)
    else:
        predictions[field][0] = bad
    monkeypatch.setattr(model, "_cross_fit_nuisances", lambda **kw: (predictions, {}, folds))
    error = ValueError if isinstance(bad, str) else RuntimeError
    with pytest.raises(error, match="shape|real|non-finite"):
        model.fit()
    assert not hasattr(model, "predictions_")
    assert not hasattr(model, "m_hat_")
    assert not hasattr(model, "result_")
    assert np.isfinite(old_estimate.value)


@pytest.mark.parametrize("index", [2, 3, 4, 5, 6])
@pytest.mark.parametrize("bad", ["scalar", "complex", "infinity"])
def test_iv_validates_fold_outputs_before_assignment_or_clipping(monkeypatch, index, bad):
    model = estimator("iv", dataset("iv"))
    original = model._fit_nuisances_for_fold

    def malformed(**kwargs):
        result = list(original(**kwargs))
        result[index] = (np.full_like(result[index], np.inf) if bad == "infinity"
                         else output(result[index], bad))
        return tuple(result)

    monkeypatch.setattr(model, "_fit_nuisances_for_fold", malformed)
    with pytest.raises(RuntimeError if bad == "infinity" else ValueError,
                       match="shape|real|non-finite"):
        model.fit()
    assert not hasattr(model, "m_hat_")
