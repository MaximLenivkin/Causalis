"""Score diagnostics for multi-treatment unconfoundedness."""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from causalis.data_contracts.multicausal_estimate import MultiCausalEstimate
from causalis.data_contracts.multicausaldata import MultiCausalData
from causalis.scenarios.unconfoundedness.refutation.score.score_validation import (
    _oos_moment_test_from_psi,
)
from causalis.scenarios.multi_unconfoundedness._utils import (
    _normalize_multiclass_ipw_terms,
    _normalize_rows_to_simplex,
    _trim_multiclass_propensity,
)


def _grade(value: float, warn: float, strong: float) -> str:
    if value is None or not np.isfinite(value):
        return "NA"
    v = float(value)
    if v < warn:
        return "GREEN"
    if v < strong:
        return "YELLOW"
    return "RED"


def _validate_estimate_matches_data(data: MultiCausalData, estimate: MultiCausalEstimate) -> None:
    if str(estimate.outcome) != str(data.outcome):
        raise ValueError(
            "estimate.outcome must match data.outcome "
            f"({estimate.outcome!r} != {data.outcome!r})."
        )

    est_treatments = [str(name) for name in list(estimate.treatment)]
    data_treatments = [str(name) for name in list(data.treatment_names)]
    if est_treatments != data_treatments:
        raise ValueError(
            "estimate.treatment must match data.treatment_names in the same order "
            f"({est_treatments!r} != {data_treatments!r})."
        )


def _resolve_trimming_threshold(
    trimming_threshold: Optional[float],
    diagnostic_data: Any,
    estimate: MultiCausalEstimate,
) -> float:
    if trimming_threshold is not None:
        return float(trimming_threshold)

    trim_thr = getattr(diagnostic_data, "trimming_threshold", None)
    if trim_thr is None:
        trim_thr = estimate.model_options.get("trimming_threshold", None)
    if trim_thr is None:
        trim_thr = 0.01
    return float(trim_thr)


def _resolve_normalize_ipw(score: str, diagnostic_data: Any, estimate: MultiCausalEstimate) -> bool:
    normalize_ipw = getattr(diagnostic_data, "normalize_ipw", None)
    if normalize_ipw is None:
        normalize_ipw = estimate.model_options.get("normalize_ipw", False)
    if str(score).upper() == "ATTE":
        return False
    return bool(normalize_ipw)


def _resolve_treatment_names(diag: Any, data: MultiCausalData, k: int) -> List[str]:
    names = [str(name) for name in list(data.treatment_names)]
    if len(names) == k:
        return names

    diag_names = getattr(diag, "treatment_names", None)
    if diag_names is None:
        diag_names = getattr(diag, "d_names", None)
    if diag_names is not None:
        diag_names = [str(name) for name in list(diag_names)]
        if len(diag_names) == k:
            return diag_names

    return [f"d_{idx}" for idx in range(k)]


def _comparison_labels(treatment_names: List[str]) -> List[str]:
    baseline = str(treatment_names[0])
    return [f"{name} vs {baseline}" for name in treatment_names[1:]]


def _build_basis(x: np.ndarray, n_basis_funcs: Optional[int]) -> np.ndarray:
    n, p = x.shape
    if n_basis_funcs is None:
        n_basis_funcs = int(p + 1)
    n_covs = min(max(int(n_basis_funcs) - 1, 0), int(p))

    if n_covs <= 0:
        return np.ones((n, 1), dtype=float)

    x_sel = x[:, :n_covs]
    x_std = (x_sel - np.mean(x_sel, axis=0)) / (np.std(x_sel, axis=0) + 1e-8)
    return np.c_[np.ones(n), x_std]


def _normalize_ipw_terms(d: np.ndarray, m: np.ndarray, *, normalize_ipw: bool) -> np.ndarray:
    return _normalize_multiclass_ipw_terms(d=d, m_hat=m, normalize_ipw=normalize_ipw)


def _resolve_theta(value: Any, n_contrasts: int) -> np.ndarray:
    arr = np.asarray(value, dtype=float).reshape(-1)
    if arr.size == 1 and n_contrasts > 1:
        arr = np.repeat(arr, n_contrasts)
    if arr.size != n_contrasts:
        raise ValueError(
            f"estimate.value must have length {n_contrasts} (number of baseline contrasts), got {arr.size}."
        )
    return arr


