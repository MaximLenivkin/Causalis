"""Independent public references for Gaussian-marginal treatment probabilities."""

import importlib
import math
from types import SimpleNamespace
import warnings

import numpy as np
import pandas as pd
import pytest
from scipy.integrate import IntegrationWarning, quad
from scipy.special import softmax

from causalis.dgp.multicausaldata import MultiCausalDatasetGenerator as Generator
from causalis.dgp.multicausaldata.functional import generate_multitreatment


X = np.array([[-1.25, 0.2], [-0.2, -0.7], [0.6, 0.4], [1.4, 1.1]])
PROBABILITY_ATOL = 2e-9


def _gaussian_reference(scores, slopes):
    """Scalar QUADPACK reference, split around affine score intersections.

    Each softmax integrand lies in [0,1]; the omitted N(0,1) tails beyond
    +/-12 have mass below 4e-33. This reference does not use DGP helpers,
    vector quadrature or a fixed Gaussian-node approximation.
    """
    scores = np.asarray(scores, dtype=float)
    slopes = np.asarray(slopes, dtype=float)
    result = np.empty_like(scores)
    normalizer = math.sqrt(2.0 * math.pi)
    for row_idx, row in enumerate(scores):
        points = []
        for first in range(len(slopes)):
            for second in range(first):
                difference = slopes[first] - slopes[second]
                if difference == 0.0:
                    continue
                crossing = (row[second] - row[first]) / difference
                # Resolve the narrow logistic transition on either side of a
                # score crossing, including slopes of magnitude 1000.
                for point in (crossing - 16.0 / abs(difference), crossing,
                              crossing + 16.0 / abs(difference)):
                    if -12.0 < point < 12.0:
                        points.append(float(point))
        distinct_points = []
        for point in sorted(set(points)):
            if distinct_points:
                previous = distinct_points[-1]
                resolution = np.spacing(max(1.0, abs(point), abs(previous)))
                if point - previous <= 32.0 * resolution:
                    # Algebraically identical crossings can differ by a few
                    # ULPs. Coalesce partition knots, preserving the full
                    # integration domain and the unmodified integrand.
                    continue
            distinct_points.append(point)
        points = distinct_points
        for arm in range(len(slopes)):
            with warnings.catch_warnings(record=True) as recorded:
                warnings.simplefilter("always", IntegrationWarning)
                value, error = quad(
                    lambda latent: float(softmax(row + slopes * latent)[arm])
                    * math.exp(-0.5 * latent * latent) / normalizer,
                    -12.0, 12.0, points=points, epsabs=2e-12,
                    epsrel=2e-12, limit=500,
                )
            assert not any(issubclass(item.category, IntegrationWarning) for item in recorded)
            assert error < 5e-11
            result[row_idx, arm] = value
    return result


def _columns(names):
    return [f"m_marginal_{name}" for name in names]


def _assert_probabilities(actual, expected):
    assert np.isfinite(actual).all()
    assert ((actual >= 0.0) & (actual <= 1.0)).all()
    np.testing.assert_allclose(actual.sum(axis=1), 1.0, rtol=0.0, atol=2e-12)
    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=PROBABILITY_ATOL)


def _varying_settings(arms, strength):
    intercepts = np.linspace(-0.8, 0.7, arms)
    coefficients = np.column_stack((np.linspace(-0.6, 0.9, arms),
                                    np.linspace(0.4, -0.3, arms)))
    slopes = np.linspace(-0.7, 1.3, arms) * strength
    sharpness = 1.4
    settings = dict(n_treatments=arms, k=2, x_sampler=lambda n, k, seed: X.copy(),
                    alpha_d=intercepts, beta_d=coefficients, u_strength_d=slopes,
                    propensity_sharpness=sharpness, theta=0.0, seed=731,
                    assignment_policy="iid", include_marginal_propensity=True)
    return settings, X @ coefficients.T * sharpness + intercepts, slopes


NUMERIC_CASES = [(3, strength) for strength in (0.0, 0.1, 1.0, 2.0, 5.0, 10.0, 50.0)]
NUMERIC_CASES += [(2, strength) for strength in (0.1, 2.0, 50.0)]
NUMERIC_CASES += [(5, strength) for strength in (1.0, 10.0, 50.0)]


