"""
High-level helpers for instrumental-variable synthetic datasets.

Use this module when you want a ready-made binary-instrument, binary-treatment
dataset compatible with :class:`causalis.data_contracts.iv_causal_data.IVCausalData`.
For lower-level structural control, instantiate
:class:`causalis.dgp.causaldata_instrumental.base.InstrumentalGenerator`
directly.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from causalis.data_contracts.iv_causal_data import IVCausalData
from causalis.dgp.base import _add_ancillary_info

from .base import InstrumentalGenerator

def generate_iv_data(
    n: int = 1_000,
    *,
    outcome_type: str = "continuous",
    theta: float = 1.0,
    tau: Optional[Callable[[np.ndarray], np.ndarray]] = None,
    sigma_y: float = 1.0,
    alpha_y: float = 0.0,
    gamma_shape: float = 2.0,
    first_stage: float = 1.25,
    alpha_d: float = -0.2,
    alpha_z: float = 0.0,
    target_d_rate: Optional[float] = None,
    target_z_rate: Optional[float] = 0.5,
    confounder_specs: Optional[List[Dict[str, Any]]] = None,
    beta_y: Optional[Union[List[float], np.ndarray]] = None,
    beta_d: Optional[Union[List[float], np.ndarray]] = None,
    beta_z: Optional[Union[List[float], np.ndarray]] = None,
    g_y: Optional[Callable[[np.ndarray], np.ndarray]] = None,
    g_d: Optional[Callable[[np.ndarray], np.ndarray]] = None,
    g_z: Optional[Callable[[np.ndarray], np.ndarray]] = None,
    u_strength_d: float = 0.8,
    u_strength_y: float = 0.8,
    propensity_sharpness: float = 1.0,
    instrument_sharpness: float = 1.0,
    random_state: Optional[int] = 42,
    k: int = 2,
    x_sampler: Optional[Callable[[int, int, int], np.ndarray]] = None,
    use_copula: bool = False,
    copula_corr: Optional[np.ndarray] = None,
    include_oracle: bool = True,
    return_causal_data: bool = False,
    instrument_name: str = "z",
    add_ancillary: bool = False,
    deterministic_ids: bool = False,
) -> Union[pd.DataFrame, IVCausalData]:
    """
    Generate a synthetic instrumental-variable dataset.

    Parameters
    ----------
    n : int, default=1000
        Number of samples.
    outcome_type : {"continuous", "binary", "poisson", "gamma"}, default="continuous"
        Outcome family.
    theta : float, default=1.0
        Constant treatment effect on the structural outcome scale.
    first_stage : float, default=1.25
        Additive log-odds effect of the instrument on treatment.
    target_z_rate : float, optional
        Target marginal instrument rate.
    target_d_rate : float, optional
        Target marginal treatment rate after instrument assignment.
    u_strength_d, u_strength_y : float, default=0.8
        Latent confounding strengths in treatment and outcome.
    return_causal_data : bool, default=False
        If True, return a validated :class:`IVCausalData` object, retaining
        actual numeric features (including disabled oracle names). Only an
        identifier added by ancillary generation receives the user_id role.
    instrument_name : str, default="z"
        Instrument column name. Disabled oracle names and user_id are valid
        instrument names when those extra roles are not emitted. Ancillary
        name collisions raise ValueError instead of overwriting the instrument.

    Returns
    -------
    pandas.DataFrame or IVCausalData
        Synthetic IV dataset or validated IV data contract.

    Examples
    --------
    >>> from causalis.dgp.causaldata_instrumental import generate_iv_data
    >>> data = generate_iv_data(n=500, return_causal_data=True)
    >>> data.instruments
    ['z']
    """
    gen = InstrumentalGenerator(
        theta=theta,
        tau=tau,
        beta_y=None if beta_y is None else np.asarray(beta_y, dtype=float),
        beta_d=None if beta_d is None else np.asarray(beta_d, dtype=float),
        g_y=g_y,
        g_d=g_d,
        alpha_y=alpha_y,
        alpha_d=alpha_d,
        sigma_y=sigma_y,
        outcome_type=outcome_type,
        confounder_specs=confounder_specs,
        k=int(k),
        x_sampler=x_sampler,
        use_copula=use_copula,
        copula_corr=copula_corr,
        target_d_rate=target_d_rate,
        u_strength_d=u_strength_d,
        u_strength_y=u_strength_y,
        propensity_sharpness=propensity_sharpness,
        gamma_shape=gamma_shape,
        include_oracle=include_oracle,
        seed=random_state,
        instrument_name=instrument_name,
        first_stage=first_stage,
        beta_z=None if beta_z is None else np.asarray(beta_z, dtype=float),
        g_z=g_z,
        alpha_z=alpha_z,
        target_z_rate=target_z_rate,
        instrument_sharpness=instrument_sharpness,
    )
    df = gen.generate(n)
    x_cols = list(gen._generated_confounder_names)
    emitted_instrument = next(name for name, role in gen._generated_column_roles if role == "instrument")
    oracle_cols = [name for name, role in gen._generated_column_roles if role.endswith(" oracle")]

    if add_ancillary:
        rng = np.random.default_rng(random_state)
        df = _add_ancillary_info(df, int(n), rng, deterministic_ids, x_cols)

    if not return_causal_data:
        return _order_columns(
            df, instrument_name=emitted_instrument, oracle_columns=oracle_cols,
            has_identifier=add_ancillary,
        )

    feature_names = x_cols + ([
        "age", "cnt_trans", "platform_Android", "platform_iOS", "invited_friend",
    ] if add_ancillary else [])
    confounder_cols = [
        c for c in feature_names if pd.api.types.is_numeric_dtype(df[c])
    ]
    return IVCausalData.from_df(
        df,
        treatment="d",
        outcome="y",
        instruments=emitted_instrument,
        confounders=confounder_cols,
        user_id="user_id" if add_ancillary else None,
    )


def _order_columns(
    df: pd.DataFrame, *, instrument_name: str,
    oracle_columns: List[str], has_identifier: bool,
) -> pd.DataFrame:
    """Return each column once in the order of its actual emitted role."""
    core = (["user_id"] if has_identifier else []) + ["y", "d", instrument_name]
    reserved = set(core + oracle_columns)
    confounders = [c for c in df.columns if c not in reserved]
    return df[core + confounders + oracle_columns]
