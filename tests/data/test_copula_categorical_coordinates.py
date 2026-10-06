"""Independent Gaussian-coordinate references for categorical copula draws."""

import numpy as np
import pytest
from scipy.special import ndtr
from scipy.stats import norm

from causalis.dgp import CausalDatasetGenerator, generate_iv_data
from causalis.dgp.base import _gaussian_copula
from causalis.dgp.multicausaldata.base import MultiCausalDatasetGenerator

SEED = 731
JITTER = 1e-10


def _latent_reference(rng, n, dimension, rho):
    """Analytic lower-triangular projection of independent standard normals.

    Only positive-definite equicorrelation matrices of dimension <= 3 are
    used. This never calls the production PSD correction or copula sampler.
    The established diagonal jitter is part of the numeric-only contract.
    """
    independent = rng.normal(size=(n, dimension))
    latent = np.empty_like(independent)
    diagonal = 1.0 + JITTER
    first_scale = np.sqrt(diagonal)
    latent[:, 0] = first_scale * independent[:, 0]
    if dimension >= 2:
        first_loading = rho / first_scale
        second_scale = np.sqrt(diagonal - first_loading**2)
        latent[:, 1] = (
            first_loading * independent[:, 0] + second_scale * independent[:, 1]
        )
    if dimension == 3:
        second_loading = (rho - first_loading**2) / second_scale
        third_scale = np.sqrt(diagonal - first_loading**2 - second_loading**2)
        latent[:, 2] = (
            first_loading * independent[:, 0]
            + second_loading * independent[:, 1]
            + third_scale * independent[:, 2]
        )
    return latent


def _corr(dimension, rho):
    matrix = np.full((dimension, dimension), rho)
    np.fill_diagonal(matrix, 1.0)
    return matrix


def _categorical_reference(latent, spec):
    categories = list(spec.get("categories", [0, 1, 2]))
    mass = np.asarray(spec.get("probs", np.ones(len(categories))), dtype=float)
    mass = mass / mass.sum()
    if len(categories) == 1:
        return np.zeros((len(latent), 1)), [spec["name"] + "__onlylevel"]
    uniform = ndtr(latent)
    cumulative = np.cumsum(mass)
    lower = 0.0
    active = np.flatnonzero(mass > 0)
    labels = np.full(len(latent), int(active[-1]))
    # Explicit disjoint CDF intervals; saturated U=1 stays in the final
    # positive-mass interval, including when raw categories have zero tails.
    for index, upper in enumerate(cumulative):
        labels[(uniform >= lower) & (uniform < upper)] = index
        lower = upper
    columns = [(labels == index).astype(float) for index in range(1, len(categories))]
    return np.column_stack(columns), [
        f"{spec['name']}_{level}" for level in categories[1:]
    ]


def _mixed_reference(latent, specs):
    columns = []
    names = []
    for coordinate, spec in enumerate(specs):
        if spec["dist"] == "categorical":
            values, expanded_names = _categorical_reference(latent[:, coordinate], spec)
        else:
            uniform = np.clip(ndtr(latent[:, coordinate]), 1e-12, 1.0 - 1e-12)
            if spec["dist"] == "normal":
                values = spec.get("mu", 0.0) + spec.get("sd", 1.0) * norm.ppf(uniform)
            elif spec["dist"] == "uniform":
                values = (
                    spec.get("a", 0.0)
                    + (spec.get("b", 1.0) - spec.get("a", 0.0)) * uniform
                )
            else:
                values = (uniform < spec.get("p", 0.5)).astype(float)
            values = values[:, None]
            expanded_names = [spec["name"]]
        columns.append(values)
        names.extend(expanded_names)
    return np.column_stack(columns), names


def _sample_reference(specs, n=257, rho=0.0):
    rng = np.random.default_rng(SEED)
    latent = _latent_reference(rng, n, len(specs), rho)
    values, names = _mixed_reference(latent, specs)
    return values, names, rng


@pytest.mark.parametrize("rho", [-0.3, 0.0, 0.6])
@pytest.mark.parametrize("order", ["cnn", "ncc", "cnc"])
def test_each_categorical_coordinate_uses_its_own_gaussian_uniform(order, rho):
    first = {
        "name": "first",
        "dist": "categorical",
        "categories": ["base", "low", "high"],
        "probs": [1, 2, 1],
    }
    second = {
        "name": "second",
        "dist": "categorical",
        "categories": ["off", "on"],
        "probs": [0.65, 0.35],
    }
    numeric = {"name": "numeric", "dist": "normal", "mu": 2.0, "sd": 1.5}
    if order == "cnn":
        specs = [
            first,
            numeric,
            {"name": "other", "dist": "uniform", "a": -1.0, "b": 3.0},
        ]
    elif order == "ncc":
        specs = [numeric, first, second]
    else:
        specs = [first, numeric, second]
    expected, names, reference_rng = _sample_reference(specs, rho=rho)
    actual_rng = np.random.default_rng(SEED)
    actual, actual_names = _gaussian_copula(actual_rng, 257, specs, _corr(3, rho))
    assert actual_names == names
    np.testing.assert_allclose(actual, expected, rtol=1e-11, atol=1e-11)
    assert np.isfinite(actual).all()
    np.testing.assert_array_equal(actual_rng.random(10), reference_rng.random(10))


