"""Actual emitted roles govern augmentation, ordering and automatic projection."""

import re

import numpy as np
import pandas as pd
import pytest

from causalis.dgp.base import _add_ancillary_info
from causalis.dgp.causaldata.base import CausalDatasetGenerator
from causalis.dgp.causaldata.functional import (
    generate_cuped_binary,
    generate_rct,
    make_cuped_tweedie,
    obs_linear_effect,
)
from causalis.dgp.causaldata.preperiod import PreCorrSpec, add_preperiod_covariate
from causalis.dgp.causaldata_instrumental.base import InstrumentalGenerator
from causalis.dgp.causaldata_instrumental.functional import generate_iv_data
from causalis.dgp.multicausaldata.base import MultiCausalDatasetGenerator
from causalis.dgp.multicausaldata.functional import generate_multitreatment


N = 96
SEED = 731
BINARY_ORACLES = ("m", "m_obs", "tau_link", "g0", "g1", "cate")
IV_ORACLES = (
    "m", "r_obs", "r_z0", "r_z1", "g_z0", "g_z1", "iv_first_stage",
    "iv_reduced_form", "late_x", "late", "tau_link", "g_d0", "g_d1", "cate",
)
ANCILLARY = (
    "user_id", "age", "cnt_trans", "platform_Android", "platform_iOS", "invited_friend",
)
ORACLE_CASES = [("binary", name) for name in BINARY_ORACLES] + [
    ("iv", name) for name in IV_ORACLES
]


def _specs(*names):
    return [{"name": name, "dist": "normal"} for name in names]


def _rct(**kwargs):
    options = dict(
        n=N, random_state=SEED, outcome_type="normal",
        confounder_specs=_specs("feature", "other"), beta_y=[0.4, -0.2],
        add_ancillary=False, add_pre=False, use_prognostic=False,
    )
    options.update(kwargs)
    return generate_rct(**options)


def _iv(**kwargs):
    options = dict(
        n=N, random_state=SEED, k=0, confounder_specs=_specs("feature"),
        beta_y=[0.4], add_ancillary=False,
    )
    options.update(kwargs)
    return generate_iv_data(**options)


def _direct(kind, **kwargs):
    options = dict(k=0, seed=SEED, confounder_specs=_specs("feature"), beta_y=[0.4])
    options.update(kwargs)
    cls = CausalDatasetGenerator if kind == "binary" else InstrumentalGenerator
    return cls(**options)


def _convert(generator, kind, **kwargs):
    method = generator.to_causal_data if kind == "binary" else generator.to_iv_causal_data
    return method(N, **kwargs)


def _collision(operation, column):
    with pytest.raises(ValueError) as caught:
        operation()
    message = str(caught.value)
    assert repr(column) in message
    assert re.search("collid|collision|overlap|already.*exist", message, re.IGNORECASE)


def _input_frame():
    x = np.linspace(-2.0, 2.0, N)
    return pd.DataFrame({"y": 0.3 * x + np.sin(np.arange(N)), "d": np.arange(N) % 2, "feature": x})


def _add_pre(frame, name, rng, builder=None):
    if builder is None:
        builder = lambda data: 0.3 * data["feature"].to_numpy()
    return add_preperiod_covariate(
        frame, y_col="y", d_col="d", pre_name=name, base_builder=builder,
        spec=PreCorrSpec(target_corr=0.2, transform="none", winsor_q=None), rng=rng,
    )


@pytest.mark.parametrize("include_oracle", [False, True])
@pytest.mark.parametrize("pre_name", ["y", "d", "m", "feature"])
def test_unused_rct_pre_name_does_not_change_values_schema_or_order(pre_name, include_oracle):
    expected = _rct(include_oracle=include_oracle)
    actual = _rct(include_oracle=include_oracle, pre_name=pre_name)
    assert actual.columns.is_unique
    pd.testing.assert_frame_equal(actual, expected)


@pytest.mark.parametrize("include_oracle", [False, True])
def test_unused_pre_name_does_not_reclassify_an_ancillary_field(include_oracle):
    options = dict(include_oracle=include_oracle, add_ancillary=True, deterministic_ids=True)
    pd.testing.assert_frame_equal(_rct(pre_name="age", **options), _rct(**options))


