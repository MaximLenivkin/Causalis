"""Analytic, vertex-enumeration and actual CSA references for trend projection."""
from dataclasses import FrozenInstanceError
from itertools import combinations, product
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from causalis.data_contracts import PanelDataDID
from causalis.scenarios.did import CallawaySantAnnaDID, HonestDiD


@pytest.mark.parametrize("restriction", ["smoothness", "relative_magnitude"])
@pytest.mark.parametrize("bound", [0., .2, 2.])
@pytest.mark.parametrize("weights", [[1., 0.], [.4, .6], [1., -1.], [-2., .5]])
@pytest.mark.parametrize("scale", [1e-80, 1., 1e80])
def test_one_pre_period_analytic_projection(restriction, bound, weights, scale):
    beta = np.array([.3, 2., 3.])*scale
    se = np.array([.1, .2, .15])*scale
    weights = np.array(weights)
    actual_bound = bound*scale if restriction == "smoothness" else bound
    result = HonestDiD(beta, np.diag(se**2), [-2, 0, 1]).infer(
        restriction=restriction, bound=actual_bound, post_weights=weights)
    q = norm.isf(.05/6)
    center = weights @ beta[1:]
    radius = q * (np.abs(weights) @ se[1:])
    if restriction == "smoothness":
        slope_weight = weights @ [1., 2.]
        center += slope_weight*beta[0]
        radius += abs(slope_weight)*q*se[0]
        radius += actual_bound*(abs(weights[0]+2*weights[1])+abs(weights[1]))
    else:
        largest = abs(beta[0])+q*se[0]
        radius += bound*largest*(abs(weights.sum())+abs(weights[1]))
    np.testing.assert_allclose(result.confidence_set[0], [center-radius, center+radius], rtol=2e-12)
    assert result.contains(result.confidence_set[0][0])
    assert result.contains(result.confidence_set[0][1])


def _vertex_oracle(beta, se, bound, weights):
    """Enumerate intersections of independently written inequalities; no LP solver."""
    q = norm.isf(.05/(2*len(beta)))
    # Variables are delta_-3, delta_-2, delta_0, delta_1; omitted delta_-1=0.
    restrictions = np.array([[1., -2., 0., 0.], [0., 1., 1., 0.],
                             [0., 0., -2., 1.]])
    a = np.vstack([restrictions, -restrictions, np.eye(4)[:2], -np.eye(4)[:2]])
    b = np.r_[np.full(6, bound), beta[:2]+q*se[:2], -beta[:2]+q*se[:2]]
    vertices = []
    for selected in combinations(range(len(b)), 4):
        mat = a[list(selected)]
        if np.linalg.matrix_rank(mat) != 4:
            continue
        point = np.linalg.solve(mat, b[list(selected)])
        if np.all(a @ point <= b+1e-10):
            vertices.append(weights @ point[2:])
    if not vertices:
        return ()
    center = weights @ beta[2:]
    radius = q*(np.abs(weights) @ se[2:])
    return ((center-radius-max(vertices), center+radius-min(vertices)),)


@pytest.mark.parametrize("beta", [[.6, .3, 2., 3.], [-1., .2, 1., -2.], [0., 0., 1., 2.]])
@pytest.mark.parametrize("bound", [0., .1, 1.])
@pytest.mark.parametrize("weights", [[1., 0.], [.5, .5], [-1., 2.]])
def test_two_pre_smoothness_matches_independent_vertex_enumeration(beta, bound, weights):
    beta, weights = np.asarray(beta), np.asarray(weights)
    se = np.array([.1, .05, .2, .15])
    expected = _vertex_oracle(beta, se, bound, weights)
    result = HonestDiD(beta, np.diag(se**2), [-3, -2, 0, 1]).infer(
        restriction="smoothness", bound=bound, post_weights=weights)
    if expected:
        np.testing.assert_allclose(result.confidence_set, expected, atol=1e-11)
    else:
        assert result.confidence_set == () and result.set_type == "empty"
        assert not result.contains(0.)


@pytest.mark.parametrize("weights", [[1., 0., 0.], [1., -2., .5], [-.2, .3, .7]])
@pytest.mark.parametrize("bound", [0., .5, 2.])
def test_relative_magnitudes_all_pre_slopes_and_signed_post_contrast(weights, bound):
    beta = np.array([-.9, .7, .3, 2., 3., 1.])
    se = np.array([.1, .2, .05, .15, .1, .3])
    q = norm.isf(.05/12)
    maximum = max(max(abs(np.diff(np.r_[corner, 0.])))
                  for corner in product(*zip(beta[:3]-q*se[:3], beta[:3]+q*se[:3])))
    post_biases = [np.asarray(weights) @ np.cumsum(slopes)
                   for slopes in product([-bound*maximum, bound*maximum], repeat=3)]
    center = np.asarray(weights) @ beta[3:]
    width = q*(np.abs(weights) @ se[3:])
    result = HonestDiD(beta, np.diag(se**2), [-4, -3, -2, 0, 1, 2]).infer(
        restriction="relative_magnitude", bound=bound, post_weights=weights)
    np.testing.assert_allclose(result.confidence_set[0],
                               [center-width-max(post_biases), center+width-min(post_biases)])


