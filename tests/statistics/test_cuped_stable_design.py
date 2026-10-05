"""Independent QR references for CUPED projection and sandwich covariance."""
import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from causalis.data_contracts import CausalData, RctCausalData
from causalis.scenarios.cuped import CUPEDModel
from causalis.scenarios.cuped.refutation.regression_checks import leverage_and_cooks


def sample(near_collinear=False):
    rng = np.random.default_rng(476)
    n = 400
    d = np.arange(n) % 2
    x = rng.normal(size=n)
    x2 = x + 1e-7 * rng.normal(size=n) if near_collinear else rng.normal(size=n)
    y = 20 + 2 * d + .9 * x - .3 * x2 + (1 + .8 * d) * rng.normal(size=n)
    return pd.DataFrame(dict(d=d, x=x, x2=x2, y=y))


def qr_reference(z, y, cov_type):
    q, r = np.linalg.qr(z, mode="reduced")
    p = np.linalg.solve(r, q.T)
    b = p @ y
    residual = y - z @ b
    h = np.sum(q * q, axis=1)
    n, k = z.shape
    scale = residual ** 2
    if cov_type == "nonrobust":
        cov = p @ p.T * (residual @ residual / (n - k))
    else:
        if cov_type == "HC1":
            scale *= n / (n - k)
        elif cov_type == "HC2":
            scale /= 1 - h
        elif cov_type == "HC3":
            scale /= (1 - h) ** 2
        cov = (p * scale) @ p.T
    return b, cov, h, p


@pytest.mark.parametrize("cov_type", ["HC0", "HC1", "HC2", "HC3", "nonrobust"])
@pytest.mark.parametrize("use_t", [False, True])
def test_result_inference_matches_public_statsmodels(cov_type, use_t):
    frame = sample()
    data = CausalData.from_df(frame, "d", "y", ["x", "x2"])
    model = CUPEDModel(cov_type=cov_type, use_t=use_t).fit(data, covariates=["x", "x2"])
    actual = model._result
    expected = sm.OLS(frame.y, actual.model.data.orig_exog).fit(cov_type=cov_type, use_t=use_t)
    for name in ("params", "bse", "pvalues", "fittedvalues", "resid"):
        np.testing.assert_allclose(getattr(actual, name), getattr(expected, name), atol=1e-10, rtol=1e-10)
    np.testing.assert_allclose(actual.cov_params(), expected.cov_params(), atol=1e-12)
    np.testing.assert_allclose(actual.conf_int(alpha=.1), expected.conf_int(alpha=.1), atol=1e-10)
    assert actual.df_model == expected.df_model
    assert actual.df_resid == expected.df_resid
    assert actual.rsquared == pytest.approx(expected.rsquared, abs=1e-12)
    assert actual.use_t == use_t
    assert actual.cov_type == expected.cov_type
    assert "OLS Regression Results" in actual.summary().as_text()


@pytest.mark.parametrize("scale", [1., 3e7, 1e8])
def test_leverage_and_cooks_matches_qr_under_rescaling(scale):
    frame = sample()
    d, x, y = frame.d.to_numpy(), frame.x.to_numpy(), frame.y.to_numpy()
    x = scale * (x - x.mean())
    z = np.column_stack([np.ones(len(x)), d, x, d*x])
    b, _, h_expected, _ = qr_reference(z, y, "nonrobust")
    h, cooks, std = leverage_and_cooks(y, z, b)
    residual = y - z @ b
    mse = residual @ residual / (len(y) - z.shape[1])
    np.testing.assert_allclose(h, h_expected, atol=2e-9, rtol=2e-8)
    assert h.sum() == pytest.approx(4., abs=1e-8)
    np.testing.assert_allclose(cooks, residual**2/(4*mse)*h_expected/(1-h_expected)**2,
                               atol=2e-9, rtol=1e-7)
    np.testing.assert_allclose(std, residual/np.sqrt(mse*(1-h_expected)), atol=1e-8)


