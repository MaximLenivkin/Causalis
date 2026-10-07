"""Public generated-column contracts for binary-treatment and IV generators."""

import re

import numpy as np
import pandas as pd
import pytest

from causalis.dgp.causaldata.base import CausalDatasetGenerator
from causalis.dgp.causaldata.functional import generate_rct
from causalis.dgp.causaldata_instrumental.base import InstrumentalGenerator
from causalis.dgp.causaldata_instrumental.functional import generate_iv_data

N = 64
SEED = 731
BINARY_ORACLES = ("m", "m_obs", "tau_link", "g0", "g1", "cate")
IV_ORACLES = (
    "m",
    "r_obs",
    "r_z0",
    "r_z1",
    "g_z0",
    "g_z1",
    "iv_first_stage",
    "iv_reduced_form",
    "late_x",
    "late",
    "tau_link",
    "g_d0",
    "g_d1",
    "cate",
)
ORACLE_CASES = [("binary", name) for name in BINARY_ORACLES] + [
    ("iv", name) for name in IV_ORACLES
]


def _generator(kind, **kwargs):
    options = dict(k=0, seed=SEED)
    options.update(kwargs)
    cls = CausalDatasetGenerator if kind == "binary" else InstrumentalGenerator
    return cls(**options)


def _collision(operation, column, roles):
    with pytest.raises(ValueError) as caught:
        operation()
    message = str(caught.value)
    assert repr(column) in message
    assert re.search("collid|collision|overlap", message, flags=re.IGNORECASE)
    for role in roles:
        assert role in message.lower()


@pytest.mark.parametrize("kind", ["binary", "iv"])
@pytest.mark.parametrize("include_oracle", [False, True])
@pytest.mark.parametrize("column,role", [("y", "outcome"), ("d", "treatment")])
def test_confounders_cannot_replace_fixed_outcome_or_treatment(
    kind, include_oracle, column, role
):
    _collision(
        lambda: _generator(
            kind,
            include_oracle=include_oracle,
            confounder_specs=[{"name": column, "dist": "normal"}],
        ).generate(N),
        column,
        ("confounder", role),
    )


def test_confounder_cannot_replace_instrument():
    _collision(
        lambda: _generator("iv", confounder_specs=[{"name": "z"}]).generate(N),
        "z",
        ("confounder", "instrument"),
    )


@pytest.mark.parametrize("kind,column", ORACLE_CASES)
def test_confounders_cannot_replace_any_enabled_family_oracle(kind, column):
    _collision(
        lambda: _generator(kind, confounder_specs=[{"name": column}]).generate(N),
        column,
        ("confounder", "oracle"),
    )


@pytest.mark.parametrize("column", IV_ORACLES)
def test_instrument_cannot_share_an_enabled_oracle_name(column):
    _collision(
        lambda: _generator("iv", instrument_name=column).generate(N),
        column,
        ("instrument", "oracle"),
    )


@pytest.mark.parametrize("kind,column", ORACLE_CASES)
def test_disabled_oracle_names_remain_available_and_preserve_covariate_values(
    kind, column
):
    covariate = np.linspace(-2.0, 2.0, N).reshape(N, 1)
    frame = _generator(
        kind,
        include_oracle=False,
        confounder_specs=[{"name": column}],
        x_sampler=lambda n, k, seed: covariate.copy(),
    ).generate(N)
    expected_columns = ["y", "d"] + (["z"] if kind == "iv" else []) + [column]
    assert list(frame.columns) == expected_columns
    np.testing.assert_array_equal(frame[column], covariate[:, 0])
    assert frame["d"].isin([0.0, 1.0]).all()


@pytest.mark.parametrize(
    "kind,column", [("binary", "z"), ("binary", "r_z0"), ("iv", "g0"), ("iv", "m_obs")]
)
def test_names_not_emitted_by_the_current_family_are_not_reserved(kind, column):
    frame = _generator(kind, confounder_specs=[{"name": column}]).generate(N)
    expected = np.random.default_rng(SEED).normal(size=(N, 1))[:, 0]
    np.testing.assert_array_equal(frame[column], expected)


def test_disabled_oracles_allow_instrument_name_that_looks_like_an_oracle():
    generator = _generator("iv", instrument_name="m", include_oracle=False)
    frame = generator.generate(N)
    assert list(frame.columns) == ["y", "d", "m"]
    assert frame["m"].isin([0.0, 1.0]).all()


