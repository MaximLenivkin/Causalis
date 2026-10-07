"""Gaussian potential-outcome references independent of generator quadrature."""

import math

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.special import expit, ndtr

from causalis.dgp.causaldata.base import CausalDatasetGenerator
from causalis.dgp.causaldata_instrumental.base import InstrumentalGenerator


def reference(location, strength, family):
    """Scalar Gaussian integral with explicit transition/clipping neighborhoods."""
    strength = abs(strength)
    if strength == 0.0:
        return float(expit(location) if family == "binary" else np.exp(np.clip(location, -20, 20)))
    points = {0.0}
    if family == "binary":
        center = -location / strength
        for offset in (0.0, 0.5, 2.0, 8.0, 32.0, 64.0):
            points.update((center - offset / strength, center + offset / strength))
        scale = 1.0
    else:
        points.update(((-20.0 - location) / strength, (20.0 - location) / strength))
        # Scale near the tilted Gaussian mode; floor keeps the clipped lower tail.
        mode = min(12.0, max(-12.0, strength))
        scale = max(math.exp(-20.0), math.exp(
            min(20.0, max(-20.0, location + strength * mode)) - mode * mode / 2))
    knots = [-12.0, *sorted(p for p in points if -12.0 < p < 12.0), 12.0]
    def integrand(u):
        link = location + strength * u
        mean = float(expit(link)) if family == "binary" else math.exp(min(20.0, max(-20.0, link)))
        return (mean / scale) * math.exp(-u * u / 2) / math.sqrt(2 * math.pi)
    values = [quad(integrand, low, high, epsabs=2e-12, epsrel=2e-12,
                   limit=300, full_output=True) for low, high in zip(knots[:-1], knots[1:])]
    assert all(len(value) == 3 for value in values), "Reference did not converge"
    return scale * sum(value[0] for value in values)


@pytest.mark.parametrize("generator_cls", [CausalDatasetGenerator, InstrumentalGenerator])
@pytest.mark.parametrize("family,location,strength", [
    ("binary", -5.0, 50.0), ("binary", 5.0, -50.0),
    ("binary", -0.9, 3.0), ("binary", 0.7, -10.0),
    ("binary", -50.0, 100.0), ("binary", -2e5, 1e6),
    ("binary", 0.2, 0.999), ("binary", -0.2, 1.001),
    ("poisson", -25.0, 10.0), ("gamma", 0.0, 10.0),
    ("poisson", -19.0, 1.7), ("gamma", 19.0, -1.7),
    ("poisson", -21.0, 3.0), ("gamma", 21.0, 3.0),
    ("poisson", 0.0, 8.001), ("gamma", -30.0, 100.0),
    ("poisson", -100.0, 10.0), ("gamma", -200.0, 20.0),
])
def test_public_marginal_outcomes_match_adaptive_reference(generator_cls, family, location, strength):
    gen = generator_cls(k=0, alpha_y=location, theta=0.8, outcome_type=family,
                        u_strength_y=strength, seed=71)
    frame = gen.generate(9, U=np.zeros(9))
    names = ("g_d0", "g_d1") if generator_cls is InstrumentalGenerator else ("g0", "g1")
    expected = [reference(location + effect, strength, family) for effect in (0.0, 0.8)]
    np.testing.assert_allclose(frame[list(names)], np.tile(expected, (9, 1)),
                               rtol=3e-10, atol=2e-11 if family == "binary" else 0.0)
    np.testing.assert_allclose(frame["cate"], expected[1] - expected[0],
                               rtol=2e-8, atol=4e-11 if family == "binary" else 1e-16)


@pytest.mark.parametrize("family", ["binary", "poisson", "gamma"])
@pytest.mark.parametrize("strength", [0.5, -3.0, 50.0])
def test_outcome_callables_agree_with_generated_oracles(family, strength):
    x = np.linspace(-0.7, 0.7, 7).reshape(-1, 1)
    gen = CausalDatasetGenerator(k=1, x_sampler=lambda n, k, seed: x.copy(),
        beta_y=np.array([0.3]), alpha_y=0.1, tau=lambda values: 0.5 + values[:, 0] * 0.2,
        outcome_type=family, u_strength_y=strength, seed=31)
    frame = gen.generate(len(x))
    for order in (5, 21, 61):
        _, g0, g1 = gen.oracle_nuisance(num_quad=order)
        for index, row in enumerate(x):
            actual = np.array([g0(row), g1(row)])
            np.testing.assert_array_equal(actual, frame.loc[index, ["g0", "g1"]].to_numpy(dtype=float))
            expected = [reference(0.1 + 0.3 * row[0] + d * (0.5 + 0.2 * row[0]), strength, family)
                        for d in (0, 1)]
            np.testing.assert_allclose(actual, expected, rtol=3e-10,
                                      atol=2e-11 if family == "binary" else 0.0)


@pytest.mark.parametrize("generator_cls", [CausalDatasetGenerator, InstrumentalGenerator])
@pytest.mark.parametrize("family", ["continuous", "binary", "poisson", "gamma"])
def test_supplied_latent_values_do_not_change_gaussian_reference(generator_cls, family):
    kwargs = dict(k=0, alpha_y=0.2, theta=0.8, outcome_type=family,
                  u_strength_y=10.0, seed=24)
    left = generator_cls(**kwargs).generate(12, U=np.zeros(12))
    right = generator_cls(**kwargs).generate(12, U=np.full(12, 2.0))
    names = ["g_d0", "g_d1", "cate"] if generator_cls is InstrumentalGenerator else ["g0", "g1", "cate"]
    np.testing.assert_array_equal(left[names], right[names])


@pytest.mark.parametrize("generator_cls", [CausalDatasetGenerator, InstrumentalGenerator])
@pytest.mark.parametrize("family", ["continuous", "binary", "poisson", "gamma"])
def test_zero_strength_preserves_natural_mean(generator_cls, family):
    gen = generator_cls(k=0, alpha_y=0.3, theta=-0.4, outcome_type=family, seed=55)
    frame = gen.generate(8)
    names = ["g_d0", "g_d1"] if generator_cls is InstrumentalGenerator else ["g0", "g1"]
    expected = np.array([0.3, 0.3 - 0.4])
    if family == "binary":
        # Preserve the generator's existing sigmoid arithmetic.
        from causalis.dgp.base import _sigmoid
        expected = _sigmoid(expected)
    elif family != "continuous":
        expected = np.exp(expected)
    np.testing.assert_array_equal(frame[names], np.tile(expected, (8, 1)))


def test_oracle_identification_guard_remains():
    gen = CausalDatasetGenerator(u_strength_y=50.0, u_strength_d=0.2)
    with pytest.raises(ValueError, match="identification fails"):
        gen.oracle_nuisance()
