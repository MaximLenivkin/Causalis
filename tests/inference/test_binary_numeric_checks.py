"""Numeric fast-path equivalence, including the distinct multi-outcome policy."""
import numpy as np
import pandas as pd
import pytest
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


def legacy_binary(values):
    uniq = np.unique(values)
    return np.array_equal(np.sort(uniq), np.array([0, 1])) or np.array_equal(
        np.sort(uniq), np.array([0.0, 1.0]))


def legacy_multi(values):
    uniq = np.unique(values)
    return bool(uniq.size and np.all(np.isin(uniq, np.array([0, 1], dtype=float))))


ARRAYS = [
    np.array([]), np.array([0]), np.array([1]), np.array([0, 1]),
    np.array([-0.0, 1.0]), np.array([0, 1, 0, 1]),
    np.array([False, True]), np.array([True]),
    np.array([0, 1], dtype=np.int8), np.array([0, 1], dtype=np.uint64),
    np.array([0, 1, 2**63 + 1], dtype=np.uint64),
    np.array([0, 1, -1]), np.array([0, 1, 2]),
    np.array([0, 1, np.nan]), np.array([0, 1, np.inf]),
    np.array([0, 1, -np.inf]), np.array([np.nan]),
    np.array([0, np.nextafter(1.0, 2.0)]),
    np.array([0, np.nextafter(0.0, 1.0), 1.0]),
    np.array([0, 1], dtype=np.float32), np.array([0, 1], dtype=np.longdouble),
    np.array([0, 1], dtype=complex), np.array([0, 1, 1j]),
    np.array([[0, 1], [1, 0]]), np.array(1),
    np.arange(10)[::2], np.tile([0, 1, 0, 1], (10, 1)).T,
    np.array([0, 1], dtype=object), np.array([False, True], dtype=object),
    np.array(["0", "1"]), np.array([None, 0, 1], dtype=object),
    np.array(["a", "b"], dtype=object),
    np.array(["2025-01-01", "2025-01-02"], dtype="datetime64[D]"),
]


@pytest.mark.parametrize("values", ARRAYS)
@pytest.mark.parametrize("actual,reference", [
    (binary_utils._is_binary, legacy_binary), (multi_utils._is_binary, legacy_multi)])
def test_same_numeric_and_fallback_semantics(values, actual, reference):
    try:
        expected = reference(values)
    except (TypeError, ValueError) as exc:
        with pytest.raises(type(exc)):
            actual(values)
    else:
        assert bool(actual(values)) == bool(expected)


@pytest.mark.parametrize("check", [binary_utils._is_binary, multi_utils._is_binary])
def test_numeric_path_does_not_sort_and_preserves_readonly_input(monkeypatch, check):
    values = np.tile([0.0, 1.0], 1000)[::3]
    values.flags.writeable = False
    before = values.copy()
    def forbidden(*args, **kwargs):
        raise AssertionError("numeric binary detection must not call unique or sort")
    monkeypatch.setattr(np, "unique", forbidden)
    monkeypatch.setattr(np, "sort", forbidden)
    assert check(values)
    np.testing.assert_array_equal(values, before)
    assert not values.flags.writeable


@pytest.mark.parametrize("kind", ["binary", "multi", "iv"])
@pytest.mark.parametrize("binary_outcome", [False, True])
def test_same_folds_predictions_scores_and_inference(monkeypatch, kind, binary_outcome):
    rng = np.random.default_rng(7403)
    n = 360
    x = rng.normal(size=n)
    z = rng.binomial(1, 0.5, n)
    d = rng.binomial(1, 1 / (1 + np.exp(-(.5 * x + 1.3 * z))))
    labels = np.tile([0, 1, 2], n // 3)
    rng.shuffle(labels)
    continuous = 10 + .7 * x + 1.2 * d + rng.normal(size=n)
    binary = rng.binomial(1, 1 / (1 + np.exp(-(.5 * x + .7 * d))))
    y = binary if binary_outcome else continuous
    g = LogisticRegression(max_iter=500) if binary_outcome else LinearRegression()
    df = pd.DataFrame(dict(y=y, d=d, x=x, z=z), index=np.arange(n) // 2)
    options = dict(ml_g=g, ml_m=LogisticRegression(max_iter=500),
                   n_folds=3, random_state=56, n_jobs=1)
    if kind == "binary":
        data = CausalData.from_df(df, "d", "y", ["x"])
        factory = lambda: IRM(data=data, **options)
        module, legacy = binary_model, legacy_binary
        attrs = ["g0_hat_", "g1_hat_", "m_hat_", "psi_", "psi_a_", "psi_b_"]
    elif kind == "iv":
        data = IVCausalData.from_df(df, "d", "y", "z", ["x"])
        factory = lambda: IIVM(data=data, ml_r=LogisticRegression(max_iter=500), **options)
        module, legacy = iv_model, legacy_binary
        attrs = ["g_hat0_", "g_hat1_", "m_hat_", "r_hat0_", "r_hat1_",
                 "psi_", "psi_a_", "psi_b_", "phi_y_", "phi_d_"]
    else:
        for k in range(3):
            df[f"d{k}"] = (labels == k).astype(int)
        data = MultiCausalData(df=df, outcome="y", treatment_names=["d0", "d1", "d2"],
                               confounders=["x"], control_treatment="d0")
        factory = lambda: MultiTreatmentIRM(data=data, **options)
        module, legacy = multi_model, legacy_multi
        attrs = ["g_hat_", "m_hat_", "psi_", "psi_a_", "psi_b_"]
    before = data.get_df()
    optimized = factory().fit()
    optimized_result = optimized.estimate()
    with monkeypatch.context() as patch:
        patch.setattr(module, "_is_binary", legacy)
        reference = factory().fit()
        reference_result = reference.estimate()
    for attr in attrs:
        np.testing.assert_array_equal(getattr(optimized, attr), getattr(reference, attr))
    np.testing.assert_array_equal(optimized.folds_, reference.folds_)
    for attr in ["value", "p_value", "ci_lower_absolute", "ci_upper_absolute"]:
        np.testing.assert_array_equal(getattr(optimized_result, attr), getattr(reference_result, attr))
    pd.testing.assert_frame_equal(data.get_df(), before)
