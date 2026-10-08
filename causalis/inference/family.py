"""IID influence-function inference with Bonferroni or Gaussian max-t bands."""
from dataclasses import dataclass
from numbers import Integral, Real
from collections.abc import Mapping

import numpy as np
import pandas as pd
from scipy.stats import norm

from causalis.scenarios._numerics import _checked_arithmetic, _require_finite
from causalis.scenarios._prediction import _real_array, _prediction_vector


def _names(names, size):
    if isinstance(names, str):
        raise ValueError("names must be a sequence of unique nonempty strings")
    names = tuple(names)
    if (len(names) != size or any(not isinstance(n, str) or not n for n in names)
            or len(set(names)) != size):
        raise ValueError("names must contain one unique nonempty string per estimand")
    return names


@dataclass(frozen=True)
class FamilyInferenceResult:
    """Owned aggregate inference; summary() returns a fresh DataFrame.

    Intervals are simultaneous, two-sided, absolute-scale bands centered on
    estimates. P-values test the supplied nulls; adjusted p-values control the
    declared family asymptotically, subject to valid input influence functions.
    Gaussian max-t p-values use (1 + exceedances)/(n_boot + 1), including ties.
    No observation-level influences or bootstrap draws are returned.
    """

    names: tuple
    estimates: tuple
    std_errors: tuple
    null_values: tuple
    p_values: tuple
    adjusted_p_values: tuple
    ci_lower: tuple
    ci_upper: tuple
    alpha: float
    method: str
    critical_value: float
    n_observations: int
    n_boot: int
    random_state: object

    def summary(self):
        """Return aggregate rows, with rejection defined by adjusted p <= alpha."""
        return pd.DataFrame({
            "estimate": self.estimates, "std_error": self.std_errors,
            "null_value": self.null_values, "p_value": self.p_values,
            "p_value_adjusted": self.adjusted_p_values,
            "ci_lower": self.ci_lower, "ci_upper": self.ci_upper,
            "is_significant": np.asarray(self.adjusted_p_values) <= self.alpha,
        }, index=pd.Index(self.names, name="estimand"))


