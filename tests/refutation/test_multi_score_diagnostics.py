import numpy as np
import pandas as pd
import pytest

from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LogisticRegression

from causalis.data_contracts.multicausaldata import MultiCausalData
from causalis.scenarios.multi_unconfoundedness.model import MultiTreatmentIRM
from causalis.scenarios.multi_unconfoundedness.refutation.score.score_validation import run_score_diagnostics


def _make_multi_causal_data(n: int = 180, seed: int = 42) -> MultiCausalData:
    rng = np.random.default_rng(seed)
    x1 = rng.normal(0.0, 1.0, size=n)
    x2 = rng.normal(0.0, 1.0, size=n)

    labels = np.tile(np.array([0, 1, 2], dtype=int), int(np.ceil(n / 3)))[:n]
    rng.shuffle(labels)
    d = np.eye(3, dtype=int)[labels]

    effects = np.array([0.0, -0.5, 0.8], dtype=float)
    y = 1.0 + 0.8 * x1 - 0.4 * x2 + effects[labels] + rng.normal(0.0, 0.1, size=n)

    df = pd.DataFrame(
        {
            "y": y,
            "x1": x1,
            "x2": x2,
            "d_0": d[:, 0],
            "d_1": d[:, 1],
            "d_2": d[:, 2],
        }
    )

    return MultiCausalData(
        df=df,
        outcome="y",
        treatment_names=["d_0", "d_1", "d_2"],
        confounders=["x1", "x2"],
        control_treatment="d_0",
    )


def _make_estimate(
    data: MultiCausalData,
    *,
    normalize_ipw: bool = False,
    score: str = "ATE",
):
    model = MultiTreatmentIRM(
        data=data,
        ml_g=DummyRegressor(strategy="mean"),
        ml_m=LogisticRegression(max_iter=1000),
        normalize_ipw=normalize_ipw,
        n_folds=3,
        random_state=1,
    ).fit()
    return model.estimate(score=score, diagnostic_data=True)


def test_multi_score_diagnostics_runs_and_returns_long_summary():
    data = _make_multi_causal_data(seed=17)
    estimate = _make_estimate(data)

    report = run_score_diagnostics(data, estimate, return_summary=True)

    assert "summary" in report
    summary = report["summary"]
    assert list(summary.columns) == ["comparison", "metric", "value", "flag"]
    assert {"d_1 vs d_0", "d_2 vs d_0"}.issubset(set(summary["comparison"]))
    assert {"se_plugin", "max_|t|", "oos_tstat_fold", "oos_tstat_strict"}.issubset(
        set(summary["metric"])
    )


def test_multi_score_diagnostics_exposes_core_blocks():
    data = _make_multi_causal_data(seed=33)
    estimate = _make_estimate(data)

    report = run_score_diagnostics(data, estimate, return_summary=True)

    assert "orthogonality_derivatives" in report
    assert "influence_diagnostics" in report
    assert "oos_moment_test" in report
    assert "flags" in report
    assert "flags_by_comparison" in report
    assert report["params"]["score"] == "ATE"


def test_multi_score_refutation_namespace_exposes_runner():
    import causalis.scenarios.multi_unconfoundedness.refutation as ref

    assert hasattr(ref, "run_score_diagnostics")


def test_multi_score_diagnostics_warns_and_disables_hajek_for_orthogonality():
    data = _make_multi_causal_data(seed=71)
    estimate = _make_estimate(data, normalize_ipw=True)

    with pytest.warns(RuntimeWarning, match="normalize_ipw=False"):
        report = run_score_diagnostics(data, estimate, return_summary=True)

    assert report["params"]["normalize_ipw"] is True
    assert report["params"]["orthogonality_normalize_ipw"] is False
    assert report["meta"]["orthogonality_derivatives_use_score_normalization"] is False


def test_multi_score_diagnostics_support_atte_estimates():
    data = _make_multi_causal_data(seed=91)
    estimate = _make_estimate(data, score="ATTE")

    report = run_score_diagnostics(data, estimate, return_summary=True)

    assert report["params"]["score"] == "ATTE"
    assert report["params"]["normalize_ipw"] is False
    assert report["params"]["orthogonality_normalize_ipw"] is False
    assert list(report["summary"].columns) == ["comparison", "metric", "value", "flag"]
    assert {"d_1 vs d_0", "d_2 vs d_0"}.issubset(set(report["summary"]["comparison"]))
    assert np.allclose(report["orthogonality_derivatives"]["d_gk"].to_numpy(dtype=float), 0.0)
    assert np.allclose(report["orthogonality_derivatives"]["t_gk"].to_numpy(dtype=float), 0.0)


