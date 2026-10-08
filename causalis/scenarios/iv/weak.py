"""Division-free, iid orthogonal-score tests and Fieller confidence sets."""
from dataclasses import dataclass
from math import copysign, frexp, fsum, sqrt
from numbers import Real

import numpy as np
import pandas as pd
from scipy.stats import norm

from causalis.scenarios._numerics import _checked_arithmetic, _require_finite
from causalis.scenarios._prediction import _real_array, _prediction_vector


def _scalar(value, name):
    if (isinstance(value, (bool, np.bool_)) or not isinstance(value, Real)
            or not np.isfinite(value)):
        raise ValueError(f"{name} must be a finite real scalar")
    return float(value)


@_checked_arithmetic
def _quadratic_set(a, b, c):
    """Solve a*t**2 + b*t + c <= 0, retaining every closed component.

    Exact float64 zeros determine linear/tangent cases; there is no tolerance
    that turns a small quadratic coefficient into a linear one. Finite roots
    must be representable; infinity is reserved for genuinely unbounded sets.
    """
    _require_finite(a, b, c)
    scale = max(abs(a), abs(b), abs(c))
    if scale == 0:
        return "all-real", ((-np.inf, np.inf),)
    original = np.array([a, b, c])
    # Binary scaling is exact for normal float64 values; division by an
    # arbitrary maximum can move otherwise exactly representable endpoints.
    a, b, c = np.ldexp(original, -frexp(scale)[1])
    if np.any((original != 0) & (np.array([a, b, c]) == 0)):
        raise RuntimeError("Quadratic coefficients underflowed; rescale the signals")
    if a == 0:
        if b == 0:
            return ("all-real", ((-np.inf, np.inf),)) if c <= 0 else ("empty", ())
        root = float(-c / b)
        _require_finite(root)
        return "half-line", ((-np.inf, root),) if b > 0 else ((root, np.inf),)
    discriminant = fsum([float(b * b), float(-4 * a * c)])
    if discriminant < 0:
        return ("all-real", ((-np.inf, np.inf),)) if a < 0 else ("empty", ())
    if discriminant == 0:
        if a < 0:
            return "all-real", ((-np.inf, np.inf),)
        root = float(-b / (2 * a))
        _require_finite(root)
        return "singleton", ((root, root),)
    # Stable formula avoids subtracting nearly equal numbers for one root.
    q = -.5 * (b + copysign(sqrt(discriminant), b))
    roots = sorted((float(q / a), float(c / q)))
    _require_finite(roots)
    lo, hi = roots
    if a > 0:
        return "bounded", ((lo, hi),)
    return "two-rays", ((-np.inf, lo), (hi, np.inf))


@dataclass(frozen=True)
class WeakIVResult:
    """Aggregate immutable result with a full union of closed intervals.

    Infinite endpoints denote unbounded components; an empty tuple denotes
    an empty set. No single lower/upper pair or Wald standard error is supplied.
    Rejection uses statistic > critical_value**2; boundary points are accepted.
    This is asymptotic inference, not an exact finite-sample AR/F test.
    """

    confidence_set: tuple
    set_type: str
    null_value: float
    statistic: float
    p_value: float
    is_significant: bool
    alpha: float
    critical_value: float
    numerator: float
    denominator: float
    n_observations: int
    method: str = "orthogonal-ar"

    def contains(self, value):
        """Test membership for a finite real candidate, including endpoints."""
        value = _scalar(value, "value")
        return any(lo <= value <= hi for lo, hi in self.confidence_set)

    def summary(self):
        """Return a fresh one-row aggregate DataFrame, preserving set geometry."""
        return pd.DataFrame([self.__dict__.copy()])


