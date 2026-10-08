"""Aggregate nuisance and effect diagnostics on an independent binary sample."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, clone
from sklearn.utils.validation import check_is_fitted

from causalis.data_contracts import CausalData
from causalis.scenarios._prediction import _prediction_vector
from causalis.scenarios.unconfoundedness._utils import _is_binary, _predict_prob_or_value
from causalis.scenarios.uplift.learners import DRLearner, RLearner, _oof_training_sample, _scoring_features
from causalis.scenarios.uplift.model import _fit_arm_model


@dataclass(frozen=True)
class CATEValidationResult:
    """Finite aggregate diagnostics, without causal confidence intervals.

    DR loss includes pseudo-outcome noise; it is not measured CATE MSE. The
    gain is zero-effect loss minus candidate loss on the same sample/pilots.
    R loss weights CATE errors by overlap when its pilots are correct. Arm
    outcome MSEs describe factual, arm-specific covariate distributions.
    Propensity Brier/log loss use probabilities before overlap clipping.
    """

    n: int
    n_control: int
    n_treated: int
    outcome_mse_control: float
    outcome_mse_treated: float
    propensity_brier: float
    propensity_log_loss: float
    propensity_min: float
    propensity_max: float
    n_propensity_clipped: int
    mean_cate: float
    mean_dr_signal: float
    dr_loss: float
    dr_gain_vs_zero: float
    r_loss: float


def _identities(data):
    """Require caller-supplied stable identities, rather than row positions."""
    if not data.user_id_name:
        raise ValueError("Held-out validation requires a stable user_id column on both samples.")
    ids = pd.Index(data.user_id.copy())
    if ids.hasnans or not ids.is_unique:
        raise ValueError("Validation identities must be nonmissing and unique.")
    return ids


class HeldOutCATEValidation(BaseEstimator):
    """Own a DR/R learner and full-training nuisance models for held-out scoring.

    `learner` is an unfitted DRLearner/RLearner template (default: DRLearner).
    `fit(irm)` requires B25's internal single-partition iid unweighted binary
    IRM with clipping and stable unique user_id values. It clones and fits the
    effect learner on IRM's OOF signals and refits the *current* ml_g/ml_m
    templates on training data only. These evaluation pilots are separate
    from the discarded fold models. Failed refits retain the previous fit.

    `evaluate(data)` checks disjoint identities, matching roles/features and
    finite real binary-treatment observations, then returns aggregate factual
    nuisance metrics and surrogate DR/R losses. No models fit during evaluate.
    Identity checks cannot certify independence, relabelled duplicates, hidden
    preprocessing, or tuning history. The caller must reserve the entire
    validation sample before preprocessing/tuning any training component.
    Selecting models with this sample makes it validation, not a final test;
    use another independent test or nested outer full-pipeline refits.

    Identification of E[Y(1)-Y(0)|X] requires consistency, unconfoundedness,
    overlap and iid sampling. These metrics do not test unconfoundedness,
    certify CATE calibration, or provide individual effects/causal intervals.
    Compare losses only with the same validation sample and evaluation pilots.
    For R, q=(1-e)*g0+e*g1; no separate marginal-outcome learner is fitted.
    """

    def __init__(self, learner=None):
        self.learner = learner

    def fit(self, irm):
        """Fit owned models using only a supported IRM's training sample."""
        X, y, d, _, _, _, names, _ = _oof_training_sample(irm)
        ids = _identities(irm.data)
        template = DRLearner() if self.learner is None else self.learner
        if not isinstance(template, (DRLearner, RLearner)):
            raise TypeError("learner must be a DRLearner or RLearner template.")
        effect = clone(template).fit(irm)
        binary = _is_binary(y)
        models = tuple(_fit_arm_model(irm, X.copy(), y.copy(), d.copy(), arm, binary)
                       for arm in (0, 1))
        propensity = clone(irm.ml_m)
        propensity.fit(X.copy(), d.copy())
        threshold = float(irm._fit_overlap_threshold_)
        if not np.isfinite(threshold) or not 0 <= threshold < .5:
            raise ValueError("Fitted overlap threshold must be finite and in [0, .5).")
        self.__dict__.update(learner_=effect, outcome_models_=models,
                             propensity_model_=propensity, _training_ids_=ids.copy(),
                             _feature_names_=tuple(names), _roles_=(irm.data.outcome_name,
                             irm.data.treatment_name, irm.data.user_id_name),
                             _binary_outcome_=binary, _threshold_=threshold,
                             n_training_samples_=len(y))
        return self

    def evaluate(self, data):
        """Return immutable aggregate metrics; do not fit or tune on `data`.

        Both arms must be present. Binary training outcomes require binary
        validation values (constant validation outcomes are allowed). Features
        may be reordered by name. Raw probabilities must lie in [0, 1]; only
        the fitted overlap threshold clips propensities used in DR/R signals.
        At threshold zero, boundary probabilities reject. Log loss bounds its
        arguments at machine epsilon independently of the causal clipping.
        Extreme arithmetic rejects instead of returning non-finite metrics.
        """
        check_is_fitted(self, attributes=["learner_", "_training_ids_"])
        if not isinstance(data, CausalData):
            raise TypeError("evaluate requires CausalData.")
        if not data.df.columns.is_unique:
            raise ValueError("Validation DataFrame columns must be unique.")
        if (data.outcome_name, data.treatment_name, data.user_id_name) != self._roles_:
            raise ValueError("Validation outcome/treatment/user_id roles must match training.")
        if set(data.confounders) != set(self._feature_names_) or len(data.confounders) != len(self._feature_names_):
            raise ValueError("Validation confounders must match training features.")
        ids = _identities(data)
        if self._training_ids_.isin(ids).any():
            raise ValueError("Validation identities overlap the training sample.")
        X = _scoring_features(data.X, self._feature_names_)
        n = len(X)
        if n == 0:
            raise ValueError("Validation sample must be nonempty with both treatment arms.")
        y = _prediction_vector(data.outcome.to_numpy(), n, name="Validation outcomes").copy()
        d = _prediction_vector(data.treatment.to_numpy(), n, name="Validation treatments").copy()
        if not _is_binary(d):
            raise ValueError("Validation treatments must contain both binary arms 0 and 1.")
        if self._binary_outcome_ and np.any((y != 0) & (y != 1)):
            raise ValueError("Binary training outcomes require binary validation outcomes.")
        g0, g1 = (_predict_prob_or_value(model, X.copy()).copy()
                  for model in self.outcome_models_)
        if self._binary_outcome_ and any(np.any((g < 0) | (g > 1)) for g in (g0, g1)):
            raise ValueError("Binary outcome predictions must lie in [0, 1].")
        raw_e = _predict_prob_or_value(self.propensity_model_, X.copy()).copy()
        if np.any((raw_e < 0) | (raw_e > 1)):
            raise ValueError("Validation propensity predictions must lie in [0, 1].")
        e = np.clip(raw_e, self._threshold_, 1-self._threshold_)
        if np.any((e <= 0) | (e >= 1)):
            raise ValueError("Validation propensities must be strictly inside (0, 1) after clipping.")
        tau = _prediction_vector(self.learner_.predict(X.copy()), n, name="Validation CATE").copy()
        with np.errstate(over="ignore", divide="ignore", invalid="ignore", under="ignore"):
            signal = g1-g0 + d*(y-g1)/e - (1-d)*(y-g0)/(1-e)
            q = (1-e)*g0 + e*g1
            # Compute the loss difference directly, without subtracting two
            # noisy squared losses with a shared signal-squared term.
            log_e = np.clip(raw_e, np.finfo(float).eps, 1-np.finfo(float).eps)
            metrics = dict(outcome_mse_control=np.mean((y[d == 0]-g0[d == 0])**2),
                           outcome_mse_treated=np.mean((y[d == 1]-g1[d == 1])**2),
                           propensity_brier=np.mean((d-raw_e)**2),
                           propensity_log_loss=-np.mean(d*np.log(log_e)+(1-d)*np.log1p(-log_e)),
                           propensity_min=np.min(raw_e), propensity_max=np.max(raw_e),
                           mean_cate=np.mean(tau), mean_dr_signal=np.mean(signal),
                           dr_loss=np.mean((signal-tau)**2),
                           dr_gain_vs_zero=np.mean(2*signal*tau-tau**2),
                           r_loss=np.mean((y-q-(d-e)*tau)**2))
        if not np.all(np.isfinite(list(metrics.values()))):
            raise RuntimeError("Validation metric arithmetic produced non-finite values.")
        return CATEValidationResult(n=n, n_control=int(np.sum(d == 0)),
                                    n_treated=int(np.sum(d == 1)),
                                    n_propensity_clipped=int(np.sum(raw_e != e)),
                                    **{name: float(value) for name, value in metrics.items()})


__all__ = ["HeldOutCATEValidation", "CATEValidationResult"]
