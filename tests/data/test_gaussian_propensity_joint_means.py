"""Independent scalar Gaussian references for propensity and shared-U targets."""

import math

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.special import expit

from causalis.dgp.causaldata.base import CausalDatasetGenerator
from causalis.dgp.causaldata_instrumental.base import InstrumentalGenerator


def joint_reference(a, s, b, t, family):
    points = {0.0}
    for base, slope, kind in ((a, s, "binary"), (b, t, family)):
        if slope:
            offsets = (-64, -16, -4, -1, 0, 1, 4, 16, 64) if kind == "binary" else (-20, 20)
            points.update((offset - base) / slope for offset in offsets)
    if t and family != "binary":
        points.add(t)
    knots = [-12.0, *sorted(p for p in points if -12 < p < 12), 12.0]
    scale = 1.0
    def function(u):
        y = expit(b + t*u) if family == "binary" else math.exp(np.clip(b + t*u, -20, 20))
        return expit(a + s*u) * y / scale * math.exp(-u*u/2) / math.sqrt(2*math.pi)
    values = [quad(function, lo, hi, epsabs=2e-14, epsrel=2e-13, limit=400,
                   full_output=True) for lo, hi in zip(knots[:-1], knots[1:])]
    assert all(len(v) == 3 for v in values), "Independent reference failed"
    return scale * sum(v[0] for v in values)


@pytest.mark.parametrize("strength", [0.0, 0.5, -3.0, 50.0, -100.0, 1e6])
@pytest.mark.parametrize("generator_cls", [CausalDatasetGenerator, InstrumentalGenerator])
def test_public_propensity_matches_gaussian_reference(generator_cls, strength):
    gen = generator_cls(k=0, alpha_d=-5, u_strength_d=strength, seed=42)
    frame = gen.generate(5, U=np.zeros(5))
    if generator_cls is InstrumentalGenerator:
        for z in (0, 1):
            expected = 2 * joint_reference(-5 + z*gen.first_stage, strength, 0, 0, "binary")
            np.testing.assert_allclose(frame[f"r_z{z}"], expected, atol=2e-11, rtol=0)
    else:
        expected = 2 * joint_reference(-5, strength, 0, 0, "binary")
        np.testing.assert_allclose(frame["m"], expected, atol=2e-11, rtol=0)
        for order in (5, 21, 61):
            m, _, _ = gen.oracle_nuisance(num_quad=order)
            assert m(np.empty(0)) == frame["m"].iloc[0]


@pytest.mark.parametrize("family", ["continuous", "binary", "poisson", "gamma"])
@pytest.mark.parametrize("sd,sy", [(0, 0), (0, 50), (50, 0), (2, 50), (-20, 10),
                                  (50, -10), (1e6, -1e6)])
def test_iv_joint_mean_matches_shared_gaussian_reference(family, sd, sy):
    x = np.array([[-0.3], [0.4]])
    tau = 0.7 + 0.2*x[:, 0]
    gen = InstrumentalGenerator(k=1, alpha_d=-5, beta_d=np.array([0.3]),
        score_bounding=1.2, propensity_sharpness=1.7, alpha_y=-5,
        beta_y=np.array([0.2]), g_y=lambda v: 0.1*v[:, 0]**2,
        u_strength_d=sd, u_strength_y=sy, outcome_type=family, seed=8)
    for z in (0, 1):
        actual = gen._g_by_z(x, z, tau)
        for row in range(2):
            a = -5 + 1.2*np.tanh(1.7*0.3*x[row, 0]/1.2) + z*gen.first_stage
            b = -5 + 0.2*x[row, 0] + 0.1*x[row, 0]**2
            if family == "continuous":
                expected = b + tau[row]*2*joint_reference(a, sd, 0, 0, "binary")
            else:
                expected = (joint_reference(-a, -sd, b, sy, family)
                            + joint_reference(a, sd, b + tau[row], sy, family))
            np.testing.assert_allclose(actual[row], expected, atol=3e-11,
                                       rtol=3e-10 if family in {"poisson", "gamma"} else 0)


@pytest.mark.parametrize("sz,sy", [(0, 0), (50, 0), (0, 10), (2, 10),
                                  (-50, 10), (50, -10), (1e6, -1e6)])
@pytest.mark.parametrize("positive_family", ["gamma", "lognormal"])
def test_tweedie_joint_mean_matches_shared_gaussian_reference(sz, sy, positive_family):
    x = np.array([[-0.3], [0.4]])
    gen = CausalDatasetGenerator(k=1, x_sampler=lambda n, k, seed: x.copy(),
        outcome_type="tweedie", pos_dist=positive_family, alpha_zi=-5,
        beta_zi=np.array([0.2]), g_zi=lambda v: 0.1*v[:, 0]**2,
        tau_zi=lambda v: 0.6 + 0.2*v[:, 0], alpha_y=-1,
        beta_y=np.array([0.3]), tau=lambda v: 0.8 + 0.1*v[:, 0],
        u_strength_zi=sz, u_strength_y=sy, seed=7)
    frame = gen.generate(2, U=np.zeros(2))
    for row in range(2):
        for d in (0, 1):
            a = -5 + 0.2*x[row, 0] + 0.1*x[row, 0]**2 + d*(0.6+0.2*x[row, 0])
            b = -1 + 0.3*x[row, 0] + d*(0.8+0.1*x[row, 0])
            expected = joint_reference(a, sz, b, sy, "gamma")
            np.testing.assert_allclose(frame.loc[row, f"g{d}"], expected, atol=1e-12, rtol=3e-10)


def test_joint_dependence_cannot_be_replaced_by_product_of_marginals():
    gen = CausalDatasetGenerator(k=0, outcome_type="tweedie", alpha_zi=0,
        alpha_y=0, theta=0, u_strength_zi=-5, u_strength_y=5, seed=18)
    actual = gen.generate(3, U=np.zeros(3))["g0"].iloc[0]
    joint = joint_reference(0, -5, 0, 5, "gamma")
    independent = joint_reference(0, -5, 0, 0, "binary")*4*joint_reference(0, 0, 0, 5, "gamma")
    assert abs(joint - independent) > 100
    np.testing.assert_allclose(actual, joint, rtol=3e-10)


@pytest.mark.parametrize("generator_cls", [CausalDatasetGenerator, InstrumentalGenerator])
def test_supplied_u_preserves_gaussian_propensity_reference(generator_cls):
    kwargs = dict(k=0, alpha_d=-5, u_strength_d=50, seed=31)
    left = generator_cls(**kwargs).generate(8, U=np.zeros(8))
    right = generator_cls(**kwargs).generate(8, U=np.ones(8)*2)
    names = ["r_z0", "r_z1", "g_z0", "g_z1"] if generator_cls is InstrumentalGenerator else ["m"]
    np.testing.assert_array_equal(left[names], right[names])
