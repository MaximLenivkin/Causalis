"""Bind external nuisances to an ordered sample and declared outer splits."""
from copy import deepcopy
from collections.abc import Mapping
from numbers import Integral
import json

import numpy as np
import pandas as pd

from causalis.scenarios._prediction import _real_array
from ._repeated import validate_n_rep


def _integers(values, shape, name):
    raw = np.asarray(values)
    if raw.shape != shape or raw.dtype.kind not in "iu":
        raise ValueError(f"{name} must be an integer array with shape {shape}")
    # Check before conversion to avoid unsigned overflow.
    if np.any(raw > np.iinfo(np.int64).max):
        raise ValueError(f"{name} contains out-of-range integers")
    return raw.astype(np.int64, copy=True)


def _shape(n, repetitions):
    return (n,) if repetitions == 1 else (n, repetitions)


def prediction_arrays(predictions, index, repetitions, binary):
    """Snapshot all nuisances before any fit publication or overlap repair."""
    if not isinstance(predictions, Mapping) or set(predictions) != {"g0", "g1", "m"}:
        raise ValueError("external_predictions must contain exactly g0, g1 and m")
    arrays = {}
    for name, values in predictions.items():
        if isinstance(values, (pd.Series, pd.DataFrame)) and not values.index.equals(index):
            raise ValueError(f"{name} index must match input row index in order")
        array = _real_array(values, name=f"external {name}")
        if array.shape != _shape(len(index), repetitions):
            raise ValueError(f"external {name} must have shape {_shape(len(index), repetitions)}")
        if (name == "m" or binary) and np.any((array < 0) | (array > 1)):
            raise ValueError(f"external {name} probabilities must lie in [0, 1]")
        arrays[name] = array.copy()
    return arrays


def context(model, X, y, d, codes):
    """Use existing ordered numeric fingerprints plus the role/cluster schema."""
    if not np.all(np.isfinite(X)) or not np.all(np.isfinite(y)):
        raise ValueError("External OOF sample must contain finite outcomes and confounders")
    return {
        "sample": model._compute_sample_fingerprint(X=X, y=y, d=d),
        "roles": {"outcome": model.data.outcome.name,
                  "treatment": model.data.treatment.name,
                  "confounders": list(model.data.confounders)},
        "cluster_hash": None if codes is None else model._hash_array(codes, dtype=np.int64),
        "n_folds": model.n_folds, "n_rep": validate_n_rep(model.n_rep),
    }


def build_manifest(model, arrays, sample_context, folds, training_indices, split_seeds):
    return dict(schema_version=1, **deepcopy(sample_context),
                prediction_hashes={name: model._hash_array(value, dtype=float)
                                   for name, value in arrays.items()},
                folds=deepcopy(folds), training_indices=deepcopy(training_indices),
                split_seeds=deepcopy(split_seeds))


def validate_manifest(model, arrays, manifest, sample_context, d, codes):
    """Validate declared disjoint complements; return a portable owned mapping.

    This checks declarations, not the training history of an external program.
    """
    expected_keys = set(sample_context) | {
        "schema_version", "prediction_hashes", "folds", "training_indices", "split_seeds"}
    if not isinstance(manifest, Mapping) or set(manifest) != expected_keys:
        raise ValueError("oof_manifest has missing or unknown fields")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise ValueError("Unsupported oof_manifest schema_version")
    for name, expected in sample_context.items():
        try:
            matches = json.dumps(manifest[name], sort_keys=True) == json.dumps(expected, sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"oof_manifest {name} must contain portable schema values") from exc
        if not matches:
            raise ValueError(f"oof_manifest {name} does not match current sample/configuration")
    hashes = {name: model._hash_array(value, dtype=float) for name, value in arrays.items()}
    if manifest["prediction_hashes"] != hashes:
        raise ValueError("oof_manifest prediction_hashes do not match external_predictions")
    n, repetitions, count = len(d), model.n_rep, model.n_folds
    folds = _integers(manifest["folds"], _shape(n, repetitions), "oof_manifest folds")
    seeds = manifest["split_seeds"]
    if not isinstance(seeds, (list, tuple)) or len(seeds) != repetitions or any(
        isinstance(seed, (bool, np.bool_)) or not isinstance(seed, Integral)
        or not 0 <= seed <= np.iinfo(np.uint32).max for seed in seeds
    ):
        raise ValueError("oof_manifest split_seeds must contain one uint32 integer per repetition")
    training = manifest["training_indices"]
    if not isinstance(training, (list, tuple)) or len(training) != repetitions:
        raise ValueError("oof_manifest training_indices must contain one partition per repetition")
    owned_training = []
    for rep in range(repetitions):
        assignment = folds if repetitions == 1 else folds[:, rep]
        if not np.array_equal(np.unique(assignment), np.arange(count)):
            raise ValueError("oof_manifest folds must cover every fold id from 0 to n_folds-1")
        if codes is not None:
            for group in range(int(codes.max()) + 1):
                if np.unique(assignment[codes == group]).size != 1:
                    raise ValueError("oof_manifest splits a cluster between train and test")
        partition = training[rep]
        if not isinstance(partition, (list, tuple)) or len(partition) != count:
            raise ValueError("oof_manifest training_indices must contain every fold")
        owned_partition = []
        for fold in range(count):
            expected = np.flatnonzero(assignment != fold)
            train = _integers(partition[fold], expected.shape, "oof_manifest training indices")
            if not np.array_equal(np.sort(train), expected):
                raise ValueError("oof_manifest training indices must equal the held-out complement")
            if np.unique(d[train]).size != 2:
                raise ValueError("oof_manifest training sample must contain both treatment arms")
            owned_partition.append(train.tolist())
        owned_training.append(owned_partition)
    return dict(schema_version=1, **deepcopy(sample_context), prediction_hashes=hashes,
                folds=folds.tolist(), training_indices=owned_training,
                split_seeds=[int(seed) for seed in seeds])


def partition_manifest(model, arrays, manifest, rep):
    """Detach one validated repeated partition for the ordinary scalar fit."""
    child = deepcopy(manifest)
    child.update(n_rep=1, folds=np.asarray(manifest["folds"])[:, rep].tolist(),
                 training_indices=[manifest["training_indices"][rep]],
                 split_seeds=[manifest["split_seeds"][rep]],
                 prediction_hashes={name: model._hash_array(value, dtype=float)
                                    for name, value in arrays.items()})
    return child
