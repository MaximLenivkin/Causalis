"""Independent references for Gaussian-marginal multi-treatment outcomes."""

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.special import expit
from scipy.stats import norm

from causalis.dgp.multicausaldata import MultiCausalDatasetGenerator


def _clipped_exp_normal_reference(location, strength):
    """Adaptive integration, split at clipping knots and scaled for accuracy."""
    scale = np.exp(np.clip(location, -20.0, 20.0))
    sigma = abs(strength)
    knots = [(-20.0 - location) / sigma, (20.0 - location) / sigma]
    integrand = lambda z: (
        np.exp(np.clip(location + sigma * z, -20.0, 20.0))
        / scale
        * norm.pdf(z)
    )
    boundaries = [-np.inf, *knots, np.inf]
    return scale * sum(
        quad(integrand, low, high, epsabs=1e-12, epsrel=1e-12)[0]
        for low, high in zip(boundaries[:-1], boundaries[1:])
    )


@pytest.mark.parametrize("outcome_type", ["poisson", "gamma"])
@pytest.mark.parametrize("strength", [1.2, -1.2])
def test_log_link_oracles_integrate_gaussian_latent_with_heterogeneous_effects(
    outcome_type, strength
):
    x = np.linspace(-0.6, 0.6, 24).reshape(-1, 1)
    theta = [0.0, 0.7, -0.4]
    generator = MultiCausalDatasetGenerator(
        n_treatments=3,
        k=1,
        x_sampler=lambda n, k, seed: x.copy(),
        beta_y=np.array([0.3]),
        alpha_y=0.2,
        theta=theta,
        tau=[None, lambda values: 0.2 * values[:, 0], None],
        outcome_type=outcome_type,
        u_strength_y=strength,
        seed=123,
    )
    frame = generator.generate(len(x))
    locations = 0.2 + 0.3 * x + np.asarray(theta)
    locations[:, 1] += 0.2 * x[:, 0]
    # At these locations clipping tails are < 1e-40; use the analytic MGF.
    expected = np.exp(locations + strength**2 / 2.0)
    actual = frame[[f"g_d_{arm}" for arm in range(3)]].to_numpy()
    np.testing.assert_allclose(actual, expected, rtol=2e-13, atol=0.0)
    np.testing.assert_allclose(
        frame[["cate_d_1", "cate_d_2"]].to_numpy(),
        expected[:, 1:] - expected[:, [0]],
        rtol=2e-13,
        atol=0.0,
    )


@pytest.mark.parametrize("strength", [0.6, 1.5, -2.0, 2.00001, 3.0, 5.0, -10.0])
def test_binary_oracles_match_adaptive_gaussian_integration(strength):
    x = np.linspace(-1.0, 1.0, 15).reshape(-1, 1)
    generator = MultiCausalDatasetGenerator(
        k=1,
        x_sampler=lambda n, k, seed: x.copy(),
        alpha_y=0.3,
        beta_y=np.array([0.4]),
        theta=[0.0, 0.8, -0.5],
        outcome_type="binary",
        u_strength_y=strength,
        seed=71,
    )
    frame = generator.generate(len(x))
    locations = 0.3 + 0.4 * x + np.array([0.0, 0.8, -0.5])
    expected = np.array(
        [
            [
                quad(
                    lambda z: expit(location + strength * z) * norm.pdf(z),
                    -12.0,
                    12.0,
                    epsabs=1e-13,
                    epsrel=1e-13,
                )[0]
                for location in row
            ]
            for row in locations
        ]
    )
    actual = frame[[f"g_d_{arm}" for arm in range(3)]].to_numpy()
    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=2e-9)
    np.testing.assert_allclose(
        frame[["cate_d_1", "cate_d_2"]].to_numpy(),
        expected[:, 1:] - expected[:, [0]],
        rtol=0.0,
        atol=4e-9,
    )


@pytest.mark.parametrize("outcome_type", ["poisson", "gamma"])
@pytest.mark.parametrize("location", [-21.0, -19.0, 19.0, 21.0])
def test_log_link_marginal_oracles_respect_generation_clipping(outcome_type, location):
    strength = 1.7
    theta = np.array([0.0, 0.5, -0.6])
    generator = MultiCausalDatasetGenerator(
        k=0,
        alpha_y=location,
        theta=theta,
        outcome_type=outcome_type,
        u_strength_y=strength,
        seed=61,
    )
    frame = generator.generate(20)
    expected = np.array(
        [_clipped_exp_normal_reference(location + effect, strength) for effect in theta]
    )
    actual = frame[[f"g_d_{arm}" for arm in range(3)]].to_numpy()
    np.testing.assert_allclose(actual, np.tile(expected, (len(frame), 1)), rtol=2e-11)
    # Applying an unclipped lognormal correction after clipping is also wrong.
    assert not np.isclose(
        expected[0],
        np.exp(np.clip(location, -20.0, 20.0) + strength**2 / 2.0),
        rtol=1e-4,
        atol=0.0,
    )


@pytest.mark.parametrize("outcome_type", ["continuous", "binary", "poisson", "gamma"])
def test_zero_strength_preserves_natural_scale_oracles(outcome_type):
    generator = MultiCausalDatasetGenerator(
        k=0,
        alpha_y=0.3,
        theta=[0.0, 0.8, -0.5],
        outcome_type=outcome_type,
        u_strength_y=0.0,
        seed=24,
    )
    frame = generator.generate(20)
    locations = 0.3 + np.array([0.0, 0.8, -0.5])
    if outcome_type == "continuous":
        expected = locations
    elif outcome_type == "binary":
        expected = expit(locations)
    else:
        expected = np.exp(locations)
    np.testing.assert_allclose(
        frame[[f"g_d_{arm}" for arm in range(3)]].to_numpy(),
        np.tile(expected, (len(frame), 1)),
        rtol=1e-14,
    )


@pytest.mark.parametrize("outcome_type", ["continuous", "binary", "poisson", "gamma"])
def test_supplied_u_changes_draws_but_keeps_gaussian_reference_oracle(outcome_type):
    settings = dict(
        k=0,
        theta=0.0,
        alpha_y=0.3,
        sigma_y=0.0,
        outcome_type=outcome_type,
        u_strength_y=1.0,
        seed=55,
    )
    low = MultiCausalDatasetGenerator(**settings).generate(100, U=np.full(100, -3.0))
    high = MultiCausalDatasetGenerator(**settings).generate(100, U=np.full(100, 3.0))
    columns = [f"g_d_{arm}" for arm in range(3)] + ["cate_d_1", "cate_d_2"]
    np.testing.assert_array_equal(low[columns].to_numpy(), high[columns].to_numpy())
    assert high.y.mean() > low.y.mean()
    if outcome_type == "continuous":
        np.testing.assert_allclose(low.g_d_0, 0.3, atol=0.0)


def test_disabling_oracles_preserves_observed_draws_with_latent_noise():
    settings = dict(k=1, outcome_type="binary", u_strength_y=1.3, seed=51)
    without = MultiCausalDatasetGenerator(**settings, include_oracle=False).generate(50)
    with_oracles = MultiCausalDatasetGenerator(**settings, include_oracle=True).generate(50)
    np.testing.assert_array_equal(without.to_numpy(), with_oracles[without.columns].to_numpy())
