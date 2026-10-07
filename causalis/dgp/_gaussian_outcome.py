"""Deterministic Gaussian-reference means for single-treatment outcome links.

These means integrate the structural response over independent N(0, 1), even
when a caller supplies a different realized U. They are potential-outcome means,
not outcome regressions conditional on an endogenously assigned treatment.
"""

import math

import numpy as np
from scipy.integrate import quad_vec
from scipy.special import expit, log_ndtr, ndtr


_BATCH_SIZE = 1024
_ABS_TOL = 1e-11


def _integrate(function, low, high, tolerance):
    """Check the backend's estimated max-norm error; no silent fallback."""
    value, error, info = quad_vec(
        function, low, high, epsabs=tolerance, epsrel=0.0, norm="max",
        cache_size=2**20, limit=256, full_output=True,
    )
    if (not info.success or not np.isfinite(error) or error > tolerance
            or not np.all(np.isfinite(value))):
        raise ValueError("Gaussian outcome mean integration did not converge")
    return value


def _binary_mean(link, strength):
    """Smooth integrands on both sides of strength=1; absolute-error policy."""
    out = np.empty_like(link)
    for start in range(0, link.size, _BATCH_SIZE):
        values = link[start:start + _BATCH_SIZE]
        if strength < 1.0:
            # Normal tails beyond +/-12 contribute < 3.6e-33 in total.
            def function(u):
                return expit(values + strength * u) * math.exp(-u * u / 2) / math.sqrt(2 * math.pi)
            means = _integrate(function, -12.0, 12.0, _ABS_TOL)
        else:
            # For independent Logistic L and Gaussian Z,
            # E[sigmoid(a+sZ)] = E[Phi((a-L)/s)]. Width is at least one,
            # even for huge s; omitted logistic mass is < 8.5e-18.
            def function(u):
                return ndtr(values / strength - u / strength) * expit(u) * expit(-u)
            means = _integrate(function, -40.0, 40.0, _ABS_TOL)
        rounding = 4 * np.finfo(float).eps
        if np.any((means < -rounding) | (means > 1.0 + rounding)):
            raise ValueError("Gaussian outcome probability is outside [0, 1]")
        out[start:start + len(values)] = np.clip(means, 0.0, 1.0)
    return out


def _clipped_exp_mean(link, strength):
    """Lower/upper tails plus a truncated exponential Gaussian moment.

    The analytic middle term uses log-CDF differences for strength <= 8.
    Larger strengths use a normalized, smooth integral on the clipped link
    interval, avoiding cancellation between O(strength**2) log terms.
    """
    low, high = -20.0, 20.0
    with np.errstate(over="ignore", divide="ignore"):
        lower_z = (low - link) / strength
        upper_z = (high - link) / strength
    # Bounding the other contributions by exp(high)*P(Z>12) gives relative
    # error < exp(40)*Phi(-12) < 4.2e-16 even against the lower clipped mean.
    below = lower_z >= 12.0
    above = upper_z <= -12.0
    active = ~(below | above)
    out = np.empty_like(link)
    out[below], out[above] = math.exp(low), math.exp(high)
    values = link[active]
    if not values.size:
        return out
    lower_z, upper_z = lower_z[active], upper_z[active]
    tails = math.exp(low) * ndtr(lower_z) + math.exp(high) * ndtr(-upper_z)
    if strength <= 8.0:
        shifted_low, shifted_high = lower_z - strength, upper_z - strength
        reflected = shifted_low > 0.0
        log_high = log_ndtr(np.where(reflected, -shifted_low, shifted_high))
        log_low = log_ndtr(np.where(reflected, -shifted_high, shifted_low))
        with np.errstate(divide="ignore", invalid="ignore"):
            log_interval = log_high + np.log(-np.expm1(log_low - log_high))
        middle = np.exp(values + strength * strength / 2.0 + log_interval)
    else:
        middle = np.empty_like(values)
        for start in range(0, values.size, _BATCH_SIZE):
            batch = values[start:start + _BATCH_SIZE]
            # The log-integrand peaks at clip(a+s**2, low, high).
            # The branch avoids squaring enormous finite strengths.
            z_high = high / strength - batch / strength
            peak = np.full_like(batch, high)
            interior = z_high > strength
            if np.any(interior):
                peak[interior] = np.clip(batch[interior] + strength * strength, low, high)
            max_log = peak - 0.5 * (peak / strength - batch / strength)**2
            def function(t):
                z = t / strength - batch / strength
                return np.exp(t - 0.5 * z * z - max_log)
            integral = _integrate(function, low, high, _ABS_TOL)
            middle[start:start + len(batch)] = (np.exp(max_log) / strength
                / math.sqrt(2 * math.pi)) * integral
    result = tails + middle
    if not np.all(np.isfinite(result)) or np.any(result < 0.0):
        raise ValueError("Gaussian clipped exponential mean has unsupported floating-point geometry")
    # Only roundoff can exceed the exact clipped range.
    out[active] = np.clip(result, math.exp(low), math.exp(high))
    return out


def _gaussian_outcome_mean(link, strength, family):
    """Mean of sigmoid or exp(clip(link+sZ,-20,20)), Z independent N(0,1).

    Binary adaptive errors are estimated absolute max-norm errors, not rigorous
    certificates or rare-probability relative bounds. Working storage is O(n)
    plus bounded 1024-value integration batches. No random numbers are drawn.
    """
    if np.iscomplexobj(link) or np.iscomplexobj(strength):
        raise ValueError("Gaussian outcome mean requires real links and latent strength")
    link = np.asarray(link, dtype=float)
    strength = abs(float(strength))
    if not np.all(np.isfinite(link)) or not math.isfinite(strength):
        raise ValueError("Gaussian outcome mean requires finite links and latent strength")
    if family not in {"binary", "poisson", "gamma"}:
        raise ValueError("Unsupported Gaussian outcome family")
    if strength == 0.0:
        return expit(link) if family == "binary" else np.exp(np.clip(link, -20.0, 20.0))
    distinct, inverse = np.unique(link, return_inverse=True)
    means = _binary_mean(distinct, strength) if family == "binary" else _clipped_exp_mean(distinct, strength)
    return means[inverse].reshape(link.shape)
