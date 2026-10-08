"""One-way cluster membership, disjoint splits and scalar CR1 inference."""
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

from causalis.scenarios._numerics import _checked_arithmetic, _require_finite


def cluster_codes(labels, index):
    """Snapshot positional scalar labels; Series must match row index exactly."""
    if isinstance(labels, pd.Series) and not labels.index.equals(index):
        raise ValueError("cluster_groups Series index must match fitted row index in order")
    # Object dtype preserves heterogeneous scalar labels instead of coercing
    # distinct integers and strings to the same string.
    values = np.asarray(labels, dtype=object)
    if values.ndim != 1 or len(values) != len(index):
        raise ValueError("cluster_groups must be a one-dimensional vector matching fitted rows")
    if any(not pd.api.types.is_scalar(value) for value in values):
        raise ValueError("cluster_groups must contain hashable scalar labels")
    if pd.isna(values).any():
        raise ValueError("cluster_groups must not contain missing labels")
    try:
        codes, unique = pd.factorize(values, sort=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("cluster_groups must contain hashable scalar labels") from exc
    if len(unique) < 2:
        raise ValueError("cluster_groups must contain at least two distinct clusters")
    codes = np.asarray(codes, dtype=int).copy()
    codes.setflags(write=False)
    return codes, len(unique)


def cluster_splits(codes, d, n_folds, seed):
    """Split whole clusters and check every training arm before learner fitting."""
    groups = np.arange(int(codes.max()) + 1)
    if len(groups) < n_folds:
        raise ValueError("n_folds exceeds the number of distinct cluster_groups")
    splitter = KFold(n_splits=n_folds, shuffle=True, random_state=seed)
    splits = []
    for fold, (_, held_out) in enumerate(splitter.split(groups)):
        mask = np.isin(codes, held_out)
        train, test = np.flatnonzero(~mask), np.flatnonzero(mask)
        if np.unique(d[train]).size != 2:
            raise ValueError(
                f"Cluster fold {fold} training sample must contain both treatment arms; "
                "change n_folds/seed or collect more independent clusters"
            )
        splits.append((train, test))
    return splits


@_checked_arithmetic
def cluster_standard_error(influence, codes):
    """Scalar CR1 for a row-weighted moment, centered at the row mean."""
    influence = np.asarray(influence, dtype=float)
    if influence.ndim != 1 or influence.shape != codes.shape:
        raise ValueError("Influence function must match fit-time cluster membership")
    _require_finite(influence)
    count = int(codes.max()) + 1
    sums = np.bincount(codes, weights=influence - influence.mean(), minlength=count)
    variance = float(count / (count - 1) * np.sum(sums**2) / len(influence)**2)
    error = float(np.sqrt(variance))
    _require_finite(sums, variance, error)
    return error
