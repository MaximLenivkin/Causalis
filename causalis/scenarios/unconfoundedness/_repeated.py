"""Partition seeds and scalar median-variance aggregation for repeated IRM."""
from numbers import Integral

import numpy as np
from scipy.stats import norm

from causalis.data_contracts.causal_estimate import CausalEstimate
from causalis.data_contracts.repeated_causal_estimate import RepeatedCausalEstimate
from causalis.scenarios._numerics import _checked_arithmetic, _require_finite


def validate_n_rep(n_rep):
    """Require an integer count without lossy coercion or boolean counts."""
    if isinstance(n_rep, (bool, np.bool_)) or not isinstance(n_rep, Integral) or n_rep < 1:
        raise ValueError("n_rep must be a positive integer")
    return int(n_rep)


def repetition_seeds(random_state, n_rep):
    """Keep the first integer seed and prefix-stable local child seeds."""
    if random_state is not None and (
        isinstance(random_state, (bool, np.bool_))
        or not isinstance(random_state, Integral)
        or not 0 <= random_state <= np.iinfo(np.uint32).max
    ):
        raise ValueError("Repeated IRM random_state must be None or a uint32 integer")
    root = np.random.SeedSequence(None if random_state is None else int(random_state))
    first = int(root.generate_state(1)[0]) if random_state is None else int(random_state)
    return [first] + [int(child.generate_state(1)[0]) for child in root.spawn(n_rep - 1)]


@_checked_arithmetic
def median_inference(values, errors, alpha):
    """Return scalar median, split-adjusted SE and normal Wald inference.

    Errors are sample-scaled SEs. Repetitions reuse observations, so there is
    no division by their count. All repetitions must have finite inference.
    """
    values, errors = np.asarray(values, dtype=float), np.asarray(errors, dtype=float)
    if values.ndim != 1 or values.size == 0 or errors.shape != values.shape:
        raise ValueError("Repetition effects and SEs must be nonempty matching vectors")
    _require_finite(values, errors)
    if np.any(errors < 0):
        raise ValueError("Repetition SEs must be non-negative")
    theta = float(np.median(values))
    se = float(np.sqrt(np.median(errors**2 + (values - theta)**2)))
    z = float(norm.ppf(1 - alpha / 2))
    low, high = theta - z * se, theta + z * se
    if se == 0:
        statistic = 0.0 if theta == 0 else np.copysign(np.inf, theta)
        p_value = 1.0 if theta == 0 else 0.0
    else:
        statistic = theta / se
        p_value = float(2 * norm.sf(abs(statistic)))
        _require_finite(statistic)
    _require_finite(theta, se, z, low, high, p_value)
    return theta, se, statistic, p_value, low, high


def aggregate_estimates(estimates, seeds, relative_errors, alpha):
    """Construct an aggregate without assigning it a single-partition payload."""
    values = [result.value for result in estimates]
    errors = [result.model_options["std_error"] for result in estimates]
    theta, se, statistic, p_value, low, high = median_inference(values, errors, alpha)
    relative = [result.value_relative for result in estimates]
    if all(value is not None and np.isfinite(value) for value in relative) and np.all(
        np.isfinite(relative_errors)
    ):
        rel, rel_se, _, _, rel_low, rel_high = median_inference(relative, relative_errors, alpha)
    else:
        rel = rel_se = rel_low = rel_high = float("nan")
    first = estimates[0]
    options = dict(first.model_options)
    options.update(
        n_rep=len(estimates), aggregation="median_variance", std_error=se,
        t_stat=statistic, std_error_relative=rel_se,
        repetition_seeds=list(seeds), repetition_values=list(values),
        repetition_std_errors=list(errors),
    )
    # The first result supplies unchanged sample counts and role labels only.
    # Its seed describes a partition, so omit it from aggregate metadata.
    options.pop("random_state", None)
    options.pop("cluster_split_seed", None)
    options.pop("oof_split_seed", None)
    fields = {name: getattr(first, name) for name in CausalEstimate.model_fields}
    fields.update(
        model="RepeatedIRM", model_options=options, value=theta,
        ci_lower_absolute=low, ci_upper_absolute=high, p_value=p_value,
        is_significant=p_value < alpha, value_relative=rel,
        ci_lower_relative=rel_low, ci_upper_relative=rel_high, diagnostic_data=None,
    )
    return RepeatedCausalEstimate(
        **fields, repetition_estimates=estimates, repetition_seeds=list(seeds)
    )