class InferenceFamily:
    """Snapshot a fixed family of estimates and aligned iid influences.

    `values` has shape (p,), `influence` shape (n, p), and `names` length p.
    An influence column is on the observation scale: theta_hat - theta equals
    mean(IF) plus an asymptotically negligible remainder. It is NOT already
    divided by n. Rows must describe the same independent observational units
    across all columns. Inputs are copied; columns are empirically centered.
    Covariance is IF_centered.T @ IF_centered / (n * (n - 1)).

    Validity requires a jointly asymptotically linear estimator, adequate
    moments, nondegenerate variances and a prespecified family. For causal IRM
    this additionally requires identification, overlap and appropriate nuisance
    convergence. This API cannot verify those assumptions or selection history.
    Neither method certifies finite-sample coverage or arbitrary growing p.
    Cluster, repeated-split and pointwise CATE inference need other contracts.
    """

    @_checked_arithmetic
    def __init__(self, values, influence, names):
        values = _real_array(values, name="estimates")
        influence = _real_array(influence, name="influence")
        if (values.ndim != 1 or values.size == 0 or influence.ndim != 2
                or influence.shape[1] != values.size or influence.shape[0] < 2):
            raise ValueError("Require values (p,), influence (n, p), p >= 1, n >= 2")
        self._names = _names(names, values.size)
        self._values = values.copy()
        self._influence = influence - influence.mean(axis=0)
        self._n = len(influence)
        # Scale before squaring; retain tiny but nonzero influences and avoid
        # needless overflow for large finite columns. True covariance overflow
        # still fails rather than silently repairing an input.
        scale = np.max(np.abs(self._influence), axis=0)
        if np.any(scale == 0):
            raise ValueError("Every estimand must have positive influence variance")
        scaled = self._influence / scale
        length = np.sqrt(np.sum(scaled ** 2, axis=0))
        self._unit = scaled / length
        self._se = (scale / np.sqrt(self._n)) * (length / np.sqrt(self._n - 1))
        if np.any(self._se <= 0):
            raise ValueError("Standard errors must be positive; rescale the estimands")
        self._covariance = (self._unit.T @ self._unit) * self._se[:, None] * self._se[None, :]
        _require_finite(self._influence, self._se, self._covariance)
        if np.any(np.diag(self._covariance) <= 0):
            raise ValueError("Covariance diagonal underflowed; rescale the estimands")

    @property
    def covariance(self):
        """Return a detached covariance matrix of the estimates, not raw IFs."""
        return self._covariance.copy()

    @_checked_arithmetic
    def contrast(self, matrix, names):
        """Create a new prespecified linear family: L theta, IF L.T.

        L must have shape (q, p). Singular joint covariance is permitted;
        a contrast with zero empirical variance is rejected.
        """
        matrix = _real_array(matrix, name="contrast matrix")
        if matrix.ndim != 2 or matrix.shape[1] != len(self._values) or not len(matrix):
            raise ValueError("contrast matrix must have shape (q, p), q >= 1")
        return type(self)(matrix @ self._values, self._influence @ matrix.T, names)

    @classmethod
    def from_irm(cls, models, *, score="ATE"):
        """Snapshot a named mapping of supported fitted binary IRMs.

        Supports absolute ATE or ATTE across outcomes on the same ordered,
        unique, nonmissing stable user IDs and treatment vector. Current data
        must still match each fit snapshot. Only internal single-partition iid,
        unweighted clip fits with normalize_ipw=False are supported. Different
        features/folds are allowed. No fit, predict, RNG draw, source inference
        cache update or diagnostics construction occurs. Active clipping can
        bias the target; the family method does not cure nuisance bias.
        """
        from causalis.scenarios.unconfoundedness.model import IRM
        from sklearn.utils.validation import check_is_fitted

        if not isinstance(models, Mapping) or not models:
            raise ValueError("models must be a nonempty named mapping of fitted IRMs")
        names = _names(models.keys(), len(models))
        if score not in {"ATE", "ATTE"}:
            raise ValueError("score must be ATE or ATTE")
        values, columns = [], []
        reference = None
        for model in models.values():
            if not isinstance(model, IRM):
                raise TypeError("Each model must be a fitted binary IRM")
            if hasattr(model, "_fit_repetitions_"):
                raise NotImplementedError("Family adapter requires a single-partition IRM")
            check_is_fitted(model, attributes=["g0_hat_", "g1_hat_", "m_hat_"])
            if (getattr(model, "_fit_external_oof_", False)
                    or getattr(model, "_fit_cluster_codes_", None) is not None
                    or getattr(model, "_fit_weights_used_", False)
                    or getattr(model, "_fit_overlap_policy_", None) != "clip"
                    or model.normalize_ipw):
                raise NotImplementedError("Require internal iid unweighted clip IRM with normalize_ipw=False")
            roles = (model.data.outcome_name, model.data.treatment_name,
                     tuple(model.data.confounders), model.data.user_id_name)
            if roles != model._fit_data_roles_ or roles[3] is None:
                raise ValueError("Unchanged fitted data roles and stable user IDs are required")
            ids = pd.Index(model.data.user_id.copy(), name=roles[3])
            if ids.hasnans or not ids.is_unique or not ids.equals(model._fit_index_):
                raise ValueError("Unique nonmissing ordered user IDs must match the IRM fit")
            X = _real_array(model.data.X.to_numpy(), name="IRM features")
            y = _prediction_vector(model.data.outcome.to_numpy(), len(ids), name="IRM outcomes")
            d = _prediction_vector(model.data.treatment.to_numpy(), len(ids), name="IRM treatment")
            if not np.all(np.isin(d, [0, 1])):
                raise ValueError("IRM treatment must remain binary")
            model._validate_current_data_matches_fit(X=X, y=y, d=d)
            if reference is None:
                reference = (ids, roles[1], d.copy())
            elif (not ids.equals(reference[0]) or roles[1] != reference[1]
                  or not np.array_equal(d, reference[2])):
                raise ValueError("All IRMs must use the same ordered IDs and treatment")
            g0, g1, e = (_prediction_vector(getattr(model, attr), len(ids), name=attr).copy()
                         for attr in ("g0_hat_", "g1_hat_", "m_hat_"))
            if np.any((e <= 0) | (e >= 1)):
                raise ValueError("IRM propensities must be strictly interior")
            components = model._compute_estimate_components(
                y=y.copy(), d=d.copy(), g0_hat=g0, g1_hat=g1, m_hat=e, score=score)
            value, influence, *_ = model._solve_moment_equation(
                psi_a=components["psi_a"], psi_b=components["psi_b"], alpha=.05)
            values.append(value)
            columns.append(influence)
        return cls(values, np.column_stack(columns), names)

    @_checked_arithmetic
    def infer(self, *, alpha=.05, method="bonferroni", null=0., n_boot=999,
              random_state=None):
        """Return two-sided family bands and adjusted tests without refitting.

        Methods are `bonferroni` (normal marginal tests; no random draws) and
        `max-t` (Gaussian multipliers shared across columns). Max-t requires
        integer n_boot >= 99, alpha >= 1/(n_boot+1), and None or a uint32 seed.
        It draws at most 256*n multipliers at a time with a local Generator;
        no source/global RNG is consumed. No exact cross-version RNG promise.
        Its critical value is ordered draw ceil((1-alpha)*(B+1)), one-based,
        so bands and corrected p-values use the same finite-draw convention.
        Null may be a scalar or (p,) vector; intervals stay centered on values.
        n_boot/random_state are used only for max-t and reported as 0/None for
        Bonferroni. Max-t performs score perturbation, not a pipeline refit.
        """
        if (isinstance(alpha, (bool, np.bool_)) or not isinstance(alpha, Real)
                or not np.isfinite(alpha) or not 0 < alpha < 1):
            raise ValueError("alpha must be a real number in (0, 1)")
        if method not in {"bonferroni", "max-t"}:
            raise ValueError("method must be bonferroni or max-t")
        null = _real_array(null, name="null")
        if null.ndim == 0:
            null = np.full(len(self._values), float(null))
        if null.shape != self._values.shape:
            raise ValueError("null must be a scalar or one value per estimand")
        statistic = np.abs((self._values - null) / self._se)
        _require_finite(statistic)
        p_values = 2 * norm.sf(statistic)
        if method == "bonferroni":
            critical = float(norm.isf(alpha / (2 * len(self._values))))
            adjusted = np.minimum(1., len(self._values) * p_values)
            n_boot, random_state = 0, None
        else:
            if (isinstance(n_boot, (bool, np.bool_)) or not isinstance(n_boot, Integral)
                    or n_boot < 99 or alpha < 1 / (int(n_boot) + 1)):
                raise ValueError("max-t requires integer n_boot >= 99 and alpha >= 1/(n_boot+1)")
            if random_state is not None and (
                    isinstance(random_state, (bool, np.bool_))
                    or not isinstance(random_state, Integral)
                    or not 0 <= random_state <= np.iinfo(np.uint32).max):
                raise ValueError("random_state must be None or a uint32 integer")
            n_boot = int(n_boot)
            random_state = None if random_state is None else int(random_state)
            rng = np.random.default_rng(random_state)
            maxima = np.empty(n_boot)
            for start in range(0, n_boot, 256):
                stop = min(start + 256, n_boot)
                perturbed = rng.normal(size=(stop - start, self._n)) @ self._unit
                maxima[start:stop] = np.max(np.abs(perturbed), axis=1)
            _require_finite(maxima)
            adjusted = np.array([(1 + np.count_nonzero(maxima >= t)) / (n_boot + 1)
                                 for t in statistic])
            rank = min(n_boot, int(np.ceil((1 - alpha) * (n_boot + 1))))
            critical = float(np.partition(maxima, rank - 1)[rank - 1])
        lower, upper = self._values - critical * self._se, self._values + critical * self._se
        _require_finite(critical, p_values, adjusted, lower, upper)
        return FamilyInferenceResult(
            names=self._names, estimates=tuple(map(float, self._values)),
            std_errors=tuple(map(float, self._se)), null_values=tuple(map(float, null)),
            p_values=tuple(map(float, p_values)), adjusted_p_values=tuple(map(float, adjusted)),
            ci_lower=tuple(map(float, lower)), ci_upper=tuple(map(float, upper)),
            alpha=float(alpha), method=method, critical_value=critical,
            n_observations=self._n, n_boot=n_boot, random_state=random_state)