@pytest.mark.parametrize("probabilities", [None, [0.2, 0.5, 0.3], [2.0, 5.0, 3.0]])
def test_first_categorical_default_explicit_and_unnormalized_probabilities(
    probabilities,
):
    spec = {
        "name": "segment",
        "dist": "categorical",
        "categories": ["base", "mid", "top"],
    }
    if probabilities is not None:
        spec["probs"] = probabilities
    expected, names, reference_rng = _sample_reference([spec], n=200)
    actual_rng = np.random.default_rng(SEED)
    actual, actual_names = _gaussian_copula(actual_rng, 200, [spec])
    assert actual_names == names == ["segment_mid", "segment_top"]
    np.testing.assert_array_equal(actual, expected)
    assert (actual.sum(axis=1) <= 1).all()
    np.testing.assert_array_equal(actual_rng.random(10), reference_rng.random(10))


@pytest.mark.parametrize("first", [False, True])
def test_single_category_emits_existing_onlylevel_schema(first):
    singleton = {"name": "constant", "dist": "categorical", "categories": ["sole"]}
    numeric = {"name": "numeric", "dist": "normal"}
    specs = [singleton, numeric] if first else [numeric, singleton]
    expected, names, reference_rng = _sample_reference(specs, n=11)
    actual_rng = np.random.default_rng(SEED)
    actual, actual_names = _gaussian_copula(actual_rng, 11, specs)
    assert actual_names == names
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)
    np.testing.assert_array_equal(
        actual[:, names.index("constant__onlylevel")], np.zeros(11)
    )
    np.testing.assert_array_equal(actual_rng.random(10), reference_rng.random(10))


class _FixedNormals:
    def __init__(self, values):
        self.values = np.asarray(values, dtype=float).reshape(-1, 1)
        self.calls = 0

    def normal(self, size):
        assert size == self.values.shape
        self.calls += 1
        return self.values.copy()


def _categorical_from_fixed_normals(values, categories, probabilities):
    rng = _FixedNormals(values)
    actual, names = _gaussian_copula(
        rng,
        len(values),
        [
            {
                "name": "segment",
                "dist": "categorical",
                "categories": categories,
                "probs": probabilities,
            }
        ],
    )
    assert rng.calls == 1
    return actual, names


def test_category_threshold_and_saturated_tails_have_explicit_interval_semantics():
    actual, names = _categorical_from_fixed_normals(
        [-1000.0, -1.0, 0.0, 1.0, 1000.0], ["low", "high"], [0.5, 0.5]
    )
    assert names == ["segment_high"]
    np.testing.assert_array_equal(actual[:, 0], [0.0, 0.0, 1.0, 1.0, 1.0])


@pytest.mark.parametrize(
    "categories,probabilities,expected",
    [
        (["possible", "zero"], [1.0, 0.0], [[0.0]]),
        (["base", "possible", "zero"], [0.5, 0.5, 0.0], [[1.0, 0.0]]),
    ],
)
def test_upper_saturation_never_selects_zero_probability_tail(
    categories, probabilities, expected
):
    actual, _ = _categorical_from_fixed_normals([1000.0], categories, probabilities)
    np.testing.assert_array_equal(actual, expected)


def test_lower_saturation_skips_zero_probability_leading_category():
    actual, names = _categorical_from_fixed_normals(
        [-1000.0], ["zero", "possible", "other"], [0.0, 0.5, 0.5]
    )
    assert names == ["segment_possible", "segment_other"]
    np.testing.assert_array_equal(actual, [[1.0, 0.0]])


@pytest.mark.parametrize("tail", ["lower", "upper"])
def test_tiny_valid_category_intervals_are_not_erased_by_numeric_inverse_cdf_clipping(
    tail,
):
    if tail == "lower":
        probabilities = [5e-13, 0.4, 0.6 - 5e-13]
        gaussian = norm.ppf(1e-13)
        expected = [[0.0, 0.0]]
    else:
        probabilities = [0.5, 0.5 - 5e-13, 5e-13]
        gaussian = norm.isf(1e-13)
        expected = [[0.0, 1.0]]
    actual, _ = _categorical_from_fixed_normals(
        [gaussian], ["base", "mid", "top"], probabilities
    )
    np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize("rho", [-0.3, 0.6])
