"""Known-cost net value and whole-leaf empirical capacity contracts."""
from itertools import product

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm
from sklearn.base import clone

from causalis.scenarios.uplift import UpliftPolicyTree
from causalis.scenarios.uplift.policy import _capacity_actions
from tests.scenarios.uplift.test_policy_tree import make_irm, manual_signal


def exact_irm(prefix="train", *, effects=(-3., 4., -7., 6.), costs=None, scale=1.):
    irm = make_irm(prefix)
    if scale != 1:
        irm.data.df.y *= scale
        irm.fit()
    if costs is not None:
        irm.data.df.z = np.repeat(costs, 30)
        irm.fit()
    phi = np.repeat(effects, 30) * scale
    y, d = irm.data.outcome.to_numpy(), irm.data.treatment.to_numpy()
    irm.g0_hat_ = y - d * phi
    irm.g1_hat_ = y + (1 - d) * phi
    return irm


def policy(irm, **kwargs):
    return UpliftPolicyTree(max_depth=3, min_samples_leaf=20,
                           min_samples_per_arm=5, **kwargs).fit(irm, policy_features=["x"])


@pytest.mark.parametrize("seed", range(24))
def test_capacity_optimizer_matches_exhaustive_binary_choices(seed):
    rng = np.random.default_rng(seed)
    counts = rng.integers(1, 10, 7)
    rewards = rng.integers(-6, 30, 7).astype(float)
    capacity = int(rng.integers(0, counts.sum() + 1))
    choices = [np.array(a) for a in product((0, 1), repeat=7)
               if np.dot(a, counts) <= capacity]
    best_value = max(np.dot(a, rewards) for a in choices)
    min_count = min(np.dot(a, counts) for a in choices if np.dot(a, rewards) == best_value)
    actual = _capacity_actions(counts, rewards, capacity)
    assert np.dot(actual, rewards) == best_value
    assert np.dot(actual, counts) == min_count
    assert not actual[rewards <= 0].any()


@pytest.mark.parametrize("fraction,expected", [(0, 0), (.25, 30), (.5, 60), (1, 60)])
def test_training_capacity_selects_whole_profitable_leaves(fraction, expected):
    irm = exact_irm()
    fitted = policy(irm, max_treatment_fraction=fraction)
    assignments = fitted.assign(irm.data.df, user_id="client_id")
    rules = fitted.rules()
    assert assignments.action.sum() == expected
    assert (rules.action * rules.n_train).sum() <= int(np.floor(120 * fraction))
    if fraction == .25:
        assert assignments.loc[irm.data.df.x == 2, "action"].eq(1).all()
        assert assignments.loc[irm.data.df.x == -1, "action"].eq(0).all()
    for row in rules.itertuples():
        selected = assignments.rule_id == row.rule_id
        assert assignments.loc[selected, "action"].eq(row.action).all()


def test_capacity_uses_net_rewards_not_gross_uplift():
    irm = exact_irm(costs=(0, 0, 0, 5))
    fitted = policy(irm, treatment_cost="z", max_treatment_fraction=.25)
    assigned = fitted.assign(irm.data.df, user_id="client_id")
    assert assigned.loc[irm.data.df.x == -1, "action"].eq(1).all()
    assert assigned.loc[irm.data.df.x == 2, "action"].eq(0).all()


@pytest.mark.parametrize("cost,action", [(0, 1), (2, 0), (3, 0)])
def test_known_scalar_cost_and_zero_net_tie(cost, action):
    fitted = policy(exact_irm(effects=(2, 2, 2, 2)), treatment_cost=cost)
    assert fitted.rules().action.tolist() == [action]


def test_positive_constant_root_can_leave_capacity_unused():
    fitted = policy(exact_irm(effects=(2, 2, 2, 2)), max_treatment_fraction=.9)
    assert fitted.rules().action.tolist() == [0]
    assert fitted.training_diagnostics_["training_targeted"] == 0
    assert fitted.training_diagnostics_["training_capacity"] == 108


