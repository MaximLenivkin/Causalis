"""Cross-fitted DR and R effect regressions for binary, iid IRM fits."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.linear_model import LinearRegression
from sklearn.utils.validation import check_is_fitted

from causalis.scenarios._prediction import _prediction_vector, _real_array
from causalis.scenarios.unconfoundedness.model import IRM
from causalis.scenarios.unconfoundedness._utils import _safe_is_classifier


def _oof_training_sample(irm):
    """Validate the supported fit and detach aligned sample and OOF arrays."""
    if not isinstance(irm, IRM):
        raise TypeError("fit requires a fitted binary IRM.")
    if hasattr(irm, "_fit_repetitions_"):
        raise NotImplementedError("DR/R learners require a single-partition IRM fit.")
    check_is_fitted(irm, attributes=["g0_hat_", "g1_hat_", "m_hat_"])
    if getattr(irm, "_fit_external_oof_", False):
        raise NotImplementedError("DR/R learners do not support external OOF IRM fits.")
    if getattr(irm, "_fit_cluster_codes_", None) is not None:
        raise NotImplementedError("DR/R learners do not support cluster IRM fits.")
    if getattr(irm, "_fit_overlap_policy_", None) != "clip":
        raise NotImplementedError("DR/R learners require an overlap clip IRM fit.")
    if getattr(irm, "_fit_weights_used_", False):
        raise NotImplementedError("DR/R learners do not support custom-weight IRM fits.")
    roles = (irm.data.outcome_name, irm.data.treatment_name,
             tuple(irm.data.confounders), irm.data.user_id_name)
    names = roles[2]
    if not names:
        raise ValueError("DR/R learners require at least one confounder.")
    if roles != irm._fit_data_roles_:
        raise RuntimeError("Current data roles differ from the IRM fit; refit IRM.")
    # IRM's historical reload casts to float. Validate the current raw values
    # first so even zero-imaginary complex mutations cannot pass that cast.
    _real_array(irm.data.X.to_numpy(), name="CATE training features")
    _real_array(irm.data.outcome.to_numpy(), name="CATE outcomes")
    _real_array(irm.data.treatment.to_numpy(), name="CATE treatments")
    X, y, d, _ = irm._check_data()
    irm._validate_current_data_matches_fit(X=X, y=y, d=d)
    X = _real_array(X, name="CATE training features").copy()
    n = len(y)
    y = _prediction_vector(y, n, name="CATE outcomes").copy()
    d = _prediction_vector(d, n, name="CATE treatments").copy()
    g0, g1, e = (_prediction_vector(getattr(irm, name), n, name=name).copy()
                 for name in ("g0_hat_", "g1_hat_", "m_hat_"))
    if np.any((e <= 0) | (e >= 1)):
        raise ValueError("DR/R learners require all fitted propensities strictly inside (0, 1).")
    folds = np.asarray(irm._full_sample_folds_).copy()
    if folds.shape != (n,) or folds.dtype.kind not in "iu" or np.any(folds < 0):
        raise ValueError("IRM OOF fold assignments must be an aligned integer vector.")
    return X, y, d, g0, g1, e, names, folds


def _scoring_features(X, names):
    """Resolve a new batch against the predictor's frozen feature schema."""
    if isinstance(X, pd.DataFrame):
        if not X.columns.is_unique:
            raise ValueError("Scoring DataFrame columns must be unique.")
        missing = [name for name in names if name not in X.columns]
        if missing:
            raise ValueError(f"Scoring data is missing required feature columns: {missing}.")
        X = X.loc[:, list(names)].to_numpy()
    array = _real_array(X, name="CATE scoring features")
    if array.ndim == 1:
        array = array.reshape(1, -1)
    if array.ndim != 2 or array.shape[1] != len(names):
        raise ValueError(f"CATE scoring features must have shape (n, {len(names)}).")
    return array.copy()


