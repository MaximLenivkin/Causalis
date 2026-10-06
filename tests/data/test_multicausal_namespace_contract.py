"""Public schema guarantees for the multi-treatment data generators."""

import re

import numpy as np
import pandas as pd
import pytest

from causalis.dgp.multicausaldata.base import MultiCausalDatasetGenerator as Generator
from causalis.dgp.multicausaldata.functional import generate_multitreatment

N = 30
SEED = 1
ORACLE_PREFIXES = ("m", "m_obs", "tau_link", "g")


def _generate(**kwargs):
    return Generator(n_treatments=2, k=0, seed=SEED, **kwargs).generate(N)


def _assert_collision(column, **kwargs):
    # Identifying the actual column makes a rejected custom schema actionable.
    with pytest.raises(ValueError, match=re.escape(column)):
        _generate(**kwargs)


@pytest.mark.parametrize("include_oracle", [False, True])
@pytest.mark.parametrize(
    "kwargs,column",
    [
        ({"d_names": ["y", "arm"]}, "y"),
        ({"d_names": ["arm", "arm"]}, "arm"),
        ({"confounder_specs": [{"name": "y", "dist": "normal"}]}, "y"),
        ({"confounder_specs": [{"name": "d_0", "dist": "normal"}]}, "d_0"),
        (
            {"confounder_specs": [{"name": "age"}, {"name": "age"}]},
            "age",
        ),
    ],
)
def test_outcome_treatment_and_confounder_collisions_raise(
    kwargs, column, include_oracle
):
    _assert_collision(column, include_oracle=include_oracle, **kwargs)


@pytest.mark.parametrize("prefix", ORACLE_PREFIXES)
@pytest.mark.parametrize("arm", ["control", "active"])
def test_confounders_cannot_overwrite_enabled_oracle_columns(prefix, arm):
    column = f"{prefix}_{arm}"
    _assert_collision(
        column,
        d_names=["control", "active"],
        confounder_specs=[{"name": column, "dist": "normal"}],
    )


def test_confounder_cannot_overwrite_noncontrol_contrast():
    _assert_collision(
        "cate_active",
        d_names=["control", "active"],
        confounder_specs=[{"name": "cate_active", "dist": "normal"}],
    )


@pytest.mark.parametrize("prefix", ORACLE_PREFIXES)
def test_treatment_names_cannot_overwrite_another_arms_oracle(prefix):
    column = f"{prefix}_control"
    _assert_collision(column, d_names=["control", column])


def test_control_treatment_name_cannot_overwrite_noncontrol_contrast():
    _assert_collision("cate_active", d_names=["cate_active", "active"])


def test_distinct_arms_cannot_generate_the_same_oracle_column():
    # m_<obs_control> and m_obs_<control> both become m_obs_control.
    _assert_collision("m_obs_control", d_names=["control", "obs_control"])


@pytest.mark.parametrize("include_oracle", [False, True])
@pytest.mark.parametrize("use_copula", [False, True])
@pytest.mark.parametrize(
    "specs,d_names,column",
    [
        (
            [{"name": "platform", "dist": "categorical", "categories": ["A", "B"]}],
            ["control", "platform_B"],
            "platform_B",
        ),
        (
            [{"name": "tier", "dist": "categorical", "categories": ["A"]}],
            ["control", "tier__onlylevel"],
            "tier__onlylevel",
        ),
        (
            [
                {"name": "tier", "dist": "categorical", "categories": ["A", "B"]},
                {"name": "tier_B", "dist": "normal"},
            ],
            ["control", "active"],
            "tier_B",
        ),
        (
            [{"name": "tier", "dist": "categorical", "categories": [0, 1, 1]}],
            ["control", "active"],
            "tier_1",
        ),
        (
            [{"name": "tier", "dist": "categorical", "categories": [0, 1, "1"]}],
            ["control", "active"],
            "tier_1",
        ),
        (
            [
                {"name": "tier", "dist": "categorical", "categories": ["A"]},
                {
                    "name": "tier_",
                    "dist": "categorical",
                    "categories": ["A", "onlylevel"],
                },
            ],
            ["control", "active"],
            "tier__onlylevel",
        ),
    ],
)
def test_expanded_categorical_namespace_has_no_collisions(
    specs, d_names, column, include_oracle, use_copula
):
    # A continuous first coordinate also keeps this check independent of the
    # separate existing first-coordinate categorical copula sampling defect.
    _assert_collision(
        column,
        confounder_specs=[{"name": "continuous", "dist": "normal"}] + specs,
        d_names=d_names,
        use_copula=use_copula,
        include_oracle=include_oracle,
    )