@pytest.mark.parametrize("pre_name", ["y", "d", "g0", "feature"])
def test_unused_pre_name_also_preserves_automatic_rct_projection(pre_name):
    expected = _rct(return_causal_data=True)
    actual = _rct(return_causal_data=True, pre_name=pre_name)
    assert actual.confounders_names == ["feature", "other"]
    pd.testing.assert_frame_equal(actual.df, expected.df)


@pytest.mark.parametrize("pre_name", ["y", "d", "g0", "feature", "age", "user_id"])
def test_enabled_rct_pre_covariate_cannot_replace_an_emitted_column(pre_name):
    _collision(
        lambda: _rct(add_pre=True, pre_name=pre_name, add_ancillary=pre_name in ANCILLARY),
        pre_name,
    )


@pytest.mark.parametrize("pre_name", ["m", "user_id"])
def test_rct_retains_actual_pre_covariate_when_oracle_or_identifier_role_is_inactive(pre_name):
    options = dict(include_oracle=False, add_pre=True, return_causal_data=True)
    actual, expected = _rct(pre_name=pre_name, **options), _rct(**options)
    assert actual.confounders_names == ["feature", "other", pre_name]
    assert actual.user_id_name is None
    pd.testing.assert_frame_equal(actual.df.rename(columns={pre_name: "y_pre"}), expected.df)


@pytest.mark.parametrize("column", ANCILLARY)
def test_shared_ancillary_rejects_existing_fields_before_mutation_or_rng(column):
    frame = _input_frame()
    frame[column] = np.linspace(10.0, 11.0, N)
    before = frame.copy(deep=True)
    rng, untouched = np.random.default_rng(SEED), np.random.default_rng(SEED)
    _collision(lambda: _add_ancillary_info(frame, N, rng, True, ["feature"]), column)
    pd.testing.assert_frame_equal(frame, before)
    np.testing.assert_array_equal(rng.random(10), untouched.random(10))


@pytest.mark.parametrize("column", ["y", "d", "feature"])
def test_shared_pre_rejects_existing_fields_before_builder_or_rng(column):
    frame = _input_frame()
    before = frame.copy(deep=True)
    calls = []
    rng, untouched = np.random.default_rng(SEED), np.random.default_rng(SEED)
    _collision(lambda: _add_pre(frame, column, rng, lambda data: calls.append(True)), column)
    assert calls == []
    pd.testing.assert_frame_equal(frame, before)
    np.testing.assert_array_equal(rng.random(10), untouched.random(10))


@pytest.mark.parametrize("pre_name", [None, "", 7, [], b"pre"])
def test_shared_pre_requires_an_actual_nonempty_string_before_side_effects(pre_name):
    frame, calls = _input_frame(), []
    before = frame.copy(deep=True)
    rng, untouched = np.random.default_rng(SEED), np.random.default_rng(SEED)
    with pytest.raises(ValueError, match="(?i)nonempty string"):
        _add_pre(frame, pre_name, rng, lambda data: calls.append(True))
    assert calls == []
    pd.testing.assert_frame_equal(frame, before)
    np.testing.assert_array_equal(rng.random(10), untouched.random(10))


@pytest.mark.parametrize("pre_name", [np.str_("baseline"), " ", "y_pre_suffix"])
def test_pre_names_are_preserved_literally(pre_name):
    frame = _add_pre(_input_frame(), pre_name, np.random.default_rng(SEED))
    assert list(frame.columns) == ["y", "d", "feature", pre_name]
    assert np.isfinite(frame[pre_name]).all()


@pytest.mark.parametrize("augmentation", ["pre", "ancillary"])
def test_augmentation_rejects_duplicate_input_columns_before_side_effects(augmentation):
    frame = _input_frame()
    frame = pd.concat([frame, frame[["feature"]]], axis=1)
    before, calls = frame.copy(deep=True), []
    rng, untouched = np.random.default_rng(SEED), np.random.default_rng(SEED)
    with pytest.raises(ValueError, match="(?i)duplicate"):
        if augmentation == "pre":
            _add_pre(frame, "baseline", rng, lambda data: calls.append(True))
        else:
            _add_ancillary_info(frame, N, rng, True, [])
    assert calls == []
    pd.testing.assert_frame_equal(frame, before)
    np.testing.assert_array_equal(rng.random(10), untouched.random(10))


