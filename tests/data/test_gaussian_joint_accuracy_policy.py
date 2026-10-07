"""Failure, storage and shared-latent symmetry contracts."""

from types import SimpleNamespace

import numpy as np
import pytest

from causalis.dgp import _gaussian_joint as joint
from causalis.dgp.causaldata.base import CausalDatasetGenerator


@pytest.mark.parametrize("family", ["binary", "gamma"])
@pytest.mark.parametrize("shape", [(), (0,), (2, 0), (3, 1)])
def test_shapes_and_simultaneous_sign_reflection(family, shape):
    a, b = np.full(shape, -0.7), np.full(shape, 0.3)
    value = joint._gaussian_product_mean(a, 5, b, -10, family)
    other = joint._gaussian_product_mean(a, -5, b, 10, family)
    assert value.shape == shape
    np.testing.assert_allclose(value, other, rtol=3e-13, atol=1e-14)


@pytest.mark.parametrize("family", ["binary", "gamma"])
def test_single_slope_reflection_changes_joint_target(family):
    left = joint._gaussian_product_mean(0, 5, 0, 5, family)
    right = joint._gaussian_product_mean(0, -5, 0, 5, family)
    assert left > right * 2


@pytest.mark.parametrize("args", [(np.nan, 1, 0, 1), (0, np.inf, 0, 1),
    (0, 1, np.inf, 1), (0, 1, 0, np.nan), (1j, 1, 0, 1), (0, 1j, 0, 1)])
def test_nonfinite_or_complex_inputs_fail(args):
    with pytest.raises(ValueError, match="requires (real|finite)"):
        joint._gaussian_product_mean(*args, "binary")


@pytest.mark.parametrize("family", ["binary", "gamma"])
@pytest.mark.parametrize("strengths", [(1e308, 1), (1, 1e308)])
def test_unresolvable_transitions_fail_explicitly(family, strengths):
    with pytest.raises(ValueError, match="floating-point geometry"):
        joint._gaussian_product_mean(0, strengths[0], 0, strengths[1], family)


@pytest.mark.parametrize("value,error,success", [(0.5, 0, False), (np.nan, 0, True),
    (0.5, np.nan, True), (0.5, 1e-8, True), (-1, 0, True), (100, 0, True)])
def test_backend_failures_are_not_silently_returned(monkeypatch, value, error, success):
    monkeypatch.setattr(joint, "quad_vec", lambda *a, **kw:
        (np.array([value]), error, SimpleNamespace(success=success)))
    with pytest.raises(ValueError, match="(did not converge|outside)"):
        joint._gaussian_product_mean(0, 2, 0, 3, "binary")


def test_bounded_batches_preserve_order_and_duplicates(monkeypatch):
    real_backend, sizes = joint.quad_vec, []
    def backend(function, low, high, **kwargs):
        sizes.append(len(function(0)))
        assert kwargs["norm"] == "max"
        assert kwargs["limit"] == 4096
        assert kwargs["cache_size"] == 2**20
        assert len(kwargs["points"]) < 32*22
        return real_backend(function, low, high, **kwargs)
    monkeypatch.setattr(joint, "quad_vec", backend)
    a = np.linspace(-5, 5, 70)[::-1]
    b = np.linspace(3, -3, 70)
    a, b = np.r_[a, a[:4]], np.r_[b, b[:4]]
    value = joint._gaussian_product_mean(a, 50, b, -10, "gamma")
    assert sizes == [32, 32, 6]
    np.testing.assert_array_equal(value[:4], value[-4:])
    for index in (0, 31, 32, 69):
        scalar = joint._gaussian_product_mean(a[index], 50, b[index], -10, "gamma")
        np.testing.assert_allclose(value[index], scalar, rtol=1e-12)


@pytest.mark.parametrize("order", [0, -1])
def test_num_quad_positive_validation_preserved(order):
    with pytest.raises(ValueError):
        CausalDatasetGenerator(k=0).oracle_nuisance(order)


@pytest.mark.parametrize("strength", [0, 0.5, 50])
def test_legacy_num_quad_no_longer_changes_propensity(strength):
    gen = CausalDatasetGenerator(k=0, alpha_d=-5, u_strength_d=strength)
    values = [gen.oracle_nuisance(order)[0](np.empty(0)) for order in (1, 5, 21, 61)]
    assert len(set(values)) == 1


def test_zero_strength_tweedie_is_exact_natural_arithmetic():
    gen = CausalDatasetGenerator(k=0, outcome_type="tweedie", alpha_zi=-0.3,
                                alpha_y=0.2, theta=0.7, seed=4)
    frame = gen.generate(4)
    from causalis.dgp.base import _sigmoid
    for d in (0, 1):
        expected = _sigmoid(-0.3)*np.exp(0.2 + 0.7*d)
        np.testing.assert_array_equal(frame[f"g{d}"], np.full(4, expected))
