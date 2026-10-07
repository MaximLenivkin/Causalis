"""Numeric helpers for binary-treatment unconfoundedness estimators."""
from __future__ import annotations

from typing import Any, Optional
import warnings

import numpy as np
from sklearn.base import is_classifier
from causalis.scenarios._prediction import (
    _prediction_vector, _probability_classes, _probability_output,
)


def _is_binary(values: np.ndarray) -> bool:
    """Require both 0 and 1, using linear comparisons for numeric arrays.

    Object/string inputs retain the legacy unique-value fallback. Constants
    are not binary outcomes for this estimator (unlike multi-treatment IRM).
    """
    values = np.asarray(values)
    if values.dtype.kind in "biufc":
        zero = values == 0
        one = values == 1
        return bool(np.all(zero | one) and np.any(zero) and np.any(one))
    uniq = np.unique(values)
    return np.array_equal(np.sort(uniq), np.array([0, 1])) or np.array_equal(np.sort(uniq), np.array([0.0, 1.0]))


def _safe_is_classifier(estimator) -> bool:
    """Safely check if an estimator is a classifier."""
    try:
        return is_classifier(estimator)
    except (AttributeError, TypeError):
        return getattr(estimator, "_estimator_type", None) == "classifier"


def _binary_label_is_one(label: Any) -> Optional[bool]:
    """Map a binary-like class label to {False, True}, if possible."""
    if isinstance(label, (bool, np.bool_)):
        return bool(label)
    try:
        val = float(label)
    except (TypeError, ValueError):
        return None
    if np.isclose(val, 1.0):
        return True
    if np.isclose(val, 0.0):
        return False
    return None


def _predict_prob_or_value(model, X: np.ndarray, is_propensity: bool = False) -> np.ndarray:
    """Predict real, finite, row-aligned values before applying probability bounds."""
    n = X.shape[0]
    if _safe_is_classifier(model) and hasattr(model, "predict_proba"):
        proba = _probability_output(model.predict_proba(X), n,
                                    name="Model predict_proba()", binary=True)
        classes = (_probability_classes(model, proba.shape[1], name="Model")
                   if proba.ndim == 2 else np.asarray([]))
        if proba.ndim == 1:
            # Assume this is already P(class=1).
            res = proba.ravel()
        elif proba.shape[1] == 1:
            # Can happen if the training fold has a single class.
            # Resolve P(class=1) from classes_ when available.
            if classes.size == 1:
                class_is_one = _binary_label_is_one(classes[0])
                if class_is_one is True:
                    res = proba[:, 0]
                elif class_is_one is False:
                    res = np.zeros(proba.shape[0], dtype=float)
                else:
                    # Unknown class label semantics; fall back to available column.
                    res = proba[:, 0]
            else:
                # No reliable class metadata; infer from hard labels when possible.
                if hasattr(model, "predict"):
                    pred = np.asarray(model.predict(X))
                    # Validate geometry and reality even when legacy label conversion
                    # falls back to the available probability column.
                    if pred.shape not in {(n,), (n, 1)}:
                        raise ValueError(f"Model predict() fallback has invalid shape {pred.shape}.")
                    if np.iscomplexobj(pred) or (pred.dtype.kind == "O" and
                            any(np.iscomplexobj(value) for value in pred.flat)):
                        raise ValueError("Model predict() fallback must contain real values.")
                    try:
                        pred_f = pred.astype(float)
                    except (TypeError, ValueError):
                        res = proba[:, 0]
                    else:
                        pred_f = _prediction_vector(pred_f, n, name="Model predict() fallback")
                        res = np.where(np.isclose(pred_f, 1.0), 1.0, 0.0)
                else:
                    res = proba[:, 0]
        else:
            pos_idx = None
            if classes.size == proba.shape[1]:
                for i, cls in enumerate(classes):
                    if _binary_label_is_one(cls) is True:
                        pos_idx = i
                        break
            if pos_idx is None:
                # Fallback to the second column when binary classes metadata is missing.
                pos_idx = 1
            res = proba[:, pos_idx]
    else:
        res = model.predict(X)

    res = _prediction_vector(res, n, name="Model predictions")
    if is_propensity:
        if np.any((res < -1e-12) | (res > 1.0 + 1e-12)):
            warnings.warn(
                "Propensity model produced values outside [0, 1]. "
                "Consider using a classifier or a model with a logistic link.",
                RuntimeWarning,
            )
        res = np.clip(res, 0.0, 1.0)
    return res


def _validate_overlap_config(policy: str, threshold: float) -> tuple[str, float]:
    """Validate and normalize the overlap policy configuration."""
    policy_norm = str(policy).lower()
    if policy_norm not in {"clip", "drop"}:
        raise ValueError("overlap_policy must be either 'clip' or 'drop'.")

    threshold_f = float(threshold)
    if not np.isfinite(threshold_f) or not (0.0 <= threshold_f < 0.5):
        raise ValueError("overlap_threshold must be finite and in [0, 0.5).")
    return policy_norm, threshold_f


def _overlap_retained_mask(p: np.ndarray, threshold: float) -> np.ndarray:
    """Return rows whose propensity scores satisfy strict overlap."""
    threshold_f = float(threshold)
    p_arr = np.asarray(p, dtype=float).ravel()
    return (p_arr > threshold_f) & (p_arr < 1.0 - threshold_f)


def _apply_overlap_policy(
    p: np.ndarray,
    *,
    policy: str,
    threshold: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply the configured overlap policy to a propensity vector.

    ``clip`` returns a clipped vector with an all-true mask. ``drop`` returns
    only retained propensity scores and the full-sample boolean retention mask.
    """
    policy_norm, threshold_f = _validate_overlap_config(policy, threshold)
    p_arr = np.asarray(p, dtype=float).ravel()

    if policy_norm == "clip":
        mask = np.ones(p_arr.shape[0], dtype=bool)
        return np.clip(p_arr, threshold_f, 1.0 - threshold_f), mask

    mask = _overlap_retained_mask(p_arr, threshold_f)
    return p_arr[mask], mask
