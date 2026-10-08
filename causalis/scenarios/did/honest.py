"""Conservative HonestDiD-style projection under bounded trend violations."""
from dataclasses import dataclass
from numbers import Integral, Real

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.stats import norm

from causalis.scenarios._numerics import _checked_arithmetic, _require_finite
from causalis.scenarios._prediction import _real_array


def _scalar(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(name + " must be a finite real scalar")
    try:
        converted = float(value)
    except (ValueError, OverflowError) as error:
        raise ValueError(name + " must be a finite real scalar") from error
    if not np.isfinite(converted):
        raise ValueError(name + " must be a finite real scalar")
    return converted


@dataclass(frozen=True)
class HonestDiDResult:
    """Aggregate projection interval; an empty set is explicit model incompatibility.

    An empty interval does not establish a treatment effect or reject a scalar
    null. ``contains`` uses closed endpoints. ``summary`` returns a fresh frame.
    """

    confidence_set: tuple
    restriction: str
    bound: float
    alpha: float
    critical_value: float
    post_weights: tuple
    event_times: tuple
    method: str = "bonferroni-projection"

    @property
    def set_type(self):
        return "bounded" if self.confidence_set else "empty"

    def contains(self, value):
        """Check membership of a finite scalar in the projected interval."""
        value = _scalar(value, "value")
        return any(lower <= value <= upper for lower, upper in self.confidence_set)

    def summary(self):
        """Return aggregate endpoints and the imposed restriction, without p-values."""
        return pd.DataFrame([dict(confidence_set=self.confidence_set, set_type=self.set_type,
                                 restriction=self.restriction, bound=self.bound,
                                 alpha=self.alpha, method=self.method)])


class HonestDiD:
    """Own event-study estimates and their estimator covariance, excluding time -1.

    ``event_times`` must be ordered consecutive integer pre-periods ending at -2,
    followed by consecutive post-periods starting at 0. The omitted common
    reference period -1 has coefficient zero. Require at least one pre and one
    post coefficient; covariance is of estimates, NOT observation-level scores.

    The population model is beta = tau + delta, with tau_pre = 0 and delta_-1 = 0.
    ``smoothness`` bounds every consecutive second difference of delta by M;
    M=0 permits an arbitrary linear trend, not necessarily parallel trends.
    ``relative_magnitude`` bounds each post first difference by M times the
    largest absolute pre first difference (including the difference into -1).
    Its M=0 imposes zero post violation, without restricting pre violations.

    Inference projects a coordinatewise Bonferroni Gaussian confidence rectangle
    through these restrictions and accounts for uncertainty in pre estimates.
    It is conservative, not the original R package's conditional/hybrid or
    optimal fixed-length interval. Off-diagonal covariance is validated but
    unused. Coverage requires jointly asymptotically normal coefficients,
    consistently estimated positive marginal variances, no anticipation,
    a common population/comparison/reference, and the imposed population trend
    restriction. This API cannot verify identification or adaptive selection.
    No finite-sample, few-cluster, growing-dimension or data-selected-bound
    guarantee is supplied. Smoothness LP endpoints have float64 solver precision.
    """

    @_checked_arithmetic
    def __init__(self, estimates, covariance, event_times):
        values = _real_array(estimates, name="estimates")
        cov = _real_array(covariance, name="covariance")
        times = tuple(event_times)
        if (values.ndim != 1 or len(values) < 2 or cov.shape != (len(values), len(values))
                or len(times) != len(values)):
            raise ValueError("Require estimates (p,), covariance (p,p), event_times length p >= 2")
        if any(isinstance(t, (bool, np.bool_)) or not isinstance(t, Integral) for t in times):
            raise ValueError("event_times must contain integers")
        k = sum(t < -1 for t in times)
        expected = tuple(range(-k-1, -1)) + tuple(range(len(values)-k))
        if k == 0 or k == len(values) or times != expected:
            raise ValueError("Require consecutive pre times through -2, omit -1, and post times from 0")
        scale = float(np.max(np.abs(cov)))
        if scale == 0 or np.any(np.diag(cov) <= 0):
            raise ValueError("Covariance must have positive marginal variances")
        normalized = cov / scale
        if (np.max(np.abs(normalized-normalized.T)) > 1e-10
                or np.linalg.eigvalsh((normalized+normalized.T)/2).min() < -1e-10):
            raise ValueError("Covariance must be symmetric positive semidefinite (relative tolerance 1e-10)")
        self._values = values.copy()
        self._se = np.sqrt(np.diag(cov)).copy()
        self._times = times
        self._k = k

    @classmethod
    @_checked_arithmetic
    def from_did(cls, result):
        """Snapshot an iid, single-cohort CSA result with stable cell populations.

        Requires universal base, anticipation=0, never-treated controls, pre
        coefficients and diagnostic_data=True. Changing cell memberships,
        clustered inference, staggered cohorts and varying bases are rejected.
        No fit/estimate callbacks or random numbers are used. Mutable result
        edits cannot be certified; later edits do not change the owned snapshot.
        """
        from causalis.data_contracts.panel_did_estimate import CallawaySantAnnaDIDEstimate

        if not isinstance(result, CallawaySantAnnaDIDEstimate):
            raise TypeError("result must be a CallawaySantAnnaDIDEstimate")
        if (result.base_period != "universal" or result.anticipation != 0
                or result.control_group != "never_treated" or not result.include_pre_periods
                or result.cluster_col is not None):
            raise ValueError("Require iid universal-base, no-anticipation, never-treated pre-period results")
        cells = result.att_gt.sort_values("event_time").copy()
        required = {"cohort", "base_time", "time", "cell_id", "event_time", "att"}
        if not required <= set(cells):
            raise ValueError("Missing common-reference cell metadata")
        if (cells.cohort.nunique() != 1 or cells.cell_id.duplicated().any()
                or cells.base_time.nunique() != 1):
            raise ValueError("Require one cohort, unique cells and a common base period")
        base = cells.base_time.iloc[0]
        axis = sorted(list(cells.time) + [base])
        if (not isinstance(base, pd.Period) or axis != list(pd.period_range(axis[0], axis[-1], freq=base.freq))
                or cells.loc[cells.event_time == 0, "time"].tolist() != [cells.cohort.iloc[0]]
                or base + 1 != cells.cohort.iloc[0]):
            raise ValueError("Require equally spaced calendar periods and reference immediately before treatment")
        diag = result.diagnostics
        scores = diag.get("influence_scores")
        units = diag.get("unit_level")
        if not isinstance(scores, pd.DataFrame) or not isinstance(units, pd.DataFrame):
            raise ValueError("Require diagnostic_data=True with aligned unit influences and membership")
        if not {"cell_id", result.unit_col, "is_treated_cohort"} <= set(units):
            raise ValueError("Missing unit membership metadata")
        if not scores.index.is_unique or not scores.columns.is_unique or len(scores) < 2:
            raise ValueError("Influences require unique unit IDs/columns and at least two units")
        if set(scores.columns) != set(cells.cell_id):
            raise ValueError("Influence columns must match all cells")
        if set(units.cell_id) != set(cells.cell_id):
            raise ValueError("Unit memberships must match all cells")
        membership = None
        for cell in cells.cell_id:
            group = units.loc[units.cell_id == cell]
            if (group[result.unit_col].duplicated().any()
                    or set(group[result.unit_col]) != set(scores.index)
                    or not group.is_treated_cohort.isin([0, 1]).all()):
                raise ValueError("Require complete common cell populations and binary membership")
            current = group.set_index(result.unit_col).is_treated_cohort.reindex(scores.index).to_numpy()
            if not 0 < current.sum() < len(current):
                raise ValueError("Require both treated and control units")
            if membership is not None and not np.array_equal(current, membership):
                raise ValueError("Treated/control memberships must be identical across cells")
            membership = current
        raw = _real_array(scores.loc[:, cells.cell_id].to_numpy(), name="influence_scores")
        centered = raw - raw.mean(axis=0)
        n = len(raw)
        # Match CSA's existing iid covariance convention, ddof=0 / n.
        scale = float(np.max(np.abs(centered)))
        if scale == 0:
            raise ValueError("Require positive marginal influence variances")
        small = centered / scale
        if np.any((small == 0) & (centered != 0)):
            raise RuntimeError("Influence normalization lost to underflow; rescale outcomes")
        cov = (small.T @ small / n) * (scale / n) * scale
        _require_finite(cov)
        if np.any((cov == 0) & ((small.T @ small) != 0)):
            raise RuntimeError("Influence covariance lost to underflow; rescale outcomes")
        return cls(cells.att.to_numpy(), cov, cells.event_time.to_numpy())

    @_checked_arithmetic
    def infer(self, *, restriction, bound, post_weights=None, alpha=.05):
        """Project under a prespecified nonnegative bound and fixed post contrast.

        Default contrast selects event time 0. Weights can be signed, need not
        sum to one and must be finite/nonzero. Bounds refer to one event step;
        irregular time spacing is unsupported. Empty smoothness projections
        explicitly signal that the confidence rectangle cannot satisfy the
        restriction. Solver errors raise rather than return an ordinary CI.
        """
        if restriction not in ("smoothness", "relative_magnitude"):
            raise ValueError("restriction must be smoothness or relative_magnitude")
        bound = _scalar(bound, "bound")
        alpha = _scalar(alpha, "alpha")
        if bound < 0 or not 0 < alpha < 1:
            raise ValueError("Require bound >= 0 and 0 < alpha < 1")
        p, k = len(self._values), self._k
        weights = np.eye(1, p-k)[0] if post_weights is None else _real_array(post_weights, name="post_weights")
        if weights.shape != (p-k,) or not np.any(weights):
            raise ValueError("post_weights must be a nonzero vector with one entry per post period")
        critical = float(norm.isf(alpha / (2*p)))
        _require_finite(critical)
        physical_scale = max(float(np.max(np.abs(self._values))), float(self._se.max()),
                             bound if restriction == "smoothness" else 0.)
        values = self._values / physical_scale
        radii = (self._se / physical_scale) * critical
        weight_scale = float(np.max(np.abs(weights)))
        w = weights / weight_scale
        if (np.any((values == 0) & (self._values != 0)) or np.any(radii == 0)
                or np.any((w == 0) & (weights != 0))):
            raise RuntimeError("Scale normalization lost a nonzero quantity; rescale inputs")
        lower, upper = values[:k]-radii[:k], values[:k]+radii[:k]
        center = float(w @ values[k:])
        radius = float(np.abs(w) @ radii[k:])
        if restriction == "relative_magnitude":
            # The largest pre slope over a rectangle occurs at a pair of corners.
            lo = np.r_[lower, 0.]
            hi = np.r_[upper, 0.]
            largest = max(float(np.max(hi[1:]-lo[:-1])), float(np.max(hi[:-1]-lo[1:])))
            violation = bound * largest * float(np.abs(np.cumsum(w[::-1])).sum())
            bounds = (center-radius-violation, center+radius+violation)
        else:
            # Insert the omitted reference before taking all second differences.
            full = np.eye(p+1)[:, np.arange(p+1) != k]
            second = np.diff(full, n=2, axis=0)
            a = np.vstack([second, -second])
            rhs = np.full(len(a), bound / physical_scale)
            if (bound > 0 and bound / physical_scale < 1e-8) or radii.min() < 1e-8:
                raise RuntimeError("Smoothness bound or marginal uncertainty is below normalized solver resolution")
            objective = np.r_[np.zeros(k), w]
            lp_bounds = list(zip(lower, upper)) + [(None, None)]*(p-k)
            extrema = []
            for sign in (1., -1.):
                solved = linprog(sign*objective, A_ub=a, b_ub=rhs, bounds=lp_bounds,
                                 method="highs", options={"primal_feasibility_tolerance": 1e-9,
                                                         "dual_feasibility_tolerance": 1e-9})
                if solved.status == 2:
                    extrema = []
                    break
                if not solved.success:
                    raise RuntimeError("Smoothness projection solver failed: " + solved.message)
                _require_finite(solved.fun, solved.x)
                if (np.max(a @ solved.x-rhs) > 1e-8
                        or np.any(solved.x[:k] < lower-1e-8)
                        or np.any(solved.x[:k] > upper+1e-8)):
                    raise RuntimeError("Smoothness solver returned an infeasible endpoint")
                gradient = (sign*objective - a.T @ solved.ineqlin.marginals
                            - solved.lower.marginals - solved.upper.marginals)
                dual = (rhs @ solved.ineqlin.marginals
                        + lower @ solved.lower.marginals[:k]
                        + upper @ solved.upper.marginals[:k])
                if (np.max(np.abs(gradient)) > 1e-8
                        or abs(dual-solved.fun) > 1e-8*max(1., abs(solved.fun))
                        or np.any(solved.ineqlin.marginals > 1e-8)
                        or np.any(solved.lower.marginals < -1e-8)
                        or np.any(solved.upper.marginals > 1e-8)):
                    raise RuntimeError("Smoothness solver failed its dual optimality check")
                extrema.append(sign * float(solved.fun))
            bounds = (center-radius-extrema[1], center+radius-extrema[0]) if extrema else None
        intervals = ()
        if bounds is not None:
            endpoints = np.asarray(bounds) * physical_scale * weight_scale
            _require_finite(endpoints)
            if np.any((endpoints == 0) & (np.asarray(bounds) != 0)):
                raise RuntimeError("Projection endpoint lost to underflow; rescale inputs")
            intervals = ((float(endpoints[0]), float(endpoints[1])),)
        return HonestDiDResult(intervals, restriction, bound, alpha, critical,
                               tuple(float(x) for x in weights), self._times)
