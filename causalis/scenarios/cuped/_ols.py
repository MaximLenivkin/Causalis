"""Owned design factorization and a small public statsmodels result adapter."""
from dataclasses import dataclass

import numpy as np
from statsmodels.regression.linear_model import OLSResults


@dataclass(frozen=True)
class OLSDesign:
    pinv: np.ndarray
    normalized_covariance: np.ndarray
    singular_values: np.ndarray
    leverage: np.ndarray
    rank: int
    condition: float


def factor_design(z: np.ndarray) -> OLSDesign:
    """Factor the design itself; never square its condition number via X'X.

    The validation rank uses NumPy's default matrix_rank tolerance. The
    pseudoinverse uses the statsmodels pinv_extended relative cutoff (1e-15).
    CUPED's full-rank guard is applied by the caller; standalone diagnostics
    can also use this projection for a rank-deficient design.
    """
    z = np.asarray(z, dtype=float)
    u, singular, vt = np.linalg.svd(z, full_matrices=False)
    largest = singular[0] if singular.size else 0.
    retained = singular > 1e-15 * largest
    inverse = np.zeros_like(singular)
    np.divide(1., singular, out=inverse, where=retained)
    pinv = (vt.T * inverse) @ u.T
    covariance = pinv @ pinv.T
    h = np.sum(u[:, retained] ** 2, axis=1)
    rank = int(np.sum(singular > largest * max(z.shape) * np.finfo(float).eps))
    condition = float(largest / singular[-1]) if singular.size and singular[-1] > 0 else np.inf
    for array in (pinv, covariance, singular, h):
        array.setflags(write=False)
    return OLSDesign(pinv, covariance, singular, h, rank, condition)


class StableOLSResults(OLSResults):
    """OLSResults with HC2/HC3 using the design's stable projection diagonal.

    statsmodels' public constructor supplies inference and result methods.
    HC2/HC3 properties are overridden because contracting X(P P')X' can
    suffer cancellation for near-collinear designs even with a stable P.
    """

    def _stable_hc(self, power: int) -> np.ndarray:
        design = self.model._cuped_design
        # Keep the ordinary HC2/HC3 formula, including its h=1 degeneracy.
        self.het_scale = self.wresid ** 2 / (1. - design.leverage) ** power
        return (design.pinv * self.het_scale) @ design.pinv.T

    @property
    def cov_HC2(self) -> np.ndarray:
        return self._stable_hc(1)

    @property
    def cov_HC3(self) -> np.ndarray:
        return self._stable_hc(2)


def fit_from_design(model, design: OLSDesign, params: np.ndarray,
                    cov_type: str, use_t: bool) -> OLSResults:
    """Create results without invoking OLS.fit or writing its private cache.

    These model attributes are the protocol used by public OLSResults for
    HC covariance and degrees of freedom. Their values belong to the shared
    design; coefficients, residuals and covariance remain outcome-specific.
    Keep version compatibility checks concentrated in this adapter.
    """
    model.pinv_wexog = design.pinv
    model.normalized_cov_params = design.normalized_covariance
    model.wexog_singular_values = design.singular_values
    model.rank = design.rank
    model._cuped_design = design
    return StableOLSResults(model, params, normalized_cov_params=design.normalized_covariance,
                            cov_type=cov_type, use_t=use_t)