def test_m_zero_smoothness_extrapolates_linear_trend_relative_magnitude_does_not():
    inference = HonestDiD([2., 3.], np.eye(2)*.01, [-2, 0])
    smooth = inference.infer(restriction="smoothness", bound=0.)
    relative = inference.infer(restriction="relative_magnitude", bound=0.)
    assert np.mean(smooth.confidence_set[0]) == pytest.approx(5.)
    assert np.mean(relative.confidence_set[0]) == pytest.approx(3.)


@pytest.mark.parametrize("restriction", ["smoothness", "relative_magnitude"])
def test_bounds_are_nested_with_prespecified_same_rectangle(restriction):
    inference = HonestDiD([.6, .3, 2., 3.], np.eye(4)*.01, [-3, -2, 0, 1])
    intervals = [inference.infer(restriction=restriction, bound=m).confidence_set[0]
                 for m in [0., .1, .5, 1., 2.]]
    assert all(b[0] <= a[0]+1e-12 and b[1] >= a[1]-1e-12 for a, b in zip(intervals, intervals[1:]))


def _panel(missing=False, staggered=False):
    rng = np.random.default_rng(1409)
    times = pd.period_range("2020-01", periods=6, freq="M")
    rows = []
    for unit in range(40):
        cohort = 3 if unit < 20 else (4 if staggered and unit < 30 else 99)
        slope = rng.normal(.1, .2)
        for t, time in enumerate(times):
            if missing and unit == 0 and t == 1:
                continue
            treated = t >= cohort
            rows.append(dict(unit=unit, time=time, d=int(treated),
                             y=unit+slope*t+2.*treated+rng.normal(scale=.2)))
    return PanelDataDID(df=pd.DataFrame(rows), y="y", unit_col="unit", time_col="time", treated_time="d")


def _result(**kwargs):
    return CallawaySantAnnaDID(control_group="never_treated", base_period="universal",
                              include_pre_periods=True, bootstrap_replications=0,
                              **kwargs).fit(_panel()).estimate()


def test_actual_csa_adapter_owns_inputs_matches_iid_covariance_and_never_calls_model():
    source = _result()
    cells = source.att_gt.sort_values("event_time")
    raw = source.diagnostics["influence_scores"].loc[:, cells.cell_id].to_numpy()
    centered = raw-raw.mean(axis=0)
    cov = centered.T @ centered/len(raw)**2
    generic = HonestDiD(cells.att.to_numpy(), cov, cells.event_time)
    rng_before = np.random.get_state()
    with patch.object(CallawaySantAnnaDID, "fit", side_effect=AssertionError("fit")), \
            patch.object(CallawaySantAnnaDID, "estimate", side_effect=AssertionError("estimate")):
        snapshot = HonestDiD.from_did(source)
    after = np.random.get_state()
    np.testing.assert_array_equal(rng_before[1], after[1])
    assert rng_before[2:] == after[2:]
    for restriction in ["smoothness", "relative_magnitude"]:
        assert snapshot.infer(restriction=restriction, bound=.2) == generic.infer(restriction=restriction, bound=.2)
    np.testing.assert_allclose(np.sqrt(np.diag(cov)), cells.se)
    expected = snapshot.infer(restriction="relative_magnitude", bound=1.)
    source.att_gt.loc[:, "att"] = 999.
    source.diagnostics["influence_scores"].iloc[:, :] = 0.
    assert snapshot.infer(restriction="relative_magnitude", bound=1.) == expected


@pytest.mark.parametrize("change", ["varying", "anticipation", "controls", "cluster", "no_pre",
                                    "no_diag", "duplicate_ids", "duplicate_columns", "missing_columns",
                                    "missing_membership", "changed_membership", "nonbinary", "nan_score",
                                    "complex_score", "mixed_base"])
