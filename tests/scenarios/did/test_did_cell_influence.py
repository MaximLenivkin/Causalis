"""Independent empirical-estimator derivatives for traditional panel DiD inference."""

import numpy as np
import pandas as pd
import pytest
from scipy.optimize import root
from scipy.special import expit

from causalis.data_contracts import PanelDataDID
from causalis.scenarios.did import CallawaySantAnnaDID
from causalis.scenarios.did.model import _cell_influence_scores, _fit_logistic_propensity, _fit_outcome_regression


def _cell_arrays(seed=4219, n=96):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, 2))
    d = rng.binomial(1, expit(-0.2 + 1.1 * x[:, 0] - 0.5 * x[:, 1]))
    dy = np.exp(0.6 * x[:, 0]) + 0.4 * x[:, 1] ** 2 + rng.normal(size=n) + 2.0 * d
    return x, d, dy


def _panel(x, d, dy, *, common_trend=0.0, unbalanced=False, covariates=True):
    times = pd.period_range("2020-01", periods=2, freq="M")
    omitted = set()
    if unbalanced:
        omitted.update((int(i), 0) for i in np.flatnonzero(d)[:5])
        omitted.update((int(i), 1) for i in np.flatnonzero(1 - d)[:5])
    rows = []
    for i in range(len(d)):
        for t, time in enumerate(times):
            if (i, t) not in omitted:
                rows.append({"id": i, "time": time, "d": int(d[i] * t),
                             "y": 7.0 + t * (dy[i] + common_trend),
                             "x1": x[i, 0], "x2": x[i, 1]})
    return PanelDataDID(df=pd.DataFrame(rows), y="y", unit_col="id", time_col="time",
                        treated_time="d", covariates=["x1", "x2"] if covariates else [])


def _independent_weighted_att(design, d, dy, mass, *, estimator, ridge, clip):
    """Refit weighted estimating equations; no library fitting or IF helper is used."""
    if design.shape[1] == 1:
        p = np.full(len(d), np.clip(mass @ d, clip, 1.0 - clip))
    else:
        penalty = np.diag(np.r_[0.0, np.repeat(ridge, design.shape[1] - 1)])

        def equation(gamma):
            return design.T @ (mass * (expit(design @ gamma) - d)) + penalty @ gamma

        def jacobian(gamma):
            p0 = expit(design @ gamma)
            return design.T @ ((mass * p0 * (1.0 - p0))[:, None] * design) + penalty

        fitted = root(equation, np.zeros(design.shape[1]), jac=jacobian, tol=1e-11)
        assert np.max(np.abs(equation(fitted.x))) < 2e-9
        p = np.clip(expit(design @ fitted.x), clip, 1.0 - clip)
    if estimator in {"dr", "aipw"}:
        control = d == 0
        sqrt_mass = np.sqrt(mass[control])
        beta = np.linalg.lstsq(design[control] * sqrt_mass[:, None],
                               dy[control] * sqrt_mass, rcond=None)[0]
        residual = dy - design @ beta
    else:
        residual = dy
    odds = (1.0 - d) * p / (1.0 - p)
    return (mass @ (d * residual)) / (mass @ d) - (mass @ (odds * residual)) / (mass @ odds)


@pytest.mark.parametrize("estimator", ["dr", "aipw", "ipw"])
@pytest.mark.parametrize("ridge,clip", [(0.0, 1e-6), (0.07, 1e-6), (0.0, 0.25), (0.07, 0.25)])
def test_cell_if_matches_refitted_empirical_contamination(estimator, ridge, clip):
    x, d, dy = _cell_arrays()
    result = CallawaySantAnnaDID(estimator=estimator, control_group="never_treated",
                                logit_ridge=ridge, propensity_clip=clip,
                                optimizer_tol=1e-11).fit(_panel(x, d, dy)).estimate()
    local = result.diagnostics["unit_level"].sort_values("id")
    design = np.column_stack([np.ones(len(d)), x])
    mass = np.full(len(d), 1.0 / len(d))
    independent = _independent_weighted_att(design, d, dy, mass,
                                            estimator=estimator, ridge=ridge, clip=clip)
    assert result.att_gt.iloc[0].att == pytest.approx(independent, abs=2e-8)
    scores = local.influence_score.to_numpy()
    epsilon = 2e-5
    derivatives = []
    for i in range(len(d)):
        direction = -mass.copy()
        direction[i] += 1.0
        upper = _independent_weighted_att(design, d, dy, mass + epsilon * direction,
                                          estimator=estimator, ridge=ridge, clip=clip)
        lower = _independent_weighted_att(design, d, dy, mass - epsilon * direction,
                                          estimator=estimator, ridge=ridge, clip=clip)
        derivatives.append((upper - lower) / (2.0 * epsilon))
    np.testing.assert_allclose(scores, derivatives, atol=3e-6, rtol=2e-6)
    assert np.mean(scores) == pytest.approx(0.0, abs=2e-8)
    if clip == 0.25:
        assert ((local.propensity_score == clip) | (local.propensity_score == 1.0 - clip)).any()


