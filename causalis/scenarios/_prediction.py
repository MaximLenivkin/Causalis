"""Validate learner outputs before selection, flattening or probability repair."""
from __future__ import annotations

import numpy as np


def _real_array(values, *, name: str) -> np.ndarray:
    """Keep float-convertible real inputs; reject complex values without casting."""
    try:
        raw = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must have a regular shape and real values.") from exc
    if np.iscomplexobj(raw) or (raw.dtype.kind == "O" and
                               any(np.iscomplexobj(value) for value in raw.flat)):
        raise ValueError(f"{name} must contain real values; complex outputs are unsupported.")
    try:
        with np.errstate(over="ignore", invalid="ignore"):
            result = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain real values convertible to float.") from exc
    if not np.all(np.isfinite(result)):
        raise RuntimeError(f"{name} contains non-finite values.")
    return result


def _prediction_vector(values, n: int, *, name: str, allow_column: bool = True) -> np.ndarray:
    """Require one prediction per row, optionally accepting a single column."""
    result = _real_array(values, name=name)
    if result.shape == (n,):
        return result
    if allow_column and result.shape == (n, 1):
        return result[:, 0]
    expected = f"({n},) or ({n}, 1)" if allow_column else f"({n},)"
    raise ValueError(f"{name} must have shape {expected}; got shape {result.shape}.")


def _probability_output(values, n: int, *, name: str, binary: bool) -> np.ndarray:
    """Validate every probability cell, including columns later discarded."""
    result = _real_array(values, name=name)
    if binary and result.shape == (n,):
        return result
    if (result.ndim == 2 and result.shape[0] == n and result.shape[1] >= 1
            and (not binary or result.shape[1] <= 2)):
        return result
    expected = f"({n},), ({n}, 1) or ({n}, 2)" if binary else f"({n}, K), K >= 1"
    raise ValueError(f"{name} must have shape {expected}; got shape {result.shape}.")


def _probability_classes(model, n_columns: int, *, name: str) -> np.ndarray:
    """Check available class metadata against probability columns."""
    metadata = getattr(model, "classes_", None)
    classes = np.asarray([] if metadata is None else metadata)
    if classes.ndim != 1 or (classes.size and classes.size != n_columns):
        raise ValueError(f"{name}.classes_ must be 1D with one label per probability column.")
    return classes
