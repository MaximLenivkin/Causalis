"""Candidate screening and exact comparisons for validated contract columns."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
import pandas as pd


def sampled_signature_groups(
    df: pd.DataFrame,
    columns: Sequence[str],
    signature: Callable[[pd.Series], tuple[str, int, str]],
) -> dict[tuple[str, int, str], list[str]]:
    """Group at most 64 positions, retaining first-column group order.

    This uses the same fingerprint as full-column screening. Validated numeric
    columns with equal values cannot have different sampled fingerprints;
    collisions merely cause an extra full-column comparison. Float-convertible object
    user IDs share numeric screening; exact value equality is still required. Matching
    samples never establish equality.
    """
    positions = np.linspace(0, len(df) - 1, min(len(df), 64), dtype=np.intp)
    groups: dict[tuple[str, int, str], list[str]] = {}
    for column in columns:
        key = signature(df[column].iloc[positions])
        groups.setdefault(key, []).append(column)
    return groups


def column_values_equal(first: pd.Series, second: pd.Series) -> bool:
    """Compare values exactly, ignoring dtype and index, with bounded boxing.

    Python object equality retains mixed int/float semantics and distinguishes
    large integers even when both fingerprints round to the same float64.
    Validated contracts have already rejected missing analysis values.
    """
    if len(first) != len(second):
        return False
    return all(
        np.array_equal(
            first.iloc[start:start + 65536].to_numpy(dtype=object, copy=False),
            second.iloc[start:start + 65536].to_numpy(dtype=object, copy=False),
        )
        for start in range(0, len(first), 65536)
    )