def _compute_psi_from_nuisances(
    *,
    y: np.ndarray,
    d: np.ndarray,
    g_hat: np.ndarray,
    m: np.ndarray,
    theta: np.ndarray,
    score: str,
    normalize_ipw: bool,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    u = y[:, None] - g_hat
    score_u = str(score).upper()
    if score_u == "ATE":
        h = _normalize_ipw_terms(d=d, m=m, normalize_ipw=normalize_ipw)
        psi_b = (
            (g_hat[:, 1:] - g_hat[:, [0]])
            + (u[:, 1:] * h[:, 1:])
            - (u[:, [0]] * h[:, [0]])
        )
    else:
        h = np.full_like(m, np.nan, dtype=float)
        g0_hat = g_hat[:, [0]]
        residual0 = y[:, None] - g0_hat
        d0 = d[:, [0]].astype(float)
        dk = d[:, 1:].astype(float)
        pk = dk.mean(axis=0)
        if np.any(pk <= 0.0):
            raise RuntimeError("ATTE requested but some active treatment arms have zero sample share.")
        e0_hat = m[:, [0]]
        baseline_floor = float(np.finfo(float).tiny)
        if np.any(~np.isfinite(e0_hat)) or np.any(e0_hat <= baseline_floor):
            raise RuntimeError(
                "ATTE requested but baseline propensity m_hat[:, 0] is numerically zero after trimming/clipping. "
                "Increase trimming_threshold or inspect overlap."
            )
        ratio = np.divide(
            m[:, 1:],
            e0_hat,
            out=np.full_like(m[:, 1:], np.nan, dtype=float),
            where=e0_hat > baseline_floor,
        )
        if np.any(~np.isfinite(ratio)):
            raise RuntimeError("ATTE requested but the e_k/e_0 ratio contains non-finite values.")
        psi_b = (dk / pk[None, :]) * residual0 - (d0 / pk[None, :]) * ratio * residual0
    psi_a = -np.ones_like(psi_b) if score_u == "ATE" else -dk / pk[None, :]
    psi = psi_b + psi_a * theta[None, :]
    return psi, psi_b, h, u


def _orthogonality_derivatives_ate(
    *,
    x_basis: np.ndarray,
    d: np.ndarray,
    m: np.ndarray,
    h: np.ndarray,
    u: np.ndarray,
    comparison_labels: List[str],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    n, b = x_basis.shape
    j = len(comparison_labels)

    rows: List[Dict[str, Any]] = []
    max_rows: List[Dict[str, Any]] = []

    for idx in range(j):
        k = idx + 1

        d_gk_terms = x_basis * (1.0 - h[:, k])[:, None]
        d_g0_terms = x_basis * (-1.0 + h[:, 0])[:, None]
        d_mk_terms = -x_basis * ((u[:, k] * d[:, k]) / (m[:, k] ** 2))[:, None]
        d_m0_terms = x_basis * ((u[:, 0] * d[:, 0]) / (m[:, 0] ** 2))[:, None]

        d_gk = d_gk_terms.mean(axis=0)
        d_g0 = d_g0_terms.mean(axis=0)
        d_mk = d_mk_terms.mean(axis=0)
        d_m0 = d_m0_terms.mean(axis=0)

        se_gk = d_gk_terms.std(axis=0, ddof=1) / np.sqrt(n) if n > 1 else np.full(b, np.nan)
        se_g0 = d_g0_terms.std(axis=0, ddof=1) / np.sqrt(n) if n > 1 else np.full(b, np.nan)
        se_mk = d_mk_terms.std(axis=0, ddof=1) / np.sqrt(n) if n > 1 else np.full(b, np.nan)
        se_m0 = d_m0_terms.std(axis=0, ddof=1) / np.sqrt(n) if n > 1 else np.full(b, np.nan)

        t_gk = d_gk / np.maximum(se_gk, 1e-12)
        t_g0 = d_g0 / np.maximum(se_g0, 1e-12)
        t_mk = d_mk / np.maximum(se_mk, 1e-12)
        t_m0 = d_m0 / np.maximum(se_m0, 1e-12)

        for basis_idx in range(b):
            rows.append(
                {
                    "comparison": comparison_labels[idx],
                    "basis": int(basis_idx),
                    "d_gk": float(d_gk[basis_idx]),
                    "se_gk": float(se_gk[basis_idx]),
                    "t_gk": float(t_gk[basis_idx]),
                    "d_g0": float(d_g0[basis_idx]),
                    "se_g0": float(se_g0[basis_idx]),
                    "t_g0": float(t_g0[basis_idx]),
                    "d_mk": float(d_mk[basis_idx]),
                    "se_mk": float(se_mk[basis_idx]),
                    "t_mk": float(t_mk[basis_idx]),
                    "d_m0": float(d_m0[basis_idx]),
                    "se_m0": float(se_m0[basis_idx]),
                    "t_m0": float(t_m0[basis_idx]),
                }
            )

        max_rows.append(
            {
                "comparison": comparison_labels[idx],
                "max_|t|_gk": float(np.nanmax(np.abs(t_gk))),
                "max_|t|_g0": float(np.nanmax(np.abs(t_g0))),
                "max_|t|_mk": float(np.nanmax(np.abs(t_mk))),
                "max_|t|_m0": float(np.nanmax(np.abs(t_m0))),
            }
        )

    max_df = pd.DataFrame(max_rows)
    max_df["max_|t|"] = np.nanmax(
        max_df[["max_|t|_gk", "max_|t|_g0", "max_|t|_mk", "max_|t|_m0"]].to_numpy(dtype=float),
        axis=1,
    )

    return pd.DataFrame(rows), max_df


def _orthogonality_derivatives_atte(
    *,
    x_basis: np.ndarray,
    y: np.ndarray,
    d: np.ndarray,
    g_hat: np.ndarray,
    m: np.ndarray,
    comparison_labels: List[str],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    n, b = x_basis.shape
    j = len(comparison_labels)

    rows: List[Dict[str, Any]] = []
    max_rows: List[Dict[str, Any]] = []

    g0_hat = g_hat[:, 0]
    residual0 = y - g0_hat
    d0 = d[:, 0].astype(float)

    for idx in range(j):
        k = idx + 1
        dk = d[:, k].astype(float)
        pk = float(np.mean(dk))
        if pk <= 0.0:
            raise RuntimeError("ATTE requested but some active treatment arms have zero sample share.")

        ratio = m[:, k] / m[:, 0]
        d_gk_terms = np.zeros((n, b), dtype=float)
        d_g0_terms = x_basis * (((d0 * ratio) - dk) / pk)[:, None]
        d_mk_terms = -x_basis * ((d0 * residual0) / (pk * m[:, 0]))[:, None]
        d_m0_terms = x_basis * ((d0 * residual0 * ratio) / (pk * m[:, 0]))[:, None]

        d_gk = d_gk_terms.mean(axis=0)
        d_g0 = d_g0_terms.mean(axis=0)
        d_mk = d_mk_terms.mean(axis=0)
        d_m0 = d_m0_terms.mean(axis=0)

        se_gk = d_gk_terms.std(axis=0, ddof=1) / np.sqrt(n) if n > 1 else np.full(b, np.nan)
        se_g0 = d_g0_terms.std(axis=0, ddof=1) / np.sqrt(n) if n > 1 else np.full(b, np.nan)
        se_mk = d_mk_terms.std(axis=0, ddof=1) / np.sqrt(n) if n > 1 else np.full(b, np.nan)
        se_m0 = d_m0_terms.std(axis=0, ddof=1) / np.sqrt(n) if n > 1 else np.full(b, np.nan)

        t_gk = np.zeros(b, dtype=float)
        t_g0 = d_g0 / np.maximum(se_g0, 1e-12)
        t_mk = d_mk / np.maximum(se_mk, 1e-12)
        t_m0 = d_m0 / np.maximum(se_m0, 1e-12)

        for basis_idx in range(b):
            rows.append(
                {
                    "comparison": comparison_labels[idx],
                    "basis": int(basis_idx),
                    "d_gk": float(d_gk[basis_idx]),
                    "se_gk": float(se_gk[basis_idx]),
                    "t_gk": float(t_gk[basis_idx]),
                    "d_g0": float(d_g0[basis_idx]),
                    "se_g0": float(se_g0[basis_idx]),
                    "t_g0": float(t_g0[basis_idx]),
                    "d_mk": float(d_mk[basis_idx]),
                    "se_mk": float(se_mk[basis_idx]),
                    "t_mk": float(t_mk[basis_idx]),
                    "d_m0": float(d_m0[basis_idx]),
                    "se_m0": float(se_m0[basis_idx]),
                    "t_m0": float(t_m0[basis_idx]),
                }
            )

        max_rows.append(
            {
                "comparison": comparison_labels[idx],
                "max_|t|_gk": float(np.nanmax(np.abs(t_gk))),
                "max_|t|_g0": float(np.nanmax(np.abs(t_g0))),
                "max_|t|_mk": float(np.nanmax(np.abs(t_mk))),
                "max_|t|_m0": float(np.nanmax(np.abs(t_m0))),
            }
        )

    max_df = pd.DataFrame(max_rows)
    max_df["max_|t|"] = np.nanmax(
        max_df[["max_|t|_gk", "max_|t|_g0", "max_|t|_mk", "max_|t|_m0"]].to_numpy(dtype=float),
        axis=1,
    )

    return pd.DataFrame(rows), max_df


def _influence_summary(
    *,
    psi: np.ndarray,
    m: np.ndarray,
    u: np.ndarray,
    comparison_labels: List[str],
    k_top: int = 10,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    n, j = psi.shape
    rows: List[Dict[str, Any]] = []
    top_rows: List[Dict[str, Any]] = []

    for idx in range(j):
        psi_j = psi[:, idx]

        se = float(np.std(psi_j, ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
        abs_psi = np.abs(psi_j)
        med = float(np.median(abs_psi)) if n > 0 else float("nan")
        p99 = float(np.quantile(abs_psi, 0.99)) if n > 0 else float("nan")

        var = float(np.var(psi_j, ddof=1)) if n > 1 else float("nan")
        if np.isfinite(var) and var > 0.0:
            kurt = float(np.mean((psi_j - float(np.mean(psi_j))) ** 4) / (var ** 2 + 1e-12))
        else:
            kurt = float("nan")

        rows.append(
            {
                "comparison": comparison_labels[idx],
                "se_plugin": se,
                "kurtosis": kurt,
                "p99_over_med": float(p99 / (med + 1e-12)) if np.isfinite(p99) and np.isfinite(med) else float("nan"),
            }
        )

        top_idx = np.argsort(-abs_psi)[: min(int(k_top), n)]
        for i in top_idx:
            top_rows.append(
                {
                    "comparison": comparison_labels[idx],
                    "i": int(i),
                    "psi": float(psi_j[i]),
                    "m_k": float(m[i, idx + 1]),
                    "residual_k": float(u[i, idx + 1]),
                    "residual_0": float(u[i, 0]),
                }
            )

    return pd.DataFrame(rows), pd.DataFrame(top_rows)


def _oos_moment_test(
    *,
    psi_b: np.ndarray,
    folds: Optional[np.ndarray],
    comparison_labels: List[str],
    psi_a: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """Describe fold stability for each linear score, without OOS inference.

    The binary helper supplies the same psi_a * theta + psi_b algebra per
    contrast. ATTE needs its ratio Jacobian; ATE defaults to minus one.
    Legacy t-statistics and p-values are unavailable in every case because
    cached cross-fitted scores do not provide an independent validation test.
    """
    psi_b = np.asarray(psi_b, dtype=float)
    n, j = psi_b.shape
    if len(comparison_labels) != j:
        raise ValueError("comparison_labels must match the number of score columns.")
    if psi_a is None:
        psi_a = -np.ones_like(psi_b)
    else:
        psi_a = np.asarray(psi_a, dtype=float)
        if psi_a.ndim == 1 and psi_a.size == n:
            psi_a = np.broadcast_to(psi_a[:, None], (n, j))
        if psi_a.shape != psi_b.shape:
            raise ValueError("psi_a must have shape (n,) or match psi_b shape (n, J).")
    folds_arr = None if folds is None else np.asarray(folds).ravel()
    valid_folds = folds_arr is not None and folds_arr.size == n
    rows = []
    tables = []
    for idx, comp in enumerate(comparison_labels):
        result = _oos_moment_test_from_psi(
            psi_a=psi_a[:, idx] if valid_folds else np.array([]),
            psi_b=psi_b[:, idx] if valid_folds else np.array([]),
            folds=folds_arr if valid_folds else np.array([]),
        )
        table = result.pop("fold_table")
        table.insert(0, "comparison", comp)
        tables.append(table)
        rows.append({"comparison": comp, **result})
    by_comp_df = pd.DataFrame(rows)
    fold_table = pd.concat(tables, ignore_index=True)
    return {
        "available": False,
        "inference_status": "unavailable",
        "reason": "Cached cross-fitted scores are reused; an independent OOS test is not calibrated.",
        "fold_diagnostics_available": bool(by_comp_df["fold_diagnostics_available"].all()),
        "by_comparison": by_comp_df,
        "fold_table": fold_table,
    }


def run_score_diagnostics(
    data: MultiCausalData,
    estimate: MultiCausalEstimate,
    *,
    trimming_threshold: Optional[float] = None,
    n_basis_funcs: Optional[int] = None,
    return_summary: bool = True,
) -> Dict[str, Any]:
    """Run score diagnostics for multi-treatment baseline contrasts.

    ``oos_moment_test`` reports descriptive fold stability by comparison,
    including effect ranges and leave-fold gaps. It reuses cached cross-fit
    scores, rather than refitting nuisances on a separate validation split.
    Consequently ``available=False``, legacy t-statistics and p-values are
    NaN, and ``flags['oos_moment']`` is ``NA``. Fold summaries are ungraded
    and do not certify model validity. ATTE fold solutions use the ratio
    Jacobian ``-d_k / p_k`` rather than a constant ATE Jacobian.
    Cached ATTE residuals incompatible with ``psi_b + psi_a * theta`` are
    reconstructed and identified in ``meta['psi_cache_status']``. This does
    not repair uncertainty intervals stored in an older estimate; re-estimate
    with the current model for corrected estimator inference.
    """

    if not isinstance(data, MultiCausalData):
        raise TypeError(f"data must be MultiCausalData, got {type(data).__name__}.")
    if not isinstance(estimate, MultiCausalEstimate):
        raise TypeError(
            f"estimate must be MultiCausalEstimate, got {type(estimate).__name__}."
        )

    _validate_estimate_matches_data(data=data, estimate=estimate)

    diag = estimate.diagnostic_data
    if diag is None:
        raise ValueError(
            "Missing estimate.diagnostic_data. "
            "Call estimate(diagnostic_data=True) first."
        )

    m_raw = getattr(diag, "m_hat", None)
    d_raw = getattr(diag, "d", None)
    g_hat_raw = getattr(diag, "g_hat", None)
    if m_raw is None or d_raw is None or g_hat_raw is None:
        raise ValueError("estimate.diagnostic_data must include `m_hat`, `d`, and `g_hat`.")

    score_raw = getattr(diag, "score", estimate.estimand)
    score = str(score_raw).upper()
    if score not in {"ATE", "ATTE"}:
        raise ValueError(
            "Multi-treatment score diagnostics support only ATE or ATTE. "
            f"Got score={score_raw!r}."
        )

    y_raw = getattr(diag, "y", None)
    if y_raw is None:
        y_raw = data.get_df()[str(data.outcome)].to_numpy(dtype=float)

    x_raw = getattr(diag, "x", None)
    if x_raw is None:
        x_raw = data.get_df()[list(data.confounders)].to_numpy(dtype=float)

    y = np.asarray(y_raw, dtype=float).reshape(-1)
    d = np.asarray(d_raw, dtype=float)
    g_hat = np.asarray(g_hat_raw, dtype=float)
    m = np.asarray(m_raw, dtype=float)
    x = np.asarray(x_raw, dtype=float)

    if d.ndim != 2 or m.ndim != 2 or g_hat.ndim != 2:
        raise ValueError("`d`, `m_hat`, and `g_hat` must be 2D arrays of shape (n, K).")
    if d.shape != m.shape or d.shape != g_hat.shape:
        raise ValueError("`d`, `m_hat`, and `g_hat` must have matching shape (n, K).")
    if x.ndim != 2:
        raise ValueError("Confounder matrix must be 2D with shape (n, p).")

    n, k = d.shape
    if y.size != n or x.shape[0] != n:
        raise ValueError("All diagnostic arrays must share the same sample size n.")
    if k < 2:
        raise ValueError("Need at least 2 treatment columns for multi-treatment score diagnostics.")

    d = (d > 0.5).astype(float)
    m = _normalize_rows_to_simplex(m)

    comparison_labels = _comparison_labels(_resolve_treatment_names(diag=diag, data=data, k=k))
    j = len(comparison_labels)
    theta = _resolve_theta(estimate.value, n_contrasts=j)

    trimming_thr = _resolve_trimming_threshold(trimming_threshold, diag, estimate)
    normalize_ipw = _resolve_normalize_ipw(score, diag, estimate)
    m_diag = _trim_multiclass_propensity(m, trimming_thr)

    x_basis = _build_basis(x=x, n_basis_funcs=n_basis_funcs)

    psi_comp, psi_b_comp, _, u = _compute_psi_from_nuisances(
        y=y,
        d=d,
        g_hat=g_hat,
        m=m_diag,
        theta=theta,
        score=score,
        normalize_ipw=normalize_ipw,
    )

    normalize_ipw_for_orthogonality = bool(normalize_ipw)
    if score == "ATTE":
        normalize_ipw_for_orthogonality = False
    elif normalize_ipw_for_orthogonality:
        warnings.warn(
            "Orthogonality derivatives are computed with normalize_ipw=False because "
            "m-derivatives for Hajek-normalized IPW are not implemented.",
            RuntimeWarning,
            stacklevel=2,
        )
        normalize_ipw_for_orthogonality = False
    h_ortho = _normalize_ipw_terms(
        d=d,
        m=m_diag,
        normalize_ipw=normalize_ipw_for_orthogonality,
    )

    psi_override = getattr(diag, "psi", None)
    used_estimator_psi = False
    psi_cache_status = "missing"
    if psi_override is not None:
        psi_override = np.asarray(psi_override, dtype=float)
        if psi_override.ndim == 1 and j == 1:
            psi_override = psi_override.reshape(-1, 1)
        if psi_override.shape == psi_comp.shape:
            psi = psi_override
            used_estimator_psi = True
            psi_cache_status = "used"
        else:
            psi = psi_comp
            psi_cache_status = "invalid_shape"
    else:
        psi = psi_comp

    psi_b_override = getattr(diag, "psi_b", None)
    if psi_b_override is not None:
        psi_b_override = np.asarray(psi_b_override, dtype=float)
        if psi_b_override.ndim == 1 and j == 1:
            psi_b_override = psi_b_override.reshape(-1, 1)
        if psi_b_override.shape == psi_b_comp.shape:
            psi_b = psi_b_override
        else:
            psi_b = psi_b_comp
    else:
        psi_b = psi_b_comp

    # Older diagnostic payloads lack psi_a. Reconstruct the correct score
    # Jacobian as a fallback; new payloads preserve the estimator's Jacobian.
    psi_a = (
        -np.ones_like(psi_b) if score == "ATE"
        else -d[:, 1:] / d[:, 1:].mean(axis=0)[None, :]
    )
    psi_a_override = getattr(diag, "psi_a", None)
    used_estimator_psi_a = False
    if psi_a_override is not None:
        psi_a_override = np.asarray(psi_a_override, dtype=float)
        if score == "ATE" and psi_a_override.ndim == 1 and psi_a_override.size == n:
            psi_a_override = np.broadcast_to(psi_a_override[:, None], psi_b.shape)
        if psi_a_override.shape == psi_b.shape:
            psi_a = psi_a_override
            used_estimator_psi_a = True
    reconstructed_psi = psi_b + psi_a * theta[None, :]
    if score == "ATTE" and used_estimator_psi and not np.allclose(
        psi, reconstructed_psi, rtol=1e-10, atol=1e-12, equal_nan=True,
    ):
        used_estimator_psi = False
        psi_cache_status = "inconsistent_atte_score"
    if not used_estimator_psi:
        psi = reconstructed_psi

    folds = getattr(diag, "folds", None)
    folds_arr = None if folds is None else np.asarray(folds).reshape(-1)

    finite_rows = (
        np.isfinite(y)
        & np.all(np.isfinite(d), axis=1)
        & np.all(np.isfinite(g_hat), axis=1)
        & np.all(np.isfinite(m_diag), axis=1)
        & np.all(np.isfinite(x_basis), axis=1)
        & np.all(np.isfinite(psi), axis=1)
        & np.all(np.isfinite(psi_b), axis=1)
        & np.all(np.isfinite(psi_a), axis=1)
        & np.all(np.isfinite(h_ortho), axis=1)
    )
    if folds_arr is not None and folds_arr.size == n:
        finite_rows = finite_rows & np.isfinite(folds_arr.astype(float))

    y = y[finite_rows]
    d = d[finite_rows]
    g_hat = g_hat[finite_rows]
    m_diag = m_diag[finite_rows]
    x_basis = x_basis[finite_rows]
    psi = psi[finite_rows]
    psi_b = psi_b[finite_rows]
    psi_a = psi_a[finite_rows]
    h_ortho = h_ortho[finite_rows]
    u = u[finite_rows]
    folds_arr = folds_arr[finite_rows] if folds_arr is not None and folds_arr.size == n else None

    if score == "ATE":
        ortho_df, ortho_max = _orthogonality_derivatives_ate(
            x_basis=x_basis,
            d=d,
            m=m_diag,
            h=h_ortho,
            u=u,
            comparison_labels=comparison_labels,
        )
    else:
        ortho_df, ortho_max = _orthogonality_derivatives_atte(
            x_basis=x_basis,
            y=y,
            d=d,
            g_hat=g_hat,
            m=m_diag,
            comparison_labels=comparison_labels,
        )

    infl_df, top_influential = _influence_summary(
        psi=psi,
        m=m_diag,
        u=u,
        comparison_labels=comparison_labels,
    )

    oos = _oos_moment_test(psi_a=psi_a, psi_b=psi_b, folds=folds_arr, comparison_labels=comparison_labels)
    oos_df = oos["by_comparison"].copy()

    comp_diag = infl_df.merge(ortho_max, on="comparison", how="left")
    comp_diag = comp_diag.merge(oos_df, on="comparison", how="left")

    thresholds = {
        "tail_ratio_warn": 10.0,
        "tail_ratio_strong": 20.0,
        "kurt_warn": 10.0,
        "kurt_strong": 30.0,
        "t_warn": 2.0,
        "t_strong": 4.0,
    }

    def _worst_flag(flags: List[str]) -> str:
        level = {"NA": -1, "GREEN": 0, "YELLOW": 1, "RED": 2}
        inv_level = {v: k for k, v in level.items()}
        return inv_level[max(level.get(flag, -1) for flag in flags)]

    flag_rows: List[Dict[str, Any]] = []
    summary_rows: List[Dict[str, Any]] = []

    for row in comp_diag.to_dict(orient="records"):
        comparison = str(row["comparison"])
        flag_tail = _grade(float(row["p99_over_med"]), thresholds["tail_ratio_warn"], thresholds["tail_ratio_strong"])
        flag_kurt = _grade(float(row["kurtosis"]), thresholds["kurt_warn"], thresholds["kurt_strong"])
        flag_ortho = _grade(float(row["max_|t|"]), thresholds["t_warn"], thresholds["t_strong"])

        flag_oos = "NA"

        overall_flag_comp = _worst_flag([flag_tail, flag_kurt, flag_ortho, flag_oos])

        flag_rows.append(
            {
                "comparison": comparison,
                "psi_tail_ratio": flag_tail,
                "psi_kurtosis": flag_kurt,
                "ortho_max_|t|": flag_ortho,
                "oos_moment": flag_oos,
                "overall_flag": overall_flag_comp,
            }
        )

        summary_rows.extend(
            [
                {"comparison": comparison, "metric": "se_plugin", "value": float(row["se_plugin"]), "flag": "NA"},
                {"comparison": comparison, "metric": "psi_p99_over_med", "value": float(row["p99_over_med"]), "flag": flag_tail},
                {"comparison": comparison, "metric": "psi_kurtosis", "value": float(row["kurtosis"]), "flag": flag_kurt},
                {"comparison": comparison, "metric": "max_|t|_gk", "value": float(row["max_|t|_gk"]), "flag": flag_ortho},
                {"comparison": comparison, "metric": "max_|t|_g0", "value": float(row["max_|t|_g0"]), "flag": flag_ortho},
                {"comparison": comparison, "metric": "max_|t|_mk", "value": float(row["max_|t|_mk"]), "flag": flag_ortho},
                {"comparison": comparison, "metric": "max_|t|_m0", "value": float(row["max_|t|_m0"]), "flag": flag_ortho},
                {"comparison": comparison, "metric": "max_|t|", "value": float(row["max_|t|"]), "flag": flag_ortho},
                {"comparison": comparison, "metric": "oos_tstat_fold", "value": float(row["oos_tstat_fold"]), "flag": flag_oos},
                {"comparison": comparison, "metric": "oos_tstat_strict", "value": float(row["oos_tstat_strict"]), "flag": flag_oos},
                *[
                    {"comparison": comparison, "metric": metric, "value": float(row[metric]), "flag": "NA"}
                    for metric in (
                        "fold_score_mean_rms", "fold_score_mean_max_abs",
                        "fold_theta_range", "fold_theta_gap_max_abs",
                    )
                ],
            ]
        )

    flags_by_comp = pd.DataFrame(flag_rows)

    if flags_by_comp.empty:
        global_flags = {
            "psi_tail_ratio": "NA",
            "psi_kurtosis": "NA",
            "ortho_max_|t|_gk": "NA",
            "ortho_max_|t|_g0": "NA",
            "ortho_max_|t|_mk": "NA",
            "ortho_max_|t|_m0": "NA",
            "ortho_max_|t|": "NA",
            "oos_moment": "NA",
        }
        overall_flag = "NA"
    else:
        global_flags = {
            "psi_tail_ratio": _worst_flag(flags_by_comp["psi_tail_ratio"].tolist()),
            "psi_kurtosis": _worst_flag(flags_by_comp["psi_kurtosis"].tolist()),
            "ortho_max_|t|": _worst_flag(flags_by_comp["ortho_max_|t|"].tolist()),
            "oos_moment": _worst_flag(flags_by_comp["oos_moment"].tolist()),
            "ortho_max_|t|_gk": _grade(float(np.nanmax(comp_diag["max_|t|_gk"].to_numpy(dtype=float))), thresholds["t_warn"], thresholds["t_strong"]),
            "ortho_max_|t|_g0": _grade(float(np.nanmax(comp_diag["max_|t|_g0"].to_numpy(dtype=float))), thresholds["t_warn"], thresholds["t_strong"]),
            "ortho_max_|t|_mk": _grade(float(np.nanmax(comp_diag["max_|t|_mk"].to_numpy(dtype=float))), thresholds["t_warn"], thresholds["t_strong"]),
            "ortho_max_|t|_m0": _grade(float(np.nanmax(comp_diag["max_|t|_m0"].to_numpy(dtype=float))), thresholds["t_warn"], thresholds["t_strong"]),
        }
        overall_flag = _worst_flag(list(global_flags.values()))

    report: Dict[str, Any] = {
        "params": {
            "score": score,
            "trimming_threshold": float(trimming_thr),
            "normalize_ipw": bool(normalize_ipw),
            "orthogonality_normalize_ipw": bool(normalize_ipw_for_orthogonality),
        },
        "orthogonality_derivatives": ortho_df,
        "orthogonality_max_t": ortho_max,
        "influence_diagnostics": {
            "by_comparison": infl_df,
            "top_influential": top_influential,
        },
        "oos_moment_test": oos,
        "flags": global_flags,
        "flags_by_comparison": flags_by_comp,
        "thresholds": thresholds,
        "overall_flag": overall_flag,
        "meta": {
            "n": int(y.size),
            "K": int(k),
            "comparisons": list(comparison_labels),
            "used_estimator_psi": bool(used_estimator_psi),
            "used_estimator_psi_a": bool(used_estimator_psi_a),
            "psi_cache_status": psi_cache_status,
            "orthogonality_derivatives_use_score_normalization": bool(
                normalize_ipw_for_orthogonality == normalize_ipw
            ),
        },
    }

    if return_summary:
        summary = pd.DataFrame(
            summary_rows,
            columns=["comparison", "metric", "value", "flag"],
        )
        report["summary"] = summary

    return report


__all__ = ["run_score_diagnostics"]
