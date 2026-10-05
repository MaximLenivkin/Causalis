"""Allocation validation and deterministic assignment boundaries."""

import numpy as np
import pandas as pd
import pytest

from causalis.shared.rct_design import assign_variants_df
from causalis.shared.rct_design import split


@pytest.mark.parametrize("weight", [np.nan, np.inf, -np.inf])
def test_assignment_rejects_nonfinite_weights_before_hashing(weight, monkeypatch):
    def unexpected_hash(key):
        raise AssertionError("Invalid allocation must be rejected before hashing")

    monkeypatch.setattr(split, "_hash_to_unit_interval", unexpected_hash)
    with pytest.raises(ValueError, match="finite real number"):
        assign_variants_df(
            pd.DataFrame({"id": [1, 2, 3]}), "id", "trial",
            {"control": weight, "treated": 0.5},
        )


@pytest.mark.parametrize("weight", [None, "0.5", True, np.bool_(True), 0.5 + 0j, pd.NA])
def test_assignment_rejects_nonreal_or_boolean_weights(weight):
    with pytest.raises(ValueError, match="finite real number"):
        assign_variants_df(
            pd.DataFrame({"id": [1]}), "id", "trial", {"control": weight},
        )


@pytest.mark.parametrize("variants,message", [
    ({}, "cannot be empty"),
    ({"control": -0.1, "treated": 0.5}, "negative weight"),
    ({"control": 0.0}, "must be > 0"),
    ({"control": 0.7, "treated": 0.5}, "exceeds 1.0"),
])
def test_assignment_keeps_existing_allocation_constraints(variants, message):
    with pytest.raises(ValueError, match=message):
        assign_variants_df(pd.DataFrame({"id": [1]}), "id", "trial", variants)


def test_partial_coverage_has_half_open_boundaries_and_preserves_input(monkeypatch):
    draws = iter([0.0, 0.249, 0.25, 0.499, 0.5, 0.999])
    monkeypatch.setattr(split, "_hash_to_unit_interval", lambda key: next(draws))
    frame = pd.DataFrame({"id": list("abcdef"), "feature": range(6)}, index=[7] * 6)
    snapshot = frame.copy(deep=True)

    actual = assign_variants_df(
        frame, "id", "trial", {"treated": np.float64(0.25), "zero": 0, "control": 0.25},
        variant_col="assigned",
    )

    assert actual.assigned.iloc[:4].tolist() == ["control", "control", "treated", "treated"]
    assert actual.assigned.iloc[4:].isna().all()
    pd.testing.assert_frame_equal(frame, snapshot)
    pd.testing.assert_frame_equal(actual.drop(columns="assigned"), snapshot)


def test_full_coverage_is_repeatable_and_independent_of_mapping_order():
    frame = pd.DataFrame({"id": list(range(1000)) + [7, 7]})
    first = assign_variants_df(frame, "id", "trial", {"control": 0.5, "treated": 0.5})
    second = assign_variants_df(frame, "id", "trial", {"treated": 0.5, "control": 0.5})

    pd.testing.assert_frame_equal(first, second)
    assert not first.variant.isna().any()
    assert set(first.variant) == {"control", "treated"}
    assert first.variant.iloc[7] == first.variant.iloc[-1] == first.variant.iloc[-2]