@pytest.mark.parametrize("arms,strength", NUMERIC_CASES)
def test_gaussian_marginal_matches_independent_scalar_integration_with_varying_x(arms, strength):
    settings, scores, slopes = _varying_settings(arms, strength)
    generator = Generator(**settings)
    frame = generator.generate(len(X), U=np.zeros(len(X)))
    actual = frame[_columns(generator.d_names)].to_numpy()
    _assert_probabilities(actual, _gaussian_reference(scores, slopes))
    np.testing.assert_allclose(frame[[f"m_{name}" for name in generator.d_names]],
                               softmax(scores, axis=1), rtol=2e-14, atol=2e-15)


def test_asymmetric_very_steep_scores_resolve_separate_dominant_arm_transitions():
    settings, _, _ = _varying_settings(3, 1000.0)
    intercepts = np.array([-400.0, 300.0, -800.0])
    slopes = np.array([-1000.0, 0.0, 1000.0])
    settings.update(alpha_d=intercepts, u_strength_d=slopes)
    scores = X @ settings["beta_d"].T * settings["propensity_sharpness"] + intercepts
    frame = Generator(**settings).generate(len(X), U=0.0)
    actual = frame[_columns(["d_0", "d_1", "d_2"])].to_numpy()
    _assert_probabilities(actual, _gaussian_reference(scores, slopes))
    assert (actual > 0.05).all()
    assert np.max(np.abs(actual - frame[["m_d_0", "m_d_1", "m_d_2"]].to_numpy())) > 0.1


@pytest.mark.parametrize("strength", [-1000.0, -50.0, -0.1, 0.0, 0.1, 50.0, 1000.0])
def test_two_arm_zero_intercept_has_closed_form_half_by_gaussian_symmetry(strength):
    frame = Generator(n_treatments=2, k=0, alpha_d=[0.0, 0.0],
                      u_strength_d=[0.0, strength], assignment_policy="iid",
                      include_marginal_propensity=True, seed=731).generate(3, U=0.0)
    _assert_probabilities(frame[_columns(["d_0", "d_1"])].to_numpy(), np.full((3, 2), 0.5))


@pytest.mark.parametrize("common_slope", [-1000.0, 0.0, 1000.0])
def test_equal_latent_slopes_cancel_and_return_existing_probabilities_exactly(common_slope):
    settings, _, _ = _varying_settings(3, 1.0)
    settings["u_strength_d"] = [common_slope] * 3
    frame = Generator(**settings).generate(len(X), U=np.array([-2.0, -0.1, 0.3, 3.0]))
    np.testing.assert_array_equal(frame[_columns(["d_0", "d_1", "d_2"])].to_numpy(),
                                  frame[["m_d_0", "m_d_1", "m_d_2"]].to_numpy())


@pytest.mark.parametrize("transformation", ["latent_sign", "common_shifts", "arm_permutation"])
def test_gaussian_probability_symmetries_are_preserved(transformation):
    settings, _, slopes = _varying_settings(5, 5.0)
    reference = Generator(**settings).generate(len(X), U=0.0)
    expected = reference[_columns([f"d_{arm}" for arm in range(5)])].to_numpy()
    transformed = settings.copy()
    if transformation == "latent_sign":
        transformed["u_strength_d"] = -slopes
    elif transformation == "common_shifts":
        transformed["alpha_d"] = settings["alpha_d"] + 17.0
        transformed["beta_d"] = settings["beta_d"] + np.array([2.0, -3.0])
        transformed["u_strength_d"] = slopes + 23.0
    else:
        permutation = np.array([3, 0, 4, 1, 2])
        for name in ("alpha_d", "beta_d", "u_strength_d"):
            transformed[name] = np.asarray(settings[name])[permutation]
        expected = expected[:, permutation]
    frame = Generator(**transformed).generate(len(X), U=0.0)
    _assert_probabilities(frame[_columns([f"d_{arm}" for arm in range(5)])].to_numpy(), expected)


