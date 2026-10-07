"""Shared-Gaussian two-link means with bounded adaptive integration.

Integrates sigmoid(a+sU)*h(b+tU), with the *same* independent N(0,1) U
in both factors. The error policy concerns the truncated Gaussian integral;
it is an estimated error, not a certificate for rare-event relative accuracy.
"""

import math

import numpy as np
from scipy.integrate import quad_vec
from scipy.special import expit, log_expit

from causalis.dgp._gaussian_outcome import _gaussian_outcome_mean


_BATCH_SIZE = 32
_LIMIT = 4096
_TOL = 1e-11


def _knots(base, slope, family):
    if slope == 0:
        return []
    offsets = (-40, -16, -4, -1, 0, 1, 4, 16, 40) if family == "binary" else (-20, 20)
    # Division before subtraction avoids overflowing offset-base.
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        center = -base / slope
        points = [offset / slope + center for offset in offsets]
    # Transitions narrower than floating-point resolution cannot be certified
    # by sampling. Reject rather than silently treating a smooth link as a step.
    active = np.abs(center) < 12
    if family == "binary" and np.any(active):
        width = 1 / abs(slope)
        if np.any(width <= 32*np.finfo(float).eps*np.maximum(1, np.abs(center[active]))):
            raise ValueError("Gaussian joint mean has unsupported floating-point geometry")
    if family != "binary":
        for point in points:
            active = np.abs(point) < 12
            if np.any(active) and 40 / abs(slope) <= 32*np.finfo(float).eps*np.max(
                    np.maximum(1, np.abs(point[active]))):
                raise ValueError("Gaussian joint mean has unsupported floating-point geometry")
    return points


def _gaussian_product_mean(a, s, b, t, family):
    """E[sigmoid(a+sU)*h(b+tU)]; h is sigmoid or exp(clip(.,-20,20)).

    Storage is O(n) plus at most 32 rows, 4096 intervals and 1 MiB backend
    cache. Inputs must be real and finite. No random draws or callbacks occur.
    Gaussian tails omitted outside [-12,12] have absolute bound 3.6e-33
    for binary and exp(20)*3.6e-33 for clipped exponential responses.
    """
    if any(np.iscomplexobj(v) for v in (a, s, b, t)):
        raise ValueError("Gaussian joint mean requires real links and strengths")
    a, b = np.broadcast_arrays(np.asarray(a, dtype=float), np.asarray(b, dtype=float))
    s, t = float(s), float(t)
    if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))
            and math.isfinite(s) and math.isfinite(t)):
        raise ValueError("Gaussian joint mean requires finite links and strengths")
    if family not in {"binary", "poisson", "gamma"}:
        raise ValueError("Unsupported Gaussian joint family")
    if s == 0:
        return expit(a) * _gaussian_outcome_mean(b, t, family)
    if t == 0:
        natural = expit(b) if family == "binary" else np.exp(np.clip(b, -20, 20))
        return _gaussian_outcome_mean(a, s, "binary") * natural
    rows, inverse = np.unique(np.column_stack((a.ravel(), b.ravel())), axis=0, return_inverse=True)
    out = np.empty(len(rows))
    for start in range(0, len(rows), _BATCH_SIZE):
        aa, bb = rows[start:start + _BATCH_SIZE].T
        candidates = [np.zeros_like(aa), np.full_like(aa, -12), np.full_like(aa, 12)]
        candidates += _knots(aa, s, "binary") + _knots(bb, t, family)
        if family != "binary":
            candidates.append(np.full_like(aa, np.clip(t, -12, 12)))
        candidates = np.clip(np.asarray(candidates), -12, 12)
        def log_value(u):
            # Saturating links allow harmless affine overflow; NaNs are never accepted.
            with np.errstate(over="ignore", invalid="ignore"):
                first, second = aa + s*u, bb + t*u
                response = log_expit(second) if family == "binary" else np.clip(second, -20, 20)
                return log_expit(first) + response - u*u/2
        # Row-specific positive scaling keeps large exponential means and small
        # joint probabilities in the same bounded max-norm integration batch.
        scale = np.max(log_value(candidates), axis=0)
        if not np.all(np.isfinite(scale)):
            raise ValueError("Gaussian joint mean has unsupported floating-point geometry")
        points = np.unique(candidates.ravel())
        # Coalesce near-identical knots; integration of a few-ULP interval can
        # otherwise trigger roundoff failure in the backend.
        kept = [points[0]]
        for point in points[1:]:
            if point - kept[-1] > 32*np.finfo(float).eps*max(1, abs(point), abs(kept[-1])):
                kept.append(point)
        if kept[-1] != 12.0:
            kept[-1] = 12.0
        def function(u):
            return np.exp(log_value(u) - scale) / math.sqrt(2*math.pi)
        value, error, info = quad_vec(function, -12, 12, points=kept[1:-1],
            epsabs=_TOL, epsrel=0, norm="max", cache_size=2**20,
            limit=_LIMIT, full_output=True)
        if (not info.success or not np.isfinite(error) or error > _TOL
                or not np.all(np.isfinite(value)) or np.any(value < 0)):
            raise ValueError("Gaussian joint mean integration did not converge")
        result = np.exp(scale) * value
        bound = 1.0 if family == "binary" else math.exp(20)
        if not np.all(np.isfinite(result)) or np.any(result > bound*(1+8*np.finfo(float).eps)):
            raise ValueError("Gaussian joint mean is outside its natural range")
        out[start:start + len(aa)] = np.clip(result, 0, bound)
    return out[inverse].reshape(a.shape)
