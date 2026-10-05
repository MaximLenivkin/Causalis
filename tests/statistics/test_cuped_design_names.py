"""The regression's statistical meaning must not depend on user column names."""
import numpy as np
import pandas as pd
import pytest

from causalis.data_contracts import CausalData
from causalis.scenarios.cuped import CUPEDModel
from causalis.scenarios.cuped.refutation import CUPEDRefutationConfig


@pytest.mark.parametrize("treatment,covariates", [
    ("intercept", []), ("x__centered", ["x"]),
    ("d:x", ["x"]), ("d", ["x__centered"]),
    ("intercept", ["intercept__cuped_1", "x"]),
    ("d", ["x__centered", "d:x"]),
])
@pytest.mark.parametrize("method", ["delta", "bootstrap"])
@pytest.mark.parametrize("checks", [False, True])
def test_column_renaming_preserves_full_estimate(treatment, covariates, method, checks):
    rng = np.random.default_rng(1067)
    n = 240
    d = np.arange(n) % 2
    x = rng.normal(size=(n, len(covariates)))
    y = 20 + 2 * d + rng.normal(size=n)
    if covariates:
        y += x @ np.arange(1, len(covariates) + 1) + .7 * d * x[:, 0]
    frame = pd.DataFrame(x, columns=covariates)
    frame[treatment] = d
    frame["outcome"] = y
    original = frame.copy(deep=True)
    data = CausalData.from_df(frame, treatment, "outcome", covariates)
    renamed = {treatment: "safe_d", **{name: f"safe_x{i}" for i, name in enumerate(covariates)}}
    safe_names = [renamed[name] for name in covariates]
    safe = CausalData.from_df(frame.rename(columns=renamed), "safe_d", "outcome", safe_names)
    options = dict(relative_ci_method=method, relative_ci_bootstrap_draws=40,
                   relative_ci_bootstrap_seed=86,
                   refutation_config=CUPEDRefutationConfig(check_action="ignore"))
    model = CUPEDModel(**options).fit(data, covariates=covariates, run_checks=checks)
    reference = CUPEDModel(**options).fit(safe, covariates=safe_names, run_checks=checks)
    actual, expected = model.estimate(), reference.estimate()
    for name in ("value", "p_value", "ci_lower_absolute", "ci_upper_absolute",
                 "value_relative", "ci_lower_relative", "ci_upper_relative",
                 "adjusted_control_mean", "adjusted_treatment_mean"):
        assert getattr(actual, name) == pytest.approx(getattr(expected, name), abs=1e-10)
    assert model._result.model.exog.shape[1] == 2 + 2 * len(covariates)
    assert len(set(model._result.model.exog_names)) == model._result.model.exog.shape[1]
    for name in ("beta_covariates", "gamma_interactions"):
        np.testing.assert_allclose(getattr(actual.diagnostic_data, name),
                                   getattr(expected.diagnostic_data, name), atol=1e-12)
        assert len(getattr(actual.diagnostic_data, name)) == len(covariates)
    if checks:
        a, b = model._regression_checks, reference._regression_checks
        assert a.p_main_covariates == b.p_main_covariates == len(covariates)
        for name in ("ate_adj_winsor", "max_leverage", "max_cooks", "max_abs_std_resid"):
            assert getattr(a, name) == pytest.approx(getattr(b, name))
    pd.testing.assert_frame_equal(frame, original)