def test_nonlinear_treatment_callbacks_enter_the_same_gaussian_reference_scores():
    slopes = np.array([0.0, 2.0, -1.0])
    frame = Generator(k=2, x_sampler=lambda n, k, seed: X.copy(),
                      alpha_d=[0.2, -0.4, 0.7], propensity_sharpness=0.8,
                      g_d=[lambda x: x[:, 0] ** 2, lambda x: np.sin(x[:, 1]),
                           lambda x: x[:, 0] * x[:, 1]],
                      u_strength_d=slopes, assignment_policy="iid",
                      include_marginal_propensity=True, seed=731).generate(len(X), U=0.0)
    scores = 0.8 * np.column_stack((X[:, 0] ** 2, np.sin(X[:, 1]), X[:, 0] * X[:, 1]))
    scores += [0.2, -0.4, 0.7]
    _assert_probabilities(frame[_columns(["d_0", "d_1", "d_2"])].to_numpy(),
                         _gaussian_reference(scores, slopes))


def test_calibration_stays_at_u_zero_and_marginal_columns_use_calibrated_scores():
    target = np.array([0.2, 0.3, 0.5])
    slopes = np.array([0.0, 2.0, 2.0])
    frame = Generator(k=0, target_d_rate=target, u_strength_d=slopes,
                      include_marginal_propensity=True, seed=731,
                      assignment_policy="iid").generate(5, U=0.0)
    nominal = frame[["m_d_0", "m_d_1", "m_d_2"]].to_numpy()
    np.testing.assert_allclose(nominal, np.tile(target, (len(frame), 1)), rtol=0.0, atol=1e-6)
    expected = _gaussian_reference(np.log(nominal), slopes)
    actual = frame[_columns(["d_0", "d_1", "d_2"])].to_numpy()
    _assert_probabilities(actual, expected)
    assert np.max(np.abs(actual - nominal)) > 0.05


def test_supplied_nongaussian_or_x_dependent_u_does_not_change_reference_law():
    settings, scores, slopes = _varying_settings(3, 2.0)
    settings.update(sigma_y=0.0, u_strength_y=0.7)
    first = Generator(**settings).generate(len(X), U=np.full(len(X), -7.0))
    second = Generator(**settings).generate(len(X), U=3.0 * X[:, 0] + 2.0)
    columns = _columns(["d_0", "d_1", "d_2"])
    np.testing.assert_array_equal(first[columns], second[columns])
    _assert_probabilities(first[columns].to_numpy(), _gaussian_reference(scores, slopes))
    assert not np.array_equal(first[["m_obs_d_0", "m_obs_d_1", "m_obs_d_2"]],
                              second[["m_obs_d_0", "m_obs_d_1", "m_obs_d_2"]])
    assert not np.array_equal(first["y"], second["y"])


@pytest.mark.parametrize("policy", ["ensure_all", "iid"])
def test_probability_columns_describe_nominal_model_even_when_all_arm_policy_repairs(policy):
    n = 3 if policy == "ensure_all" else 1
    frame = Generator(k=0, alpha_d=[0.0, -1000.0, -1000.0], u_strength_d=0.0,
                      assignment_policy=policy, include_marginal_propensity=True,
                      seed=731).generate(n, U=0.0)
    np.testing.assert_array_equal(frame[_columns(["d_0", "d_1", "d_2"])],
                                  np.tile([1.0, 0.0, 0.0], (n, 1)))
    if policy == "ensure_all":
        np.testing.assert_array_equal(frame[["d_0", "d_1", "d_2"]].sum(), [1.0, 1.0, 1.0])
    else:
        assert frame.loc[0, "d_0"] == 1.0