def test_pre_builder_cannot_create_a_column_that_augmentation_would_overwrite():
    frame = _input_frame()
    rng, untouched = np.random.default_rng(SEED), np.random.default_rng(SEED)

    def builder(data):
        data["baseline"] = -99.0
        return data["feature"].to_numpy()

    _collision(lambda: _add_pre(frame, "baseline", rng, builder), "baseline")
    np.testing.assert_array_equal(frame["baseline"], np.full(N, -99.0))
    np.testing.assert_array_equal(rng.random(10), untouched.random(10))


@pytest.mark.parametrize("path", ["rct", "iv", "observational"])
@pytest.mark.parametrize("column", ANCILLARY)
def test_public_ancillary_paths_reject_actual_confounder_collisions(path, column):
    options = dict(confounder_specs=_specs(column), beta_y=[0.4], include_oracle=False, add_ancillary=True)
    if path == "rct":
        operation = lambda: _rct(**options)
    elif path == "iv":
        operation = lambda: _iv(**options)
    else:
        operation = lambda: obs_linear_effect(n=N, random_state=SEED, **options)
    _collision(operation, column)


@pytest.mark.parametrize("column", ANCILLARY)
def test_iv_ancillary_fields_cannot_replace_the_actual_instrument(column):
    _collision(lambda: _iv(instrument_name=column, add_ancillary=True, include_oracle=False), column)


@pytest.mark.parametrize("kind,column", ORACLE_CASES)
@pytest.mark.parametrize("path", ["direct", "wrapper"])
def test_automatic_projection_retains_actual_disabled_oracle_named_features(kind, column, path):
    options = dict(confounder_specs=_specs(column), include_oracle=False, beta_y=[0.4])
    if path == "direct":
        data = _convert(_direct(kind, **options), kind)
    elif kind == "binary":
        data = _rct(return_causal_data=True, **options)
    else:
        data = _iv(return_causal_data=True, **options)
    assert data.confounders_names == [column]
    assert data.user_id_name is None
    expected = np.random.default_rng(SEED).normal(size=(N, 1))[:, 0]
    np.testing.assert_array_equal(data.X[column], expected)


@pytest.mark.parametrize("kind", ["binary", "iv"])
@pytest.mark.parametrize("path", ["direct", "wrapper"])
def test_numeric_user_id_confounder_remains_a_feature_without_ancillary_ids(kind, path):
    options = dict(confounder_specs=_specs("user_id"), beta_y=[0.4])
    if path == "direct":
        data = _convert(_direct(kind, **options), kind)
    elif kind == "binary":
        data = _rct(return_causal_data=True, **options)
    else:
        data = _iv(return_causal_data=True, **options)
    assert data.confounders_names == ["user_id"]
    assert data.user_id_name is None
    np.testing.assert_array_equal(data.X["user_id"], np.random.default_rng(SEED).normal(size=(N, 1))[:, 0])


@pytest.mark.parametrize("kind,column", [("binary", "g0"), ("iv", "g_d0")])
def test_direct_automatic_projection_uses_actual_sampler_names(kind, column, monkeypatch):
    first = np.linspace(-2.0, 2.0, N)
    second = np.sin(np.arange(N))
    X = np.column_stack([first, second])
    generator = _direct(
        kind, include_oracle=False, confounder_specs=_specs("declared"), beta_y=[0.4, -0.2],
    )
    monkeypatch.setattr(
        type(generator), "_sample_X", lambda self, n: (X.copy(), [column, "expanded_feature"]),
    )
    data = _convert(generator, kind)
    assert data.confounders_names == [column, "expanded_feature"]
    np.testing.assert_array_equal(data.X.to_numpy(), X)