@pytest.mark.parametrize("cost", [0., 1., "z"])
def test_independent_net_value_paired_variance_and_rule_hc3(cost):
    training = exact_irm(costs=(.1, .2, .4, 1.))
    evaluation = exact_irm("eval", effects=(-2., 3., -1., 8.), costs=(.2, 1., .3, 2.))
    fitted = policy(training, treatment_cost=cost, max_treatment_fraction=.25)
    before = fitted.rules()
    assigned = fitted.assign(evaluation.data.df, user_id="client_id")
    gross = manual_signal(evaluation)
    costs = evaluation.data.df.z.to_numpy() if cost == "z" else np.full(120, cost)
    net = gross - costs
    a = assigned.action.to_numpy()
    result = fitted.evaluate(evaluation, alpha=.1)
    for row, weight in zip(result.summary().itertuples(), [a, a - 1, np.ones(120)]):
        signal = weight * net
        expected = np.mean(signal)
        se = np.sqrt(np.dot(signal - expected, signal - expected) / (120 * 119))
        assert row.value == pytest.approx(expected)
        assert row.std_error == pytest.approx(se)
        assert row.gross_value == pytest.approx(np.mean(weight * gross))
        assert row.incremental_cost == pytest.approx(np.mean(weight * costs))
        assert row.value == pytest.approx(row.gross_value - row.incremental_cost)
        assert row.ci_lower == pytest.approx(expected - norm.ppf(.95) * se)
        assert row.ci_upper == pytest.approx(expected + norm.ppf(.95) * se)
    for row in result.rules_summary().itertuples():
        values = net[assigned.rule_id.to_numpy() == row.rule_id]
        assert row.value == pytest.approx(values.mean())
        assert row.std_error == pytest.approx(np.linalg.norm(values - values.mean()) / (len(values) - 1))
        assert row.value == pytest.approx(row.gross_value - row.mean_cost)
    pd.testing.assert_frame_equal(before, fitted.rules())


def test_cost_sampling_variation_enters_net_standard_error():
    training = exact_irm(effects=(10, 10, 10, 10), costs=(1, 2, 3, 4))
    evaluation = exact_irm("eval", effects=(10, 10, 10, 10), costs=(1, 2, 3, 4))
    result = policy(training, treatment_cost="z").evaluate(evaluation)
    row = result.summary().set_index("comparison").loc["policy_vs_none"]
    assert row.value == pytest.approx(7.5)
    assert row.std_error == pytest.approx(np.std(evaluation.data.df.z, ddof=1) / np.sqrt(120))
    assert row.std_error > 0  # Gross signal is constant; subtracting only mean cost is wrong.


def test_capacity_is_training_only_and_assignments_are_pointwise():
    irm = exact_irm()
    fitted = policy(irm, max_treatment_fraction=.25)
    batch = pd.DataFrame({"id": range(10), "x": np.full(10, 2.)})
    assert fitted.assign(batch, user_id="id").action.eq(1).all()
    reversed_batch = batch.iloc[::-1]
    pd.testing.assert_frame_equal(fitted.assign(reversed_batch, user_id="id"),
                                  fitted.assign(batch, user_id="id").iloc[::-1])
    assert fitted.assign(batch.iloc[:0], user_id="id").empty


def test_cost_feature_need_not_be_a_policy_feature_or_assignment_input():
    fitted = policy(exact_irm(costs=(0, 1, 0, 3)), treatment_cost="z")
    assert fitted.policy_features_ == ("x",)
    assert fitted.assign(pd.DataFrame({"id": [1], "x": [2.]}), user_id="id").action.item() == 1