class WeakIVInference:
    """Own two aligned iid observation-scale signals for a ratio moment.

    Inputs phi_y and phi_d have shape (n,), n >= 2. For candidate theta the
    moment is mean(phi_y - theta*phi_d), and its variance is the empirically
    centered sample variance divided by n (ddof=1). No first-stage division,
    first-stage pretest, random draws, nuisance fitting or grid truncation occurs.

    Inference requires a valid CLT for the candidate score, positive limiting
    score variance, adequate moments and negligible nuisance remainder. For
    LATE also require consistency, conditional IV exogeneity, exclusion,
    monotonicity and instrument overlap; a nonzero population complier share
    defines the causal ratio. At zero population first stage the moment can
    still be tested, but a unique complier LATE need not exist. Cross-fitting
    alone does not guarantee the nuisance conditions uniformly under weak IV.
    Clipping/misspecification bias, invalid IV, clusters, repeated splitting,
    weights and adaptive selection are not repaired by this method.
    """

    @_checked_arithmetic
    def __init__(self, phi_y, phi_d):
        y = _real_array(phi_y, name="phi_y")
        d = _real_array(phi_d, name="phi_d")
        if y.ndim != 1 or d.shape != y.shape or y.size < 2:
            raise ValueError("Require aligned phi_y and phi_d of shape (n,), n >= 2")
        self._n = len(y)
        signals = np.column_stack((y, d))
        # A common scale leaves the ratio and test unchanged and keeps squared
        # coefficients representable for large/small common signal scales.
        self._scale = float(np.max(np.abs(signals)))
        if self._scale == 0:
            raise ValueError("Signals must have nonzero score variance")
        scaled = signals / self._scale
        if np.any((signals != 0) & (scaled == 0)):
            raise RuntimeError("Signal scaling underflowed; rescale the inputs")
        self._means = scaled.mean(axis=0)
        self._centered = scaled - self._means
        self._covariance = self._centered.T @ self._centered / (self._n * (self._n - 1))
        if not np.any(np.diag(self._covariance) > 0):
            raise ValueError("Signals must have nonzero score variance")
        if np.any((np.any(self._centered != 0, axis=0)) & (np.diag(self._covariance) == 0)):
            raise RuntimeError("Signal covariance underflowed; rescale the inputs")
        _require_finite(self._means, self._centered, self._covariance)

    @classmethod
    @_checked_arithmetic
    def from_iivm(cls, model):
        """Snapshot fitted IIVM arrays without estimate/fit/predict or mutation.

        Only current normalize_ipw=False, n_rep=1 and truncate are supported.
        Uses owned successful-fit y/d/z and nuisance arrays, not mutable live
        data. IIVM has no cluster/weight/external-OOF fit API; independence and
        absence of leakage remain caller responsibilities. Public fitted array
        mutation is not certified. Strictly interior fitted m is mandatory.
        """
        from sklearn.utils.validation import check_is_fitted
        from .model import IIVM

        if not isinstance(model, IIVM):
            raise TypeError("model must be a fitted IIVM")
        names = ("y_", "d_", "z_", "g_hat0_", "g_hat1_", "m_hat_", "r_hat0_", "r_hat1_")
        check_is_fitted(model, attributes=list(names))
        if model.normalize_ipw or model.n_rep != 1 or model.trimming_rule != "truncate":
            raise NotImplementedError("Require single-partition IIVM with normalize_ipw=False and truncate")
        n = len(model.y_)
        y, d, z, g0, g1, m, r0, r1 = (
            _prediction_vector(getattr(model, name), n, name=name, allow_column=False).copy()
            for name in names)
        if not np.all(np.isin(d, [0, 1])) or not np.all(np.isin(z, [0, 1])):
            raise ValueError("Fitted treatment and instrument must be binary")
        if np.any((m <= 0) | (m >= 1)):
            raise ValueError("Fitted instrument propensities must be strictly interior")
        if np.any((r0 < 0) | (r0 > 1) | (r1 < 0) | (r1 > 1)):
            raise ValueError("Fitted treatment probabilities must be in [0, 1]")
        w1, w0 = z / m, (1 - z) / (1 - m)
        return cls(g1 - g0 + w1 * (y - g1) - w0 * (y - g0),
                   r1 - r0 + w1 * (d - r1) - w0 * (d - r0))

    @_checked_arithmetic
    def infer(self, *, alpha=.05, null=0.):
        """Test a finite candidate and invert all candidate score tests.

        The two-sided statistic is mean(score)**2 / Var(mean(score)); normal
        critical z=norm.isf(alpha/2). The confidence set solves the complete
        quadratic inequality, with no imposed treatment-effect bounds. Generic
        singular signal covariance is allowed, but zero empirical variance at
        the requested null raises. At other zero-variance candidates the set
        retains the algebraic inequality; no validity claim covers those points.
        Exact float64 boundary cases determine geometry, without tolerances.
        Finite endpoints/statistics lost to overflow/underflow raise explicitly.
        """
        alpha = _scalar(alpha, "alpha")
        null = _scalar(null, "null")
        if not 0 < alpha < 1:
            raise ValueError("alpha must be in (0, 1)")
        critical = float(norm.isf(alpha / 2))
        _require_finite(critical)
        # Scale the null contrast before constructing a potentially huge score.
        contrast_scale = max(1., abs(null))
        contrast = np.array([1 / contrast_scale, -null / contrast_scale])
        score = self._centered @ contrast
        variance = float(score @ score / (self._n * (self._n - 1)))
        if variance <= 0:
            raise ValueError("Requested null must have positive empirical score variance")
        t = float((self._means @ contrast) / sqrt(variance))
        statistic = t * t
        p_value = float(2 * norm.sf(abs(t)))
        y, d = self._means
        vyy, vyd, vdd = self._covariance[0, 0], self._covariance[0, 1], self._covariance[1, 1]
        k = critical * critical
        left = np.array([d, y, y, k, k, k])
        right = np.array([d, d, y, vdd, vyd, vyy])
        products = left * right
        if np.any((left != 0) & (right != 0) & (products == 0)):
            raise RuntimeError("Confidence-set coefficients underflowed; rescale the signals")
        dd, yd, yy, kvdd, kvyd, kvyy = products
        set_type, intervals = _quadratic_set(dd - kvdd, -2 * yd + 2 * kvyd, yy - kvyy)
        numerator, denominator = self._means * self._scale
        _require_finite(statistic, p_value, numerator, denominator)
        return WeakIVResult(intervals, set_type, null, statistic, p_value,
                            bool(statistic > k), alpha, critical,
                            float(numerator), float(denominator), self._n)