@pytest.mark.parametrize("instrument_name", ["user_id", "m", "age"])
@pytest.mark.parametrize("return_causal_data", [False, True])
def test_iv_instrument_role_takes_precedence_over_inactive_wrapper_roles(instrument_name, return_causal_data):
    result = _iv(instrument_name=instrument_name, include_oracle=False, return_causal_data=return_causal_data)
    frame = result.df if return_causal_data else result
    assert frame.columns.is_unique
    assert list(frame.columns) == ["y", "d", instrument_name, "feature"]
    assert frame[instrument_name].isin([0.0, 1.0]).all()
    if return_causal_data:
        assert result.instruments_names == [instrument_name]
        assert result.confounders_names == ["feature"]
        assert result.user_id_name is None


@pytest.mark.parametrize("kind", ["binary", "iv"])
@pytest.mark.parametrize("path", ["direct", "wrapper"])
def test_enabled_oracles_are_excluded_from_default_feature_projection(kind, path):
    if path == "direct":
        data = _convert(_direct(kind), kind)
    elif kind == "binary":
        data = _rct(confounder_specs=_specs("feature"), beta_y=[0.4], return_causal_data=True)
    else:
        data = _iv(return_causal_data=True)
    assert data.confounders_names == ["feature"]
    assert data.user_id_name is None


@pytest.mark.parametrize("kind,column", [("binary", "g0"), ("iv", "g_d0")])
def test_explicit_direct_projection_can_select_a_varying_generated_oracle(kind, column):
    data = _convert(_direct(kind), kind, confounders=column)
    assert data.confounders_names == [column]
    assert np.ptp(data.X[column].to_numpy()) > 0


@pytest.mark.parametrize("include_oracle", [False, True])
@pytest.mark.parametrize("path", ["direct", "wrapper"])
def test_multi_conversion_keeps_literal_numeric_features_as_regression_control(include_oracle, path):
    options = dict(confounder_specs=_specs("user_id", "g0"), include_oracle=include_oracle, beta_y=[0.4, -0.2])
    if path == "direct":
        data = MultiCausalDatasetGenerator(k=0, seed=SEED, **options).to_multicausal_data(N)
    else:
        data = generate_multitreatment(n=N, random_state=SEED, return_causal_data=True, **options)
    assert data.confounders == ["user_id", "g0"]
    assert data.user_id is None


@pytest.mark.parametrize("add_pre", [False, True])
@pytest.mark.parametrize("add_ancillary", [False, True])
def test_disabled_oracle_named_rct_feature_participates_in_pre_and_ancillary_signal(add_pre, add_ancillary):
    options = dict(
        include_oracle=False, add_pre=add_pre, add_ancillary=add_ancillary,
        deterministic_ids=True, beta_y=[0.4],
    )
    expected = _rct(confounder_specs=_specs("feature"), **options)
    actual = _rct(confounder_specs=_specs("m"), **options).rename(columns={"m": "feature"})
    pd.testing.assert_frame_equal(actual, expected)


@pytest.mark.parametrize("path", ["iv", "observational"])
def test_disabled_oracle_named_feature_participates_in_other_ancillary_paths(path):
    options = dict(include_oracle=False, add_ancillary=True, deterministic_ids=True, beta_y=[0.4])
    if path == "iv":
        wrapper = _iv
    else:
        wrapper = lambda **kwargs: obs_linear_effect(n=N, random_state=SEED, **kwargs)
    expected = wrapper(confounder_specs=_specs("feature"), **options)
    actual = wrapper(confounder_specs=_specs("m"), **options).rename(columns={"m": "feature"})
    pd.testing.assert_frame_equal(actual, expected)


@pytest.mark.parametrize("augmentation", ["pre", "ancillary"])
def test_valid_shared_augmentation_preserves_values_and_rng_when_feature_is_renamed(augmentation):
    expected, actual = _input_frame(), _input_frame().rename(columns={"feature": "m"})
    expected_rng, actual_rng = np.random.default_rng(SEED), np.random.default_rng(SEED)
    if augmentation == "pre":
        _add_pre(expected, "baseline", expected_rng)
        _add_pre(actual, "baseline", actual_rng, lambda data: 0.3 * data["m"].to_numpy())
    else:
        _add_ancillary_info(expected, N, expected_rng, True, ["feature"])
        _add_ancillary_info(actual, N, actual_rng, True, ["m"])
        assert set(ANCILLARY).issubset(actual.columns)
        assert actual["user_id"].is_unique
    pd.testing.assert_frame_equal(actual.rename(columns={"m": "feature"}), expected)
    np.testing.assert_array_equal(actual_rng.random(10), expected_rng.random(10))


