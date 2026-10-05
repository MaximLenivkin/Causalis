"""HC covariance must preserve within-group noise under a large signal shift."""

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm
from sklearn.base import BaseEstimator

from causalis.data_contracts.causaldata import CausalData
from causalis.scenarios.gate.model import (
    _GatePartition,
    _estimate_gate_groupwise_summary_from_partition,
    _estimate_gatet_groupwise_summary_from_partition,
    estimate_gate_from_irm,
)


def _reference_variances(phi, codes, cov_type):
    """Independent saturated-regression HC sandwich, with centered residuals."""
    counts = np.bincount(codes)
    variances = []
    for group, count in enumerate(counts):
        sample = phi[codes == group]
        residuals = sample - sample.mean()
        meat = np.dot(residuals, residuals)
        if cov_type == "HC1":
            meat *= len(phi) / (len(phi) - len(counts))
        elif cov_type == "HC2":
            meat /= 1 - 1 / count
        elif cov_type == "HC3":
            meat /= (1 - 1 / count) ** 2
        variances.append(meat / count**2)
    return np.array(variances)


@pytest.mark.parametrize("cov_type", ["HC0", "HC1", "HC2", "HC3"])
@pytest.mark.parametrize("shift", [1e8, -1e8, 1e12])
def test_gate_variance_translation_invariance(cov_type, shift):
    # Unequal, interleaved groups and exactly representable within-group noise.
    codes = np.tile([0, 1, 0, 2, 1, 0, 2, 0], 20)
    d = np.arange(len(codes)) % 2
    # Ensure both treatment values appear inside every group.
    d[codes == 0] = np.arange(np.sum(codes == 0)) % 2
    d[codes == 1] = np.arange(np.sum(codes == 1)) % 2
    d[codes == 2] = np.arange(np.sum(codes == 2)) % 2
    phi = np.zeros(len(codes))
    for group in range(3):
        phi[codes == group] = group * 4 + np.tile([-1.0, 1.0], np.sum(codes == group) // 2)
    partition = _GatePartition(group_names=["a", "b", "c"], codes=codes)
    kwargs = dict(d=d, m_hat=np.full(len(d), 0.5), partition=partition,
                  cov_type=cov_type, alpha=0.05)
    original = _estimate_gate_groupwise_summary_from_partition(phi=phi, **kwargs)
    shifted = _estimate_gate_groupwise_summary_from_partition(phi=phi + shift, **kwargs)
    expected = _reference_variances(phi, codes, cov_type)
    np.testing.assert_allclose(np.diag(shifted["covariance"]), expected, rtol=1e-13)
    np.testing.assert_allclose(shifted["std_errors"], original["std_errors"], rtol=1e-13)
    np.testing.assert_allclose(shifted["std_phi"], original["std_phi"], rtol=1e-13)
    np.testing.assert_array_equal(shifted["values"] - shift, original["values"])


class _SignalIRM(BaseEstimator):
    """Fitted IRM interface with known canonical DR signals, independent of learners."""

    def __init__(self, phi, codes):
        n = len(phi)
        d = np.tile([0, 1], n // 2)
        # g0=g1=0, m=1/2 gives phi=2*(2*d-1)*y.
        y = (2 * d - 1) * phi / 2
        frame = pd.DataFrame({"id": np.arange(n), "y": y, "d": d, "x": codes})
        self.data = CausalData(df=frame, outcome="y", treatment="d", confounders=["x"], user_id="id")
        self._y, self._d = y, d
        self.g0_hat_ = self.g1_hat_ = np.zeros(n)
        self.m_hat_ = np.full(n, 0.5)
        self._fit_index_ = pd.Index(self.data.user_id, name="id")
        self._fit_row_index_ = self.data.df.index.copy()
        self.store_diagnostics = True
        self.overlap_threshold = 1e-3

    def fit(self):
        return self


@pytest.mark.parametrize("cov_type", ["HC0", "HC1", "HC2", "HC3"])
def test_public_gate_large_shift_preserves_covariance_and_contrast(cov_type):
    codes = np.repeat([0, 1], [100, 80])
    phi = 1e8 + codes * 4 + np.tile([-1.0, 1.0], len(codes) // 2)
    model = _SignalIRM(phi, codes)
    groups = pd.Series(codes, index=model._fit_index_, name="group")
    result = estimate_gate_from_irm(model, groups, cov_type=cov_type)
    expected_var = _reference_variances(phi, codes, cov_type)
    np.testing.assert_allclose(np.diag(result.covariance), expected_var, rtol=1e-13)
    np.testing.assert_allclose(result.std_errors, np.sqrt(expected_var), rtol=1e-13)
    contrast = result.contrast(result.group_names[1], result.group_names[0])
    assert contrast.value == pytest.approx(4.0)
    assert contrast.std_error == pytest.approx(np.sqrt(expected_var.sum()))
    assert contrast.p_value == pytest.approx(2 * norm.sf(4 / np.sqrt(expected_var.sum())))


@pytest.mark.parametrize("cov_type", ["HC0", "HC1", "HC2", "HC3"])
def test_gatet_descriptive_std_does_not_abort_valid_large_shift_inference(cov_type):
    # Treated-only groups are supported by GATET, with an overlap warning.
    z = 1e8 + np.tile([-1.0, 1.0], 50)
    codes = np.zeros(100, dtype=int)
    with pytest.warns(RuntimeWarning, match="no control observations"):
        result = _estimate_gatet_groupwise_summary_from_partition(
            z=z, d=np.ones(100), m_hat=np.full(100, 0.5),
            partition=_GatePartition(group_names=["treated"], codes=codes),
            cov_type=cov_type, alpha=0.05,
        )
    np.testing.assert_allclose(result["std_phi"], [np.std(z, ddof=1)], rtol=1e-13)
    np.testing.assert_allclose(result["std_errors"] ** 2, _reference_variances(z, codes, cov_type), rtol=1e-13)
