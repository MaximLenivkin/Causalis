"""
Tests for binary-outcome inference in the classic RCT module.
"""

import pytest
import numpy as np
import pandas as pd

from causalis.data_contracts import CausalData
from causalis.scenarios.classic_rct import conversion_ztest


@pytest.fixture
def random_seed():
    return 42


@pytest.fixture
def conv_test_data(random_seed):
    np.random.seed(random_seed)
    n = 5000
    baseline = 0.10
    uplift = 0.03  # absolute uplift in treatment

    treatment = np.random.choice([0, 1], size=n)
    # control prob = baseline; treatment prob = baseline + uplift
    probs = np.where(treatment == 1, baseline + uplift, baseline)
    target = (np.random.rand(n) < probs).astype(int)

    df = pd.DataFrame({
        'treatment': treatment,
        'outcome': target,
        'age': np.random.randint(18, 70, size=n)
    })

    return {
        'df': df,
        'baseline': baseline,
        'uplift': uplift,
        'n': n,
    }


@pytest.fixture
def causal_data(conv_test_data):
    return CausalData(
        df=conv_test_data['df'],
        outcome='outcome',
        treatment='treatment',
        confounders=['age']
    )


def test_basic_keys_and_types(causal_data):
    res = conversion_ztest(causal_data)
    expected_keys = ['p_value', 'absolute_difference', 'absolute_ci', 'relative_difference', 'relative_ci']
    assert all(k in res for k in expected_keys)
    assert isinstance(res['p_value'], float)
    assert 0 <= res['p_value'] <= 1
    assert isinstance(res['absolute_ci'], tuple) and len(res['absolute_ci']) == 2
    assert isinstance(res['relative_ci'], tuple) and len(res['relative_ci']) == 2


def test_effect_size_and_ci(causal_data, conv_test_data):
    res = conversion_ztest(causal_data)
    expected_diff = conv_test_data['uplift']
    actual_diff = res['absolute_difference']
    # allow sampling noise
    assert abs(actual_diff - expected_diff) < 0.015

    lower, upper = res['absolute_ci']
    assert lower <= expected_diff <= upper


def test_relative_difference(causal_data, conv_test_data):
    res = conversion_ztest(causal_data)
    expected_rel = (conv_test_data['uplift'] / conv_test_data['baseline']) * 100
    assert abs(res['relative_difference'] - expected_rel) < 5


def test_alphas_change_width(causal_data):
    res10 = conversion_ztest(causal_data, alpha=0.10)
    res05 = conversion_ztest(causal_data, alpha=0.05)
    res01 = conversion_ztest(causal_data, alpha=0.01)

    w10 = res10['absolute_ci'][1] - res10['absolute_ci'][0]
    w05 = res05['absolute_ci'][1] - res05['absolute_ci'][0]
    w01 = res01['absolute_ci'][1] - res01['absolute_ci'][0]

    assert w10 < w05 < w01


def test_errors_non_binary_treatment(conv_test_data):
    df = conv_test_data['df'].copy()
    df['treatment'] = np.random.choice([0, 1, 2], size=conv_test_data['n'])
    with pytest.raises(ValueError, match="binary encoded"):
        CausalData(df=df, outcome='outcome', treatment='treatment', confounders=['age'])


def test_errors_non_binary_outcome(conv_test_data):
    df = conv_test_data["df"].copy()
    # make the outcome non-binary
    df["outcome"] = np.random.normal(size=conv_test_data["n"])
    ck = CausalData(
        df=df, outcome="outcome", treatment="treatment", confounders=["age"]
    )
    with pytest.raises(ValueError):
        conversion_ztest(ck)