def test_sklearn_clone_and_fitted_configuration_ownership():
    fitted = policy(exact_irm(costs=(0, 1, 0, 3)), treatment_cost="z", max_treatment_fraction=.25)
    evaluation = exact_irm("eval", costs=(0, 1, 0, 3))
    expected = fitted.evaluate(evaluation).summary()
    copied = clone(fitted)
    assert copied.treatment_cost == "z" and copied.max_treatment_fraction == .25
    assert not hasattr(copied, "root_")
    fitted.treatment_cost = 1000
    fitted.max_treatment_fraction = 0
    pd.testing.assert_frame_equal(expected, fitted.evaluate(evaluation).summary())


def test_failed_refit_preserves_complete_previous_policy():
    irm = exact_irm()
    fitted = policy(irm, treatment_cost=1, max_treatment_fraction=.25)
    before = fitted.rules()
    assignments = fitted.assign(irm.data.df, user_id="client_id")
    fitted.treatment_cost = -1
    with pytest.raises(ValueError):
        fitted.fit(irm)
    pd.testing.assert_frame_equal(before, fitted.rules())
    pd.testing.assert_frame_equal(assignments, fitted.assign(irm.data.df, user_id="client_id"))
    assert fitted._cost_definition_ == 1


@pytest.mark.parametrize("cost", [-1, np.nan, np.inf, -np.inf, True, 1j, [], {}, "y", "missing", 10**400])
def test_rejects_invalid_cost_definitions(cost):
    with pytest.raises((ValueError, RuntimeError)):
        policy(exact_irm(), treatment_cost=cost)


@pytest.mark.parametrize("fraction", [-.1, 1.1, np.nan, np.inf, True, 1j, "0.5", [], 10**400])
def test_rejects_invalid_capacity(fraction):
    with pytest.raises(ValueError):
        policy(exact_irm(), max_treatment_fraction=fraction)


@pytest.mark.parametrize("change", ["negative", "complex", "nan", "string", "bool"])
def test_cost_column_validated_even_when_excluded_from_policy_features(change):
    irm = exact_irm(costs=(0, 1, 0, 3))
    if change == "negative":
        irm.data.df.z = -np.ones(120)
        irm.fit()
    elif change == "complex":
        irm.data.df.z = irm.data.df.z.astype(complex)
    elif change == "nan":
        irm.data.df.z = np.nan
    elif change == "string":
        irm.data.df.z = irm.data.df.z.astype(str)
    else:
        irm.data.df.z = irm.data.df.z.astype(bool)
    with pytest.raises((ValueError, RuntimeError)):
        policy(irm, treatment_cost="z")


@pytest.mark.parametrize("context", ["repeated", "external", "cluster"])
@pytest.mark.parametrize("stage", ["fit", "evaluate"])
def test_nondefault_policy_context_rejects_unsupported_fit_metadata(context, stage):
    training, evaluation = exact_irm(), exact_irm("eval")
    target = training if stage == "fit" else evaluation
    if context == "repeated":
        target._fit_repetitions_ = [{}]
    elif context == "external":
        target._fit_external_oof_ = True
    else:
        target._fit_cluster_codes_ = np.arange(120)
    with pytest.raises(NotImplementedError, match="single-partition iid"):
        if stage == "fit":
            policy(training, treatment_cost=1)
        else:
            policy(training, treatment_cost=1).evaluate(evaluation)


@pytest.mark.parametrize("scale", [1e-80, 1., 1e80])
def test_net_objective_scale_invariance(scale):
    irm = exact_irm(scale=scale)
    fitted = policy(irm, treatment_cost=scale, max_treatment_fraction=.25)
    assert fitted.assign(pd.DataFrame({"id": [1, 2], "x": [-1, 2]}), user_id="id").action.tolist() == [0, 1]