@pytest.mark.parametrize("use_copula", [False, True])
@pytest.mark.parametrize("prefix", ORACLE_PREFIXES + ("cate",))
def test_categorical_expansion_cannot_overwrite_enabled_oracle(prefix, use_copula):
    column = f"{prefix}_active"
    _assert_collision(
        column,
        d_names=["control", "active"],
        confounder_specs=[
            {"name": "continuous", "dist": "normal"},
            {"name": prefix, "dist": "categorical", "categories": ["base", "active"]},
        ],
        use_copula=use_copula,
    )


@pytest.mark.parametrize(
    "column",
    ["m_control", "m_obs_control", "tau_link_control", "g_control", "cate_active"],
)
def test_disabled_oracle_names_remain_available_for_actual_confounders(column):
    x = np.linspace(-2.0, 2.0, N).reshape(N, 1)
    generator = Generator(
        n_treatments=2,
        d_names=["control", "active"],
        confounder_specs=[{"name": column}],
        x_sampler=lambda n, k, seed: x.copy(),
        include_oracle=False,
        seed=SEED,
    )
    frame = generator.generate(N)
    assert list(frame.columns) == ["y", "control", "active", column]
    assert generator.confounder_names_ == [column]
    np.testing.assert_array_equal(frame[column], x[:, 0])


@pytest.mark.parametrize(
    "d_names",
    [["control", "m_control"], ["cate_active", "active"], ["control", "obs_control"]],
)
def test_disabled_oracles_do_not_reserve_names_for_treatments(d_names):
    frame = _generate(d_names=d_names, include_oracle=False)
    assert list(frame.columns) == ["y"] + d_names
    np.testing.assert_array_equal(frame[d_names].sum(axis=1), np.ones(N))


def test_control_contrast_name_is_available_because_no_control_contrast_is_emitted():
    frame = _generate(
        d_names=["control", "active"],
        confounder_specs=[{"name": "cate_control", "dist": "normal"}],
    )
    expected = np.random.default_rng(SEED).normal(size=(N, 1))[:, 0]
    np.testing.assert_array_equal(frame["cate_control"], expected)
    assert "cate_active" in frame.columns


def test_custom_sampler_uses_actual_names_without_categorical_expansion():
    x = np.linspace(-2.0, 2.0, N).reshape(N, 1)
    frame = _generate(
        d_names=["control", "platform_B"],
        confounder_specs=[
            {"name": "platform", "dist": "categorical", "categories": ["A", "B"]}
        ],
        x_sampler=lambda n, k, seed: x.copy(),
    )
    np.testing.assert_array_equal(frame["platform"], x[:, 0])
    assert frame[["control", "platform_B"]].sum(axis=1).eq(1).all()
    assert "platform_A" not in frame.columns


@pytest.mark.parametrize("return_causal_data", [False, True])
@pytest.mark.parametrize(
    "kwargs,column",
    [
        ({"d_names": ["y", "arm"]}, "y"),
        ({"confounder_specs": [{"name": "d_0"}]}, "d_0"),
        ({"confounder_specs": [{"name": "g_d_0"}]}, "g_d_0"),
        (
            {
                "d_names": ["control", "tier_B"],
                "confounder_specs": [
                    {"name": "tier", "dist": "categorical", "categories": ["A", "B"]}
                ],
            },
            "tier_B",
        ),
    ],
)
def test_functional_wrapper_rejects_collisions_in_both_return_modes(
    kwargs, column, return_causal_data
):
    with pytest.raises(ValueError, match=re.escape(column)):
        generate_multitreatment(
            n=N,
            n_treatments=2,
            random_state=SEED,
            return_causal_data=return_causal_data,
            **kwargs,
        )


@pytest.mark.parametrize("method", ["generate", "to_multicausal_data"])
def test_reusing_generator_revalidates_mutated_arm_names(method):
    generator = Generator(n_treatments=2, k=0, seed=SEED)
    generator.generate(N)
    generator.d_names[:] = ["y", "arm"]
    with pytest.raises(ValueError, match="y"):
        getattr(generator, method)(N)


def test_enabling_oracles_on_existing_generator_revalidates_namespace():
    generator = Generator(
        n_treatments=2,
        seed=SEED,
        include_oracle=False,
        confounder_specs=[{"name": "g_d_0", "dist": "normal"}],
    )
    generator.generate(N)
    generator.include_oracle = True
    with pytest.raises(ValueError, match="g_d_0"):
        generator.generate(N)


@pytest.mark.parametrize("include_oracle", [False, True])
@pytest.mark.parametrize(
    "d_names", [[None, "arm"], [1, "arm"], ["", "arm"], [[], "arm"], "ab"]
)
def test_treatment_columns_require_nonempty_string_names(d_names, include_oracle):
    with pytest.raises(ValueError, match="d_names|treatment|column name"):
        _generate(d_names=d_names, include_oracle=include_oracle)