@pytest.mark.parametrize("outcome_type", ["continuous", "binary", "poisson", "gamma"])
def test_opt_in_preserves_existing_columns_callback_calls_and_consecutive_rng(outcome_type):
    def make_generator(enabled):
        calls = []

        def record(name, value):
            def callback(x):
                calls.append((name, x.copy()))
                return value * x[:, 0]
            return callback

        generator = Generator(k=2, seed=731, outcome_type=outcome_type,
                              u_strength_d=[0.0, 1.2, -0.8], u_strength_y=0.5,
                              g_d=[None, record("g_d_1", 0.3), record("g_d_2", -0.2)],
                              g_y=record("g_y", 0.4), tau=[None, record("tau_1", 0.1), None],
                              include_marginal_propensity=enabled)
        return generator, calls

    ordinary, old_calls = make_generator(False)
    enabled, new_calls = make_generator(True)
    columns = _columns(["d_0", "d_1", "d_2"])
    for n in (23, 17):
        old_frame, new_frame = ordinary.generate(n), enabled.generate(n)
        assert list(new_frame.columns) == list(old_frame.columns) + columns
        pd.testing.assert_frame_equal(new_frame.drop(columns=columns), old_frame)
        assert ordinary.rng.bit_generator.state == enabled.rng.bit_generator.state
    assert len(old_calls) == len(new_calls) == 8
    for (old_name, old_x), (new_name, new_x) in zip(old_calls, new_calls):
        assert old_name == new_name
        np.testing.assert_array_equal(old_x, new_x)
    np.testing.assert_array_equal(ordinary.rng.random(10), enabled.rng.random(10))


@pytest.mark.parametrize("include_oracle", [False, True])
def test_default_and_explicit_disabled_option_preserve_schema_draws_and_next_rng(include_oracle):
    settings = dict(k=2, seed=731, include_oracle=include_oracle,
                    u_strength_d=[0.0, 1.0, -2.0], u_strength_y=0.4)
    default = Generator(**settings)
    disabled = Generator(**settings, include_marginal_propensity=False)
    for n in (31, 19):
        old_frame, disabled_frame = default.generate(n), disabled.generate(n)
        pd.testing.assert_frame_equal(old_frame, disabled_frame)
        assert not any(name.startswith("m_marginal_") for name in old_frame.columns)
        assert default.rng.bit_generator.state == disabled.rng.bit_generator.state
    np.testing.assert_array_equal(default.rng.random(10), disabled.rng.random(10))


def test_existing_full_positional_constructor_remains_compatible():
    args = (3, ["control", "one", "two"], [0.0, 0.4, -0.1], None,
            np.array([0.2]), None, 0.1, 0.7, "continuous", 2.0, 0.3, None,
            1, None, False, None, np.array([0.5]), None, [-0.2, 0.1, 0.4],
            [0.0, 1.0, 2.0], 1.0, None, True, 731, "iid")
    positional = Generator(*args)
    keyword = Generator(n_treatments=3, d_names=["control", "one", "two"],
                        theta=[0.0, 0.4, -0.1], beta_y=np.array([0.2]), alpha_y=0.1,
                        sigma_y=0.7, u_strength_y=0.3, k=1, beta_d=np.array([0.5]),
                        alpha_d=[-0.2, 0.1, 0.4], u_strength_d=[0.0, 1.0, 2.0],
                        seed=731, assignment_policy="iid")
    pd.testing.assert_frame_equal(positional.generate(31), keyword.generate(31))
    np.testing.assert_array_equal(positional.rng.random(10), keyword.rng.random(10))


@pytest.mark.parametrize("flag", [False, True, np.bool_(False), np.bool_(True)])
def test_python_and_numpy_boolean_flags_are_accepted(flag):
    frame = Generator(k=0, include_marginal_propensity=flag, seed=731).generate(9)
    assert all(name in frame for name in _columns(["d_0", "d_1", "d_2"])) == bool(flag)


INVALID_FLAGS = [None, 0, 1, 0.0, "true", [], np.array(True)]


@pytest.mark.parametrize("flag", INVALID_FLAGS)
@pytest.mark.parametrize("phase", ["constructor", "generate"])
def test_nonboolean_option_is_rejected_before_sampler_or_rng_use(flag, phase):
    def forbidden_sampler(n, k, seed):
        raise AssertionError("invalid flags must be rejected before sampling")

    if phase == "constructor":
        with pytest.raises(ValueError, match="include_marginal_propensity"):
            Generator(x_sampler=forbidden_sampler, include_marginal_propensity=flag, seed=731)
    else:
        generator = Generator(x_sampler=forbidden_sampler, seed=731)
        state = generator.rng.bit_generator.state
        generator.include_marginal_propensity = flag
        with pytest.raises(ValueError, match="include_marginal_propensity"):
            generator.generate(9)
        assert generator.rng.bit_generator.state == state