@pytest.mark.parametrize("estimator", ["dr", "aipw", "ipw"])
@pytest.mark.parametrize("covariates", [False, True])
@pytest.mark.parametrize("unbalanced", [False, True])
def test_cell_inference_is_common_trend_invariant_and_embeds_complete_cases(estimator, covariates, unbalanced):
    x, d, dy = _cell_arrays()
    kwargs = dict(estimator=estimator, control_group="never_treated", logit_ridge=0.07,
                  optimizer_tol=1e-11)
    original = CallawaySantAnnaDID(**kwargs).fit(
        _panel(x, d, dy, unbalanced=unbalanced, covariates=covariates)).estimate()
    shifted = CallawaySantAnnaDID(**kwargs).fit(
        _panel(x, d, dy, common_trend=1000.0, unbalanced=unbalanced, covariates=covariates)).estimate()
    np.testing.assert_allclose(original.att_gt[["att", "se", "p_value"]],
                               shifted.att_gt[["att", "se", "p_value"]], atol=2e-9, rtol=2e-8)
    np.testing.assert_allclose(original.diagnostics["influence_scores"],
                               shifted.diagnostics["influence_scores"], atol=2e-8, rtol=2e-8)
    local = original.diagnostics["unit_level"].set_index("id")
    full = original.diagnostics["influence_scores"][0]
    n_total, n_cell = len(full), len(local)
    assert n_total == len(d)
    assert n_cell == len(d) - (10 if unbalanced else 0)
    np.testing.assert_allclose(full.loc[local.index], local.influence_score * n_total / n_cell)
    assert (full.loc[~full.index.isin(local.index)] == 0.0).all()
    assert original.att_gt.iloc[0].se == pytest.approx(np.linalg.norm(local.influence_score) / n_cell)


@pytest.mark.parametrize("estimator", ["dr", "aipw", "ipw"])
def test_intercept_only_clipped_share_reduces_to_difference_in_means(estimator):
    x, _, dy = _cell_arrays(n=90)
    d = np.r_[np.ones(8), np.zeros(82)]
    result = CallawaySantAnnaDID(estimator=estimator, control_group="never_treated",
                                propensity_clip=0.2, logit_ridge=0.1).fit(
                                    _panel(x, d, dy, covariates=False)).estimate()
    scores = result.diagnostics["unit_level"].sort_values("id").influence_score.to_numpy()
    expected = d / d.mean() * (dy - dy[d == 1].mean()) - (1.0 - d) / (1.0 - d.mean()) * (dy - dy[d == 0].mean())
    assert result.att_gt.iloc[0].att == pytest.approx(dy[d == 1].mean() - dy[d == 0].mean())
    np.testing.assert_allclose(scores, expected, atol=2e-14)


def test_dr_traditional_if_matches_primary_drdid_untrimmed_mle_ols_reference():
    x, d, dy = _cell_arrays(seed=533, n=240)
    result = CallawaySantAnnaDID(estimator="dr", control_group="never_treated",
                                logit_ridge=0.0, optimizer_tol=1e-11).fit(_panel(x, d, dy)).estimate()
    local = result.diagnostics["unit_level"].sort_values("id")
    design = np.column_stack([np.ones(len(d)), x])
    p = local.propensity_score.to_numpy()
    residual = local.delta_y.to_numpy() - local.outcome_regression.to_numpy()
    wt, wc = local.treated_weight.to_numpy(), local.control_weight.to_numpy()
    beta_if = ((1.0 - d) * residual)[:, None] * design @ np.linalg.inv(design.T @ ((1.0 - d)[:, None] * design) / len(d))
    gamma_if = (d - p)[:, None] * design @ np.linalg.inv(design.T @ ((p * (1.0 - p))[:, None] * design) / len(d))
    eta_t, eta_c = np.mean(wt * residual), np.mean(wc * residual)
    reference = wt * (residual - eta_t) - wc * (residual - eta_c)
    reference -= beta_if @ np.mean((wt - wc)[:, None] * design, axis=0)
    reference -= gamma_if @ np.mean((wc * (residual - eta_c))[:, None] * design, axis=0)
    np.testing.assert_allclose(local.influence_score, reference, atol=2e-8, rtol=2e-8)


@pytest.mark.parametrize("estimator", ["dr", "aipw", "ipw"])
@pytest.mark.parametrize("scale", [1e6, 1e7])
def test_propensity_influence_preserves_valid_directions_under_covariate_rescaling(estimator, scale):
    x, d, dy = _cell_arrays()
    design = np.column_stack([np.ones(len(d)), x])
    gamma, p = _fit_logistic_propensity(design, d, clip=1e-6, ridge=0.0, tol=1e-11, max_iter=1000)
    _, outcome = _fit_outcome_regression(design, dy, d == 0)
    residual = dy - outcome if estimator != "ipw" else dy
    wt = d / d.mean()
    odds = (1.0 - d) * p / (1.0 - p)
    wc = odds / odds.mean()
    kwargs = dict(estimate_outcome=estimator != "ipw", propensity_clip=1e-6, logit_ridge=0.0)
    original = _cell_influence_scores(design, d, residual, wt, wc, gamma, **kwargs)
    rescaled_design = design.copy()
    rescaled_design[:, 1] *= scale
    rescaled_gamma = gamma.copy()
    rescaled_gamma[1] /= scale
    rescaled = _cell_influence_scores(rescaled_design, d, residual, wt, wc, rescaled_gamma, **kwargs)
    # Gamma is transformed analytically so this checks the influence solver,
    # independently of optimizer convergence on very differently scaled inputs.
    np.testing.assert_allclose(rescaled, original, atol=3e-7, rtol=3e-7)