def test_adapter_rejects_unsupported_or_corrupted_result(change):
    result = _result()
    if change == "varying": result.base_period = "varying"
    elif change == "anticipation": result.anticipation = 1
    elif change == "controls": result.control_group = "not_yet_treated"
    elif change == "cluster": result.cluster_col = "unit"
    elif change == "no_pre": result.include_pre_periods = False
    elif change == "no_diag": result.diagnostics.pop("influence_scores")
    elif change == "duplicate_ids": result.diagnostics["influence_scores"].index = [0]*40
    elif change == "duplicate_columns": result.diagnostics["influence_scores"].columns = [0]*5
    elif change == "missing_columns": result.diagnostics["influence_scores"] = result.diagnostics["influence_scores"].iloc[:, :-1]
    elif change == "missing_membership": result.diagnostics["unit_level"] = result.diagnostics["unit_level"].iloc[1:]
    elif change == "changed_membership": result.diagnostics["unit_level"].loc[0, "is_treated_cohort"] = 0
    elif change == "nonbinary":
        result.diagnostics["unit_level"]["is_treated_cohort"] = result.diagnostics["unit_level"].is_treated_cohort.astype(float)
        result.diagnostics["unit_level"].loc[0, "is_treated_cohort"] = .5
    elif change in ["nan_score", "complex_score"]:
        frame = result.diagnostics["influence_scores"].astype(complex if change == "complex_score" else float)
        frame.iloc[0, 0] = 1j if change == "complex_score" else np.nan
        result.diagnostics["influence_scores"] = frame
    elif change == "mixed_base": result.att_gt.loc[0, "base_time"] = result.att_gt.time.iloc[0]
    with pytest.raises((ValueError, RuntimeError)):
        HonestDiD.from_did(result)


@pytest.mark.parametrize("missing,staggered", [(True, False), (False, True)])
def test_actual_unbalanced_or_staggered_fit_is_rejected(missing, staggered):
    result = CallawaySantAnnaDID(control_group="never_treated", base_period="universal",
                               include_pre_periods=True, bootstrap_replications=0).fit(
                                   _panel(missing, staggered)).estimate()
    with pytest.raises(ValueError):
        HonestDiD.from_did(result)


@pytest.mark.parametrize("times", [[-2, -1, 0], [-4, -2, 0], [-2, 0, 2], [0, 1, 2],
                                   [-4, -3, -2], [-2., 0., 1.], [-2, False, 1], [0, -2, 1]])
def test_time_axis_requires_consecutive_common_reference(times):
    with pytest.raises(ValueError):
        HonestDiD([0., 1., 2.], np.eye(3), times)


@pytest.mark.parametrize("cov", [np.zeros((2, 2)), [[1., 2.], [2., 1.]], [[1., .1], [.2, 1.]],
                                 [[-1., 0.], [0., 1.]], [[1., 0.], [0., 0.]], np.eye(3)])
def test_covariance_contract(cov):
    with pytest.raises(ValueError):
        HonestDiD([0., 1.], cov, [-2, 0])


@pytest.mark.parametrize("field", ["estimates", "covariance", "post_weights"])
@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf, 1j, complex(1, 0)])
def test_real_finite_arrays(field, bad):
    estimates, cov, weights = [0., 1.], np.eye(2).tolist(), [1.]
    if field == "estimates": estimates[0] = bad
    elif field == "covariance": cov[0][0] = bad
    else: weights[0] = bad
    with pytest.raises((ValueError, RuntimeError)):
        HonestDiD(estimates, cov, [-2, 0]).infer(restriction="smoothness", bound=1., post_weights=weights)


@pytest.mark.parametrize("kwargs", [dict(alpha=True), dict(alpha=0.), dict(alpha=1.), dict(alpha=np.nan),
                                   dict(bound=-1.), dict(bound="1"), dict(bound=1j), dict(bound=True),
                                   dict(restriction="FLCI"), dict(post_weights=[0.]), dict(post_weights=[[1.]]),
                                   dict(post_weights=[1., 2.])])
def test_inference_contract(kwargs):
    args = dict(restriction="smoothness", bound=1.)
    args.update(kwargs)
    with pytest.raises((ValueError, RuntimeError)):
        HonestDiD([0., 1.], np.eye(2), [-2, 0]).infer(**args)


def test_owned_result_and_covariance_correlation_is_unused_but_validated():
    values, cov = np.array([.2, 1.]), np.array([[1., 1.], [1., 1.]])
    obj = HonestDiD(values, cov, [-2, 0])
    expected = obj.infer(restriction="smoothness", bound=0.)
    values[:] = 999.
    cov[:] = 0.
    assert obj.infer(restriction="smoothness", bound=0.) == expected
    assert HonestDiD([.2, 1.], np.eye(2), [-2, 0]).infer(restriction="smoothness", bound=0.) == expected
    with pytest.raises(FrozenInstanceError):
        expected.alpha = .1
    summary = expected.summary()
    summary.loc[0, "bound"] = 999.
    assert expected.bound == 0.
    with pytest.raises(ValueError): expected.contains(np.inf)
    with pytest.raises(TypeError): HonestDiD.from_did(object())


@pytest.mark.parametrize("status", [1, 3, 4])
def test_solver_failures_never_fall_back_to_plain_interval(status):
    from types import SimpleNamespace
    with patch("causalis.scenarios.did.honest.linprog",
               return_value=SimpleNamespace(status=status, success=False, message="synthetic failure")):
        with pytest.raises(RuntimeError, match="solver failed"):
            HonestDiD([0., 1.], np.eye(2), [-2, 0]).infer(restriction="smoothness", bound=1.)