def test_evaluation_does_not_call_fit_predict_or_consume_rng(monkeypatch):
    training, evaluation = exact_irm(), exact_irm("eval")
    fitted = policy(training, treatment_cost=1, max_treatment_fraction=.25)
    def fail(*args, **kwargs):
        raise AssertionError("No refit or scoring callback allowed")
    for irm in (training, evaluation):
        monkeypatch.setattr(irm, "fit", fail)
        monkeypatch.setattr(irm, "estimate", fail)
        for name in ("ml_g", "ml_m"):
            monkeypatch.setattr(getattr(irm, name), "predict", fail)
    state = np.random.get_state()
    fitted.evaluate(evaluation)
    current = np.random.get_state()
    assert state[0] == current[0] and state[2:] == current[2:]
    np.testing.assert_array_equal(state[1], current[1])


def test_default_columns_and_decisions_remain_legacy_compatible():
    fitted = policy(exact_irm())
    assert "train_mean_net_gain_descriptive" not in fitted.rules()
    assert "gross_value" not in fitted.evaluate(exact_irm("eval")).summary()


def test_greedy_partition_is_not_globally_constrained_tree_optimum():
    fitted = policy(exact_irm(effects=(-3, 4, -3, 6)), max_treatment_fraction=.25)
    # The unconstrained greedy tree stops at a profitable 90-client leaf.
    # A different partition could isolate the 30-client high-benefit group.
    assert fitted.rules().n_train.tolist() == [30, 90]
    assert fitted.rules().action.eq(0).all()


@pytest.mark.parametrize("cost", [0.5, 3., 5.])
def test_first_split_matches_independent_net_reward_enumeration(cost):
    irm = exact_irm()
    phi = manual_signal(irm) - cost
    x = irm.data.df.x.to_numpy()
    thresholds = [-1.5, 0., 1.5]
    reward = lambda values: max(0., values.sum())
    candidates = [reward(phi[x <= cut]) + reward(phi[x > cut]) for cut in thresholds]
    best = int(np.argmax(candidates))
    fitted = UpliftPolicyTree(max_depth=1, min_samples_leaf=20,
                             treatment_cost=cost).fit(irm, policy_features=["x"])
    assert candidates[best] > reward(phi)
    assert fitted.rules().predicates.iloc[0][0] == ("x", "<=", thresholds[best])


@pytest.mark.parametrize("field", ["g0_hat_", "g1_hat_", "m_hat_"])
@pytest.mark.parametrize("corruption", ["complex", "nan", "shape"])
def test_cost_mode_checks_raw_owned_nuisance_contract(field, corruption):
    irm = exact_irm()
    values = getattr(irm, field)
    if corruption == "complex":
        values = values.astype(complex)
    elif corruption == "nan":
        values = values.copy()
        values[0] = np.nan
    else:
        values = values[:, None]
    setattr(irm, field, values)
    with pytest.raises((ValueError, RuntimeError)):
        policy(irm, treatment_cost=1)


def test_net_signal_overflow_fails_without_losing_previous_fit():
    irm = exact_irm()
    fitted = policy(irm, treatment_cost=1)
    before = fitted.rules()
    y, d = irm.data.outcome.to_numpy(), irm.data.treatment.to_numpy()
    irm.g0_hat_ = y + d * 1e308
    irm.g1_hat_ = y - (1 - d) * 1e308
    fitted.treatment_cost = 1e308
    with pytest.raises(RuntimeError, match="arithmetic"):
        fitted.fit(irm)
    pd.testing.assert_frame_equal(before, fitted.rules())


def test_empty_and_unsupported_cost_rule_reports_keep_explicit_status():
    fitted = policy(make_irm(), treatment_cost=1)
    report = fitted.evaluate(make_irm("eval", x_values=(1., 2.)))
    rules = report.rules_summary()
    assert "empty" in set(rules.status)
    assert rules.loc[rules.status != "ok", ["value", "gross_value", "std_error"]].isna().all().all()
    unsupported = fitted.evaluate(make_irm("unsupported", separated=True)).rules_summary()
    assert unsupported.status.eq("insufficient_arm_support").all()
    assert unsupported[["value", "gross_value", "std_error"]].isna().all().all()
