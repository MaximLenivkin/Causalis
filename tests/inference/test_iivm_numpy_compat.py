"""Joint IV folds must match Python string labels on NumPy 1.x and 2.x."""
import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import StratifiedKFold

from causalis.scenarios.iv import IIVM


def _inputs(fallback, dtype):
    # Joint cells are sufficiently common, or one cell triggers Z-only fallback.
    counts = [15, 15, 15, 15] if not fallback else [20, 20, 19, 1]
    cells = [(0, 0), (0, 1), (1, 0), (1, 1)]
    pairs = np.concatenate([np.tile(cell, (count, 1)) for cell, count in zip(cells, counts)])
    permutation = np.random.default_rng(815).permutation(len(pairs))
    z, d = pairs[permutation].T.astype(dtype)
    x = np.random.default_rng(301).normal(size=(len(d), 2))
    return x, d, z


@pytest.mark.parametrize("dtype", [int, float, bool])
@pytest.mark.parametrize("fallback", [False, True])
@pytest.mark.parametrize("seed", [0, 17])
def test_same_joint_or_instrument_folds_as_independent_python_labels(dtype, fallback, seed):
    x, d, z = _inputs(fallback, dtype)
    joint = np.array([f"{left}_{right}" for left, right in zip(z.astype(str), d.astype(str))])
    assert (int(pd.Series(joint).value_counts().min()) < 3) is fallback
    labels = z if fallback else joint
    expected = list(StratifiedKFold(n_splits=3, shuffle=True, random_state=seed).split(x, labels))
    actual = IIVM(n_folds=3, random_state=seed)._make_cross_fit_splits(X=x, d=d, z=z)
    for (actual_train, actual_test), (expected_train, expected_test) in zip(actual, expected):
        np.testing.assert_array_equal(actual_train, expected_train)
        np.testing.assert_array_equal(actual_test, expected_test)


def test_joint_folds_do_not_require_unicode_array_plus_operator():
    class LegacyUnicode(np.ndarray):
        def __add__(self, other):
            raise TypeError("NumPy 1.x has no Unicode array addition loop")

    class NumericWithLegacyStrings(np.ndarray):
        def astype(self, dtype, *args, **kwargs):
            result = super().astype(dtype, *args, **kwargs)
            return result.view(LegacyUnicode) if dtype is str else result

    x, d, z = _inputs(False, int)
    expected = IIVM(n_folds=3, random_state=17)._make_cross_fit_splits(X=x, d=d, z=z)
    actual = IIVM(n_folds=3, random_state=17)._make_cross_fit_splits(
        X=x, d=d.view(NumericWithLegacyStrings), z=z.view(NumericWithLegacyStrings))
    for (actual_train, actual_test), (expected_train, expected_test) in zip(actual, expected):
        np.testing.assert_array_equal(actual_train, expected_train)
        np.testing.assert_array_equal(actual_test, expected_test)
