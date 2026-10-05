"""Independent ratio-estimator checks for multi-arm ATT inference."""

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm
from sklearn.dummy import DummyClassifier, DummyRegressor

from causalis.data_contracts.multicausaldata import MultiCausalData
from causalis.data_contracts.causal_diagnostic_data import MultiUnconfoundednessDiagnosticData
from causalis.scenarios.multi_unconfoundedness.model import MultiTreatmentIRM
from causalis.scenarios.multi_unconfoundedness.refutation.score.score_validation import run_score_diagnostics


def _fit_with_oracle_predictions(y, d, g, m, *, store_diagnostics=True):
    """Run the fit lifecycle, then isolate inference using known nuisance values."""
    n, k = d.shape
    names = [f"d{j}" for j in range(k)]
    frame = pd.DataFrame(d, columns=names)
    frame["y"] = y
    # Preserve the covariate behind these oracle means (an affine transform of
    # x in the heterogeneous cases), rather than introducing unrelated X.
    frame["x"] = g[:, 0] if np.ptp(g[:, 0]) > 0 else np.linspace(-1.0, 1.0, n)
    data = MultiCausalData(
        df=frame,
        outcome="y",
        treatment_names=names,
        control_treatment=names[0],
        confounders=["x"],
    )
    model = MultiTreatmentIRM(
        data,
        ml_g=DummyRegressor(),
        ml_m=DummyClassifier(),
        n_folds=2,
        trimming_threshold=0.0,
        random_state=19,
        store_diagnostics=store_diagnostics,
    ).fit()
    model.g_hat_ = np.array(g, dtype=float, copy=True)
    model.m_hat_ = np.array(m, dtype=float, copy=True)
    return model


@pytest.mark.parametrize("counts", [(100, 100, 100), (150, 60, 90)])
@pytest.mark.parametrize("store_diagnostics", [True, False])
def test_noiseless_constant_arm_effects_have_zero_att_sampling_uncertainty(counts, store_diagnostics):
    labels = np.repeat(np.arange(3), counts)
    d = np.eye(3)[labels]
    effects = np.array([0.0, 2.0, 4.0])
    y = 10.0 + effects[labels]
    g = np.tile(10.0 + effects, (len(y), 1))
    m = np.tile(np.asarray(counts) / len(y), (len(y), 1))
    model = _fit_with_oracle_predictions(y, d, g, m, store_diagnostics=store_diagnostics)

    result = model.estimate(score="ATTE")

    np.testing.assert_allclose(result.value, effects[1:], atol=1e-13)
    np.testing.assert_allclose(model.psi_, 0.0, atol=1e-13)
    np.testing.assert_allclose(result.model_options["std_error"], 0.0, atol=1e-13)
    np.testing.assert_allclose(result.ci_lower_absolute, result.value, atol=1e-13)
    np.testing.assert_allclose(result.ci_upper_absolute, result.value, atol=1e-13)
    np.testing.assert_allclose(result.ci_lower_relative, result.value_relative, atol=1e-12)
    np.testing.assert_allclose(result.ci_upper_relative, result.value_relative, atol=1e-12)


def _heterogeneous_oracle_sample(seed=23):
    rng = np.random.default_rng(seed)
    n = 240
    x = rng.normal(size=n)
    probabilities = np.column_stack(
        [0.45 + 0.08 * np.tanh(x), 0.2 - 0.03 * np.tanh(x), 0.35 - 0.05 * np.tanh(x)]
    )
    labels = np.array([rng.choice(3, p=p) for p in probabilities])
    d = np.eye(3)[labels]
    g0 = 5.0 + 0.7 * x
    g = np.column_stack([g0, g0 + 1.0 + 0.4 * x, g0 - 0.5 + 0.2 * x])
    y = g[np.arange(n), labels] + rng.normal(scale=0.8, size=n)
    return y, d, g, probabilities


def _weighted_ratios(weights, y, d, g, m):
    """Empirical ATT and counterfactual baseline functionals, without score code."""
    residual0 = y - g[:, 0]
    shares = weights @ d[:, 1:]
    numerator_rows = d[:, 1:] * residual0[:, None]
    numerator_rows -= d[:, [0]] * (m[:, 1:] / m[:, [0]]) * residual0[:, None]
    baseline_rows = d[:, 1:] * g[:, [0]]
    baseline_rows += d[:, [0]] * (m[:, 1:] / m[:, [0]]) * residual0[:, None]
    return (weights @ numerator_rows) / shares, (weights @ baseline_rows) / shares


