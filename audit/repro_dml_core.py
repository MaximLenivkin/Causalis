"""Focused audit reproductions. Run with repo-local .venv, no source changes.

Each case demonstrates a discrepancy against an independent estimand/formula,
not a test that simply repeats implementation. Prints compact JSON evidence.
"""
from __future__ import annotations

import json
import warnings
from types import SimpleNamespace

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression

from causalis.dgp.causaldata import CausalData
from causalis.data_contracts.multicausaldata import MultiCausalData
from causalis.scenarios.unconfoundedness.model import IRM
from causalis.scenarios.multi_unconfoundedness.model import MultiTreatmentIRM
from causalis.scenarios.gate.model import _GatePartition, _estimate_gate_groupwise_summary_from_partition
from causalis.scenarios.unconfoundedness.refutation.unconfoundedness import unconfoundedness_validation as balance_binary
from causalis.scenarios.multi_unconfoundedness.refutation.unconfoundedness import unconfoundedness_validation as balance_multi
from causalis.scenarios.unconfoundedness.refutation.score.score_validation import _oos_moment_test_from_psi
from causalis.scenarios.multi_unconfoundedness.refutation.score.score_validation import _oos_moment_test
from causalis.scenarios.unconfoundedness.refutation.unconfoundedness.sensitivity import compute_bias_aware_ci, compute_irm_sensitivity_elements
from causalis.scenarios.multi_unconfoundedness.refutation.unconfoundedness.sensitivity import sensitivity_benchmark


def emit(case, **kwargs):
    print(json.dumps({"case": case, **kwargs}, ensure_ascii=False, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x)))