@pytest.mark.parametrize(
    "kind,spec,column",
    [
        ("binary", {"name": "m", "categories": ["base", "obs"]}, "m_obs"),
        ("binary", {"name": "tau", "categories": ["base", "link"]}, "tau_link"),
        ("iv", {"name": "r", "categories": ["base", "z0"]}, "r_z0"),
        ("iv", {"name": "iv", "categories": ["base", "first_stage"]}, "iv_first_stage"),
    ],
)
def test_categorical_expansion_cannot_replace_enabled_oracles(kind, spec, column):
    spec = dict(spec, dist="categorical")
    _collision(
        lambda: _generator(kind, confounder_specs=[spec], use_copula=True).generate(N),
        column,
        ("confounder", "oracle"),
    )


@pytest.mark.parametrize("use_copula", [False, True])
@pytest.mark.parametrize("kind", ["binary", "iv"])
def test_expanded_and_ordinary_confounders_must_have_distinct_names(kind, use_copula):
    specs = [
        {"name": "tier", "dist": "categorical", "categories": ["base", "B"]},
        {"name": "tier_B", "dist": "normal"},
    ]
    _collision(
        lambda: _generator(
            kind, confounder_specs=specs, use_copula=use_copula
        ).generate(N),
        "tier_B",
        ("confounder",),
    )


@pytest.mark.parametrize("kind", ["binary", "iv"])
def test_stringified_category_labels_cannot_produce_duplicate_columns(kind):
    specs = [{"name": "tier", "dist": "categorical", "categories": [0, 1, "1"]}]
    _collision(
        lambda: _generator(kind, confounder_specs=specs).generate(N),
        "tier_1",
        ("confounder",),
    )


@pytest.mark.parametrize(
    "spec,column",
    [
        ({"name": "offer", "categories": ["base", "B"]}, "offer_B"),
        ({"name": "tier", "categories": ["sole"]}, "tier__onlylevel"),
    ],
)
def test_expanded_confounder_cannot_replace_a_custom_instrument(spec, column):
    _collision(
        lambda: _generator(
            "iv",
            instrument_name=column,
            confounder_specs=[dict(spec, dist="categorical")],
        ).generate(N),
        column,
        ("confounder", "instrument"),
    )


@pytest.mark.parametrize("kind", ["binary", "iv"])
@pytest.mark.parametrize("name", [None, "", 1, [1]])
def test_actual_custom_sampler_names_must_be_nonempty_strings(kind, name):
    with pytest.raises(ValueError, match="confounder|column name"):
        _generator(
            kind,
            confounder_specs=[{"name": name}],
            x_sampler=lambda n, k, seed: np.linspace(-1.0, 1.0, n).reshape(n, k),
        ).generate(N)


@pytest.mark.parametrize("kind", ["binary", "iv"])
@pytest.mark.parametrize("name", [1, [1]])
def test_actual_ordinary_sampler_names_must_be_strings(kind, name):
    with pytest.raises(ValueError, match="confounder|column name"):
        _generator(kind, confounder_specs=[{"name": name, "dist": "normal"}]).generate(
            N
        )


@pytest.mark.parametrize("name", [None, "", 1, []])
def test_invalid_instrument_types_raise_a_value_error(name):
    with pytest.raises(ValueError, match="instrument|column name"):
        _generator("iv", instrument_name=name).generate(N)


@pytest.mark.parametrize("name", [None, "", 1, []])
def test_mutating_instrument_to_an_invalid_type_is_revalidated_before_sampling(name):
    calls = []
    generator = _generator(
        "iv", x_sampler=lambda n, k, seed: calls.append("sampled") or np.empty((n, k))
    )
    generator.instrument_name = name
    with pytest.raises(ValueError, match="instrument|column name"):
        generator.generate(N)
    assert calls == []


@pytest.mark.parametrize("kind", ["binary", "iv"])
@pytest.mark.parametrize("width", [0, 2])
def test_actual_name_count_must_match_custom_covariate_width(kind, width):
    with pytest.raises(ValueError, match="confounder|column|name"):
        _generator(
            kind,
            confounder_specs=[{"name": "age"}],
            x_sampler=lambda n, k, seed: np.zeros((n, width)),
        ).generate(N)