def test_enabled_marginal_probabilities_require_enabled_oracles_at_construction():
    with pytest.raises(ValueError, match="include_oracle"):
        Generator(include_oracle=False, include_marginal_propensity=True)


@pytest.mark.parametrize("mutation", ["enable_marginal", "disable_oracle"])
def test_mutable_conflicting_flags_are_rejected_before_sampling(mutation):
    def forbidden_sampler(n, k, seed):
        raise AssertionError("conflicting flags must be rejected before sampling")

    generator = Generator(x_sampler=forbidden_sampler, seed=731,
                          include_oracle=mutation == "disable_oracle",
                          include_marginal_propensity=mutation == "disable_oracle")
    state = generator.rng.bit_generator.state
    if mutation == "enable_marginal":
        generator.include_marginal_propensity = True
    else:
        generator.include_oracle = False
    with pytest.raises(ValueError, match="include_oracle"):
        generator.generate(9)
    assert generator.rng.bit_generator.state == state


@pytest.mark.parametrize("names,collision", [(["arm", "m_marginal_arm"], "m_marginal_arm"),
                                            (["arm", "marginal_arm"], "m_marginal_arm")])
def test_enabled_new_namespace_rejects_treatment_and_existing_oracle_collisions(names, collision):
    with pytest.raises(ValueError) as error:
        Generator(n_treatments=2, d_names=names, include_marginal_propensity=True)
    assert collision in str(error.value)
    assert "collid" in str(error.value).lower()


def test_actual_new_oracle_confounder_collision_rejects_before_latent_and_callbacks():
    calls = []

    def sampler(n, k, seed):
        calls.append("sample")
        return np.linspace(-1.0, 1.0, n).reshape(-1, 1)

    def forbidden_callback(x):
        raise AssertionError("actual names must be checked before callbacks")

    generator = Generator(confounder_specs=[dict(name="m_marginal_d_0")],
                          x_sampler=sampler, g_y=forbidden_callback,
                          include_marginal_propensity=True, seed=731)
    state = generator.rng.bit_generator.state
    with pytest.raises(ValueError) as error:
        generator.generate(9)
    assert "m_marginal_d_0" in str(error.value)
    assert "collid" in str(error.value).lower()
    assert calls == ["sample"]
    assert generator.rng.bit_generator.state == state


@pytest.mark.parametrize("use_copula", [False, True])
def test_expanded_categorical_names_are_checked_against_enabled_new_oracles(use_copula):
    generator = Generator(confounder_specs=[dict(name="m_marginal_d", dist="categorical",
                                                categories=["base", "0"])],
                          use_copula=use_copula, include_marginal_propensity=True, seed=731)
    with pytest.raises(ValueError) as error:
        generator.generate(12)
    assert "m_marginal_d_0" in str(error.value)
    assert "collid" in str(error.value).lower()


@pytest.mark.parametrize("include_oracle", [False, True])
def test_new_oracle_like_confounder_names_remain_available_when_option_is_disabled(include_oracle):
    generator = Generator(confounder_specs=[dict(name="m_marginal_d_0", dist="normal")],
                          include_oracle=include_oracle, seed=731)
    data = generator.to_multicausal_data(64)
    assert data.confounders == ["m_marginal_d_0"]
    np.testing.assert_array_equal(data.X["m_marginal_d_0"], data.df["m_marginal_d_0"])


@pytest.mark.parametrize("names", [["arm", "m_marginal_arm"], ["arm", "marginal_arm"]])
def test_new_names_are_not_reserved_in_default_namespace(names):
    frame = Generator(n_treatments=2, d_names=names, seed=731).generate(32)
    assert frame.columns.is_unique
    assert all(name in frame for name in names)


