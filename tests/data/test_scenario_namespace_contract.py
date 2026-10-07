"""Scenario-owned outcome and identifier roles must preserve generated features."""

import importlib
import re

import numpy as np
import pandas as pd
import pytest

from causalis.scenarios.classic_rct.dgp import classic_rct_gamma_26, generate_classic_rct_26
from causalis.scenarios.cuped.dgp import generate_cuped_tweedie_26, make_cuped_binary_26
from causalis.scenarios.iv import generate_offer_iv_26


N = 384
SEED = 731
BINARY_ORACLES = ("m", "m_obs", "tau_link", "g0", "g1", "cate")
CLASSIC_FEATURES = ["platform_ios", "country_usa", "source_paid"]
ANCILLARY_FEATURES = ["age", "cnt_trans", "platform_Android", "platform_iOS", "invited_friend"]
CUPED_BINARY_FEATURES = [
    "tenure_months", "spend_last_month", "discount_rate", "support_tickets",
    "email_open_rate", "referral_count", "plan_tier_plus", "plan_tier_pro", "region_eu",
]
CUPED_TWEEDIE_FEATURES = [
    "tenure_months", "avg_sessions_week", "spend_last_month", "discount_rate",
    "platform_ios", "platform_web",
]
IV_FEATURES = [
    "age", "tenure_months", "annual_income", "credit_score", "app_sessions_30d",
    "prior_spend_30d", "savings_balance", "premium_user", "autopay_enabled",
    "region_north", "region_west", "acquisition_paid",
]
IV_ORACLES = (
    "m", "r_obs", "r_z0", "r_z1", "g_z0", "g_z1", "iv_first_stage",
    "iv_reduced_form", "late_x", "late", "tau_link", "g_d0", "g_d1", "cate",
)


def _classic(kind, **kwargs):
    options = dict(n=N, seed=SEED, add_ancillary=False, deterministic_ids=True)
    options.update(kwargs)
    generator = generate_classic_rct_26 if kind == "binary" else classic_rct_gamma_26
    return generator(**options)


def _collision(operation, column):
    with pytest.raises(ValueError) as caught:
        operation()
    message = str(caught.value)
    assert column in message
    assert re.search("collid|collision|overlap|already.*exist", message, re.IGNORECASE)


def _assert_contract_matches_raw(raw, data, treatment):
    expected = raw[data.df.columns].copy()
    # The public data contract canonicalizes treatment to int8. Other numeric
    # columns in these scenarios retain their generated dtype.
    expected[treatment] = expected[treatment].astype(np.int8)
    pd.testing.assert_frame_equal(data.df, expected)


@pytest.mark.parametrize("return_causal_data", [False, True])
@pytest.mark.parametrize("include_oracle", [False, True])
@pytest.mark.parametrize("add_ancillary", [False, True])
def test_binary_scenario_pre_cannot_replace_renamed_conversion_outcome(
    return_causal_data, include_oracle, add_ancillary
):
    _collision(
        lambda: _classic(
            "binary", add_pre=True, pre_name="conversion", add_ancillary=add_ancillary,
            include_oracle=include_oracle, return_causal_data=return_causal_data,
        ),
        "conversion",
    )


@pytest.mark.parametrize("kind", ["binary", "gamma"])
@pytest.mark.parametrize("return_causal_data", [False, True])
@pytest.mark.parametrize("include_oracle", [False, True])
def test_classic_pre_cannot_take_the_identifier_added_by_the_scenario(
    kind, return_causal_data, include_oracle
):
    # The underlying wrapper has ancillary addition disabled, but each classic
    # scenario still emits its own identifier after underlying generation.
    _collision(
        lambda: _classic(
            kind, add_pre=True, pre_name="user_id", include_oracle=include_oracle,
            return_causal_data=return_causal_data,
        ),
        "user_id",
    )


@pytest.mark.parametrize("kind", ["binary", "gamma"])
@pytest.mark.parametrize("pre_name", BINARY_ORACLES)
def test_classic_projection_retains_a_pre_feature_named_like_a_disabled_oracle(kind, pre_name):
    options = dict(add_pre=True, include_oracle=False, return_causal_data=True)
    actual = _classic(kind, pre_name=pre_name, **options)
    expected = _classic(kind, pre_name="history", **options)
    assert actual.confounders_names == CLASSIC_FEATURES + [pre_name]
    assert actual.user_id_name == "user_id"
    pd.testing.assert_frame_equal(actual.df.rename(columns={pre_name: "history"}), expected.df)


@pytest.mark.parametrize("kind", ["binary", "gamma"])
@pytest.mark.parametrize("include_oracle", [False, True])
@pytest.mark.parametrize("pre_name", ["conversion", "user_id", "m", None, [], ""])
def test_unused_classic_pre_name_does_not_reserve_or_reclassify_columns(kind, include_oracle, pre_name):
    options = dict(add_pre=False, include_oracle=include_oracle, return_causal_data=False)
    expected = _classic(kind, **options)
    actual = _classic(kind, pre_name=pre_name, **options)
    assert actual.columns.is_unique
    pd.testing.assert_frame_equal(actual, expected)


@pytest.mark.parametrize("kind", ["binary", "gamma"])
@pytest.mark.parametrize("pre_name", ["conversion_history", np.str_("history")])
def test_valid_classic_pre_names_preserve_outcome_and_feature_values(kind, pre_name):
    options = dict(add_pre=True, include_oracle=False)
    actual, expected = _classic(kind, pre_name=pre_name, **options), _classic(kind, **options)
    assert pre_name in actual.confounders_names
    pd.testing.assert_frame_equal(actual.df.rename(columns={pre_name: "y_pre"}), expected.df)


