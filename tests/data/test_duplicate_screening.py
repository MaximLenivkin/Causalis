"""Exact reference and adversarial checks for sampled duplicate screening."""

from __future__ import annotations

from collections import Counter
import importlib

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from causalis.data_contracts import CausalData, IVCausalData, MultiCausalData, RctCausalData
from causalis.data_contracts._duplicate_columns import column_values_equal


KINDS = ("causal", "iv", "multi", "rct")


def _construct(kind, frame, confounders):
    common = dict(df=frame, confounders=confounders, user_id="uid")
    if kind == "causal":
        return CausalData(outcome="y", treatment="d", **common)
    if kind == "iv":
        return IVCausalData(outcome="y", treatment="d", instruments="z", **common)
    if kind == "multi":
        return MultiCausalData(
            outcome="y", treatment_names=["d0", "d"], control_treatment="d0", **common
        )
    return RctCausalData(outcomes="y", treatment="d", **common)


def _base(n=257):
    i = np.arange(n)
    return pd.DataFrame({
        "y": i + 0.25, "d": i % 2, "d0": 1 - i % 2,
        "z": (i // 2) % 2, "x": i**2 + 0.125,
        "uid": [f"u{j}" for j in i],
    }, index=pd.Index((i % 13)[::-1], name="nonunique"))


def _legacy_signatures(frame, columns, *, screen=True):
    """Pre-B06 full-column hash grouping, independent of new screening."""
    groups = {}
    for column in columns:
        signature = CausalData._column_value_signature(frame[column])
        groups.setdefault(signature, []).append(column)
    return groups


def _capture(kind, frame, confounders):
    try:
        return _construct(kind, frame, confounders).df
    except ValueError as error:
        return str(error)


def _assert_legacy_equivalent(monkeypatch, kind, frame, confounders):
    original = frame.copy(deep=True)
    actual = _capture(kind, frame, confounders)
    with monkeypatch.context() as context:
        context.setattr(CausalData, "_column_value_signatures", staticmethod(_legacy_signatures))
        # The pre-B06 Causal/IV/Multi path boxed complete columns. Restore an
        # independent full-array verdict as well as the full hash grouping.
        for name in ("causaldata", "iv_causal_data", "multicausaldata", "rct_causal_data"):
            module = importlib.import_module(f"causalis.data_contracts.{name}")
            context.setattr(module, "column_values_equal", lambda a, b: np.array_equal(
                a.to_numpy(dtype=object, copy=False), b.to_numpy(dtype=object, copy=False)
            ))
        expected = _capture(kind, frame, confounders)
    if isinstance(expected, str):
        assert actual == expected
    else:
        assert isinstance(actual, pd.DataFrame)
        assert_frame_equal(actual, expected)
    assert_frame_equal(frame, original)
    return actual


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("case", [
    "different", "int_float", "nullable", "signed_zero", "bool_numeric",
    "large_int_distinct", "large_int_float_distinct", "unsampled_difference",
    "object_numeric_id", "datetime_id",
])
def test_public_contracts_match_full_fingerprint_reference(monkeypatch, kind, case):
    frame = _base()
    i = np.arange(len(frame))
    confounders = ["x", "other"]
    frame["other"] = i * 3 + 0.75
    if case == "int_float":
        frame["x"] = i + 5
        frame["other"] = (i + 5).astype(float)
    elif case == "nullable":
        frame["x"] = pd.array(i + 5, dtype="Int64")
        frame["other"] = pd.array(i + 5, dtype="Float64")
        frame["d"] = pd.array(i % 2, dtype="boolean")
    elif case == "signed_zero":
        frame["x"] = np.where(i % 3, i + 1.0, -0.0)
        frame["other"] = np.where(i % 3, i + 1.0, +0.0)
    elif case == "bool_numeric":
        frame["x"] = (i % 2).astype(bool)
        frame["other"] = (i % 2).astype(float)
    elif case == "large_int_distinct":
        frame["x"] = 2**60 + 2 * i
        frame["other"] = frame["x"].to_numpy() + 1
    elif case == "large_int_float_distinct":
        frame["x"] = 2**53 + 2 * i + 1
        frame["other"] = frame["x"].to_numpy(dtype=float)
    elif case == "unsampled_difference":
        frame["other"] = frame["x"].to_numpy()
        assert 1 not in np.linspace(0, len(frame) - 1, 64, dtype=np.intp)
        frame.iloc[1, frame.columns.get_loc("other")] = -100.0
    elif case == "object_numeric_id":
        # Historical numeric/object fingerprint categories stay distinct,
        # although Python value equality alone would regard this as a duplicate.
        frame["y"] = i + 10
        frame["uid"] = np.asarray(i + 10, dtype=object)
    elif case == "datetime_id":
        frame["uid"] = pd.date_range("2020-01-01", periods=len(frame))
    result = _assert_legacy_equivalent(monkeypatch, kind, frame, confounders)
    if case in {"int_float", "nullable", "signed_zero", "bool_numeric"}:
        assert isinstance(result, str) and "have identical values" in result
    else:
        assert isinstance(result, pd.DataFrame)


@pytest.mark.parametrize("kind", KINDS)
def test_interleaved_groups_preserve_first_error(monkeypatch, kind):
    frame = _base()
    i = np.arange(len(frame))
    frame["y"] = i + 0.5
    frame["a"] = frame["y"].to_numpy()
    frame["y"] = frame["y"].to_numpy().copy()
    frame.iloc[1, frame.columns.get_loc("y")] = -50.0
    frame["c"] = frame["a"].to_numpy()
    frame["b"] = frame["x"].to_numpy()
    result = _assert_legacy_equivalent(monkeypatch, kind, frame, ["x", "a", "b", "c"])
    # RCT originally nests full groups inside sampled groups; the other
    # contracts iterate globally full-fingerprinted groups in column order.
    expected = "Columns 'a'" if kind == "rct" else "Columns 'x'"
    assert expected in result


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("duplicate", [False, True])
def test_hash_collision_requires_exact_values(monkeypatch, kind, duplicate):
    monkeypatch.setattr(
        CausalData, "_column_value_signature",
        staticmethod(lambda series: ("collision", len(series), "same")),
    )
    frame = _base()
    frame["other"] = frame["x"].to_numpy() if duplicate else np.arange(len(frame)) + 2.25
    result = _assert_legacy_equivalent(monkeypatch, kind, frame, ["x", "other"])
    assert isinstance(result, str if duplicate else pd.DataFrame)
    if duplicate:
        assert "have identical values" in result


@pytest.mark.parametrize("kind", KINDS)
def test_random_distinct_columns_avoid_full_hashing(monkeypatch, kind):
    frame = _base(1001)
    calls = []
    signature = CausalData._column_value_signature

    def record(series):
        calls.append((series.name, len(series)))
        return signature(series)

    monkeypatch.setattr(CausalData, "_column_value_signature", staticmethod(record))
    _construct(kind, frame, ["x"])
    assert calls
    assert {length for _, length in calls} == {64}


@pytest.mark.parametrize("n", [0, 1, 64, 65, 257])
def test_short_tables_do_not_repeat_full_hashing(monkeypatch, n):
    frame = pd.DataFrame({"a": np.arange(n) + 1.0, "b": np.arange(n) + 10.0})
    calls = []
    signature = CausalData._column_value_signature

    def record(series):
        calls.append((series.name, len(series)))
        return signature(series)

    monkeypatch.setattr(CausalData, "_column_value_signature", staticmethod(record))
    CausalData._column_value_signatures(frame, ["a", "b"])
    assert Counter(calls) == Counter([("a", min(n, 64)), ("b", min(n, 64))])


@pytest.mark.parametrize("n", [65535, 65536, 65537, 131073])
@pytest.mark.parametrize("equal", [False, True])
def test_exact_comparison_crosses_boxing_chunks(n, equal):
    values = 2**60 + 2 * np.arange(n, dtype=np.int64)
    first = pd.Series(values)
    second = pd.Series(values.copy(), index=np.arange(n)[::-1])
    if not equal:
        second.iloc[-1] += 1
    assert column_values_equal(first, second) is equal
    assert column_values_equal(first, second) == np.array_equal(
        first.to_numpy(dtype=object), second.to_numpy(dtype=object)
    )


def test_exact_comparison_rejects_different_lengths():
    assert not column_values_equal(pd.Series([1, 2]), pd.Series([1]))


def test_parallel_candidate_hashes_keep_input_group_order(monkeypatch):
    frame = _base()
    frame["other"] = frame["x"].to_numpy()
    monkeypatch.setattr(CausalData, "_duplicate_check_worker_count", staticmethod(lambda n, p: 2))
    groups = CausalData._column_value_signatures(frame, ["y", "x", "other", "d"])
    assert list(groups.values()) == [["x", "other"]]