@pytest.mark.parametrize("helper", [generate_cuped_binary, make_cuped_tweedie])
@pytest.mark.parametrize("pre_name", ["user_id", "g0"])
def test_cuped_helpers_retain_actual_pre_features_with_inactive_reserved_names(helper, pre_name):
    data = helper(n=384, seed=SEED, include_oracle=False, pre_name=pre_name)
    assert pre_name in data.confounders_names
    assert data.user_id_name is None
    assert np.ptp(data.X[pre_name].to_numpy()) > 0
    expected = helper(n=384, seed=SEED, include_oracle=False)
    pd.testing.assert_frame_equal(data.df.rename(columns={pre_name: "y_pre"}), expected.df)


@pytest.mark.parametrize("helper", [generate_cuped_binary, make_cuped_tweedie])
def test_cuped_helpers_cannot_replace_enabled_oracles(helper):
    _collision(lambda: helper(n=384, seed=SEED, include_oracle=True, pre_name="g0"), "g0")


@pytest.mark.parametrize("helper", [generate_cuped_binary, make_cuped_tweedie])
@pytest.mark.parametrize("pre_name", ["y", "d", "tenure_months"])
def test_cuped_helpers_cannot_replace_actual_core_or_sampled_columns(helper, pre_name):
    _collision(lambda: helper(n=384, seed=SEED, include_oracle=False, pre_name=pre_name), pre_name)


@pytest.mark.parametrize("helper", [generate_cuped_binary, make_cuped_tweedie])
@pytest.mark.parametrize("pre_name", [None, "", []])
def test_cuped_helpers_require_nonempty_string_names_when_pre_is_enabled(helper, pre_name):
    with pytest.raises(ValueError, match="(?i)nonempty string"):
        helper(n=384, seed=SEED, include_oracle=False, pre_name=pre_name, return_causal_data=False)


@pytest.mark.parametrize("helper", [generate_cuped_binary, make_cuped_tweedie])
@pytest.mark.parametrize("include_oracle", [False, True])
def test_cuped_helpers_ignore_unused_pre_name(helper, include_oracle):
    options = dict(n=384, seed=SEED, add_pre=False, include_oracle=include_oracle)
    expected = helper(**options)
    actual = helper(pre_name="y", **options)
    pd.testing.assert_frame_equal(actual.df, expected.df)
    assert actual.confounders_names == expected.confounders_names


def test_tweedie_pre_cannot_replace_a_prospective_latent_oracle():
    _collision(
        lambda: make_cuped_tweedie(n=384, seed=SEED, include_oracle=True, pre_name="_latent_A"),
        "_latent_A",
    )


def test_tweedie_disabled_latent_oracle_name_remains_available_for_actual_pre():
    data = make_cuped_tweedie(n=384, seed=SEED, include_oracle=False, pre_name="_latent_A")
    assert "_latent_A" in data.confounders_names
    expected = make_cuped_tweedie(n=384, seed=SEED, include_oracle=False)
    pd.testing.assert_frame_equal(data.df.rename(columns={"_latent_A": "y_pre"}), expected.df)


@pytest.mark.parametrize("kind", ["binary", "iv"])
def test_ancillary_conversion_marks_only_the_identifier_actually_added(kind):
    options = dict(add_ancillary=True, deterministic_ids=True, return_causal_data=True, include_oracle=False)
    data = _rct(**options) if kind == "binary" else _iv(**options)
    assert data.user_id_name == "user_id"
    assert "user_id" not in data.confounders_names
    assert set(ANCILLARY) - {"user_id"} <= set(data.confounders_names)
    assert data.df["user_id"].is_unique