def binary_data(tau=2.0, n=120):
    d = np.tile([0, 1], n // 2)
    return CausalData(df=pd.DataFrame({"y": 10.0 + tau * d, "d": d, "x": np.linspace(-1, 1, n)}), outcome="y", treatment="d", confounders=["x"])


def constant_models():
    return {"ml_g": DummyRegressor(), "ml_m": DummyClassifier(strategy="prior"), "n_folds": 2, "random_state": 42}


def multi_atte_and_binary_relative():
    n = 300
    labels = np.tile([0, 1, 2], n // 3)
    d = np.eye(3)[labels]
    frame = pd.DataFrame({"y": 10.0 + 2.0 * (labels == 1) + 4.0 * (labels == 2), "x": np.linspace(-1, 1, n), "d0": d[:, 0], "d1": d[:, 1], "d2": d[:, 2]})
    data = MultiCausalData(df=frame, outcome="y", treatment_names=["d0", "d1", "d2"], control_treatment="d0", confounders=["x"])
    model = MultiTreatmentIRM(data=data, **constant_models()).fit()
    result = model.estimate(score="ATTE")
    corrected_if = model.psi_b_ - (d[:, 1:] / d[:, 1:].mean(axis=0)) * model.coef_
    corrected_se = corrected_if.std(axis=0, ddof=1) / np.sqrt(n)
    assert np.allclose(corrected_se, 0)
    assert np.all(model.se_ > 0.1)
    emit("DML-01_multi_ATTE_IF", estimate=result.value, actual_se=model.se_, correct_se=corrected_se)

    model = IRM(data=binary_data(), **constant_models()).fit()
    result = model.estimate(score="ATTE")
    # Constant potential outcomes make the effect and relative effect known in
    # every nondegenerate empirical sample; both correct IFs are exactly zero.
    assert np.isclose(model.se_[0], 0)
    assert model.se_relative_[0] > 1
    emit("DML-02_binary_relative_ATT", relative=result.value_relative, actual_relative_se=model.se_relative_[0], correct_relative_se=0.0)


def stale_cate():
    model = IRM(data=binary_data(2), **constant_models()).fit()
    first = model.predict_cate(pd.DataFrame({"x": [0.1]}))[0]
    model.fit(binary_data(7))
    stale = model.predict_cate(pd.DataFrame({"x": [0.1]}))[0]
    fresh = IRM(data=binary_data(7), **constant_models()).fit().predict_cate(pd.DataFrame({"x": [0.1]}))[0]
    assert stale == first == 2 and fresh == 7
    emit("DML-03_stale_CATE_after_refit", before_refit=first, after_refit=stale, fresh_expected=fresh)
    model = IRM(data=binary_data(2), **constant_models()).fit()
    model.estimate()
    model.fit(binary_data(7))
    model.sensitivity_analysis(r2_y=0.1, r2_d=0.1)
    stale_theta = model.sensitivity_result["theta"]
    new_theta = model.estimate().value
    assert stale_theta == 2 and new_theta == 7
    emit("DML-03_stale_estimate_after_refit", sensitivity_theta=stale_theta, new_sample_theta=new_theta)


class FeaturePropensity(ClassifierMixin, BaseEstimator):
    def fit(self, X, y):
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X):
        p = np.where(np.asarray(X)[:, 0] < -0.5, 0.001, np.where(np.asarray(X)[:, 0] > 0.5, 0.999, 0.5))
        return np.column_stack([1 - p, p])


def drop_weight_alignment():
    data = binary_data()
    model = IRM(data=data, ml_g=DummyRegressor(), ml_m=FeaturePropensity(), n_folds=2, random_state=42, weights=np.ones(len(data.df)), overlap_policy="drop", overlap_threshold=0.1).fit()
    try:
        model.estimate()
    except ValueError as exc:
        assert "weights" in str(exc) and "shape" in str(exc)
        emit("DML-04_drop_weights", retained=len(model._y), original=len(data.df), error=str(exc))
    else:
        raise AssertionError("Expected retained/original weight length mismatch")


def infinite_balance():
    d = np.tile([0, 1], 20).astype(float)
    binary = balance_binary._balance_smd(balance_binary._BalanceInputs(x=d[:, None], d=d, m_hat=np.full(len(d), 0.5), w_bar=None, names=["x"], score="ATE", normalize=False), threshold=0.1)
    multi = balance_multi._balance_smd(balance_multi._BalanceInputs(x=d[:, None], d=np.column_stack([1-d, d]), m_hat=np.full((len(d), 2), 0.5), feature_names=["x"], treatment_names=["d0", "d1"], score="ATE", normalize=False), threshold=0.1)
    assert np.isinf(binary["smd_weighted"][0]) and binary["pass"]
    assert np.isinf(multi["smd"].iloc[0, 0]) and multi["pass"]
    emit("DML-05_infinite_balance_PASS", binary_smd=binary["smd_weighted"], binary_pass=binary["pass"], multi_smd=multi["smd"].to_numpy(), multi_pass=multi["pass"])


def tautological_oos():
    # Every fold has radically different score mean: 0, 100, 200, 300.
    folds = np.repeat(np.arange(4), 10)
    b = np.repeat([0, 100, 200, 300], 10) + np.tile(np.arange(10), 4)
    binary = _oos_moment_test_from_psi(psi_a=-np.ones(40), psi_b=b, folds=folds)
    multi = _oos_moment_test(psi_b=b[:, None], folds=folds, comparison_labels=["d1 vs d0"])
    assert abs(binary["oos_tstat_fold"]) < 1e-10
    assert np.isclose(binary["p_value_strict"], 1)
    emit("DML-06_OOS_p1_by_identity", fold_means=binary["fold_table"]["psi_mean"].to_numpy(), binary_t=binary["oos_tstat_fold"], binary_p=binary["p_value_fold"], multi_p=multi["by_comparison"]["p_value_fold"].to_numpy())


def negative_nu2():
    data = binary_data()
    # Outcome nuisance slightly misspecified, propensity grossly misspecified.
    data.df["y"] += np.sin(np.arange(len(data.df)))
    model = IRM(data=data, ml_g=DummyRegressor(), ml_m=DummyClassifier(strategy="constant", constant=0), n_folds=2, random_state=42).fit()
    estimate = model.estimate()
    result = compute_bias_aware_ci(estimate, r2_y=0.5, r2_d=0.5)
    assert estimate.diagnostic_data.nu2 < 0
    assert result["bound_width"] == 0
    emit("DML-07_negative_nu2_silenced", nu2=estimate.diagnostic_data.nu2, sensitivity_bound_width=result["bound_width"], CI_equals_sampling=bool(np.allclose(result["bias_aware_ci"], result["sampling_ci"])))


class DummySensitivityModel:
    def __init__(self):
        n = 100
        self.coef_ = np.array([1.0])
        psi = np.tile([-1.0, 1.0], n // 2)
        self.se_ = np.array([np.std(psi, ddof=1) / np.sqrt(n)])
        self.elems = {"sigma2": 1.0, "nu2": 1.0, "psi": psi, "psi_sigma2": psi, "psi_nu2": psi, "riesz_rep": np.ones(n), "m_alpha": 1 + 0.5*psi}

    def _sensitivity_element_est(self):
        return self.elems


def wrong_rva():
    model = DummySensitivityModel()
    result = compute_bias_aware_ci(model, r2_y=0.1, r2_d=0.1)
    claimed = result["rva"]
    at_claimed = compute_bias_aware_ci(model, r2_y=claimed, r2_d=claimed)
    # The lower confidence bound must cross H0 at the critical reported Rva.
    assert abs(at_claimed["bias_aware_ci"][0]) > 0.1
    emit("DML-08_RVa_not_CI_threshold", reported_rva=claimed, lower_CI_at_reported_rva=at_claimed["bias_aware_ci"][0], H0=0)


def gate_cancellation():
    phi = 1e8 + np.tile([-1.0, 1.0], 50)
    d = np.tile([0, 1], 50)
    partition = _GatePartition(group_names=["all"], codes=np.zeros(100, dtype=int))
    correct_se_hc0 = np.sqrt(np.sum((phi-phi.mean())**2)) / len(phi)
    try:
        result = _estimate_gate_groupwise_summary_from_partition(phi=phi, d=d, m_hat=np.full(len(phi), 0.5), partition=partition, cov_type="HC0", alpha=0.05)
        actual = result["std_errors"][0]
        assert not np.isclose(actual, correct_se_hc0)
        emit("DML-09_Gate_cancellation", actual_se=actual, correct_se=correct_se_hc0)
    except RuntimeError as exc:
        emit("DML-09_Gate_cancellation", error=str(exc), correct_se=correct_se_hc0)


def multi_benchmark_strength():
    rng = np.random.default_rng(2026)
    labels = np.concatenate([np.repeat([0, 1, 2], [1600, 200, 200]), np.repeat([0, 1, 2], [200, 1600, 200])])
    z = np.repeat([-1.0, 1.0], 2000)
    nuisance = rng.normal(size=len(labels))
    y = 10 + 5*z + np.take([0, 2, 4], labels) + rng.normal(size=len(labels))
    d = np.eye(3)[labels]
    frame = pd.DataFrame({"y": y, "z": z, "nuisance": nuisance, "d0": d[:, 0], "d1": d[:, 1], "d2": d[:, 2]})
    data = MultiCausalData(df=frame, outcome="y", treatment_names=["d0", "d1", "d2"], control_treatment="d0", confounders=["z", "nuisance"])
    model = MultiTreatmentIRM(data=data, ml_g=LinearRegression(), ml_m=LogisticRegression(C=1e6, max_iter=1000), n_folds=2, random_state=42).fit()
    model.estimate()
    benchmark = sensitivity_benchmark(model, benchmarking_set=["z"])
    assert benchmark["r2_y"].max() < 0.001
    assert benchmark["delta"].abs().max() > 3
    emit("DML-10_benchmark_long_residuals", r2_y=benchmark["r2_y"].to_numpy(), r2_d=benchmark["r2_d"].to_numpy(), effect_shift=benchmark["delta"].to_numpy())


def atte_sensitivity_nonorthogonality():
    # Empirical design exactly matches P(D=1)=m0=0.2, so Monte Carlo noise is
    # absent. The true representer norm is 1/[p*(1-p)] = 6.25.
    d = np.tile([0, 0, 0, 0, 1], 200).astype(float)
    p = d.mean()
    y = np.ones(len(d))
    w = d/p
    h = 1e-5

    def elements(mvalue):
        m = np.full(len(d), mvalue)
        return compute_irm_sensitivity_elements(model=None, y=y, d=d, g0=np.zeros(len(d)), g1=np.zeros(len(d)), m_hat=m, w=w, w_bar=m/p, psi=np.zeros(len(d)), score="ATTE")

    def canonical_nu2(mvalue):
        m = np.full(len(d), mvalue)
        rr = (m/p)*(d/m - (1-d)/(1-m))
        m_alpha = w*(m/p)*(1/m + 1/(1-m))
        return np.mean(2*m_alpha - rr**2)

    actual_derivative = (elements(p+h)["nu2"] - elements(p-h)["nu2"])/(2*h)
    canonical_derivative = (canonical_nu2(p+h) - canonical_nu2(p-h))/(2*h)
    assert np.isclose(actual_derivative, 62.5, rtol=1e-6)
    assert abs(canonical_derivative) < 1e-5
    emit("DML-11_ATTE_sensitivity_nuisance_derivative", actual_derivative=actual_derivative, correct_orthogonal_derivative=canonical_derivative)


if __name__ == "__main__":
    warnings.simplefilter("ignore", RuntimeWarning)
    for case in [multi_atte_and_binary_relative, stale_cate, drop_weight_alignment, infinite_balance, tautological_oos, negative_nu2, wrong_rva, gate_cancellation, multi_benchmark_strength, atte_sensitivity_nonorthogonality]:
        try:
            case()
        except Exception as exc:
            emit("REPRO_FAILED", function=case.__name__, error=repr(exc))
            raise
