"""Generated row identifiers must satisfy the public CausalData contract."""

import uuid

import numpy as np
import pandas as pd

from causalis.data_contracts import CausalData
from causalis.dgp import generate_rct
from causalis.dgp import base as dgp_base


def test_random_ids_keep_full_uuid_entropy_and_satisfy_causal_data(monkeypatch):
    # Distinct UUIDs with one shared five-character prefix reproduce truncation
    # collisions deterministically, without depending on random birthday events.
    identifiers = [uuid.UUID(int=(0xABCDE << 108) + i) for i in range(40)]
    draws = iter(identifiers)
    monkeypatch.setattr(dgp_base.uuid, "uuid4", lambda: next(draws))

    data = generate_rct(
        n=40, random_state=42, add_pre=False, return_causal_data=True,
    )

    assert isinstance(data, CausalData)
    assert data.user_id.is_unique
    assert data.user_id.tolist() == [identifier.hex for identifier in identifiers]


def test_random_id_generation_retries_a_full_uuid_collision(monkeypatch):
    first, second, third = [uuid.UUID(int=i) for i in (1, 2, 3)]
    draws = iter([first, first, second, third])
    monkeypatch.setattr(dgp_base.uuid, "uuid4", lambda: next(draws))
    frame = pd.DataFrame({"y": [0.0, 1.0, 2.0], "d": [0, 1, 0]})

    actual = dgp_base._add_ancillary_info(
        frame, 3, np.random.default_rng(11), False, [],
    )

    assert actual.user_id.tolist() == [first.hex, second.hex, third.hex]
    assert actual.user_id.is_unique


def test_deterministic_ids_remain_unique_and_seed_reproducible(monkeypatch):
    def unexpected_uuid():
        raise AssertionError("Deterministic IDs must not draw UUIDs")

    monkeypatch.setattr(dgp_base.uuid, "uuid4", unexpected_uuid)
    options = dict(n=2000, random_state=71, add_pre=False, deterministic_ids=True)
    first = generate_rct(**options)
    second = generate_rct(**options)

    pd.testing.assert_series_equal(first.user_id, second.user_id)
    assert first.user_id.is_unique
    assert len(first.user_id) == options["n"]