def test_tiny_smoothness_bound_and_nonrepresentable_endpoint_fail_explicitly():
    obj = HonestDiD([0., 1.], np.eye(2), [-2, 0])
    with pytest.raises(RuntimeError, match="resolution"):
        obj.infer(restriction="smoothness", bound=1e-12)
    with pytest.raises(RuntimeError):
        obj.infer(restriction="relative_magnitude", bound=1e308)


@pytest.mark.parametrize("restriction", ["smoothness", "relative_magnitude"])
def test_gaussian_coverage_smoke_with_nonzero_allowed_population_violation(restriction):
    rng = np.random.default_rng(915)
    # One pre period, two post: linear slope .1 with curvature .2 at first post.
    delta = np.array([-.1, .3, .6])
    tau = np.array([0., 1., 2.])
    cov = np.array([[.04, .01, .01], [.01, .04, .02], [.01, .02, .04]])
    accepted = 0
    for observed in rng.multivariate_normal(delta+tau, cov, size=250):
        result = HonestDiD(observed, cov, [-2, 0, 1]).infer(
            restriction=restriction, bound=.2 if restriction == "smoothness" else 3.,
            post_weights=[.5, .5])
        accepted += result.contains(1.5)
    assert accepted/250 >= .94


@pytest.mark.parametrize("restriction", ["smoothness", "relative_magnitude"])
@pytest.mark.parametrize("multiplier", [2., -3.])
def test_outcome_units_and_signed_contrast_scaling(restriction, multiplier):
    beta = np.array([.6, .3, 2., 3.])
    cov = np.eye(4)*.01
    original = HonestDiD(beta, cov, [-3, -2, 0, 1]).infer(
        restriction=restriction, bound=.2, post_weights=[.4, .6])
    transformed = HonestDiD(beta*multiplier, cov*multiplier**2, [-3, -2, 0, 1]).infer(
        restriction=restriction, bound=.2*abs(multiplier) if restriction == "smoothness" else .2,
        post_weights=[.4, .6])
    np.testing.assert_allclose(transformed.confidence_set[0], sorted(np.asarray(original.confidence_set[0])*multiplier))
    contrast = HonestDiD(beta, cov, [-3, -2, 0, 1]).infer(
        restriction=restriction, bound=.2, post_weights=np.array([.4, .6])*multiplier)
    np.testing.assert_allclose(contrast.confidence_set[0], sorted(np.asarray(original.confidence_set[0])*multiplier))


@pytest.mark.parametrize("corruption", ["primal", "dual"])
def test_solver_endpoint_certificates_are_checked(corruption):
    from scipy.optimize import linprog as real_solver

    def corrupted(*args, **kwargs):
        solved = real_solver(*args, **kwargs)
        if corruption == "primal":
            solved.x[:] = 999.
        else:
            solved.ineqlin.marginals[:] = 999.
        return solved

    with patch("causalis.scenarios.did.honest.linprog", side_effect=corrupted):
        with pytest.raises(RuntimeError, match="infeasible|dual optimality"):
            HonestDiD([0., 1.], np.eye(2), [-2, 0]).infer(restriction="smoothness", bound=1.)


def test_shifted_calendar_metadata_is_rejected_even_when_event_indices_are_consecutive():
    source = _result()
    oldest = source.att_gt.event_time.idxmin()
    source.att_gt.loc[oldest, "time"] = source.att_gt.loc[oldest, "time"] - 1
    with pytest.raises(ValueError, match="equally spaced"):
        HonestDiD.from_did(source)


@pytest.mark.parametrize("which", ["values", "covariance", "weights"])
def test_object_complex_values_are_rejected_without_casting(which):
    values, covariance, weights = np.array([0., 1.], dtype=object), np.eye(2).astype(object), np.array([1.], dtype=object)
    if which == "values": values[0] = complex(1, 0)
    elif which == "covariance": covariance[0, 0] = complex(1, 0)
    else: weights[0] = complex(1, 0)
    with pytest.raises(ValueError, match="complex"):
        HonestDiD(values, covariance, [-2, 0]).infer(restriction="smoothness", bound=1., post_weights=weights)


@pytest.mark.parametrize("kwargs", [dict(bound=10**1000), dict(alpha=10**1000), dict(alpha=1e-323)])
def test_unrepresentable_scalar_or_critical_value_is_rejected(kwargs):
    args = dict(restriction="smoothness", bound=1.)
    args.update(kwargs)
    with pytest.raises((ValueError, RuntimeError)):
        HonestDiD([0., 1.], np.eye(2), [-2, 0]).infer(**args)