@pytest.mark.parametrize("cached", ["present", "missing", "invalid_shape", "invalid_1d"])
def test_multi_atte_fold_solutions_preserve_or_reconstruct_ratio_jacobian(cached):
    data = _make_multi_causal_data(seed=104)
    estimate = _make_estimate(data, score="ATTE")
    diag = estimate.diagnostic_data
    d = np.asarray(diag.d, dtype=float)
    psi_b = np.asarray(diag.psi_b, dtype=float)
    pk = d[:, 1:].mean(axis=0)
    jacobian = -d[:, 1:] / pk
    # A provided scaled Jacobian must be honored; legacy payloads reconstruct
    # the treated-share ratio Jacobian rather than treating ATTE as ATE.
    if cached == "present":
        payload_jacobian = 2 * jacobian
    elif cached == "missing":
        payload_jacobian = None
    elif cached == "invalid_1d":
        payload_jacobian = -np.ones(len(d))
    else:
        payload_jacobian = np.ones(2)
    estimate.diagnostic_data = diag.model_copy(update={"psi_a": payload_jacobian})
    report = run_score_diagnostics(data, estimate)
    assert report["meta"]["used_estimator_psi_a"] is (cached == "present")
    assert report["flags"]["oos_moment"] == "NA"
    assert not report["oos_moment_test"]["available"]
    for row in report["oos_moment_test"]["fold_table"].to_dict("records"):
        j = 0 if row["comparison"] == "d_1 vs d_0" else 1
        mask = np.asarray(diag.folds) == row["fold"]
        expected = pk[j] * np.sum(psi_b[mask, j]) / np.sum(d[mask, j + 1])
        if cached == "present":
            expected /= 2
        assert row["theta_fold"] == pytest.approx(expected)


def test_multi_score_finite_filter_also_filters_cached_jacobian_rows():
    data = _make_multi_causal_data(seed=106)
    estimate = _make_estimate(data, score="ATTE")
    diag = estimate.diagnostic_data
    d = np.asarray(diag.d, dtype=float)
    a = -d[:, 1:] / d[:, 1:].mean(axis=0)
    a[0, 0] = np.nan
    estimate.diagnostic_data = diag.model_copy(update={"psi_a": a})
    report = run_score_diagnostics(data, estimate)
    assert report["meta"]["n"] == len(d) - 1
    assert report["meta"]["used_estimator_psi_a"] is True
    counts = report["oos_moment_test"]["fold_table"].groupby("comparison")["n"].sum()
    assert (counts == len(d) - 1).all()


@pytest.mark.parametrize("has_jacobian", [False, True])
def test_legacy_inconsistent_atte_cached_score_is_reconstructed_with_provenance(has_jacobian):
    data = _make_multi_causal_data(seed=107)
    estimate = _make_estimate(data, score="ATTE")
    diag = estimate.diagnostic_data
    d = np.asarray(diag.d, dtype=float)
    a = -d[:, 1:] / d[:, 1:].mean(axis=0)
    b = np.asarray(diag.psi_b)
    theta = np.asarray(estimate.value)
    # Old caches centered a ratio numerator as though its Jacobian were -1.
    old_cached_score = b - theta
    expected = b + a * theta
    estimate.diagnostic_data = diag.model_copy(update={
        "psi_a": a if has_jacobian else None,
        "psi": old_cached_score,
    })
    report = run_score_diagnostics(data, estimate)
    assert report["meta"]["used_estimator_psi"] is False
    assert report["meta"]["psi_cache_status"] == "inconsistent_atte_score"
    np.testing.assert_allclose(
        report["influence_diagnostics"]["by_comparison"]["se_plugin"],
        np.std(expected, axis=0, ddof=1) / np.sqrt(len(d)),
    )


def test_consistent_atte_cached_score_keeps_estimator_provenance():
    data = _make_multi_causal_data(seed=109)
    estimate = _make_estimate(data, score="ATTE")
    diag = estimate.diagnostic_data
    d = np.asarray(diag.d, dtype=float)
    a = -d[:, 1:] / d[:, 1:].mean(axis=0)
    psi = np.asarray(diag.psi_b) + a * np.asarray(estimate.value)
    estimate.diagnostic_data = diag.model_copy(update={"psi_a": a, "psi": psi})
    report = run_score_diagnostics(data, estimate)
    assert report["meta"]["used_estimator_psi"] is True
    assert report["meta"]["used_estimator_psi_a"] is True
    assert report["meta"]["psi_cache_status"] == "used"