@pytest.mark.parametrize("kind", ["binary", "iv"])
def test_positive_custom_covariate_width_cannot_be_hidden_by_empty_name_list(kind):
    with pytest.raises(ValueError, match="confounder|column|name"):
        _generator(kind, x_sampler=lambda n, k, seed: np.zeros((n, 2))).generate(N)


@pytest.mark.parametrize(
    "kind,n,container,include_oracle",
    [
        ("binary", n, container, include_oracle)
        for n, container in [(30, "rows"), (0, "rows"), (0, "flat"), (30, "flat")]
        for include_oracle in [False, True]
    ]
    + [("iv", n, "rows", False) for n in [0, 30]]
    + [
        ("iv", n, "flat", include_oracle)
        for n in [0, 30]
        for include_oracle in [False, True]
    ],
)
def test_legacy_zero_confounder_custom_containers_remain_valid(
    kind, n, container, include_oracle
):
    def sampler(n, k, seed):
        return (
            [[] for _ in range(n)] if container == "rows" else np.arange(n, dtype=float)
        )

    options = {"x_sampler": sampler, "include_oracle": include_oracle}
    if kind == "iv":
        options["target_z_rate"] = None
    frame = _generator(kind, **options).generate(n)
    expected_names = ["y", "d"] + (["z"] if kind == "iv" else [])
    if include_oracle:
        expected_names += list(BINARY_ORACLES if kind == "binary" else IV_ORACLES)
    assert list(frame.columns) == expected_names
    assert len(frame) == n


@pytest.mark.parametrize("kind", ["binary", "iv"])
@pytest.mark.parametrize("name", [None, "", []])
def test_existing_ordinary_default_name_fallbacks_are_preserved(kind, name):
    frame = _generator(kind, confounder_specs=[{"name": name}]).generate(N)
    assert "x1" in frame.columns


@pytest.mark.parametrize("kind", ["binary", "iv"])
@pytest.mark.parametrize("name", [" ", np.str_("feature")])
def test_literal_valid_string_names_are_preserved_without_trimming(kind, name):
    frame = _generator(kind, confounder_specs=[{"name": name}]).generate(N)
    assert name in frame.columns
    assert frame.columns.is_unique


@pytest.mark.parametrize("kind", ["binary", "iv"])
def test_actual_stringified_categorical_names_remain_valid(kind):
    frame = _generator(
        kind,
        confounder_specs=[{"name": 1, "dist": "categorical", "categories": ["A", "B"]}],
    ).generate(N)
    assert "1_B" in frame.columns
    assert "1_A" not in frame.columns


def test_custom_sampler_actual_names_are_not_replaced_by_hypothetical_category_expansion():
    covariate = np.linspace(-1.0, 1.0, N).reshape(N, 1)
    frame = _generator(
        "iv",
        instrument_name="tier_B",
        confounder_specs=[
            {"name": "tier", "dist": "categorical", "categories": ["A", "B"]}
        ],
        x_sampler=lambda n, k, seed: covariate.copy(),
    ).generate(N)
    np.testing.assert_array_equal(frame["tier"], covariate[:, 0])
    assert frame["tier_B"].isin([0.0, 1.0]).all()


@pytest.mark.parametrize("kind", ["binary", "iv"])
def test_enabling_oracles_on_a_reused_generator_revalidates_names(kind):
    generator = _generator(kind, include_oracle=False, confounder_specs=[{"name": "m"}])
    generator.generate(N)
    generator.include_oracle = True
    _collision(lambda: generator.generate(N), "m", ("confounder", "oracle"))


@pytest.mark.parametrize("kind", ["binary", "iv"])
def test_reusing_generator_revalidates_changed_confounder_specs(kind):
    generator = _generator(kind, confounder_specs=[{"name": "age"}])
    generator.generate(N)
    generator.confounder_specs[0]["name"] = "d"
    _collision(lambda: generator.generate(N), "d", ("confounder", "treatment"))


def test_mutating_instrument_to_core_column_is_rejected_on_reuse():
    generator = _generator("iv")
    generator.generate(N)
    generator.instrument_name = "y"
    _collision(lambda: generator.generate(N), "y", ("outcome", "instrument"))


def test_enabling_oracles_rejects_instrument_collision_before_custom_sampler_runs():
    calls = []
    generator = _generator(
        "iv",
        include_oracle=False,
        instrument_name="m",
        x_sampler=lambda n, k, seed: calls.append("sampled") or np.empty((n, k)),
    )
    generator.include_oracle = True
    _collision(lambda: generator.generate(N), "m", ("instrument", "oracle"))
    assert calls == []