class _EffectLearner(RegressorMixin, BaseEstimator):
    """Own the final regression lifecycle without changing the source IRM."""

    def __init__(self, ml_tau=None):
        self.ml_tau = ml_tau

    def fit(self, irm):
        """Fit a cloned final regressor to one supported IRM's OOF signals.

        `irm` must be an internally fitted, single-partition, iid, unweighted
        binary IRM with clipping. Current sample and roles must still match its
        fit snapshot. No nuisance learner is refitted. A failed refit preserves
        this predictor's previous complete fit. ATE/ATTE and IPW normalization
        on the IRM do not change the conditional-effect target here.
        """
        X, y, d, g0, g1, e, names, folds = _oof_training_sample(irm)
        template = LinearRegression() if self.ml_tau is None else self.ml_tau
        if _safe_is_classifier(template):
            raise TypeError("ml_tau must be a regressor for real conditional effects.")
        if not callable(getattr(template, "fit", None)) or not callable(getattr(template, "predict", None)):
            raise TypeError("ml_tau must provide fit and predict and support sklearn.clone.")
        model = clone(template)
        with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
            if self._method == "DR":
                target = g1 - g0 + d * (y - g1) / e - (1 - d) * (y - g0) / (1 - e)
                target = _prediction_vector(target, len(y), name="DR pseudo-outcomes")
            else:
                q = (1 - e) * g0 + e * g1
                residual_d = d - e
                target = _prediction_vector((y - q) / residual_d, len(y), name="R targets")
                weights = _prediction_vector(residual_d ** 2, len(y), name="R sample weights")
                if np.any(weights <= 0):
                    raise ValueError("R sample weights must be positive; residual squares underflowed.")
        if self._method == "DR":
            model.fit(X, target)
        else:
            # Passing weights is mandatory. A learner without this argument
            # fails here; it must never silently become an unweighted U-learner.
            model.fit(X, target, sample_weight=weights)
        self.__dict__.update(model_=model, _feature_names_=tuple(names),
                             feature_names_in_=np.asarray(names, dtype=object),
                             n_features_in_=len(names), n_training_samples_=len(y),
                             nuisance_folds_=folds)
        return self

    def predict(self, X):
        """Return one finite, real CATE prediction per row in the fitted schema.

        DataFrames may reorder columns or include extras; required columns must
        exist and all column names must be unique. Arrays are positional; a 1D
        array represents one observation. Empty batches return an empty vector.
        For binary outcomes predictions are risk differences and are not clipped
        to [-1, 1]. Training-row predictions are in-sample at the final stage.
        """
        check_is_fitted(self, attributes=["model_", "_feature_names_"])
        array = _scoring_features(X, self._feature_names_)
        if len(array) == 0:
            return np.empty(0, dtype=float)
        return _prediction_vector(self.model_.predict(array), len(array),
                                  name="CATE predictions").copy()


class DRLearner(_EffectLearner):
    """Regress unnormalized OOF AIPW pseudo-outcomes on confounders.

    `ml_tau` is a cloneable regressor (default: LinearRegression). Target:
    E[Y(1)-Y(0) | X=x], identified by consistency, unconfoundedness and overlap.
    The final regression pools all rows; a restricted learner approximates the
    CATE. Nuisance OOF predictions do not make final training predictions honest
    validation. Use independent data or outer refits of the entire pipeline to
    evaluate or tune. Hidden preprocessing must respect nuisance training folds.
    No automatic calibration, CATE intervals, individual effects or convergence
    guarantee is provided. This pooled construction does not certify the
    independent-sample assumptions of Kennedy's DR-learner theorem.

    Example: `DRLearner().fit(irm).predict(X_new)`, where `irm` is already fitted.
    """

    _method = "DR"


class RLearner(_EffectLearner):
    """Fit the OOF squared residual R loss with a weighted regressor.

    `ml_tau` is a cloneable squared-loss regressor supporting and honoring
    `sample_weight` (default: LinearRegression). The OOF marginal outcome pilot
    is q=(1-e)*g0+e*g1, using IRM's clipped propensity and arm outcome pilots;
    this differs from fitting a separate E[Y|X] learner. Targets are (Y-q)/(D-e)
    and weights (D-e)^2, without further clipping or normalization. The caller's
    estimator controls regularization and weight handling. Under misspecification,
    the population R-loss projection weights X by e(X)*(1-e(X)).

    The causal target and validation restrictions are the same as DRLearner:
    binary treatment, iid data, consistency, unconfoundedness, overlap, and no
    automatic intervals or rate guarantee. Final-stage training predictions
    require independent evaluation. Example: `RLearner().fit(irm).predict(X_new)`.
    """

    _method = "R"


__all__ = ["DRLearner", "RLearner"]