def test_att_influence_matches_empirical_contamination_derivative_and_se():
    y, d, g, m = _heterogeneous_oracle_sample()
    n = len(y)
    model = _fit_with_oracle_predictions(y, d, g, m)
    result = model.estimate(score="ATTE", diagnostic_data=False)
    uniform = np.full(n, 1.0 / n)
    theta, baseline = _weighted_ratios(uniform, y, d, g, m)
    np.testing.assert_allclose(result.value, theta, atol=1e-13)
    np.testing.assert_allclose(result.control_mean_by_arm, baseline, atol=1e-13)

    # The directional derivative of P -> (1-epsilon)P + epsilon delta_i
    # includes movement of the empirical treatment share, independent of psi_a.
    eps = 1e-5
    derivative = np.empty_like(model.psi_)
    relative_derivative = np.empty_like(model.psi_)
    for i in range(n):
        direction = -uniform.copy()
        direction[i] += 1.0
        plus, baseline_plus = _weighted_ratios(uniform + eps * direction, y, d, g, m)
        minus, baseline_minus = _weighted_ratios(uniform - eps * direction, y, d, g, m)
        derivative[i] = (plus - minus) / (2.0 * eps)
        relative_derivative[i] = (
            100.0 * plus / baseline_plus - 100.0 * minus / baseline_minus
        ) / (2.0 * eps)

    np.testing.assert_allclose(model.psi_, derivative, rtol=2e-8, atol=2e-8)
    np.testing.assert_allclose(model.psi_.mean(axis=0), 0.0, atol=1e-13)
    expected_se = derivative.std(axis=0, ddof=1) / np.sqrt(n)
    np.testing.assert_allclose(result.model_options["std_error"], expected_se, rtol=2e-8)
    z = norm.ppf(0.975)
    expected_rel_se = relative_derivative.std(axis=0, ddof=1) / np.sqrt(n)
    actual_rel_se = (result.ci_upper_relative - result.ci_lower_relative) / (2.0 * z)
    np.testing.assert_allclose(actual_rel_se, expected_rel_se, rtol=2e-8)

    # The two old fixed-share IFs contain proportional arm-share errors that
    # cancel in their ratio. Correcting both must preserve relative intervals.
    shares = d[:, 1:].mean(axis=0)
    residual0 = y[:, None] - g[:, [0]]
    baseline_signal = d[:, 1:] * g[:, [0]] / shares[None, :]
    baseline_signal += d[:, [0]] * (m[:, 1:] / m[:, [0]]) * residual0 / shares[None, :]
    legacy_relative_if = 100.0 * (
        (model.psi_b_ - theta[None, :]) / baseline[None, :]
        - theta[None, :] * (baseline_signal - baseline[None, :]) / baseline[None, :] ** 2
    )
    legacy_rel_se = legacy_relative_if.std(axis=0, ddof=1) / np.sqrt(n)
    np.testing.assert_allclose(actual_rel_se, legacy_rel_se, rtol=1e-13)


def test_constant_proportional_potential_outcomes_have_zero_relative_att_uncertainty():
    rng = np.random.default_rng(31)
    n = 240
    labels = np.repeat(np.arange(3), [100, 60, 80])
    rng.shuffle(labels)
    d = np.eye(3)[labels]
    baseline = 10.0 + rng.uniform(-2.0, 2.0, n)
    g = baseline[:, None] * np.array([1.0, 1.2, 1.4])[None, :]
    y = g[np.arange(n), labels]
    m = np.tile([0.4, 0.25, 0.35], (n, 1))
    model = _fit_with_oracle_predictions(y, d, g, m)
    result = model.estimate(score="ATTE", diagnostic_data=False)

    # Absolute ATT varies with each sample's treated covariates; the ratio is
    # identically 20% or 40% for every empirical distribution with arm support.
    assert np.all(result.model_options["std_error"] > 0.0)
    np.testing.assert_allclose(result.value_relative, [20.0, 40.0], atol=1e-12)
    np.testing.assert_allclose(result.ci_lower_relative, result.value_relative, atol=1e-12)
    np.testing.assert_allclose(result.ci_upper_relative, result.value_relative, atol=1e-12)