def test_conversion_z_test_methods():
    # Create a small dataset where methods should differ more
    np.random.seed(42)
    n = 100
    treatment = np.array([0] * n + [1] * n)
    # Control: 5/100, Treatment: 15/100
    outcome = np.array([0] * 95 + [1] * 5 + [0] * 85 + [1] * 15)

    df = pd.DataFrame({"treatment": treatment, "outcome": outcome})
    data = CausalData(df=df, outcome="outcome", treatment="treatment")

    # 1. Default (Newcombe + Pooled)
    res_default = conversion_ztest(data)

    # 2. Wald Unpooled (previously default)
    res_wald = conversion_ztest(
        data, ci_method="wald_unpooled", se_for_test="unpooled"
    )

    # Check that they differ
    assert res_default["absolute_ci"] != res_wald["absolute_ci"]
    assert res_default["p_value"] != res_wald["p_value"]

    # Newcombe should be asymmetric usually, Wald is symmetric
    diff = res_default["absolute_difference"]
    lower, upper = res_default["absolute_ci"]
    # Wald symmetry check
    w_lower, w_upper = res_wald["absolute_ci"]
    assert pytest.approx(diff - w_lower) == (w_upper - diff)

    # Newcombe asymmetry check (for this specific data_contracts)
    assert abs((upper - diff) - (diff - lower)) > 1e-5


def test_diff_in_means_passes_kwargs():
    from causalis.scenarios.classic_rct.model import DiffInMeans

    np.random.seed(42)
    n = 100
    treatment = np.array([0] * n + [1] * n)
    outcome = np.array([0] * 95 + [1] * 5 + [0] * 85 + [1] * 15)
    df = pd.DataFrame({"treatment": treatment, "outcome": outcome})
    data = CausalData(df=df, outcome="outcome", treatment="treatment")

    model = DiffInMeans().fit(data)

    # Estimate with explicit wald_unpooled to see if it's passed
    res_wald = model.estimate(method="conversion_ztest", ci_method="wald_unpooled")

    # Compare with direct call
    res_direct_wald = conversion_ztest(data, ci_method="wald_unpooled")

    assert res_wald.ci_lower_absolute == res_direct_wald["absolute_ci"][0]
    assert res_wald.ci_upper_absolute == res_direct_wald["absolute_ci"][1]


def _conversion_data_from_counts(x1, n1, x0, n0):
    df = pd.DataFrame({
        "treatment": np.r_[np.zeros(n0, dtype=int), np.ones(n1, dtype=int)],
        "outcome": np.r_[
            np.ones(x0, dtype=int), np.zeros(n0 - x0, dtype=int),
            np.ones(x1, dtype=int), np.zeros(n1 - x1, dtype=int),
        ],
    })
    return CausalData(df=df, outcome="outcome", treatment="treatment")


@pytest.mark.parametrize("alpha", [0.01, 0.05, 0.10])
@pytest.mark.parametrize("x1,n1,x0,n0", [
    (7, 34, 1, 34),       # audit counterexample
    (20, 100, 10, 100),   # ordinary conversion rates
    (0, 40, 5, 60),       # a zero-success arm
    (35, 40, 60, 60),     # an all-success arm
    (1, 10, 0, 13),       # rare events and unequal arm sizes
    (3, 5, 2, 17),        # small, unequal samples
    (11, 15, 4, 12),
])
def test_newcombe_matches_independent_reference(x1, n1, x0, n0, alpha):
    from statsmodels.stats.proportion import confint_proportions_2indep

    data = _conversion_data_from_counts(x1, n1, x0, n0)
    actual = conversion_ztest(data, alpha=alpha)["absolute_ci"]
    expected = confint_proportions_2indep(
        x1, n1, x0, n0, method="newcomb", compare="diff", alpha=alpha
    )
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-14)


def test_newcombe_group_swap_negates_interval():
    data = _conversion_data_from_counts(7, 34, 1, 34)
    swapped = _conversion_data_from_counts(1, 34, 7, 34)
    original_ci = conversion_ztest(data)["absolute_ci"]
    swapped_ci = conversion_ztest(swapped)["absolute_ci"]
    np.testing.assert_allclose(swapped_ci, (-original_ci[1], -original_ci[0]))


@pytest.mark.parametrize("parameter,value", [
    ("ci_method", "typo"),
    ("ci_method", ""),
    ("ci_method", None),
    ("se_for_test", "typo"),
    ("se_for_test", ""),
    ("se_for_test", None),
])
def test_invalid_method_options_are_rejected(causal_data, parameter, value):
    with pytest.raises(ValueError, match=parameter):
        conversion_ztest(causal_data, **{parameter: value})