def test_numeric_only_copula_and_next_rng_remain_compatible(rho):
    specs = [
        {"name": "normal", "dist": "normal", "mu": 3.0, "sd": 2.0},
        {"name": "uniform", "dist": "uniform", "a": -2.0, "b": 5.0},
        {"name": "bernoulli", "dist": "bernoulli", "p": 0.3},
    ]
    expected, names, reference_rng = _sample_reference(specs, n=100, rho=rho)
    actual_rng = np.random.default_rng(SEED)
    actual, actual_names = _gaussian_copula(actual_rng, 100, specs, _corr(3, rho))
    assert actual_names == names
    np.testing.assert_allclose(actual, expected, rtol=1e-11, atol=1e-11)
    np.testing.assert_array_equal(actual_rng.random(10), reference_rng.random(10))


@pytest.mark.parametrize("rho", [-0.75, 0.0, 0.75])
def test_observed_normal_category_correlation_matches_discretized_gaussian_law(rho):
    specs = [
        {"name": "normal", "dist": "normal"},
        {"name": "category", "dist": "categorical", "categories": [0, 1]},
    ]
    values, names = _gaussian_copula(
        np.random.default_rng(SEED), 20000, specs, _corr(2, rho)
    )
    assert names == ["normal", "category_1"]
    observed = np.corrcoef(values.T)[0, 1]
    # Corr(Z0, 1{Z1 >= 0}) = rho*sqrt(2/pi), distinct from latent rho.
    expected = rho * np.sqrt(2.0 / np.pi)
    assert observed == pytest.approx(expected, abs=0.025)
    assert values[:, 1].mean() == pytest.approx(0.5, abs=0.015)
    if rho == 0:
        agreement = np.mean(values[:, 1] == (values[:, 0] >= 0).astype(float))
        assert agreement == pytest.approx(0.5, abs=0.015)


def _public_specs(first):
    categorical = {
        "name": "segment",
        "dist": "categorical",
        "categories": ["base", "a", "b"],
        "probs": [2, 5, 3],
    }
    numeric = {"name": "age", "dist": "normal", "mu": 1.0, "sd": 0.8}
    return [categorical, numeric] if first else [numeric, categorical]


@pytest.mark.parametrize("kind", ["binary", "multi"])
@pytest.mark.parametrize("first", [False, True])
def test_full_binary_and_multi_generation_uses_correct_expanded_coordinates(
    kind, first
):
    specs = _public_specs(first)
    expected, names, _ = _sample_reference(specs, rho=-0.4)
    coefficients = np.array([0.6, -0.2, 0.3])
    options = dict(
        confounder_specs=specs,
        use_copula=True,
        copula_corr=_corr(2, -0.4),
        seed=SEED,
        beta_y=coefficients,
        alpha_y=0.2,
        sigma_y=0.3,
    )
    if kind == "binary":
        generator = CausalDatasetGenerator(
            theta=0.7, beta_d=np.array([0.1, 0.2, -0.15]), **options
        )
        oracle_names = ["g0", "g1"]
    else:
        generator = MultiCausalDatasetGenerator(
            n_treatments=2,
            theta=[0.0, 0.7],
            beta_d=np.array([0.1, 0.2, -0.15]),
            **options,
        )
        oracle_names = ["g_d_0", "g_d_1"]
    frame = generator.generate(257)
    assert [column for column in frame.columns if column in names] == names
    np.testing.assert_allclose(frame[names], expected, rtol=1e-11, atol=1e-11)
    baseline = 0.2 + expected @ coefficients
    np.testing.assert_allclose(frame[oracle_names[0]], baseline, rtol=1e-11, atol=1e-11)
    np.testing.assert_allclose(
        frame[oracle_names[1]], baseline + 0.7, rtol=1e-11, atol=1e-11
    )
    assert "segment_base" not in frame.columns
    assert np.isfinite(frame.to_numpy()).all()
    if kind == "multi":
        assert generator.confounder_names_ == names
        assert frame[["d_0", "d_1"]].sum(axis=1).eq(1).all()


@pytest.mark.parametrize("first", [False, True])
@pytest.mark.parametrize("return_causal_data", [False, True])
def test_inherited_iv_public_wrapper_uses_same_gaussian_coordinates(
    first, return_causal_data
):
    specs = _public_specs(first)
    expected, names, _ = _sample_reference(specs, rho=0.5)
    result = generate_iv_data(
        n=257,
        random_state=SEED,
        confounder_specs=specs,
        use_copula=True,
        copula_corr=_corr(2, 0.5),
        return_causal_data=return_causal_data,
    )
    frame = result.df if return_causal_data else result
    np.testing.assert_allclose(frame[names], expected, rtol=1e-11, atol=1e-11)
    assert "segment_base" not in frame.columns
    if return_causal_data:
        assert result.confounders == names