@pytest.mark.parametrize("include_oracle", [False, True])
@pytest.mark.parametrize("name", [None, "", 1, []])
def test_custom_sampler_actual_confounder_names_must_be_nonempty_strings(
    name, include_oracle
):
    with pytest.raises(ValueError, match="confounder|column name"):
        _generate(
            confounder_specs=[{"name": name}],
            x_sampler=lambda n, k, seed: np.linspace(-1.0, 1.0, n).reshape(n, k),
            include_oracle=include_oracle,
        )


@pytest.mark.parametrize(
    "d_names", [("control", "active"), np.array(["control", "active"]), [" ", "active"]]
)
def test_ordered_string_names_are_preserved_without_coercion_or_trimming(d_names):
    frame = _generate(d_names=d_names, include_oracle=False)
    assert list(frame.columns) == ["y"] + list(d_names)
    assert frame[list(d_names)].sum(axis=1).eq(1).all()


def test_mutating_treatment_count_names_raises_clear_contract_error():
    generator = Generator(n_treatments=2, k=0, seed=SEED)
    generator.generate(N)
    generator.d_names.append("extra")
    with pytest.raises(ValueError, match="d_names"):
        generator.generate(N)


@pytest.mark.parametrize("callback", ["g_y", "g_d", "tau"])
def test_invalid_namespace_is_rejected_before_structural_callbacks(callback):
    def should_not_run(x):
        raise AssertionError("a structural callback ran for an invalid schema")

    _assert_collision(
        "g_d_0", confounder_specs=[{"name": "g_d_0"}], **{callback: should_not_run}
    )


@pytest.mark.parametrize("include_oracle", [False, True])
@pytest.mark.parametrize("assignment_policy", ["ensure_all", "iid"])
@pytest.mark.parametrize("sampler", ["normal", "categorical", "copula", "custom"])
def test_valid_user_names_preserve_values_column_order_and_rng(
    include_oracle, assignment_policy, sampler
):
    kwargs = dict(
        n_treatments=2,
        seed=SEED,
        include_oracle=include_oracle,
        assignment_policy=assignment_policy,
        beta_y=[0.3, -0.2],
        beta_d=np.array([[0.0, 0.0], [0.2, -0.1]]),
    )
    if sampler == "normal":
        kwargs["k"] = 2
        old_x_names = ["x1", "x2"]
        new_x_names = old_x_names
    elif sampler == "custom":
        kwargs["confounder_specs"] = [{"name": "age"}, {"name": "income"}]
        kwargs["x_sampler"] = lambda n, k, seed: np.column_stack(
            (np.arange(n), np.linspace(-1.0, 1.0, n))
        )
        old_x_names = ["age", "income"]
        new_x_names = ["m_future", "g_future"]
    else:
        kwargs["confounder_specs"] = [
            {"name": "age", "dist": "normal"},
            {"name": "tier", "dist": "categorical", "categories": ["A", "B"]},
        ]
        kwargs["use_copula"] = sampler == "copula"
        old_x_names = ["age", "tier_B"]
        new_x_names = ["m_future", "g_future_B"]

    reference = Generator(**kwargs)
    expected = reference.generate(N)
    reference_next = reference.rng.random(10)
    if "confounder_specs" in kwargs:
        kwargs["confounder_specs"] = [dict(spec) for spec in kwargs["confounder_specs"]]
        for spec, new_name in zip(kwargs["confounder_specs"], new_x_names):
            spec["name"] = (
                new_name[:-2] if spec.get("dist") == "categorical" else new_name
            )

    arms = ["baseline arm", "β"]
    generator = Generator(d_names=arms, **kwargs)
    actual = generator.generate(N)
    rename = dict(zip(["d_0", "d_1"] + old_x_names, arms + new_x_names))
    if include_oracle:
        for old_arm, new_arm in zip(["d_0", "d_1"], arms):
            for prefix in ORACLE_PREFIXES:
                rename[f"{prefix}_{old_arm}"] = f"{prefix}_{new_arm}"
        rename["cate_d_1"] = "cate_β"
    pd.testing.assert_frame_equal(actual, expected.rename(columns=rename))
    np.testing.assert_array_equal(generator.rng.random(10), reference_next)
    assert generator.confounder_names_ == new_x_names


@pytest.mark.parametrize("return_causal_data", [False, True])
def test_valid_functional_wrapper_preserves_requested_names(return_causal_data):
    result = generate_multitreatment(
        n=N,
        n_treatments=2,
        d_names=["control", "active"],
        confounder_specs=[{"name": "baseline"}],
        random_state=SEED,
        return_causal_data=return_causal_data,
    )
    frame = result.df if return_causal_data else result
    expected_columns = (
        ["y", "baseline", "control", "active"]
        if return_causal_data
        else ["y", "control", "active", "baseline"]
    )
    assert list(frame.columns[:4]) == expected_columns
    assert frame[["control", "active"]].sum(axis=1).eq(1).all()
    if return_causal_data:
        assert result.treatment_names == ["control", "active"]
        assert result.confounders == ["baseline"]