def test_att_if_is_equivariant_to_active_arm_permutation_and_outcome_shift():
    y, d, g, m = _heterogeneous_oracle_sample()
    model = _fit_with_oracle_predictions(y, d, g, m)
    result = model.estimate(score="ATTE", diagnostic_data=False)
    perm = [0, 2, 1]
    transformed = _fit_with_oracle_predictions(y + 13.0, d[:, perm], g[:, perm] + 13.0, m[:, perm])
    other = transformed.estimate(score="ATTE", diagnostic_data=False)

    np.testing.assert_allclose(other.value, result.value[::-1], atol=1e-13)
    np.testing.assert_allclose(transformed.psi_, model.psi_[:, ::-1], atol=1e-13)
    np.testing.assert_allclose(transformed.se_, model.se_[::-1], atol=1e-13)


@pytest.mark.parametrize("score", ["ATE", "ATTE"])
def test_score_jacobian_payload_roundtrip_and_plugin_se_match_estimation(score):
    y, d, g, m = _heterogeneous_oracle_sample()
    model = _fit_with_oracle_predictions(y, d, g, m)
    result = model.estimate(score=score)
    diag = result.diagnostic_data
    expected_shape = (len(y),) if score == "ATE" else (len(y), d.shape[1] - 1)
    assert diag.psi_a.shape == expected_shape
    np.testing.assert_array_equal(diag.psi_a, model.psi_a_)
    # Omit unset optional values; sigma2's legacy sensitivity annotation does
    # not accept explicit None and is outside this score-contract change.
    result.diagnostic_data = MultiUnconfoundednessDiagnosticData(**diag.model_dump(exclude_none=True))
    np.testing.assert_array_equal(result.diagnostic_data.psi_a, model.psi_a_)

    report = run_score_diagnostics(model.data, result)
    assert report["meta"]["used_estimator_psi_a"] is True
    np.testing.assert_allclose(
        report["influence_diagnostics"]["by_comparison"]["se_plugin"], model.se_, rtol=1e-13
    )


def _oracle_interval_calibration():
    # IID treatment shares fluctuate between samples. A fixed-share IF creates
    # spurious uncertainty from the nonzero treatment effects even with oracle g0.
    rng = np.random.default_rng(4701)
    repetitions, n = 600, 600
    probabilities = np.array([0.5, 0.2, 0.3])
    effects = np.array([0.0, 2.0, 4.0])
    model = MultiTreatmentIRM()
    model.n_treatments = 3
    g = np.tile(10.0 + effects, (n, 1))
    m = np.tile(probabilities, (n, 1))
    values, standard_errors, covered = [], [], []
    for _ in range(repetitions):
        labels = rng.choice(3, size=n, p=probabilities)
        d = np.eye(3)[labels]
        y = 10.0 + effects[labels] + rng.normal(size=n)
        _, _, _, psi_a, psi_b = model._compute_score_terms(y=y, d=d, g_hat=g, m_hat=m, score="ATTE")
        theta, _, se, _, _, lower, upper, _ = model._solve_moment_and_inference(
            psi_a=psi_a, psi_b=psi_b, alpha=0.05
        )
        values.append(theta)
        standard_errors.append(se)
        covered.append((lower <= effects[1:]) & (effects[1:] <= upper))

    return {
        "repetitions": repetitions,
        "n": n,
        "coverage": np.mean(covered, axis=0),
        "empirical_sd": np.std(values, axis=0, ddof=1),
        "reported_sd": np.sqrt(np.mean(np.square(standard_errors), axis=0)),
    }


def test_att_oracle_wald_intervals_have_sampling_calibration():
    metrics = _oracle_interval_calibration()
    coverage = metrics["coverage"]
    empirical_sd = metrics["empirical_sd"]
    reported_sd = metrics["reported_sd"]
    assert np.all((coverage > 0.925) & (coverage < 0.98)), coverage
    np.testing.assert_allclose(reported_sd / empirical_sd, 1.0, atol=0.12, rtol=0.0)
