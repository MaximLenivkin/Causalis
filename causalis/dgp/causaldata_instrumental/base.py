"""
Low-level generators for instrumental-variable synthetic causal datasets.

The central class in this module is :class:`InstrumentalGenerator`, which
builds cross-sectional datasets with one binary instrument, one binary
endogenous treatment, optional observed confounders, and optional latent
confounding between treatment and outcome.

Examples
--------
>>> from causalis.dgp.causaldata_instrumental.base import InstrumentalGenerator
>>> gen = InstrumentalGenerator(k=2, first_stage=1.5, seed=3141)
>>> df = gen.generate(500)
>>> {"y", "d", "z", "x1", "x2"}.issubset(df.columns)
True
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from causalis.data_contracts.iv_causal_data import IVCausalData
from causalis.dgp.base import _sigmoid
from causalis.dgp._gaussian_outcome import _gaussian_outcome_mean
from causalis.dgp._gaussian_joint import _gaussian_product_mean
from causalis.dgp.causaldata.base import CausalDatasetGenerator

_DATACLASS_KWARGS = {"slots": True} if sys.version_info >= (3, 10) else {}


@dataclass(**_DATACLASS_KWARGS)
class InstrumentalGenerator(CausalDatasetGenerator):
    """
    Generate synthetic datasets for binary instrumental-variable estimation.

    The generated structural system is:

    - ``X`` is sampled with the same confounder machinery as
      :class:`~causalis.dgp.causaldata.base.CausalDatasetGenerator`.
    - ``Z`` is a binary instrument generated from ``P(Z=1|X)``.
    - ``D`` is a binary endogenous treatment generated from
      ``P(D=1|Z,X,U)``.
    - ``Y`` depends on ``D``, ``X``, and optionally the latent ``U``, but has no
      direct dependence on ``Z``.

    Parameters inherited from ``CausalDatasetGenerator`` keep their usual
    meaning for the outcome equation and the non-instrument part of the
    treatment equation. In particular, ``beta_d``, ``g_d``, ``alpha_d``,
    ``target_d_rate``, and ``u_strength_d`` affect treatment assignment.

    Parameters
    ----------
    instrument_name : str, default="z"
        Nonempty column name for the binary instrument. Must be unique across
        the outcome, treatment, actual expanded confounders and enabled IV
        oracle columns. Conflicts raise ``ValueError`` without renaming.
    first_stage : float, default=1.25
        Additive log-odds effect of ``Z`` on treatment assignment. Positive
        values make the instrument encourage treatment.
    beta_z : array-like, optional
        Linear coefficients of confounders in the instrument propensity.
    g_z : callable, optional
        Nonlinear instrument score ``g_z(X) -> shape (n,)``.
    alpha_z : float, default=0.0
        Instrument propensity intercept. If ``target_z_rate`` is set, this is
        calibrated on each generated sample.
    target_z_rate : float, optional
        Target marginal instrument rate. Defaults to ``0.5``.
    instrument_sharpness : float, default=1.0
        Multiplier on the X-driven instrument score.
    include_oracle : bool, default=True
        Whether to include oracle columns for IV nuisance functions and
        treatment potential-outcome means.

    Notes
    -----
    With ``include_oracle=True``, returned oracle columns include:

    - ``m``: instrument propensity ``P(Z=1|X)``.
    - ``r_z0`` and ``r_z1``: first-stage nuisances
      ``P(D=1|Z=0,X)`` and ``P(D=1|Z=1,X)``.
    - ``g_z0`` and ``g_z1``: reduced-form nuisances
      ``E[Y|Z=0,X]`` and ``E[Y|Z=1,X)``.
    - ``iv_first_stage`` and ``iv_reduced_form``: conditional differences in
      the first stage and reduced form.
    - ``late_x`` and ``late``: conditional and sample-average Wald ratios.
    - ``g_d0``, ``g_d1``, and ``cate``: treatment potential-outcome means and
      their natural-scale contrast.
    """

    instrument_name: str = "z"
    first_stage: float = 1.25
    beta_z: Optional[np.ndarray] = None
    g_z: Optional[Callable[[np.ndarray], np.ndarray]] = None
    alpha_z: float = 0.0
    target_z_rate: Optional[float] = 0.5
    instrument_sharpness: float = 1.0

    def __post_init__(self) -> None:
        """Initialize RNG and validate IV-specific configuration."""
        CausalDatasetGenerator.__post_init__(self)
        if self.outcome_type not in {"continuous", "binary", "poisson", "gamma"}:
            raise ValueError(
                "InstrumentalGenerator supports outcome_type in "
                "{'continuous', 'binary', 'poisson', 'gamma'}."
            )
        if self.target_z_rate is not None and not (0.0 < float(self.target_z_rate) < 1.0):
            raise ValueError("target_z_rate must be in (0, 1).")
        if self.target_d_rate is not None and not (0.0 < float(self.target_d_rate) < 1.0):
            raise ValueError("target_d_rate must be in (0, 1).")
        if not np.isfinite(float(self.first_stage)):
            raise ValueError("first_stage must be finite.")

    def _output_column_roles(self) -> List[Tuple[str, str]]:
        """Use IV's emitted columns, rather than the binary oracle namespace."""
        roles = [("y", "outcome"), ("d", "treatment"), (self.instrument_name, "instrument")]
        if self.include_oracle:
            roles.extend(
                (name, f"{name} oracle")
                for name in (
                    "m", "r_obs", "r_z0", "r_z1", "g_z0", "g_z1",
                    "iv_first_stage", "iv_reduced_form", "late_x", "late",
                    "tau_link", "g_d0", "g_d1", "cate",
                )
            )
        return roles

    def _linear_component(
        self,
        X: np.ndarray,
        beta: Optional[np.ndarray],
        g: Optional[Callable[[np.ndarray], np.ndarray]],
        *,
        sharpness: float = 1.0,
        name: str = "score",
    ) -> np.ndarray:
        """Build a finite one-dimensional score from linear and nonlinear terms."""
        Xf = np.asarray(X, dtype=float)
        score = np.zeros(Xf.shape[0], dtype=float)
        if beta is not None:
            coef = np.asarray(beta, dtype=float).reshape(-1)
            if coef.shape[0] != Xf.shape[1]:
                raise ValueError(
                    f"{name} beta shape {coef.shape} is incompatible with X shape {Xf.shape}."
                )
            score += np.sum(Xf * coef, axis=1)
        if g is not None:
            score += np.asarray(g(Xf), dtype=float).reshape(-1)
        score *= float(sharpness)
        if not np.all(np.isfinite(score)):
            raise ValueError(f"{name} produced non-finite values.")
        return score

    @staticmethod
    def _calibrate_intercept(score: np.ndarray, target: float) -> float:
        """Find an intercept so ``mean(sigmoid(intercept + score))`` hits target."""
        score = np.asarray(score, dtype=float)
        target = float(target)
        lo, hi = -50.0, 50.0

        def f(a: float) -> float:
            return float(_sigmoid(a + score).mean() - target)

        flo, fhi = f(lo), f(hi)
        if flo * fhi > 0:
            return lo if abs(flo) < abs(fhi) else hi
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            fm = f(mid)
            if abs(fm) < 1e-8:
                return mid
            if fm > 0:
                hi = mid
            else:
                lo = mid
        return 0.5 * (lo + hi)

    def _instrument_score(self, X: np.ndarray) -> np.ndarray:
        """Compute the X-driven instrument score, excluding ``alpha_z``."""
        return self._linear_component(
            X,
            self.beta_z,
            self.g_z,
            sharpness=self.instrument_sharpness,
            name="instrument",
        )

    def _instrument_propensity(self, X: np.ndarray) -> np.ndarray:
        """Compute ``P(Z=1|X)`` and calibrate ``alpha_z`` when requested."""
        score_z = self._instrument_score(X)
        if self.target_z_rate is not None:
            self.alpha_z = self._calibrate_intercept(score_z, float(self.target_z_rate))
        return _sigmoid(self.alpha_z + score_z)

    def _treatment_propensity(
        self,
        X: np.ndarray,
        Z: Union[float, np.ndarray],
        U: np.ndarray,
        *,
        calibrate: bool = False,
    ) -> np.ndarray:
        """Compute ``P(D=1|Z,X,U)``."""
        Xf = np.asarray(X, dtype=float)
        Zf = np.asarray(Z, dtype=float)
        Uf = np.asarray(U, dtype=float)
        if Zf.ndim == 0:
            Zf = np.full(Xf.shape[0], float(Zf), dtype=float)
        score = self._treatment_score(Xf, Uf) + float(self.first_stage) * Zf
        if calibrate and self.target_d_rate is not None:
            self.alpha_d = self._calibrate_intercept(score, float(self.target_d_rate))
        return _sigmoid(self.alpha_d + score)

    def _natural_mean_from_location(self, loc: np.ndarray) -> np.ndarray:
        """Map an outcome location/link value to the natural outcome mean."""
        loc = np.asarray(loc, dtype=float)
        if self.outcome_type == "continuous":
            return loc
        if self.outcome_type == "binary":
            return _sigmoid(loc)
        if self.outcome_type in {"poisson", "gamma"}:
            return np.exp(np.clip(loc, -20.0, 20.0))
        raise ValueError(
            "InstrumentalGenerator supports outcome_type in "
            "{'continuous', 'binary', 'poisson', 'gamma'}."
        )

    def _sample_outcome(self, loc: np.ndarray, n: int) -> np.ndarray:
        """Draw outcomes from the configured family."""
        if self.outcome_type == "continuous":
            return loc + self.rng.normal(0.0, self.sigma_y, size=n)
        if self.outcome_type == "binary":
            return self.rng.binomial(1, _sigmoid(loc), size=n).astype(float)
        if self.outcome_type == "poisson":
            lam = np.exp(np.clip(loc, -20.0, 20.0))
            return self.rng.poisson(lam).astype(float)
        if self.outcome_type == "gamma":
            mu = np.exp(np.clip(loc, -20.0, 20.0))
            shape = float(self.gamma_shape)
            scale = mu / max(shape, 1e-12)
            return self.rng.gamma(shape=shape, scale=scale, size=n).astype(float)
        raise ValueError(
            "InstrumentalGenerator supports outcome_type in "
            "{'continuous', 'binary', 'poisson', 'gamma'}."
        )

    def _u_quadrature(self, num_quad: int = 31) -> Tuple[np.ndarray, np.ndarray]:
        """Return Gauss-Hermite nodes and weights normalized for ``N(0, 1)``."""
        gh_x, gh_w = np.polynomial.hermite.hermgauss(int(num_quad))
        return np.sqrt(2.0) * gh_x, gh_w / np.sqrt(np.pi)

    def _r_by_z(self, X: np.ndarray, z_value: float) -> np.ndarray:
        """Gaussian-reference P(D=1|Z=z,X), with adaptive logistic means.

        Treatment callbacks must be deterministic functions of X; evaluate
        their base score once, outside integration, rather than at 31 GH nodes.
        """
        n = X.shape[0]
        if float(self.u_strength_d) == 0.0:
            return self._treatment_propensity(X, z_value, np.zeros(n), calibrate=False)

        base = (self.alpha_d + self._treatment_score(X, np.zeros(n))
                + float(self.first_stage) * z_value)
        return _gaussian_outcome_mean(base, self.u_strength_d, "binary")

    def _potential_outcome_means(
        self, X: np.ndarray, tau_x: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute E[Y(d)|X] over independent Gaussian-reference latent U.

        Nonlinear means share the binary generator's accuracy/failure policy.
        This does not change the joint shared-U integrals in ``_g_by_z``.
        Outcome callbacks should define deterministic functions of X; nonlinear
        means evaluate each base location once, rather than at every GH node.
        """
        n = X.shape[0]
        if float(self.u_strength_y) == 0.0:
            loc0 = self._outcome_location(X, np.zeros(n), np.zeros(n), np.zeros(n))
            loc1 = self._outcome_location(X, np.ones(n), np.zeros(n), tau_x)
            return self._natural_mean_from_location(loc0), self._natural_mean_from_location(loc1)

        if self.outcome_type in {"binary", "poisson", "gamma"}:
            loc0 = self._outcome_location(X, np.zeros(n), np.zeros(n), np.zeros(n))
            loc1 = self._outcome_location(X, np.ones(n), np.zeros(n), tau_x)
            return (
                _gaussian_outcome_mean(loc0, self.u_strength_y, self.outcome_type),
                _gaussian_outcome_mean(loc1, self.u_strength_y, self.outcome_type),
            )

        uq, wq = self._u_quadrature()
        g0 = np.zeros(n, dtype=float)
        g1 = np.zeros(n, dtype=float)
        for u, w in zip(uq, wq):
            U = np.full(n, float(u), dtype=float)
            loc0 = self._outcome_location(X, np.zeros(n), U, np.zeros(n))
            loc1 = self._outcome_location(X, np.ones(n), U, tau_x)
            g0 += float(w) * self._natural_mean_from_location(loc0)
            g1 += float(w) * self._natural_mean_from_location(loc1)
        return g0, g1

    def _g_by_z(self, X: np.ndarray, z_value: float, tau_x: np.ndarray) -> np.ndarray:
        """Gaussian-reference E[Y|Z=z,X], integrating D and the same latent U.

        Nonlinear responses use bounded adaptive shared-U products. Continuous
        responses use E[U]=0 and E[D|z,X]. Callbacks must be deterministic
        functions of X and are evaluated outside integration.
        """
        n = X.shape[0]
        needs_u_integral = (
            float(self.u_strength_d) != 0.0 or float(self.u_strength_y) != 0.0
        )
        if not needs_u_integral:
            p_d = self._treatment_propensity(X, z_value, np.zeros(n), calibrate=False)
            loc0 = self._outcome_location(X, np.zeros(n), np.zeros(n), np.zeros(n))
            loc1 = self._outcome_location(X, np.ones(n), np.zeros(n), tau_x)
            mu0 = self._natural_mean_from_location(loc0)
            mu1 = self._natural_mean_from_location(loc1)
            return (1.0 - p_d) * mu0 + p_d * mu1

        # Callbacks define deterministic functions of X and are evaluated once
        # per base location, outside numerical integration.
        base = (self.alpha_d + self._treatment_score(X, np.zeros(n))
                + float(self.first_stage) * z_value)
        loc0 = self._outcome_location(X, np.zeros(n), np.zeros(n), np.zeros(n))
        loc1 = self._outcome_location(X, np.ones(n), np.zeros(n), tau_x)
        if self.outcome_type == "continuous":
            # E[U]=0, and tau(X) does not depend on U: exact linear identity.
            r = _gaussian_outcome_mean(base, self.u_strength_d, "binary")
            return loc0 + tau_x * r
        return (
            _gaussian_product_mean(-base, -self.u_strength_d, loc0,
                                   self.u_strength_y, self.outcome_type)
            + _gaussian_product_mean(base, self.u_strength_d, loc1,
                                     self.u_strength_y, self.outcome_type)
        )

    def generate(self, n: int, U: Optional[np.ndarray] = None) -> pd.DataFrame:
        """
        Draw a synthetic IV dataset of size ``n``.

        Parameters
        ----------
        n : int
            Number of samples to generate.
        U : numpy.ndarray, optional
            Latent confounder. If omitted, sampled from ``N(0, 1)``.

        Returns
        -------
        pandas.DataFrame
            Generated dataset with outcome ``y``, treatment ``d``, instrument
            ``z`` (or ``instrument_name``), confounders, and optional oracle
            columns.

        Notes
        -----
        Names are checked on every call, including changed public settings.
        The full check follows X sampling and precedes latent draws,
        callbacks, calibration and assignment. Only enabled IV oracles are
        reserved; the binary generator's other oracle names remain available.
        Names are checked again before assembly if callbacks changed settings.
        """
        n = int(n)
        if n < 0:
            raise ValueError("n must be non-negative.")

        self._validate_column_names()
        X, names = self._sample_X(n)
        # Preserve zero-confounder samplers returning a one-dimensional array.
        x_shape = np.shape(X)
        if len(names) != (x_shape[1] if len(x_shape) > 1 else 0):
            raise ValueError("confounder names must match the number of X columns")
        self._validate_column_names(names)
        if U is None:
            U = self.rng.normal(size=n)
        U = np.asarray(U, dtype=float).reshape(-1)
        if U.shape[0] != n:
            raise ValueError("U must have shape (n,).")

        m = self._instrument_propensity(X)
        Z = self.rng.binomial(1, m).astype(float)

        r_obs = self._treatment_propensity(X, Z, U, calibrate=True)
        shared_uniform = self.rng.uniform(size=n)
        D = (shared_uniform < r_obs).astype(float)

        tau_x = (
            np.asarray(self.tau(X), dtype=float).reshape(-1)
            if self.tau is not None
            else np.full(n, float(self.theta), dtype=float)
        )
        if tau_x.shape[0] != n:
            raise ValueError("tau(X) must return shape (n,).")

        loc = self._outcome_location(X, D, U, tau_x)
        Y = self._sample_outcome(loc, n)

        self._validate_column_names(names)
        output_roles = tuple(self._output_column_roles())
        generated_names = tuple(names)
        df = pd.DataFrame({"y": Y, "d": D, self.instrument_name: Z})
        for j, name in enumerate(names):
            df[name] = X[:, j]

        if self.include_oracle:
            r_z0 = self._r_by_z(X, 0.0)
            r_z1 = self._r_by_z(X, 1.0)
            g_z0 = self._g_by_z(X, 0.0, tau_x)
            g_z1 = self._g_by_z(X, 1.0, tau_x)
            g_d0, g_d1 = self._potential_outcome_means(X, tau_x)

            first_stage = r_z1 - r_z0
            reduced_form = g_z1 - g_z0
            late_x = np.divide(
                reduced_form,
                first_stage,
                out=np.full(n, np.nan, dtype=float),
                where=np.abs(first_stage) > 1e-12,
            )
            late_denominator = float(np.mean(first_stage)) if n else np.nan
            late = (
                float(np.mean(reduced_form) / late_denominator)
                if n and abs(late_denominator) > 1e-12
                else np.nan
            )

            df["m"] = m
            df["r_obs"] = r_obs
            df["r_z0"] = r_z0
            df["r_z1"] = r_z1
            df["g_z0"] = g_z0
            df["g_z1"] = g_z1
            df["iv_first_stage"] = first_stage
            df["iv_reduced_form"] = reduced_form
            df["late_x"] = late_x
            df["late"] = late
            df["tau_link"] = tau_x
            df["g_d0"] = g_d0
            df["g_d1"] = g_d1
            df["cate"] = g_d1 - g_d0

        self._generated_confounder_names = generated_names
        self._generated_column_roles = output_roles
        return df

    def to_iv_causal_data(
        self, n: int, confounders: Optional[Union[str, List[str]]] = None
    ) -> IVCausalData:
        """
        Generate a dataset and convert it to :class:`IVCausalData`.

        When ``confounders`` is omitted, select numeric columns actually sampled
        as confounders. Enabled oracles are excluded; disabled oracle names and
        ``user_id`` remain available as features. No identifier is added here.
        """
        df = self.generate(n)
        if confounders is None:
            confounder_cols = [
                c
                for c in self._generated_confounder_names
                if pd.api.types.is_numeric_dtype(df[c])
            ]
        elif isinstance(confounders, str):
            confounder_cols = [confounders]
        else:
            confounder_cols = [c for c in confounders if c in df.columns]

        return IVCausalData.from_df(
            df,
            treatment="d",
            outcome="y",
            instruments=next(name for name, role in self._generated_column_roles if role == "instrument"),
            confounders=confounder_cols,
        )


IVCausalDatasetGenerator = InstrumentalGenerator
