import numpy as np
import pytest

from causalis.dgp.multicausaldata.base import MultiCausalDatasetGenerator as Generator


@pytest.mark.parametrize('kwargs', [
    {'alpha_y': np.inf, 'outcome_type': 'binary'},
    {'g_y': lambda X: np.full(len(X), np.inf), 'outcome_type': 'gamma'},
    {'gamma_shape': np.inf, 'outcome_type': 'gamma'},
    {'x_sampler': lambda n, k, s: np.full((n, k), np.inf)},
    {'theta': np.nan},
    {'alpha_d': np.inf},
    {'target_d_rate': [1., np.inf, 1.]},
    {'sigma_y': -1.},
    {'u_strength_y': 1e155, 'outcome_type': 'gamma'},
])
def test_invalid_values_raise_contextual_value_error(kwargs):
    with pytest.raises(ValueError):
        Generator(k=1, seed=42, **kwargs).generate(12)


@pytest.mark.parametrize('value', [0, -1, 2.5, True])
def test_observation_count_contract(value):
    with pytest.raises(ValueError, match='n'):
        Generator(seed=42).generate(value)


@pytest.mark.parametrize('value', [np.full(12, np.inf), np.zeros((3, 4)), np.zeros(11)])
def test_latent_shape_and_finiteness(value):
    with pytest.raises(ValueError, match='U'):
        Generator(k=1, seed=42).generate(12, U=value)


@pytest.mark.parametrize('outcome', ['continuous', 'binary', 'poisson', 'gamma'])
def test_scalar_and_column_latent_values_equal_vector(outcome):
    kwargs = dict(k=1, seed=42, outcome_type=outcome, u_strength_y=.4)
    expected = Generator(**kwargs).generate(12, U=np.full(12, .2))
    for supplied in [.2, np.full((12, 1), .2)]:
        actual = Generator(**kwargs).generate(12, U=supplied)
        np.testing.assert_array_equal(actual.to_numpy(), expected.to_numpy())


def test_scalar_baseline_callbacks_and_column_tau_remain_supported():
    scalar = Generator(k=1, seed=42, g_y=lambda X: 2., g_d=lambda X: .1,
                       tau=lambda X: np.full((len(X), 1), .3)).generate(12)
    vector = Generator(k=1, seed=42, g_y=lambda X: np.full(len(X), 2.),
                       g_d=lambda X: np.full(len(X), .1),
                       tau=lambda X: np.full(len(X), .3)).generate(12)
    np.testing.assert_array_equal(scalar.to_numpy(), vector.to_numpy())


@pytest.mark.parametrize('name', ['alpha_d', 'u_strength_d', 'theta', 'beta_d', 'beta_y'])
def test_complex_coefficients_rejected_before_float_conversion(name):
    value = np.array([1. + .1j])
    with pytest.raises(ValueError, match=name):
        Generator(k=1, seed=42, **{name: value}).generate(12)


def test_single_element_baseline_callback_broadcast_preserved():
    expected = Generator(k=1, seed=42, g_y=lambda X: 2., g_d=lambda X: .1).generate(12)
    actual = Generator(k=1, seed=42, g_y=lambda X: np.array([2.]),
                       g_d=lambda X: np.array([.1])).generate(12)
    np.testing.assert_array_equal(actual.to_numpy(), expected.to_numpy())


def test_overflowing_target_weight_sum_preserves_probabilities_and_draws():
    kwargs = dict(k=1, seed=42)
    expected = Generator(**kwargs, target_d_rate=[1., 1., 1.]).generate(12)
    actual = Generator(**kwargs, target_d_rate=[1e308, 1e308, 1e308]).generate(12)
    np.testing.assert_array_equal(actual.to_numpy(), expected.to_numpy())


@pytest.mark.parametrize('family', ['continuous', 'binary', 'poisson', 'gamma'])
@pytest.mark.parametrize('include_oracle', [True, False])
@pytest.mark.parametrize('callback', ['g_y', 'g_d', 'tau'])
@pytest.mark.parametrize('bad', [np.nan, np.inf, -np.inf])
def test_nonfinite_callbacks_rejected_before_links(family, include_oracle, callback, bad):
    kwargs = {callback: lambda X: np.full(len(X), bad)}
    with pytest.raises(ValueError, match=callback):
        Generator(k=1, seed=42, outcome_type=family,
                  include_oracle=include_oracle, **kwargs).generate(12)


@pytest.mark.parametrize('name', ['n_treatments', 'k'])
@pytest.mark.parametrize('value', [True, 2.5, -1])
def test_integer_configuration_contract(name, value):
    with pytest.raises(ValueError, match=name):
        Generator(**{name: value})


@pytest.mark.parametrize('shape', [(12,), (11, 1), (12, 2), (12, 1, 1)])
def test_custom_sampler_exact_shape_contract(shape):
    with pytest.raises(ValueError, match='X'):
        Generator(k=1, seed=42, x_sampler=lambda n, k, s: np.zeros(shape)).generate(12)


def test_finite_overflowing_linear_predictor_rejected_before_binary_link():
    with pytest.raises(ValueError, match='baseline outcome link'):
        Generator(k=1, seed=42, outcome_type='binary', beta_y=np.array([1e308]),
                  x_sampler=lambda n, k, s: np.full((n, k), 10.)).generate(12)


def test_continuous_large_finite_latent_strength_not_restricted_by_exponential_oracle():
    df = Generator(k=0, seed=42, u_strength_y=1e155).generate(12)
    assert np.isfinite(df.to_numpy()).all()