@pytest.mark.parametrize("mutation", ["enable_into_confounder", "disable_oracle", "rename_treatment"])
def test_late_callback_namespace_and_flag_changes_cannot_silently_corrupt_new_oracles(mutation):
    def callback(x):
        if mutation == "enable_into_confounder":
            generator.include_marginal_propensity = True
        elif mutation == "disable_oracle":
            generator.include_oracle = False
        else:
            generator.d_names[1] = "m_marginal_control"
        return np.zeros(len(x))

    specs = [dict(name="m_marginal_control" if mutation == "enable_into_confounder" else "feature")]
    generator = Generator(n_treatments=2, d_names=["control", "arm"],
                          confounder_specs=specs, g_y=callback, seed=731,
                          include_marginal_propensity=mutation != "enable_into_confounder")
    with pytest.raises(ValueError) as error:
        generator.generate(16)
    assert "include_oracle" in str(error.value) if mutation == "disable_oracle" else "m_marginal_control" in str(error.value)


@pytest.mark.parametrize("module_name", ["causalis.dgp.multicausaldata", "causalis.dgp.multicausaldata.functional"])
@pytest.mark.parametrize("return_causal_data", [False, True])
def test_public_wrapper_option_preserves_automatic_contract_features(module_name, return_causal_data):
    wrapper = getattr(importlib.import_module(module_name), "generate_multitreatment")
    settings = dict(n=64, k=2, random_state=731, beta_d=np.array([0.3, -0.2]),
                    return_causal_data=return_causal_data)
    ordinary = wrapper(**settings)
    enabled = wrapper(**settings, include_marginal_propensity=True)
    if return_causal_data:
        assert enabled.confounders == ordinary.confounders == ["x1", "x2"]
        assert enabled.control_treatment == "d_0"
        assert enabled.treatment_names == ["d_0", "d_1", "d_2"]
        pd.testing.assert_frame_equal(enabled.df, ordinary.df)
        pd.testing.assert_frame_equal(enabled.X, ordinary.X)
    else:
        columns = _columns(["d_0", "d_1", "d_2"])
        assert list(enabled.columns) == list(ordinary.columns) + columns
        pd.testing.assert_frame_equal(enabled.drop(columns=columns), ordinary)
        np.testing.assert_array_equal(enabled[columns].to_numpy(),
                                      enabled[["m_d_0", "m_d_1", "m_d_2"]].to_numpy())


def test_direct_contract_conversion_preserves_features_and_observations_with_latent_assignment():
    settings = dict(k=2, seed=731, u_strength_d=[0.0, 2.0, -1.0])
    ordinary = Generator(**settings).to_multicausal_data(64)
    enabled = Generator(**settings, include_marginal_propensity=True).to_multicausal_data(64)
    assert enabled.confounders == ordinary.confounders == ["x1", "x2"]
    pd.testing.assert_frame_equal(enabled.df, ordinary.df)
    pd.testing.assert_frame_equal(enabled.X, ordinary.X)


def test_unsupported_finite_gaussian_geometry_raises_instead_of_returning_a_guessed_probability():
    strength = np.finfo(float).max / 4.0
    settings = dict(n_treatments=2, k=0, alpha_d=[0.0, 0.0],
                    u_strength_d=[-strength, strength], assignment_policy="iid", seed=731)
    # Realized U=0 remains an ordinary finite nominal model. Only the opt-in
    # Gaussian integration must handle, or explicitly reject, its geometry.
    ordinary = Generator(**settings).generate(3, U=0.0)
    assert np.isfinite(ordinary.to_numpy()).all()
    with pytest.raises(ValueError, match="marginal|Gaussian|finite|integration"):
        Generator(**settings, include_marginal_propensity=True).generate(3, U=0.0)


def test_failed_quadrature_backend_cannot_publish_an_apparently_valid_probability(monkeypatch):
    calls = []

    def failed_backend(*args, **kwargs):
        calls.append("integration")
        # Even a bounded, unit-mass result is unusable when the numerical
        # backend explicitly reports failure. Numeric references never patch it.
        return np.array([0.5, 0.5]), 0.0, SimpleNamespace(success=False, status=1)

    module = importlib.import_module("causalis.dgp.multicausaldata.base")
    monkeypatch.setattr(module, "quad_vec", failed_backend, raising=False)
    with pytest.raises(ValueError, match="converg|integration"):
        Generator(n_treatments=2, k=0, alpha_d=[0.0, 0.5],
                  u_strength_d=[0.0, 1.0], assignment_policy="iid",
                  include_marginal_propensity=True, seed=731).generate(3, U=0.0)
    assert calls == ["integration"]
