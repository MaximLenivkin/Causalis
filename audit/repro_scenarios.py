"""Focused audit probes; no source modifications or global test execution.

Run from repository root: .venv/Scripts/python.exe audit/repro_scenarios.py
Prints JSON evidence for each independently isolated probe.
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.stats.proportion import confint_proportions_2indep

from causalis.data_contracts import CausalData, PanelDataDID
from causalis.scenarios.classic_rct.inference import conversion_ztest
from causalis.scenarios.cuped.model import CUPEDModel
from causalis.scenarios.cuped.refutation.regression_checks import leverage_and_cooks
from causalis.scenarios.did.model import CallawaySantAnnaDID


def run(name, fn):
    try:
        value = fn()
        print(json.dumps({"probe": name, "status": "executed", "evidence": value}, ensure_ascii=False, default=str))
    except Exception as exc:
        print(json.dumps({"probe": name, "status": "exception", "type": type(exc).__name__, "message": str(exc)}, ensure_ascii=False))
        traceback.print_exc()


def proportions():
    df = pd.DataFrame({"d": np.repeat([0, 1], 34), "y": [1] + [0]*33 + [1]*7 + [0]*27})
    data = CausalData(df=df, treatment="d", outcome="y", confounders=[])
    current = conversion_ztest(data)
    reference = confint_proportions_2indep(7, 34, 1, 34, method="newcomb", compare="diff")
    invalid = conversion_ztest(data, ci_method="typo", se_for_test="typo")
    return {"current": current, "statsmodels_newcombe": reference, "invalid_enum_silently_accepted": invalid}


def panel(common_slope=0.0, differential_pre_slope=0.0, deterministic=False):
    rng = np.random.default_rng(923)
    periods = pd.period_range("2020-01", periods=5, freq="M")
    rows = []
    for i in range(60):
        is_treated = i < 30
        for t, time in enumerate(periods):
            active = int(is_treated and t >= 3)
            y = (0.0 if deterministic else rng.normal()) + common_slope*t + differential_pre_slope*t*is_treated + 2.0*active
            rows.append({"id": i, "time": time, "d": active, "y": y})
    return PanelDataDID(df=pd.DataFrame(rows), y="y", unit_col="id", time_col="time", treated_time="d", covariates=[])


def did_shift():
    def fit(slope):
        result = CallawaySantAnnaDID(estimator="ipw", control_group="never_treated").fit(panel(common_slope=slope)).estimate()
        return result.att_gt[["time", "att", "se", "p_value"]].to_dict("records")
    base, shifted = fit(0.0), fit(1000.0)
    return {"original": base, "common_trend_plus_1000_per_period": shifted}


def did_pre_controls():
    data = panel(differential_pre_slope=2.0, deterministic=True)
    result = CallawaySantAnnaDID(include_pre_periods=True).fit(data).estimate()
    pre = result.att_gt[~result.att_gt.is_post_treatment]
    diag = result.diagnostics["unit_level"]
    duplicates = {str(cell): int(group["id"].duplicated().sum()) for cell, group in diag.groupby("cell_id")}
    return {"pre_cells": pre[["time", "base_time", "att", "n_treated", "n_control"]].to_dict("records"), "expected_pre_att_without_own_cohort_controls": -2.0, "duplicate_unit_rows_per_cell": duplicates}


def did_dr_mle_influence():
    from scipy.special import expit
    rng = np.random.default_rng(533)
    n = 1000
    x = rng.normal(size=n)
    group = rng.binomial(1, expit(-0.3+0.8*x))
    periods = pd.period_range("2020-01", periods=3, freq="M")
    rows = []
    for i in range(n):
        for t, time in enumerate(periods):
            active = int(group[i] and t >= 1)
            dy = np.exp(0.7*x[i]) + rng.normal(scale=0.2)
            rows.append({"id": i, "time": time, "d": active, "x": x[i], "y": t*dy+2.0*active})
    data = PanelDataDID(df=pd.DataFrame(rows), y="y", unit_col="id", time_col="time", treated_time="d", covariates=["x"])
    estimate = CallawaySantAnnaDID(estimator="dr", control_group="never_treated", logit_ridge=0.0).fit(data).estimate()
    diag = estimate.diagnostics["unit_level"]
    local = diag[diag.cell_id == 0]
    design = np.column_stack([np.ones(n), local.x.to_numpy()])
    d = local.is_treated_cohort.to_numpy()
    p = local.propensity_score.to_numpy()
    r = (local.delta_y-local.outcome_regression).to_numpy()
    wt, wc = local.treated_weight.to_numpy(), local.control_weight.to_numpy()
    eta_t, eta_c = np.mean(wt*r), np.mean(wc*r)
    beta_if = ((1-d)*r)[:, None]*design @ np.linalg.inv(design.T @ ((1-d)[:, None]*design)/n)
    gamma_if = (d-p)[:, None]*design @ np.linalg.inv(design.T @ ((p*(1-p))[:, None]*design)/n)
    m_beta = np.mean((wt-wc)[:, None]*design, axis=0)
    m_gamma = np.mean((wc*(r-eta_c))[:, None]*design, axis=0)
    full_if = wt*(r-eta_t)-wc*(r-eta_c)-beta_if@m_beta-gamma_if@m_gamma
    return {"library_se": estimate.att_gt.iloc[0].se, "reference_full_MLE_OLS_influence_se": np.sqrt(np.sum(full_if**2))/n, "weighted_control_residual_mean": eta_c, "raw_score_vs_full_influence_max_abs": np.max(np.abs(local.influence_score.to_numpy()-full_if)), "reference": "DRDID R/drdid_panel.R lines 140-190; normalized weights; ridge=0"}


def did_aggregate_weight_influence():
    periods = pd.period_range("2020-01", periods=4, freq="M")
    rows = []
    for i in range(90):
        cohort, tau = (1, 2.0) if i < 30 else (2, 10.0) if i < 60 else (100, 0.0)
        for t, time in enumerate(periods):
            active = int(t >= cohort)
            rows.append({"id": i, "time": time, "d": active, "y": 10.0+t+tau*active})
    data = PanelDataDID(df=pd.DataFrame(rows), y="y", unit_col="id", time_col="time", treated_time="d", covariates=[])
    estimate = CallawaySantAnnaDID(control_group="never_treated").fit(data).estimate()
    theta = estimate.att
    # CS population aggregate weights: q_g*m_g / sum(q_h*m_h),
    # q_1=q_2=1/3, m_1=3 and m_2=2. Each cell ATT is deterministic.
    denom = (3.0+2.0)/3.0
    weight_if = np.r_[np.repeat(3*(2-theta)/denom, 30), np.repeat(2*(10-theta)/denom, 30), np.zeros(30)]
    return {"att": theta, "library_aggregate_se": estimate.se, "population_aggregate_weight_influence_se": np.sqrt(np.sum(weight_if**2))/90, "interpretation": "conditional-on-cohort-counts inference differs; official CS population aggregation includes weight estimation influence"}


def did_single_cluster_bootstrap():
    data0 = panel()
    df = data0.df.copy()
    df["cluster"] = "only_cluster"
    data = PanelDataDID(df=df, y="y", unit_col="id", time_col="time", treated_time="d", covariates=[], cluster_col="cluster")
    model = CallawaySantAnnaDID(control_group="never_treated").fit(data)
    try:
        model.estimate()
        analytical = "unexpected success"
    except Exception as exc:
        analytical = f"{type(exc).__name__}: {exc}"
    boot = model.estimate(bootstrap_replications=199, random_state=1)
    return {"analytical": analytical, "bootstrap_se": boot.se, "bootstrap_att": boot.att, "bootstrap_cell_se": boot.att_gt.se.tolist()}


def cuped_reserved_name():
    df = pd.DataFrame({"intercept": np.repeat([0, 1], 20), "y": np.arange(40.0)})
    data = CausalData(df=df, treatment="intercept", outcome="y", confounders=[])
    evidence = {}
    try:
        result = CUPEDModel().fit(data, covariates=[], run_checks=False).estimate()
        evidence["intercept_treatment_unexpected_result"] = result.value
    except Exception as exc:
        evidence["intercept_treatment_fit_failed"] = f"{type(exc).__name__}: {exc}"
    rng = np.random.default_rng(142)
    x = rng.normal(size=100)
    d = np.repeat([0, 1], 50)
    y = 10.0 + 2.0*d + 3.0*x + rng.normal(0, 0.1, size=100)
    df = pd.DataFrame({"x__centered": d, "x": x, "y": y})
    current = CUPEDModel().fit(CausalData(df=df, treatment="x__centered", outcome="y", confounders=["x"]), covariates=["x"], run_checks=False).estimate()
    safe = df.rename(columns={"x__centered": "d"})
    reference = CUPEDModel().fit(CausalData(df=safe, treatment="d", outcome="y", confounders=["x"]), covariates=["x"], run_checks=False).estimate()
    evidence["treatment_x__centered"] = current.value
    evidence["same_data_renamed_d"] = reference.value
    return evidence


def cuped_leverage():
    rng = np.random.default_rng(452)
    n = 200
    d = np.repeat([0.0, 1.0], n//2)
    x = rng.normal(size=n)
    y = rng.normal(size=n)
    evidence = []
    for scale in [1.0, 3e7]:
        xc = scale*(x-x.mean())
        z = np.column_stack([np.ones(n), d, xc, d*xc])
        params = np.linalg.lstsq(z, y, rcond=None)[0]
        current_h, _, _ = leverage_and_cooks(y, z, params)
        correct_h = np.einsum("ij,ji->i", z, np.linalg.pinv(z))
        evidence.append({"scale": scale, "condition": np.linalg.cond(z), "sum_current_h": current_h.sum(), "sum_reference_h": correct_h.sum(), "max_abs_error": np.max(np.abs(current_h-correct_h))})
    return evidence


def scm_refutation_settings():
    from causalis.scenarios.synthetic_control import ASCM
    from causalis.scenarios.synthetic_control.dgp import generate_scm_gamma_26
    from causalis.scenarios.synthetic_control.refutation import placebo_in_space_table, leave_one_donor_out_sensitivity
    data = generate_scm_gamma_26(n_donors=3, n_pre_periods=9, n_post_periods=3, seed=241)
    kwargs = {"lambda_aug": 1000000.0, "compute_average_att_ttest": False}
    estimate = ASCM(**kwargs).fit(data).estimate()
    placebo_default = placebo_in_space_table(estimate, data)
    placebo_same = placebo_in_space_table(estimate, data, model_kwargs=kwargs)
    loo_default = leave_one_donor_out_sensitivity(estimate, data)
    loo_same = leave_one_donor_out_sensitivity(estimate, data, model_kwargs=kwargs)
    actual_default = placebo_default.loc[placebo_default.is_actual_treated, "average_post_gap"].iloc[0]
    actual_same = placebo_same.loc[placebo_same.is_actual_treated, "average_post_gap"].iloc[0]
    return {"original_post_gap": estimate.effect_by_time.mean(), "placebo_actual_row_defaults": actual_default, "placebo_actual_row_matching_config": actual_same, "loo_default": loo_default.to_dict("records"), "loo_matching_config": loo_same.to_dict("records")}


def iv_fit_and_diagnostics():
    from sklearn.linear_model import LinearRegression, LogisticRegression
    from causalis.data_contracts import IVCausalData
    from causalis.scenarios.iv import IIVM
    from causalis.scenarios.iv.refutation import first_stage
    rng = np.random.default_rng(565)
    n = 300
    z = rng.binomial(1, 0.5, n)
    d = rng.binomial(1, 0.1 + 0.7*z, n)
    y = 2.0*d + rng.normal(size=n)
    data = IVCausalData(df=pd.DataFrame({"z": z, "d": d, "y": y}), treatment="d", outcome="y", instruments=["z"], confounders=[])
    model = IIVM(ml_g=LinearRegression(), ml_m=LogisticRegression(), ml_r=LogisticRegression(), n_folds=2, random_state=1).fit(data)
    result = model.estimate()
    try:
        first_stage(model)
        diagnostic_model_status = "accepted"
    except Exception as exc:
        diagnostic_model_status = f"{type(exc).__name__}: {exc}"
    return {"late": result.value, "first_stage_result_works": first_stage(result).shape, "first_stage_model": diagnostic_model_status}


if __name__ == "__main__":
    print(json.dumps({"numpy": np.__version__, "pandas": pd.__version__}))
    for name, fn in [("newcombe", proportions), ("did_ipw_translation", did_shift), ("did_pre_controls", did_pre_controls), ("did_dr_mle_influence", did_dr_mle_influence), ("did_aggregate_weight_influence", did_aggregate_weight_influence), ("did_single_cluster_bootstrap", did_single_cluster_bootstrap), ("cuped_name_collision", cuped_reserved_name), ("cuped_leverage_scaling", cuped_leverage), ("iv_fit_diagnostics", iv_fit_and_diagnostics), ("scm_refutation_settings", scm_refutation_settings)]:
        run(name, fn)
