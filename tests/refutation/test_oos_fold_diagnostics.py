"""Fold stability is descriptive; reused cross-fit scores do not give OOS p-values."""

import numpy as np
import pytest

from causalis.scenarios.unconfoundedness.refutation.score.score_validation import (
    _oos_moment_test_from_psi,
)
from causalis.scenarios.multi_unconfoundedness.refutation.score.score_validation import (
    _compute_psi_from_nuisances,
    _oos_moment_test,
)


def _diagnose(kind, b, folds, a=None):
    if kind == "binary":
        return _oos_moment_test_from_psi(
            psi_a=-np.ones_like(b) if a is None else a, psi_b=b, folds=folds,
        )
    out = _oos_moment_test(
        psi_b=np.column_stack([b, 2 * b]), folds=folds,
        comparison_labels=["first", "second"],
        **({} if a is None else {"psi_a": np.column_stack([a, a])}),
    )
    first = out["by_comparison"].iloc[0].to_dict()
    first.update(
        available=out["available"], inference_status=out["inference_status"],
        reason=out["reason"], fold_table=out["fold_table"].query("comparison == 'first'"),
    )
    return first


@pytest.mark.parametrize("kind", ["binary", "multi"])
@pytest.mark.parametrize("jitter", [False, True])
def test_large_equal_fold_differences_are_visible_without_spurious_inference(kind, jitter):
    b = np.repeat([0., 100., 200., 300.], 2)
    if jitter:
        b += np.tile([-1., 1.], 4)
    out = _diagnose(kind, b, np.repeat(np.arange(4), 2))
    assert out["available"] is False
    assert out["inference_status"] == "unavailable"
    assert "cross-fitted" in out["reason"]
    for key in ["oos_tstat_fold", "oos_tstat_strict", "p_value_fold", "p_value_strict"]:
        assert np.isnan(out[key])
    assert bool(out["fold_diagnostics_available"])
    np.testing.assert_allclose(out["fold_table"]["psi_mean"], [-200., -200 / 3, 200 / 3, 200.])
    np.testing.assert_allclose(out["fold_table"]["theta_fold"], [0., 100., 200., 300.])
    np.testing.assert_allclose(out["fold_table"]["theta_gap"], [-200., -200 / 3, 200 / 3, 200.])
    assert out["fold_score_mean_rms"] == pytest.approx(np.sqrt(200**2 * 5 / 9))
    assert out["fold_score_mean_max_abs"] == pytest.approx(200.)
    assert out["fold_theta_range"] == pytest.approx(300.)
    assert out["fold_theta_gap_max_abs"] == pytest.approx(200.)


@pytest.mark.parametrize("kind", ["binary", "multi"])
def test_identical_constant_folds_have_zero_stability_metrics_and_no_pvalue(kind):
    out = _diagnose(kind, np.full(9, 7.), np.repeat(np.arange(3), 3))
    assert bool(out["fold_diagnostics_available"])
    for key in ["fold_score_mean_rms", "fold_score_mean_max_abs", "fold_theta_range", "fold_theta_gap_max_abs"]:
        assert out[key] == 0.
    assert np.isnan(out["p_value_fold"])


@pytest.mark.parametrize("kind", ["binary", "multi"])
def test_unequal_folds_use_sample_weighted_rms_and_keep_raw_effect_scale(kind):
    b = np.repeat([0., 10., 20.], [2, 3, 4])
    out = _diagnose(kind, b, np.repeat(np.arange(3), [2, 3, 4]))
    expected_means = np.array([-110 / 7, -10 / 3, 14.])
    np.testing.assert_allclose(out["fold_table"]["psi_mean"], expected_means)
    assert out["fold_score_mean_rms"] == pytest.approx(np.sqrt((2 * (110 / 7)**2 + 3 * (10 / 3)**2 + 4 * 14**2) / 9))
    assert out["fold_theta_range"] == 20.
    assert np.isnan(out["p_value_strict"])


@pytest.mark.parametrize("kind", ["binary", "multi"])
@pytest.mark.parametrize("case", ["single_fold", "zero_train_jacobian", "nonfinite"])
def test_unavailable_fold_inputs_do_not_report_partial_stability_as_complete(kind, case):
    b = np.arange(6, dtype=float)
    folds = np.repeat([0, 1], 3)
    a = -np.ones(6)
    if case == "single_fold":
        folds[:] = 0
    elif case == "zero_train_jacobian":
        a[3:] = 0
    else:
        b[2] = np.nan
    out = _diagnose(kind, b, folds, a)
    assert not out["available"]
    assert not out["fold_diagnostics_available"]
    assert np.isnan(out["fold_score_mean_rms"])
    assert np.isnan(out["fold_theta_range"])


@pytest.mark.parametrize("kind", ["binary", "multi"])
def test_ratio_fold_effects_use_jacobians_instead_of_signal_means(kind):
    # Three equal-size folds, with treated shares 1/3, 2/3, 1/3.
    d = np.array([1., 0., 0., 1., 1., 0., 1., 0., 0.])
    a = -d / np.mean(d)
    b = -a * np.repeat([2., 4., 8.], 3)
    out = _diagnose(kind, b, np.repeat(np.arange(3), 3), a)
    np.testing.assert_allclose(out["fold_table"]["theta_fold"], [2., 4., 8.])
    np.testing.assert_allclose(out["fold_table"]["theta_minus_k"], [16 / 3, 5., 10 / 3])
    assert out["fold_theta_range"] == pytest.approx(6.)


def test_multi_atte_score_reconstruction_uses_ratio_influence():
    labels = np.array([0, 1, 2, 0, 1, 2])
    d = np.eye(3)[labels]
    theta = np.array([2., 4.])
    y = np.array([0., 2., 4., 0., 2., 4.])
    psi, psi_b, _, _ = _compute_psi_from_nuisances(
        y=y, d=d, g_hat=np.zeros((6, 3)), m=np.full((6, 3), 1 / 3),
        theta=theta, score="ATTE", normalize_ipw=False,
    )
    np.testing.assert_allclose(psi, 0., atol=1e-14)
    np.testing.assert_allclose(psi_b.mean(axis=0), theta)


@pytest.mark.parametrize("folds", [None, np.arange(5)])
def test_multi_missing_or_misaligned_folds_have_explicit_unavailable_reason(folds):
    out = _oos_moment_test(
        psi_b=np.zeros((6, 2)), folds=folds, comparison_labels=["first", "second"],
    )
    assert out["fold_table"].empty
    assert not out["fold_diagnostics_available"]
    assert not out["available"]
    assert out["by_comparison"]["fold_diagnostics_reason"].str.contains("required").all()
