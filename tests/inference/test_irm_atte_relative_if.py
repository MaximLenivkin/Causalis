"""ATT relative inference against empirical-ratio derivatives."""

import warnings
import json

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression

from causalis.data_contracts.causaldata import CausalData
from causalis.scenarios.unconfoundedness import IRM


@pytest.mark.parametrize("normalize_ipw", [False, True])
@pytest.mark.parametrize("n_treated", [2, 12, 60])
def test_constant_potential_outcomes_have_zero_relative_att_uncertainty(
    normalize_ipw, n_treated
):
    n = 120
    d = np.zeros(n, dtype=int)
    d[np.linspace(0, n - 1, n_treated, dtype=int)] = 1
    data = CausalData(
        df=pd.DataFrame({"y": 10.0 + 2.0 * d, "d": d, "x": np.linspace(-1, 1, n)}),
        outcome="y", treatment="d", confounders=["x"],
    )
    model = IRM(
        data, ml_g=DummyRegressor(), ml_m=DummyClassifier(strategy="prior"),
        n_folds=2, normalize_ipw=normalize_ipw, random_state=3,
    ).fit()
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = model.estimate(score="ATTE")

    assert not any("Relative effect baseline" in str(item.message) for item in captured)
    assert result.value == pytest.approx(2.0)
    assert result.value_relative == pytest.approx(20.0)
    assert model.se_[0] == pytest.approx(0.0, abs=1e-13)
    assert model.se_relative_[0] == pytest.approx(0.0, abs=1e-12)
    assert result.ci_lower_relative == pytest.approx(20.0)
    assert result.ci_upper_relative == pytest.approx(20.0)


@pytest.mark.parametrize("normalize_ipw", [False, True])
@pytest.mark.parametrize("baseline", [4.0, -4.0])
def test_relative_att_matches_contamination_derivative_with_covariance(
    normalize_ipw, baseline
):
    rng = np.random.default_rng(710)
    n = 300
    x = rng.normal(size=n)
    d = rng.binomial(1, 1.0 / (1.0 + np.exp(0.4 - 0.6 * x)))
    y = baseline + 0.5 * x + d * (0.7 + 0.35 * x) + rng.normal(scale=0.3, size=n)
    data = CausalData(
        df=pd.DataFrame({"x": x, "d": d, "y": y}),
        outcome="y", treatment="d", confounders=["x"],
    )
    model = IRM(
        data, ml_g=LinearRegression(), ml_m=LogisticRegression(), n_folds=3,
        normalize_ipw=normalize_ipw, random_state=13,
    ).fit()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        result = model.estimate(score="ATTE", alpha=0.1)

    # The relative ATT is a ratio of two unnormalized population moments.
    # Perturb the empirical distribution, keeping nuisance predictions fixed.
    # This directly differentiates the target ratio rather than centering a
    # normalized baseline signal as though the treated share were fixed.
    g0 = model.g0_hat_
    odds = model.m_hat_ / (1.0 - model.m_hat_)
    numerator = d * (y - g0) - (1 - d) * odds * (y - g0)
    denominator = d * g0 + (1 - d) * odds * (y - g0)
    num_mean, den_mean = numerator.mean(), denominator.mean()
    eps = 1e-5
    ratio_plus = 100.0 * ((1 - eps) * num_mean + eps * numerator) / (
        (1 - eps) * den_mean + eps * denominator
    )
    ratio_minus = 100.0 * ((1 + eps) * num_mean - eps * numerator) / (
        (1 + eps) * den_mean - eps * denominator
    )
    derivative = (ratio_plus - ratio_minus) / (2 * eps)
    expected_se = derivative.std(ddof=1) / np.sqrt(n)
    value = 100.0 * num_mean / den_mean
    z = norm.ppf(0.95)

    assert result.value_relative == pytest.approx(value, rel=1e-12)
    assert model.se_relative_[0] == pytest.approx(expected_se, rel=2e-8)
    assert result.ci_lower_relative == pytest.approx(value - z * expected_se, rel=2e-8)
    assert result.ci_upper_relative == pytest.approx(value + z * expected_se, rel=2e-8)
    # Both moments fluctuate together: dropping their covariance materially
    # changes the standard error in this DGP.
    p = d.mean()
    theta = num_mean / p
    mu = den_mean / p
    if_theta = (numerator - d * theta) / p
    if_mu = (denominator - d * mu) / p
    no_cov_se = 100.0 * np.sqrt(
        np.var(if_theta, ddof=1) / mu**2
        + theta**2 * np.var(if_mu, ddof=1) / mu**4
    ) / np.sqrt(n)
    assert abs(no_cov_se - expected_se) > 0.01


def test_relative_att_oracle_iid_sampling_calibration(capsys):
    """Limited fixed-seed coverage check with known propensity/outcome means."""
    rng = np.random.default_rng(40317)
    n, repetitions = 600, 600
    estimates, standard_errors, covered = [], [], []
    # X is +/-1 equiprobably; propensity is .25/.75. Consequently
    # E[X|D=1]=.5, ATT=1+.6*.5 and baseline ATT=4+.7*.5.
    truth = 100.0 * 1.3 / 4.35
    model = IRM(ml_g=DummyRegressor(), ml_m=DummyClassifier(strategy="prior"))
    for _ in range(repetitions):
        x = rng.choice([-1.0, 1.0], size=n)
        p = 0.5 + 0.25 * x
        d = rng.binomial(1, p)
        g0 = 4.0 + 0.7 * x
        g1 = g0 + 1.0 + 0.6 * x
        y = np.where(d == 1, g1, g0) + rng.normal(size=n)
        components = model._compute_estimate_components(
            y=y, d=d, g0_hat=g0, g1_hat=g1, m_hat=p, score="ATTE",
        )
        theta, influence, _, _, _, _, _, z = model._solve_moment_equation(
            psi_a=components["psi_a"], psi_b=components["psi_b"], alpha=0.05,
        )
        _, relative, lower, upper, se = model._compute_relative_effect_stats(
            theta_hat=theta, IF=influence, w=components["w"], w_bar=components["w_bar"],
            g0_hat=g0, u0=components["u0"], h0=components["h0"], z=z, score="ATTE",
        )
        estimates.append(relative)
        standard_errors.append(se)
        covered.append(lower <= truth <= upper)
    coverage = float(np.mean(covered))
    empirical_sd = float(np.std(estimates, ddof=1))
    mean_se = float(np.mean(standard_errors))
    evidence = {
        "seed": 40317, "repetitions": repetitions, "n": n, "truth_percent": truth,
        "mean_estimate_percent": float(np.mean(estimates)),
        "coverage_95": coverage, "empirical_sd_percent": empirical_sd,
        "mean_se_percent": mean_se, "mean_se_over_empirical_sd": mean_se / empirical_sd,
    }
    with capsys.disabled():
        print("binary_relative_att_oracle_sampling " + json.dumps(evidence, sort_keys=True))
    assert coverage > 0.91
    assert coverage < 0.98
    assert 0.85 < mean_se / empirical_sd < 1.15
