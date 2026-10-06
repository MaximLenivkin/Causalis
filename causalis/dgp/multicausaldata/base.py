from __future__ import annotations

import numpy as np
import pandas as pd
import sys
from scipy.special import expit, log_ndtr, ndtr, roots_legendre
from dataclasses import dataclass, field
from typing import Dict, Optional, Union, List, Tuple, Callable, Any

from causalis.dgp.base import _sigmoid, _gaussian_copula
from causalis.data_contracts.multicausaldata import MultiCausalData


def _finite_array(value: Any, name: str) -> np.ndarray:
    """Reject invalid numeric values before a bounded link can conceal them."""
    try:
        raw = np.asarray(value)
        if np.iscomplexobj(raw):
            raise ValueError(f"{name} must be real numeric values")
        arr = np.asarray(value, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be real numeric values") from exc
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must contain only finite values")
    return arr


def _integer(value: Any, name: str, minimum: int) -> None:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def _softmax(scores: np.ndarray) -> np.ndarray:
    scores = _finite_array(scores, "treatment scores")
    if scores.ndim != 2:
        raise ValueError("scores must be a 2D array")
    shift = np.max(scores, axis=1, keepdims=True)
    exp_scores = np.exp(scores - shift)
    denom = exp_scores.sum(axis=1, keepdims=True)
    return exp_scores / np.clip(denom, 1e-12, np.inf)


_DATACLASS_KWARGS = {"slots": True} if sys.version_info >= (3, 10) else {}


@dataclass(**_DATACLASS_KWARGS)
class MultiCausalDatasetGenerator:
    """
    Generate synthetic causal datasets with multi-class (one-hot) treatments.

    Treatment assignment is modeled via a multinomial logistic (softmax) model:
        P(D=k | X, U) = softmax_k(alpha_d[k] + f_k(X) + u_strength_d[k] * U)

    Outcome depends on confounders and the assigned treatment class:
        outcome_type = "continuous":
            Y = alpha_y + f_y(X) + u_strength_y * U + sum_k D_k * (theta_k + tau_k(X)) + eps
        outcome_type = "binary":
            logit P(Y=1|X,D,U) = alpha_y + f_y(X) + u_strength_y * U + sum_k D_k * (theta_k + tau_k(X))
        outcome_type = "poisson":
            log E[Y|X,D,U] = alpha_y + f_y(X) + u_strength_y * U + sum_k D_k * (theta_k + tau_k(X))
        outcome_type = "gamma":
            log E[Y|X,D,U] = alpha_y + f_y(X) + u_strength_y * U + sum_k D_k * (theta_k + tau_k(X))

    Parameters
    ----------
    n_treatments : int, default=3
        Number of treatment classes (including control). Column 0 is treated as control.
        Generated treatment columns are a full one-hot encoding that sums to 1.
    d_names : list of str, optional
        Names of treatment columns. If None, uses ["d_0", "d_1", ...].
        Generated column names must be nonempty strings and unique across
        outcome, treatments, expanded confounders, and enabled oracle columns.
        Conflicts raise ValueError rather than renaming or overwriting columns.
    theta : float or array-like, optional
        Constant treatment effects on the link scale for each class.
        If scalar, applied to all non-control classes (control effect = 0).
        If length K-1, prepends 0 for control. If length K, uses as provided.
    tau : callable or list of callables, optional
        Heterogeneous effects for each class. If callable, applied to non-control classes.
        Effects are additive with theta on the link scale:
        tau_link_k(X) = theta_k + tau_k(X).
    beta_y : array-like, optional
        Linear coefficients for baseline outcome f_y(X).
    g_y : callable, optional
        Nonlinear baseline outcome function g_y(X).
    alpha_y : float, default=0.0
        Outcome intercept on link scale.
    sigma_y : float, default=1.0
        Std dev for continuous outcomes.
    outcome_type : {"continuous", "binary", "poisson", "gamma"}, default="continuous"
        Outcome family.
    gamma_shape : float, default=2.0
        Shape parameter for gamma outcomes.
    u_strength_y : float, default=0.0
        Strength of unobserved confounder in outcome.
    confounder_specs : list of dict, optional
        Schema for generating confounders (same format as CausalDatasetGenerator).
    k : int, default=5
        Number of confounders if confounder_specs is None.
    x_sampler : callable, optional
        Custom sampler (n, k, seed) -> X ndarray.
    use_copula : bool, default=False
        If True and confounder_specs provided, use Gaussian copula for X.
    copula_corr : array-like, optional
        Correlation matrix for copula.
    beta_d : array-like or list, optional
        Linear coefficients for treatment assignment. If array of shape (k,),
        applies to all non-control classes. If shape (K,k), uses per class.
    g_d : callable or list of callables, optional
        Nonlinear treatment score per class. If callable, applies to non-control classes.
    alpha_d : float or array-like, optional
        Intercepts for treatment scores. If scalar, applies to non-control classes.
    u_strength_d : float or array-like, default=0.0
        Unobserved confounder strength in treatment assignment.
        If scalar, interpreted as [0, c, c, ...] so latent U perturbs non-control
        classes relative to control (and does not cancel in softmax).
    propensity_sharpness : float, default=1.0
        Scales treatment scores to adjust overlap.
    target_d_rate : array-like, optional
        Target class probabilities (length K) for intercept calibration. Iterative
        scaling targets the mean assignment probabilities at U=0 over the
        generated X sample. It does not integrate over latent treatment noise;
        actual marginal rates can differ when U changes relative arm scores.
        Calibration on sampled X is not an exact population-X rate guarantee,
        and realized treatment frequencies also fluctuate by sampling.
    include_oracle : bool, default=True
        Whether to include oracle columns for propensities and potential outcomes.
    seed : int, optional
        Random seed.
    assignment_policy : {"ensure_all", "iid"}, default="ensure_all"
        ``ensure_all`` retries complete assignment draws and repairs missing
        arms if needed. It requires n >= n_treatments and changes the nominal
        softmax assignment law. ``iid`` draws once from that law per row,
        permitting absent arms and positive n smaller than n_treatments.

    Notes
    -----
    The latent variable is independent of X and follows N(0, 1). The natural-scale
    ``g_<arm>`` columns integrate out this Gaussian latent variable, so they are
    E[Y(arm) | X]; ``cate_<arm>`` is their difference from control. They are not
    E[Y | D=arm, X] when the same latent variable affects treatment assignment.
    Continuous means and clipped exponential means are integrated analytically;
    binary means use deterministic quadrature (Gauss-Hermite for moderate latent
    noise, logistic-normal convolution for stronger noise). The exponential
    outcome links are clipped to [-20, 20] for both draws and oracle means.
    ``m_obs_<arm>`` is the nominal softmax model probability P(D=arm | X, U)
    at the supplied or drawn latent values. For iid assignment it is the actual
    conditional probability; all-arm resampling changes the joint assignment law.
    ``m_<arm>`` is the softmax probability at U=0, which generally differs from
    the marginal P(D=arm | X) when latent noise affects treatment assignment.
    ``target_d_rate`` calibrates the sample mean of these U=0 probabilities,
    rather than Gaussian-marginal assignment probabilities. With latent
    treatment noise, the discrepancy from actual marginal arm rates need not
    disappear as the sample size increases.
    Under ``ensure_all``, m and m_obs describe the nominal softmax model rather
    than the row probabilities of the conditioned or repaired sample. Under
    ``iid``, m_obs gives the actual conditional assignment probabilities.
    """
    n_treatments: int = 3
    d_names: Optional[List[str]] = None

    theta: Optional[Union[float, List[float], np.ndarray]] = 1.0
    tau: Optional[Union[Callable[[np.ndarray], np.ndarray], List[Optional[Callable[[np.ndarray], np.ndarray]]]]] = None

    beta_y: Optional[np.ndarray] = None
    g_y: Optional[Callable[[np.ndarray], np.ndarray]] = None
    alpha_y: float = 0.0
    sigma_y: float = 1.0
    outcome_type: str = "continuous"
    gamma_shape: float = 2.0
    u_strength_y: float = 0.0

    confounder_specs: Optional[List[Dict[str, Any]]] = None
    k: int = 5
    x_sampler: Optional[Callable[[int, int, int], np.ndarray]] = None
    use_copula: bool = False
    copula_corr: Optional[np.ndarray] = None

    beta_d: Optional[Union[np.ndarray, List[Optional[np.ndarray]]]] = None
    g_d: Optional[Union[Callable[[np.ndarray], np.ndarray], List[Optional[Callable[[np.ndarray], np.ndarray]]]]] = None
    alpha_d: Optional[Union[float, List[float], np.ndarray]] = None
    u_strength_d: Union[float, List[float], np.ndarray] = 0.0
    propensity_sharpness: float = 1.0
    target_d_rate: Optional[Union[List[float], np.ndarray]] = None

    include_oracle: bool = True
    seed: Optional[int] = None
    assignment_policy: str = "ensure_all"

    rng: np.random.Generator = field(init=False, repr=False)
    confounder_names_: List[str] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        self._validate_assignment_policy()
        self.rng = np.random.default_rng(self.seed)
        _integer(self.n_treatments, "n_treatments", 2)
        if self.confounder_specs is not None:
            self.k = len(self.confounder_specs)
        _integer(self.k, "k", 0)
        if self.d_names is None:
            self.d_names = [f"d_{i}" for i in range(self.n_treatments)]
        self._validate_column_names()

    def _validate_column_names(self, confounder_names: Optional[List[str]] = None) -> None:
        """Reserve every emitted column before DataFrame assignment can replace it."""
        if isinstance(self.d_names, (str, bytes)):
            raise ValueError("d_names must be a sequence of column names")
        try:
            count = len(self.d_names)
        except TypeError as exc:
            raise ValueError("d_names must be a sequence of column names") from exc
        if count != self.n_treatments:
            raise ValueError("d_names length must match n_treatments")

        roles: Dict[str, str] = {}

        def reserve(name: str, role: str) -> None:
            if not isinstance(name, str) or not name:
                raise ValueError(f"{role} column name must be a nonempty string")
            if name in roles:
                raise ValueError(
                    f"Generated column name {name!r} collides between {roles[name]} and {role}"
                )
            roles[name] = role

        reserve("y", "outcome")
        for k, name in enumerate(self.d_names):
            reserve(name, f"treatment[{k}]")
        if confounder_names is not None:
            for j, name in enumerate(confounder_names):
                reserve(name, f"confounder[{j}]")
        if self.include_oracle:
            for k, name in enumerate(self.d_names):
                for prefix in ("m", "m_obs", "tau_link"):
                    reserve(f"{prefix}_{name}", f"{prefix} oracle[{k}]")
            for k, name in enumerate(self.d_names):
                reserve(f"g_{name}", f"g oracle[{k}]")
            for k, name in enumerate(self.d_names[1:], start=1):
                reserve(f"cate_{name}", f"cate oracle[{k}]")

    # ---------- confounder sampling ----------

    def _sample_X(self, n: int) -> Tuple[np.ndarray, List[str]]:
        if self.x_sampler is not None:
            X = self.x_sampler(n, self.k, self.seed)
            if self.confounder_specs is not None:
                names = [spec.get("name", f"x{i+1}") for i, spec in enumerate(self.confounder_specs)]
            else:
                names = [f"x{i+1}" for i in range(self.k)]
            return X, names

        if self.confounder_specs is None:
            X = self.rng.normal(size=(n, self.k))
            names = [f"x{i+1}" for i in range(self.k)]
            return X, names

        if self.use_copula:
            X, names = _gaussian_copula(self.rng, n, self.confounder_specs, self.copula_corr)
            self.k = X.shape[1]
            return X, names

        cols = []
        names = []
        for spec in self.confounder_specs:
            name = spec.get("name") or f"x{len(names)+1}"
            dist = spec.get("dist", "normal").lower()
            if dist == "normal":
                mu = spec.get("mu", 0.0)
                sd = spec.get("sd", 1.0)
                col = self.rng.normal(mu, sd, size=n)
            elif dist == "uniform":
                a = spec.get("a", 0.0)
                b = spec.get("b", 1.0)
                col = self.rng.uniform(a, b, size=n)
            elif dist == "bernoulli":
                p = spec.get("p", 0.5)
                col = self.rng.binomial(1, p, size=n).astype(float)
            elif dist == "lognormal":
                mu = spec.get("mu", 0.0)
                sigma = spec.get("sigma", 1.0)
                col = self.rng.lognormal(mean=mu, sigma=sigma, size=n)
            elif dist == "gamma":
                shape = spec.get("shape", 2.0)
                scale = spec.get("scale", None)
                if scale is None:
                    mean = spec.get("mean", 1.0)
                    scale = mean / shape
                col = self.rng.gamma(shape=shape, scale=scale, size=n)
            elif dist == "beta":
                a = spec.get("a", None)
                b = spec.get("b", None)
                if a is None or b is None:
                    mean = spec.get("mean", 0.5)
                    kappa = spec.get("kappa", 10.0)
                    a = mean * kappa
                    b = (1.0 - mean) * kappa
                col = self.rng.beta(a, b, size=n)
            elif dist == "poisson":
                lam = spec.get("lam", 1.0)
                col = self.rng.poisson(lam=lam, size=n).astype(float)
            elif dist == "negbin":
                mu = spec.get("mu", 5.0)
                alpha = spec.get("alpha", 0.5)
                r = 1.0 / max(alpha, 1e-12)
                p = r / (r + mu)
                col = self.rng.negative_binomial(r, p, size=n).astype(float)
            elif dist == "categorical":
                categories = list(spec.get("categories", [0, 1, 2]))
                probs = spec.get("probs", None)
                if probs is not None:
                    p = np.asarray(probs, dtype=float)
                    ps = p / p.sum()
                else:
                    ps = None
                col = self.rng.choice(categories, p=ps, size=n)
                rest = categories[1:]
                if len(rest) == 0:
                    cols.append(np.zeros(n, dtype=float))
                    names.append(f"{name}__onlylevel")
                    continue
                for c in rest:
                    cols.append((col == c).astype(float))
                    names.append(f"{name}_{c}")
                continue
            else:
                raise ValueError(f"Unknown dist: {dist}")

            if "clip_min" in spec or "clip_max" in spec:
                cmin = spec.get("clip_min", -np.inf)
                cmax = spec.get("clip_max", np.inf)
                col = np.clip(col, cmin, cmax)

            cols.append(col.astype(float))
            names.append(name)

        X = np.column_stack(cols) if cols else np.empty((n, 0))
        self.k = X.shape[1]
        return X, names

    # ---------- normalization helpers ----------

    def _normalize_alpha_d(self, K: int) -> np.ndarray:
        if self.alpha_d is None:
            return np.zeros(K, dtype=float)
        if np.isscalar(self.alpha_d):
            val = float(_finite_array(self.alpha_d, "alpha_d"))
            return np.array([0.0] + [val] * (K - 1), dtype=float)
        arr = _finite_array(self.alpha_d, "alpha_d").reshape(-1)
        if arr.size == K - 1:
            arr = np.concatenate([[0.0], arr])
        if arr.size != K:
            raise ValueError("alpha_d must be scalar, length K, or length K-1")
        return arr.astype(float)

    def _normalize_u_strength_d(self, K: int) -> np.ndarray:
        if np.isscalar(self.u_strength_d):
            c = float(_finite_array(self.u_strength_d, "u_strength_d"))
            # Scalar strength is applied to non-control classes only; applying the same
            # value to all classes would cancel out under softmax shift invariance.
            return np.array([0.0] + [c] * (K - 1), dtype=float)
        arr = _finite_array(self.u_strength_d, "u_strength_d").reshape(-1)
        if arr.size == K - 1:
            arr = np.concatenate([[0.0], arr])
        if arr.size != K:
            raise ValueError("u_strength_d must be scalar, length K, or length K-1")
        return arr.astype(float)

    def _normalize_beta_d(self, K: int, kx: int) -> List[Optional[np.ndarray]]:
        if self.beta_d is None:
            return [None] * K
        if isinstance(self.beta_d, list):
            vals = self.beta_d
            if len(vals) == K - 1:
                vals = [None] + vals
            if len(vals) != K:
                raise ValueError("beta_d list must have length K or K-1")
            out = []
            for v in vals:
                if v is None:
                    out.append(None)
                else:
                    arr = _finite_array(v, "beta_d element").reshape(-1)
                    if arr.size != kx:
                        raise ValueError("beta_d element has incompatible size")
                    out.append(arr)
            return out
        arr = _finite_array(self.beta_d, "beta_d")
        if arr.ndim == 1:
            if arr.size != kx:
                raise ValueError("beta_d vector has incompatible size")
            return [np.zeros(kx, dtype=float)] + [arr] * (K - 1)
        if arr.ndim == 2:
            if arr.shape[1] != kx:
                raise ValueError("beta_d matrix has incompatible width")
            if arr.shape[0] == K - 1:
                arr = np.vstack([np.zeros((1, kx), dtype=float), arr])
            if arr.shape[0] != K:
                raise ValueError("beta_d matrix must have shape (K,k) or (K-1,k)")
            return [arr[i] for i in range(K)]
        raise ValueError("beta_d must be array-like or list")

    def _normalize_g_d(self, K: int) -> List[Optional[Callable[[np.ndarray], np.ndarray]]]:
        if self.g_d is None:
            return [None] * K
        if callable(self.g_d):
            return [None] + [self.g_d] * (K - 1)
        if isinstance(self.g_d, list):
            vals = self.g_d
            if len(vals) == K - 1:
                vals = [None] + vals
            if len(vals) != K:
                raise ValueError("g_d list must have length K or K-1")
            return vals
        raise ValueError("g_d must be a callable or list of callables")

    def _normalize_theta(self, K: int) -> np.ndarray:
        if self.theta is None:
            return np.zeros(K, dtype=float)
        if np.isscalar(self.theta):
            return np.array([0.0] + [float(_finite_array(self.theta, "theta"))] * (K - 1), dtype=float)
        arr = _finite_array(self.theta, "theta").reshape(-1)
        if arr.size == K - 1:
            arr = np.concatenate([[0.0], arr])
        if arr.size != K:
            raise ValueError("theta must be scalar, length K, or length K-1")
        return arr.astype(float)

    def _normalize_tau(self, K: int) -> List[Optional[Callable[[np.ndarray], np.ndarray]]]:
        if self.tau is None:
            return [None] * K
        if callable(self.tau):
            return [None] + [self.tau] * (K - 1)
        if isinstance(self.tau, list):
            vals = self.tau
            if len(vals) == K - 1:
                vals = [None] + vals
            if len(vals) != K:
                raise ValueError("tau list must have length K or K-1")
            return vals
        raise ValueError("tau must be a callable or list of callables")

    @staticmethod
    def _normalize_outcome_type(outcome_type: str) -> str:
        # Support the common alias used in some older call sites.
        ttype = str(outcome_type).lower()
        if ttype == "normal":
            return "continuous"
        return ttype

    @staticmethod
    def _exp_link(link: np.ndarray) -> np.ndarray:
        # Clip link values to keep exp(.) numerically stable.
        return np.exp(np.clip(np.asarray(link, dtype=float), -20.0, 20.0))

    @staticmethod
    def _require_supported_outcome_type(ttype: str) -> None:
        if ttype not in {"continuous", "binary", "poisson", "gamma"}:
            raise ValueError("outcome_type must be 'continuous', 'binary', 'poisson', or 'gamma'")

    def _natural_scale_from_link(self, link: np.ndarray, ttype: str) -> np.ndarray:
        self._require_supported_outcome_type(ttype)
        link = np.asarray(link, dtype=float)
        # Oracle potential outcomes are stored on the natural outcome scale.
        if ttype == "continuous":
            return link
        if ttype == "binary":
            return _sigmoid(link)
        return self._exp_link(link)

    def _marginal_natural_scale_from_link(self, link: np.ndarray, ttype: str) -> np.ndarray:
        """Integrate the structural outcome mean over independent U ~ N(0, 1)."""
        self._require_supported_outcome_type(ttype)
        link = np.asarray(link, dtype=float)
        strength = abs(float(self.u_strength_y))
        if strength == 0.0 or ttype == "continuous":
            # The continuous structural mean is linear in a mean-zero latent U.
            return self._natural_scale_from_link(link, ttype)
        if ttype == "binary":
            mean = np.zeros_like(link)
            # Accumulate one node at a time instead of allocating n x K x nodes.
            if strength <= 2.0:
                nodes, weights = np.polynomial.hermite.hermgauss(81)
                for node, weight in zip(nodes, weights):
                    mean += (weight / np.sqrt(np.pi)) * _sigmoid(
                        link + strength * np.sqrt(2.0) * node
                    )
            else:
                # With independent L ~ Logistic and Z ~ N(0,1),
                # E[sigmoid(a+s*Z)] = P(L <= a+s*Z) = E[Phi((a-L)/s)].
                # This integrand stays smooth even when s makes the original
                # sigmoid nearly discontinuous. The omitted logistic tails
                # outside [-40,40] have total mass < 8.5e-18.
                nodes, weights = roots_legendre(256)
                nodes = 40.0 * nodes
                weights = 40.0 * weights * expit(nodes) * expit(-nodes)
                for node, weight in zip(nodes, weights):
                    mean += weight * ndtr((link - node) / strength)
            return np.clip(mean, 0.0, 1.0)

        if strength > np.sqrt(np.finfo(float).max):
            raise ValueError("u_strength_y is too large for the clipped exponential Gaussian oracle")

        # For W = link + strength * U, split E[exp(clip(W, low, high))]
        # into the lower tail, the truncated lognormal mean, and the upper tail.
        low, high = -20.0, 20.0
        lower_tail = np.exp(low) * ndtr((low - link) / strength)
        upper_tail = np.exp(high) * ndtr((link - high) / strength)
        shifted_low = (low - link - strength**2) / strength
        shifted_high = (high - link - strength**2) / strength
        # Use the smaller tail to avoid subtracting two CDF values close to one.
        reflected = shifted_low > 0.0
        log_cdf_high = log_ndtr(np.where(reflected, -shifted_low, shifted_high))
        log_cdf_low = log_ndtr(np.where(reflected, -shifted_high, shifted_low))
        with np.errstate(divide="ignore", invalid="ignore"):
            log_interval = log_cdf_high + np.log(
                -np.expm1(log_cdf_low - log_cdf_high)
            )
        middle = np.exp(link + strength**2 / 2.0 + log_interval)
        return np.clip(lower_tail + middle + upper_tail, np.exp(low), np.exp(high))

    def _sample_outcome_from_link(self, link: np.ndarray, ttype: str) -> np.ndarray:
        self._require_supported_outcome_type(ttype)
        link = np.asarray(link, dtype=float).reshape(-1)
        n = link.shape[0]
        # Draw observed outcomes from the family implied by `outcome_type`.
        if ttype == "continuous":
            return link + self.rng.normal(0, float(self.sigma_y), size=n)
        if ttype == "binary":
            p = _sigmoid(link)
            return self.rng.binomial(1, p).astype(float)
        if ttype == "poisson":
            lam = self._exp_link(link)
            return self.rng.poisson(lam).astype(float)

        # Gamma with mean mu=exp(link) and variance mu^2 / shape.
        mu = self._exp_link(link)
        shape = float(self.gamma_shape)
        if shape <= 0:
            raise ValueError("gamma_shape must be > 0 for gamma outcomes")
        scale = mu / shape
        return self.rng.gamma(shape=shape, scale=scale, size=n).astype(float)

    def _calibrate_alpha_d(self, scores_base: np.ndarray, alpha_init: np.ndarray, target: np.ndarray) -> np.ndarray:
        alpha = alpha_init.astype(float).copy()
        target = np.asarray(target, dtype=float).reshape(-1)
        if target.size != scores_base.shape[1]:
            raise ValueError("target_d_rate must have length K")
        if np.any(target <= 0):
            raise ValueError("target_d_rate must be strictly positive")
        with np.errstate(over="ignore"):
            total = target.sum()
        if np.isfinite(total):
            target = target / total
        else:
            # Preserve ordinary calibration arithmetic, and scale only when
            # finite positive weights overflow in their sum.
            scaled_target = target / target.max()
            target = scaled_target / scaled_target.sum()

        for _ in range(50):
            probs = _softmax(scores_base + alpha)
            p_bar = probs.mean(axis=0)
            delta = np.log(np.clip(target, 1e-12, 1.0)) - np.log(np.clip(p_bar, 1e-12, 1.0))
            alpha += delta
            alpha -= alpha.mean()
            if np.max(np.abs(delta)) < 1e-6:
                break
        return alpha

    def _draw_multinomial(self, probs: np.ndarray) -> np.ndarray:
        self._validate_assignment_policy()
        n, K = probs.shape
        if self.assignment_policy == "iid":
            u = self.rng.random(n)
            cdf = np.cumsum(probs, axis=1)
            cdf[:, -1] = 1.0
            return (u[:, None] < cdf).argmax(axis=1)
        if n < K:
            raise ValueError("n must be >= n_treatments to ensure all classes appear")
        classes = None
        counts = None
        for _ in range(10):
            u = self.rng.random(n)
            cdf = np.cumsum(probs, axis=1)
            classes = (u[:, None] < cdf).argmax(axis=1)
            counts = np.bincount(classes, minlength=K)
            if np.all(counts > 0):
                return classes
        # Force at least one example per class
        missing = np.where(counts == 0)[0] if counts is not None else np.arange(K)
        idxs = self.rng.choice(n, size=len(missing), replace=False)
        used = set()
        for k, idx in zip(missing, idxs):
            idx = int(idx)
            if counts[classes[idx]] <= 1:
                eligible = np.flatnonzero(counts[classes] > 1)
                eligible = np.array([i for i in eligible if int(i) not in used])
                idx = int(self.rng.choice(eligible))
            counts[classes[idx]] -= 1
            classes[idx] = int(k)
            counts[k] += 1
            used.add(idx)
        return classes

    def _validate_assignment_policy(self) -> None:
        if self.assignment_policy not in ("ensure_all", "iid"):
            raise ValueError("assignment_policy must be 'ensure_all' or 'iid'")

    # ---------- public API ----------

    def generate(self, n: int, U: Optional[np.ndarray] = None) -> pd.DataFrame:
        """Draw observations and, optionally, Gaussian-reference oracle columns.

        ``U`` overrides realized latent values used for treatment and outcome
        draws; by default these are sampled independently from N(0, 1). Oracle
        outcome means always integrate over the reference N(0, 1) law, not over
        the empirical distribution of a supplied vector. If supplied values
        follow another law or depend on X, the oracle means need not equal the
        potential-outcome means of that alternative generating process.

        Numeric configuration, sampled covariates, latent values, and callback
        outputs must be finite and real. Custom X must have shape (n, k).
        Baseline callbacks g_y/g_d accept scalars, one-element vectors, or
        vectors of length n; tau callbacks accept outputs with n elements.
        A scalar U broadcasts to n observations; vectors with shape (n,),
        (n, 1), or (1, n) are normalized to one dimension. Invalid inputs or
        non-finite calculated scores, links, outcomes, or oracles raise
        ValueError. Extremely large latent strengths unsupported by the
        clipped exponential Gaussian oracle also raise ValueError.
        Actual expanded column names are validated before treatment or outcome
        generation. Names must be nonempty strings and unique across the full
        output schema; disabled oracle names are not reserved.
        """
        self._validate_assignment_policy()
        _integer(n, "n", 1 if self.assignment_policy == "iid" else self.n_treatments)
        _integer(self.n_treatments, "n_treatments", 2)
        _integer(self.k, "k", 0)
        self._validate_column_names()
        for name in ("alpha_y", "sigma_y", "gamma_shape", "u_strength_y", "propensity_sharpness"):
            value = _finite_array(getattr(self, name), name)
            if value.ndim != 0:
                raise ValueError(f"{name} must be a scalar")
        if float(self.sigma_y) < 0:
            raise ValueError("sigma_y must be nonnegative")
        ttype = self._normalize_outcome_type(self.outcome_type)
        self._require_supported_outcome_type(ttype)
        if ttype == "gamma" and float(self.gamma_shape) <= 0:
            raise ValueError("gamma_shape must be > 0 for gamma outcomes")
        X, names = self._sample_X(n)
        X = _finite_array(X, "X / x_sampler output")
        if X.shape != (n, self.k):
            raise ValueError("X / x_sampler output must have shape (n, k)")
        if len(names) != X.shape[1]:
            raise ValueError("confounder names must match the number of X columns")
        self._validate_column_names(names)
        self.confounder_names_ = names
        if U is None:
            U = self.rng.normal(size=n)
        U = _finite_array(U, "U")
        if U.ndim == 0:
            U = np.full(n, float(U))
        elif U.shape in {(n,), (n, 1), (1, n)}:
            U = U.reshape(n)
        else:
            raise ValueError("U must be scalar or a vector of length n")

        K = self.n_treatments
        alpha_d = self._normalize_alpha_d(K)
        beta_d_list = self._normalize_beta_d(K, X.shape[1])
        g_d_list = self._normalize_g_d(K)
        u_strength_d = self._normalize_u_strength_d(K)
        alpha_d = _finite_array(alpha_d, "alpha_d")
        u_strength_d = _finite_array(u_strength_d, "u_strength_d")

        scores_base = np.zeros((n, K), dtype=float)
        for k in range(K):
            score_x = np.zeros(n, dtype=float)
            if beta_d_list[k] is not None:
                bt = _finite_array(beta_d_list[k], f"beta_d[{k}]").reshape(-1)
                if bt.size != X.shape[1]:
                    raise ValueError("beta_d incompatible with X")
                score_x += X @ bt
            if g_d_list[k] is not None:
                value = _finite_array(g_d_list[k](X), f"g_d[{k}] output")
                if value.ndim != 0 and value.shape not in {(1,), (n,)}:
                    raise ValueError(f"g_d[{k}] output must be scalar, shape (1,), or shape (n,)")
                score_x += value
            scores_base[:, k] = float(self.propensity_sharpness) * score_x

        if self.target_d_rate is not None:
            alpha_d = self._calibrate_alpha_d(scores_base, alpha_d, _finite_array(self.target_d_rate, "target_d_rate"))

        scores_base = scores_base + alpha_d
        scores_obs = scores_base + u_strength_d * U.reshape(-1, 1)

        m_obs = _softmax(scores_obs)
        m = _softmax(scores_base)

        classes = self._draw_multinomial(m_obs)
        D = np.zeros((n, K), dtype=float)
        D[np.arange(n), classes] = 1.0

        theta_vec = self._normalize_theta(K)
        theta_vec = _finite_array(theta_vec, "theta")
        tau_list = self._normalize_tau(K)

        Xf = np.asarray(X, dtype=float)
        loc_base = np.full(n, float(self.alpha_y), dtype=float)
        if self.beta_y is not None:
            by = _finite_array(self.beta_y, "beta_y").reshape(-1)
            if by.size != Xf.shape[1]:
                raise ValueError("beta_y incompatible with X")
            loc_base += Xf @ by
        if self.g_y is not None:
            value = _finite_array(self.g_y(Xf), "g_y output")
            if value.ndim != 0 and value.shape not in {(1,), (n,)}:
                raise ValueError("g_y output must be scalar, shape (1,), or shape (n,)")
            loc_base += value

        tau_mat = np.tile(theta_vec.reshape(1, -1), (n, 1))
        for k in range(K):
            if tau_list[k] is not None:
                tau_val = _finite_array(tau_list[k](Xf), f"tau[{k}] output").reshape(-1)
                if tau_val.size != n:
                    raise ValueError("tau function returned wrong shape")
                # Add heterogeneous residual on top of constant treatment effect.
                tau_mat[:, k] += tau_val

        _finite_array(loc_base, "baseline outcome link")
        _finite_array(tau_mat, "treatment outcome links")
        loc = loc_base + (D * tau_mat).sum(axis=1)
        if self.u_strength_y != 0.0:
            loc = loc + float(self.u_strength_y) * U

        _finite_array(loc, "observed outcome link")
        Y = self._sample_outcome_from_link(loc, ttype)
        _finite_array(Y, "sampled outcomes")

        df = pd.DataFrame({"y": Y})
        for k, name in enumerate(self.d_names):
            df[name] = D[:, k]
        for j, name in enumerate(names):
            df[name] = X[:, j]

        if self.include_oracle:
            for k, name in enumerate(self.d_names):
                df[f"m_{name}"] = m[:, k]
                df[f"m_obs_{name}"] = m_obs[:, k]
                df[f"tau_link_{name}"] = tau_mat[:, k]

            # Marginal potential-outcome means under the reference Gaussian law.
            potential_links = _finite_array(loc_base[:, None] + tau_mat, "potential outcome links")
            g_vals = self._marginal_natural_scale_from_link(potential_links, ttype)
            _finite_array(g_vals, "Gaussian oracle means")

            for k, name in enumerate(self.d_names):
                df[f"g_{name}"] = g_vals[:, k]

            g0 = g_vals[:, 0]
            for k in range(1, K):
                df[f"cate_{self.d_names[k]}"] = _finite_array(g_vals[:, k] - g0, "oracle treatment contrasts")

        return df

    def to_multicausal_data(
        self,
        n: int,
        confounders: Optional[Union[str, List[str]]] = None,
    ) -> MultiCausalData:
        df = self.generate(n)

        if confounders is None:
            confounder_cols = list(self.confounder_names_)
        elif isinstance(confounders, str):
            confounder_cols = [confounders]
        else:
            confounder_cols = [c for c in confounders if c in df.columns]

        return MultiCausalData(
            df=df,
            outcome="y",
            treatment_names=self.d_names,
            confounders=confounder_cols,
            control_treatment=self.d_names[0],
        )
