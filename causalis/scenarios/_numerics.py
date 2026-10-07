"""Explicit failure boundary for float64 score and inference arithmetic."""
from functools import wraps

import numpy as np


def _require_finite(*values):
    """Reject arithmetic outputs before publishing an estimate."""
    if any(not np.all(np.isfinite(value)) for value in values):
        raise RuntimeError(
            "Non-finite score/inference arithmetic. Rescale outcomes or weights "
            "or increase the overlap/trimming threshold and refit."
        )


def _checked_arithmetic(function):
    """Keep normal float64 operations, but reject overflow and invalid operations.

    Underflow retains NumPy's policy. Local intentional NaN branches (undefined
    relative effects or singular moments) remain the caller's responsibility.
    No clipping, imputation, or alternate estimating equation is applied.
    """
    @wraps(function)
    def checked(*args, **kwargs):
        try:
            with np.errstate(over='raise', invalid='raise', divide='raise'):
                return function(*args, **kwargs)
        except (FloatingPointError, OverflowError) as error:
            raise RuntimeError(
                "Non-finite score/inference arithmetic in " + function.__name__
                + ". Rescale outcomes or weights or increase the overlap/trimming threshold and refit."
            ) from error
    return checked
