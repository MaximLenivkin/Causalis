"""Boundary, convergence and batch contracts of the Gaussian mean helper."""

from types import SimpleNamespace

import numpy as np
import pytest
from scipy.special import expit, ndtr

from causalis.dgp import _gaussian_outcome as gaussian


@pytest.mark.parametrize("strength", [1e-300, 0.3, 0.999999, 1.0, 1.000001, 8.0, 8.000001, 100.0, 1e6, 1e154, 1e308])
@pytest.mark.parametrize("family", ["binary", "poisson", "gamma"])
def test_finite_extremes_ranges_and_sign_invariance(strength, family):
    link = np.array([[-1e308, -25, -20, -5, 0, 20, 25, 1e308]])
    positive = gaussian._gaussian_outcome_mean(link, strength, family)
    negative = gaussian._gaussian_outcome_mean(link, -strength, family)
    assert positive.shape == link.shape
    assert np.all(np.isfinite(positive))
    np.testing.assert_array_equal(positive, negative)
    assert np.all(np.diff(positive) >= -1e-15)
    if family == "binary":
        assert np.all((positive >= 0) & (positive <= 1))
        np.testing.assert_allclose(positive[0, 4], 0.5, atol=1e-14, rtol=0)
        reflected = gaussian._gaussian_outcome_mean(-link, strength, family)
        np.testing.assert_allclose(positive + reflected, 1.0, atol=2e-14, rtol=0)
    else:
        assert np.all((positive >= np.exp(-20)) & (positive <= np.exp(20)))


@pytest.mark.parametrize("family", ["binary", "gamma"])
@pytest.mark.parametrize("shape", [(), (0,), (2, 0), (3, 1)])
def test_scalar_empty_and_shaped_inputs(family, shape):
    values = np.full(shape, 0.2)
    actual = gaussian._gaussian_outcome_mean(values, 10.0, family)
    assert actual.shape == shape
    assert np.all(np.isfinite(actual))


@pytest.mark.parametrize("link,strength", [(np.nan, 1), (np.inf, 1), (0, np.inf), (0, np.nan), (1j, 1), (0, 1j)])
def test_invalid_input_is_rejected(link, strength):
    with pytest.raises(ValueError, match="requires (finite|real)"):
        gaussian._gaussian_outcome_mean(link, strength, "binary")


@pytest.mark.parametrize("value,error,success", [(0.5, 0.0, False), (np.nan, 0, True),
    (0.5, np.nan, True), (0.5, 1e-8, True), (-0.1, 0, True), (1.1, 0, True)])
def test_backend_failure_is_never_silently_returned(monkeypatch, value, error, success):
    monkeypatch.setattr(gaussian, "quad_vec", lambda *args, **kwargs:
                        (np.array([value]), error, SimpleNamespace(success=success)))
    with pytest.raises(ValueError, match="(did not converge|outside)"):
        gaussian._gaussian_outcome_mean([0.2], 2.0, "binary")


def test_batches_bound_backend_vectors_and_preserve_row_order(monkeypatch):
    real_backend = gaussian.quad_vec
    sizes = []
    def backend(function, low, high, **kwargs):
        sizes.append(len(function(0)))
        assert kwargs["norm"] == "max"
        assert kwargs["limit"] == 256
        assert kwargs["cache_size"] == 2**20
        return real_backend(function, low, high, **kwargs)
    monkeypatch.setattr(gaussian, "quad_vec", backend)
    values = np.linspace(-5, 5, 2100)[::-1]
    expected = gaussian._gaussian_outcome_mean(values, 100.0, "binary")
    assert sizes == [1024, 1024, 52]
    scalar = np.array([gaussian._gaussian_outcome_mean(value, 100.0, "binary")
                       for value in values[[0, 1023, 1024, -1]]])
    np.testing.assert_allclose(expected[[0, 1023, 1024, -1]], scalar, atol=2e-14, rtol=0)


@pytest.mark.parametrize("strength", [0.1, 0.5, 1, 2, 5])
def test_clipped_exponential_reduces_to_unclipped_mgf_when_tails_negligible(strength):
    # At strength 5 the actual clipping is material; compute the analytic
    # truncated moment independently with the elementary CDF formula.
    link = np.array([-0.2, 0.0, 0.2])
    z_low, z_high = (-20 - link) / strength, (20 - link) / strength
    expected = (np.exp(-20) * ndtr(z_low) + np.exp(20) * ndtr(-z_high)
                + np.exp(link + strength**2 / 2) * (ndtr(z_high - strength) - ndtr(z_low - strength)))
    actual = gaussian._gaussian_outcome_mean(link, strength, "gamma")
    np.testing.assert_allclose(actual, expected, atol=0, rtol=2e-13)