@pytest.mark.parametrize("cov_type", ["HC0", "HC1", "HC2", "HC3", "nonrobust"])
def test_scale_invariance_including_raw_control_relative_ci(cov_type):
    frame = sample()
    estimates = []
    models = []
    for scale in (1., 3e7):
        changed = frame.copy()
        changed["x"] *= scale
        data = CausalData.from_df(changed, "d", "y", ["x", "x2"])
        model = CUPEDModel(cov_type=cov_type, relative_denominator="raw_control", use_t=False)
        model.fit(data, covariates=["x", "x2"])
        estimates.append(model.estimate())
        models.append(model)
        z = model._result.model.exog
        b, cov, h, p = qr_reference(z, frame.y.to_numpy(), cov_type)
        np.testing.assert_allclose(model._result.params[:2], b[:2], rtol=2e-7, atol=1e-7)
        np.testing.assert_allclose(model._result.cov_params()[:2, :2], cov[:2, :2], rtol=1e-7, atol=1e-9)
        # Independent raw-control cross-covariance, retaining the library's HC policy.
        residual = frame.y.to_numpy() - z @ b
        weights = p[1] * residual
        n, k = z.shape
        if cov_type == "HC1":
            weights *= np.sqrt(n/(n-k))
        elif cov_type in ("HC2", "HC3"):
            weights /= (1-h)**(.5 if cov_type == "HC2" else 1.)
        weights *= np.sqrt(cov[1, 1]/np.sum(weights**2))
        controls = frame.d.to_numpy() == 0
        mu = frame.y.to_numpy()[controls].mean()
        mu_if = np.zeros(n)
        mu_if[controls] = (frame.y.to_numpy()[controls]-mu)/controls.sum()
        cross = model._cov_tau_raw_control_mean(frame.y.to_numpy(), z, controls, cov[1, 1])
        assert cross == pytest.approx(weights @ mu_if, abs=2e-9, rel=1e-7)
    for field in ("value", "ci_lower_absolute", "ci_upper_absolute", "value_relative",
                  "ci_lower_relative", "ci_upper_relative"):
        assert getattr(estimates[0], field) == pytest.approx(getattr(estimates[1], field), rel=2e-7, abs=1e-7)
    assert models[0]._regression_checks.max_leverage == pytest.approx(
        models[1]._regression_checks.max_leverage, abs=1e-9)


@pytest.mark.parametrize("cov_type", ["HC2", "HC3"])
def test_near_collinear_sandwich_uses_stable_projection(cov_type):
    frame = sample(near_collinear=True)
    data = CausalData.from_df(frame, "d", "y", ["x", "x2"])
    model = CUPEDModel(cov_type=cov_type).fit(data, covariates=["x", "x2"])
    b, cov, h, _ = qr_reference(model._result.model.exog, frame.y.to_numpy(), cov_type)
    assert np.linalg.cond(model._result.model.exog) < 1e8
    np.testing.assert_allclose(model._result.cov_params()[:2, :2], cov[:2, :2], rtol=2e-6, atol=1e-8)
    assert model._regression_checks.max_leverage == pytest.approx(h.max(), rel=1e-6)


@pytest.mark.parametrize("checks", [False, True])
def test_batch_factorization_is_reused_without_ols_fit(checks, monkeypatch):
    frame = sample()
    frame["y2"] = 2 * frame.y + frame.x2
    frame["y3"] = -frame.y + frame.x
    data = RctCausalData.from_df(frame, "d", ["y", "y2", "y3"], ["x", "x2"])
    svd_calls = []
    original = np.linalg.svd
    def counted(a, *args, **kwargs):
        svd_calls.append(a.shape)
        return original(a, *args, **kwargs)
    def forbidden(*args, **kwargs):
        raise AssertionError("CUPED must solve from its owned factorization, without OLS.fit")
    monkeypatch.setattr(np.linalg, "svd", counted)
    monkeypatch.setattr(sm.OLS, "fit", forbidden)
    model = CUPEDModel().fit(data, covariates=["x", "x2"], run_checks=checks)
    effects = model.estimate()
    assert svd_calls == [(400, 6), (400, 2)]
    assert len(effects) == 3
    children = [model._comparison_models[name]["d"] for name in ["y", "y2", "y3"]]
    assert all(child._result.model.pinv_wexog is children[0]._result.model.pinv_wexog for child in children)
    for child in children:
        b, cov, _, _ = qr_reference(child._result.model.exog, child._result.model.endog, "HC2")
        np.testing.assert_allclose(child._result.params, b, atol=1e-10)
        np.testing.assert_allclose(child._result.cov_params(), cov, atol=1e-11)