def test_conversion_remains_available_as_a_gamma_pre_feature():
    options = dict(add_pre=True, include_oracle=True)
    actual = _classic("gamma", pre_name="conversion", **options)
    expected = _classic("gamma", pre_name="history", **options)
    assert actual.outcome_name == "y"
    assert actual.confounders_names == CLASSIC_FEATURES + ["conversion"]
    pd.testing.assert_frame_equal(actual.df.rename(columns={"conversion": "history"}), expected.df)


@pytest.mark.parametrize("kind", ["binary", "gamma"])
@pytest.mark.parametrize("include_oracle", [False, True])
@pytest.mark.parametrize("add_ancillary", [False, True])
@pytest.mark.parametrize("add_pre", [False, True])
def test_valid_classic_flags_preserve_actual_features_and_raw_contract_values(
    kind, include_oracle, add_ancillary, add_pre
):
    options = dict(
        include_oracle=include_oracle, add_ancillary=add_ancillary,
        add_pre=add_pre, pre_name="history",
    )
    raw = _classic(kind, return_causal_data=False, **options)
    data = _classic(kind, return_causal_data=True, **options)
    outcome = "conversion" if kind == "binary" else "y"
    features = CLASSIC_FEATURES + (ANCILLARY_FEATURES if add_ancillary else []) + (["history"] if add_pre else [])
    assert raw.columns.is_unique and data.df.columns.is_unique
    assert data.outcome_name == outcome
    assert data.treatment_name == "d"
    assert data.confounders_names == features
    assert data.user_id_name == "user_id"
    assert raw["user_id"].is_unique
    assert set(BINARY_ORACLES).issubset(raw.columns) == include_oracle
    assert ("history" in raw.columns) == add_pre
    assert raw["d"].isin([0.0, 1.0]).all()
    if kind == "binary":
        assert raw[outcome].isin([0.0, 1.0]).all()
        assert "y" not in raw.columns
    _assert_contract_matches_raw(raw, data, "d")


@pytest.mark.parametrize(
    "kind,module,function_name",
    [
        ("binary", "causalis.dgp", "generate_classic_rct_26"),
        ("binary", "causalis.dgp.causaldata", "generate_classic_rct_26"),
        ("binary", "causalis.data_contracts", "generate_classic_rct_26"),
        ("gamma", "causalis.dgp", "classic_rct_gamma_26"),
        ("gamma", "causalis.dgp.causaldata", "classic_rct_gamma_26"),
        ("gamma", "causalis.data_contracts", "classic_rct_gamma_26"),
    ],
)
def test_public_classic_aliases_preserve_the_same_scenario_contract(kind, module, function_name):
    alias = getattr(importlib.import_module(module), function_name)
    options = dict(n=N, seed=SEED, add_pre=True, pre_name="history", add_ancillary=False, include_oracle=False)
    actual = alias(**options)
    expected = _classic(kind, add_pre=True, pre_name="history", include_oracle=False)
    assert actual.confounders_names == CLASSIC_FEATURES + ["history"]
    pd.testing.assert_frame_equal(actual.df, expected.df)


@pytest.mark.parametrize("scenario", ["binary", "tweedie"])
@pytest.mark.parametrize("include_oracle", [False, True])
@pytest.mark.parametrize("add_pre", [False, True])
def test_unchanged_cuped_scenarios_preserve_actual_pre_fields_and_oracle_flags(
    scenario, include_oracle, add_pre
):
    generator = make_cuped_binary_26 if scenario == "binary" else generate_cuped_tweedie_26
    options = dict(n=N, seed=SEED, include_oracle=include_oracle, add_pre=add_pre, pre_name="history")
    features = CUPED_BINARY_FEATURES if scenario == "binary" else CUPED_TWEEDIE_FEATURES
    if scenario == "tweedie":
        options["pre_name_2"] = "second_history"
    if add_pre:
        features = features + (["history"] if scenario == "binary" else ["history", "second_history"])
    raw = generator(return_causal_data=False, **options)
    data = generator(return_causal_data=True, **options)
    assert raw.columns.is_unique and data.df.columns.is_unique
    assert data.confounders_names == features
    assert data.user_id_name is None
    assert set(BINARY_ORACLES).issubset(raw.columns) == include_oracle
    assert ("history" in raw.columns) == add_pre
    if scenario == "tweedie":
        assert ("second_history" in raw.columns) == add_pre
    _assert_contract_matches_raw(raw, data, "d")


@pytest.mark.parametrize("include_oracle", [False, True])
@pytest.mark.parametrize("deterministic_ids", [False, True])
def test_unchanged_iv_scenario_preserves_renamed_roles_and_feature_values(include_oracle, deterministic_ids):
    options = dict(n=N, seed=SEED, include_oracle=include_oracle, deterministic_ids=deterministic_ids)
    raw = generate_offer_iv_26(return_causal_data=False, **options)
    data = generate_offer_iv_26(return_causal_data=True, **options)
    assert raw.columns.is_unique and data.df.columns.is_unique
    assert data.outcome_name == "net_revenue_90d"
    assert data.treatment_name == "accepted_offer"
    assert data.instruments_names == ["offer_eligible"]
    assert data.confounders_names == IV_FEATURES
    assert data.user_id_name == "user_id"
    assert raw["user_id"].is_unique
    assert {"y", "d", "z"}.isdisjoint(raw.columns)
    assert set(IV_ORACLES).issubset(raw.columns) == include_oracle
    assert raw["accepted_offer"].isin([0.0, 1.0]).all()
    assert raw["offer_eligible"].isin([0.0, 1.0]).all()
    _assert_contract_matches_raw(raw, data, "accepted_offer")