@pytest.mark.parametrize(
    "kind,callback",
    [
        (kind, callback)
        for kind in ["binary", "iv"]
        for callback in ["g_y", "g_d", "tau"]
    ]
    + [("iv", "g_z")],
)
def test_invalid_actual_namespace_is_rejected_before_structural_callbacks(
    kind, callback
):
    calls = []

    def should_not_run(x):
        calls.append(callback)
        raise AssertionError("callback ran for an invalid generated schema")

    _collision(
        lambda: _generator(
            kind, confounder_specs=[{"name": "d"}], **{callback: should_not_run}
        ).generate(N),
        "d",
        ("confounder", "treatment"),
    )
    assert calls == []


@pytest.mark.parametrize("kind", ["binary", "iv"])
def test_rejection_after_custom_sampling_precedes_latent_and_assignment_rng_draws(kind):
    generator = _generator(
        kind,
        confounder_specs=[{"name": "d"}],
        x_sampler=lambda n, k, seed: np.arange(n, dtype=float).reshape(n, k),
    )
    _collision(lambda: generator.generate(N), "d", ("confounder", "treatment"))
    np.testing.assert_array_equal(
        generator.rng.random(10), np.random.default_rng(SEED).random(10)
    )


@pytest.mark.parametrize("kind,callback", [("binary", "g_y"), ("iv", "g_z")])
def test_callback_enabling_oracles_cannot_silently_overwrite_confounders(
    kind, callback
):
    generator = None

    def enable_oracles(x):
        generator.include_oracle = True
        return np.zeros(len(x))

    generator = _generator(
        kind,
        include_oracle=False,
        confounder_specs=[{"name": "m"}],
        **{callback: enable_oracles},
    )
    _collision(lambda: generator.generate(N), "m", ("confounder", "oracle"))


def test_callback_mutating_instrument_cannot_silently_overwrite_outcome():
    generator = None

    def change_instrument(x):
        generator.instrument_name = "y"
        return np.zeros(len(x))

    generator = _generator("iv", g_z=change_instrument)
    _collision(lambda: generator.generate(N), "y", ("instrument", "outcome"))


@pytest.mark.parametrize("kind", ["binary", "iv"])
@pytest.mark.parametrize("include_oracle", [False, True])
def test_valid_schema_renaming_preserves_values_column_order_and_next_rng(
    kind, include_oracle
):
    options = dict(
        include_oracle=include_oracle,
        confounder_specs=[{"name": "age"}, {"name": "income"}],
        beta_y=np.array([0.3, -0.2]),
        beta_d=np.array([0.1, -0.1]),
    )
    original = _generator(kind, **options)
    expected = original.generate(N)
    next_rng = original.rng.random(10)
    options["confounder_specs"] = [{"name": "Доход"}, {"name": "baseline value"}]
    actual_generator = _generator(kind, **options)
    actual = actual_generator.generate(N)
    pd.testing.assert_frame_equal(
        actual, expected.rename(columns={"age": "Доход", "income": "baseline value"})
    )
    np.testing.assert_array_equal(actual_generator.rng.random(10), next_rng)


@pytest.mark.parametrize("return_causal_data", [False, True])
@pytest.mark.parametrize("column", ["d", "g0"])
def test_rct_wrapper_inherits_core_guard_before_optional_augmentation(
    column, return_causal_data
):
    _collision(
        lambda: generate_rct(
            n=N,
            random_state=SEED,
            outcome_type="normal",
            confounder_specs=[{"name": column}],
            add_ancillary=False,
            add_pre=False,
            return_causal_data=return_causal_data,
        ),
        column,
        ("confounder", "treatment" if column == "d" else "oracle"),
    )


@pytest.mark.parametrize("return_causal_data", [False, True])
@pytest.mark.parametrize("column", ["d", "g_z0"])
def test_iv_wrapper_inherits_core_guard_in_both_return_modes(
    column, return_causal_data
):
    _collision(
        lambda: generate_iv_data(
            n=N,
            random_state=SEED,
            confounder_specs=[{"name": column}],
            add_ancillary=False,
            return_causal_data=return_causal_data,
        ),
        column,
        ("confounder", "treatment" if column == "d" else "oracle"),
    )
