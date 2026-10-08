"""Synthetic public group leakage, score and one-way CR1 contracts."""
import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.exceptions import NotFittedError
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import KFold
import statsmodels.api as sm

from causalis.data_contracts import CausalData
from causalis.scenarios.unconfoundedness import IRM
from causalis.scenarios.unconfoundedness._cluster import cluster_standard_error


def sample(seed=24, singleton=False, binary=False):
    rng = np.random.default_rng(seed)
    groups = np.arange(250) if singleton else np.repeat(np.arange(40), rng.integers(3, 10, 40))
    x = rng.normal(size=len(groups))
    d = rng.binomial(1, 1 / (1 + np.exp(-0.3 * x)))
    y = 10 + 0.6 * x + 0.7 * d + rng.normal(size=len(x))
    if binary:
        y = rng.binomial(1, 1 / (1 + np.exp(-(1 + 0.4 * x + 0.5 * d))))
    frame = pd.DataFrame(dict(x=x, d=d, y=y), index=np.arange(len(x)) + 100)
    return CausalData(df=frame, outcome='y', treatment='d', confounders=['x']), groups


def model(**options):
    data, groups = sample()
    params = dict(data=data, cluster_groups=groups, ml_g=LinearRegression(),
                  ml_m=LogisticRegression(max_iter=300), n_folds=4, random_state=13)
    params.update(options)
    return IRM(**params)


def reference_se(influence, groups):
    # Scalar sums, independent of production bincount/vector arithmetic.
    centered = influence - sum(influence) / len(influence)
    totals = [sum(value for value, label in zip(centered, groups) if label == group)
              for group in dict.fromkeys(groups)]
    return (len(totals) / (len(totals) - 1) * sum(value**2 for value in totals))**0.5 / len(influence)


@pytest.mark.parametrize('score', ['ATE', 'ATTE'])
@pytest.mark.parametrize('normalize', [False, True])
@pytest.mark.parametrize('store', [False, True])
@pytest.mark.parametrize('singleton', [False, True])
def test_public_scores_absolute_relative_cluster_oracles(score, normalize, store, singleton):
    data, groups = sample(singleton=singleton)
    fitted = model(data=data, cluster_groups=groups, normalize_ipw=normalize,
                   store_diagnostics=store).fit()
    result = fitted.estimate(score=score, alpha=0.1)
    y, d = fitted._y, fitted._d
    m, g0, g1 = fitted.m_hat_, fitted.g0_hat_, fitted.g1_hat_
    if score == 'ATE':
        h1, h0 = d / m, (1 - d) / (1 - m)
        if normalize:
            h1, h0 = h1 / h1.mean(), h0 / h0.mean()
        signal = g1 - g0 + (y - g1) * h1 - (y - g0) * h0
        theta = signal.mean()
        influence = signal - theta
        baseline_signal = g0 + (y - g0) * h0
        baseline = baseline_signal.mean()
        baseline_if = baseline_signal - baseline
    else:
        w = d / d.mean()
        signal = w * (y - g0) - (1 - d) * m / (1 - m) / d.mean() * (y - g0)
        theta = signal.mean()
        influence = signal - w * theta
        baseline_signal = w * g0 + (1 - d) * m / (1 - m) / d.mean() * (y - g0)
        baseline = baseline_signal.mean()
        baseline_if = baseline_signal - w * baseline
    error = reference_se(influence, groups)
    relative_if = 100 * (influence / baseline - theta * baseline_if / baseline**2)
    relative_error = reference_se(relative_if, groups)
    z = norm.ppf(0.95)
    np.testing.assert_allclose(result.value, theta, rtol=1e-13)
    np.testing.assert_allclose(fitted.psi_, influence, atol=1e-13)
    np.testing.assert_allclose([fitted.se[0], result.ci_lower_absolute, result.ci_upper_absolute],
                               [error, theta-z*error, theta+z*error], rtol=1e-13)
    np.testing.assert_allclose(result.p_value, 2 * norm.sf(abs(theta/error)), atol=1e-14)
    np.testing.assert_allclose([result.value_relative, fitted.se_relative_[0],
                                result.ci_lower_relative, result.ci_upper_relative],
                               [100*theta/baseline, relative_error,
                                100*theta/baseline-z*relative_error,
                                100*theta/baseline+z*relative_error], rtol=1e-13)
    ols = sm.OLS(influence, np.ones((len(influence), 1))).fit(
        cov_type='cluster', cov_kwds=dict(groups=groups, use_correction=True), use_t=False)
    np.testing.assert_allclose(error, ols.bse[0], rtol=1e-13)
    if singleton:
        np.testing.assert_allclose(error, influence.std(ddof=1) / len(influence)**0.5)
    assert result.model_options['inference'] == 'one_way_cluster_cr1'
    assert result.model_options['n_clusters'] == len(np.unique(groups))
    assert result.model_options['cluster_target'] == 'row_weighted'
    assert (result.diagnostic_data is not None) == store
    assert fitted._fit_cluster_codes_.flags.writeable is False


@pytest.mark.parametrize('n_rep', [1, 2, 3])
@pytest.mark.parametrize('n_jobs', [1, 2])
def test_group_folds_seed_replay_and_parallel_equivalence(n_rep, n_jobs):
    data, groups = sample()
    fitted = model(n_rep=n_rep, n_jobs=n_jobs).fit()
    actual = fitted.folds_[:, None] if n_rep == 1 else fitted.folds_repetitions_
    seeds = [fitted.cluster_split_seed_] if n_rep == 1 else fitted.repetition_seeds_
    assert seeds[0] == 13
    for rep, seed in enumerate(seeds):
        splitter = KFold(n_splits=4, shuffle=True, random_state=seed)
        expected = np.empty(len(groups), dtype=int)
        for fold, (_, held_out) in enumerate(splitter.split(np.unique(groups))):
            expected[np.isin(groups, held_out)] = fold
        np.testing.assert_array_equal(actual[:, rep], expected)
        for group in np.unique(groups):
            assert np.unique(actual[groups == group, rep]).size == 1
    result = fitted.estimate()
    sequential = model(n_rep=n_rep, n_jobs=1).fit().estimate()
    assert result.value == sequential.value
    assert result.model_options['std_error'] == sequential.model_options['std_error']


@pytest.mark.parametrize('score', ['ATE', 'ATTE'])
@pytest.mark.parametrize('n_rep', [2, 3, 4])
def test_repeated_cluster_inference_matches_replayed_single_partitions(score, n_rep):
    fitted = model(n_rep=n_rep).fit()
    result = fitted.estimate(score=score)
    singles = [model(random_state=seed).fit().estimate(score=score)
               for seed in fitted.repetition_seeds_]
    values = [item.value for item in singles]
    errors = [item.model_options['std_error'] for item in singles]
    theta = np.median(values)
    error = np.median([se**2 + (value-theta)**2 for value, se in zip(values, errors)])**0.5
    np.testing.assert_allclose([result.value, fitted.se[0]], [theta, error])
    assert result.diagnostic_data is None
    assert 'cluster_split_seed' not in result.model_options
    assert result.model_options['n_clusters'] == 40
    assert result.model_options['inference'] == 'one_way_cluster_cr1'
    for single, item in zip(singles, result.repetition_estimates):
        assert single.value == item.value
        assert single.model_options == item.model_options
    small = model(n_rep=2).fit()
    assert fitted.repetition_seeds_[:2] == small.repetition_seeds_
    np.testing.assert_array_equal(fitted.folds_repetitions_[:, :2], small.folds_repetitions_)


@pytest.mark.parametrize('n_rep', [1, 3])
def test_none_seed_is_replayable_and_does_not_consume_global_rng(n_rep):
    np.random.seed(821)
    before = np.random.get_state()
    fitted = model(n_rep=n_rep, random_state=None).fit()
    after = np.random.get_state()
    np.testing.assert_array_equal(before[1], after[1])
    assert before[2:] == after[2:]
    seeds = [fitted.cluster_split_seed_] if n_rep == 1 else fitted.repetition_seeds_
    partitions = [fitted] if n_rep == 1 else fitted._fit_repetitions_
    for seed, partition in zip(seeds, partitions):
        replay = model(random_state=seed).fit()
        np.testing.assert_array_equal(partition.folds_, replay.folds_)
        assert partition.estimate().value == replay.estimate().value


class NoFit(BaseEstimator, RegressorMixin):
    def fit(self, X, y):
        raise AssertionError('Invalid cluster input reached learner fitting')


@pytest.mark.parametrize('bad', [[], 'cluster', np.zeros((240, 1)), np.zeros(240),
                                 [None]*250, [np.nan]*250, [pd.NA]*250,
                                 [{'id': 1}]*250, np.ones(250)])
def test_invalid_membership_rejects_before_learners(bad):
    data, _ = sample(singleton=True)
    with pytest.raises(ValueError, match='cluster_groups'):
        model(data=data, cluster_groups=bad, ml_g=NoFit(), ml_m=NoFit()).fit()


@pytest.mark.parametrize('kind', ['shifted', 'reversed', 'duplicate_wrong'])
def test_series_must_match_row_index_in_order(kind):
    data, labels = sample()
    index = data.df.index
    if kind == 'shifted':
        index = index + 1
    elif kind == 'reversed':
        index = index[::-1]
    else:
        index = pd.Index([0]*len(labels))
    with pytest.raises(ValueError, match='index'):
        model(cluster_groups=pd.Series(labels, index=index), ml_g=NoFit()).fit()


def test_valid_series_duplicate_indices_and_heterogeneous_labels():
    data, groups = sample()
    data.df.index = pd.Index(np.zeros(len(groups), dtype=int))
    labels = [str(g) if g % 2 else int(g) for g in groups]
    positional = model(data=data, cluster_groups=labels).fit()
    indexed = model(data=data, cluster_groups=pd.Series(labels, index=data.df.index)).fit()
    assert positional.estimate().value == indexed.estimate().value
    assert indexed.n_clusters_ == 40
    # Int 1 and str '1' remain separate labels.
    labels = np.empty(len(groups), dtype=object)
    labels[:] = groups
    labels[groups == 2] = '1'
    assert model(cluster_groups=labels).fit().n_clusters_ == 40


@pytest.mark.parametrize('seed', [-1, 2**32, 1.5, True, np.random.RandomState(4)])
def test_invalid_cluster_seeds(seed):
    with pytest.raises(ValueError, match='random_state'):
        model(random_state=seed, ml_g=NoFit()).fit()


@pytest.mark.parametrize('kind', ['drop', 'fixed', 'too_many_folds', 'one_arm_cluster'])
def test_unsupported_split_configuration_before_fitting(kind):
    fitted = model(ml_g=NoFit(), ml_m=NoFit())
    if kind == 'drop':
        fitted.overlap_policy = 'drop'
    elif kind == 'fixed':
        fitted._fixed_fold_assignments_ = np.arange(len(fitted.cluster_groups)) % 4
    elif kind == 'too_many_folds':
        fitted.cluster_groups = np.arange(len(fitted.cluster_groups)) % 3
    else:
        d = fitted.data.df['d'].to_numpy()
        fitted.cluster_groups = np.where(d == 1, 0, np.arange(len(d)) + 1)
    with pytest.raises(ValueError, match='Cluster|cluster'):
        fitted.fit()


def test_pure_treatment_clusters_are_supported_if_training_arms_remain():
    data, _ = sample()
    groups = np.arange(len(data.df)) // 5
    data.df['d'] = groups % 2
    fitted = model(data=data, cluster_groups=groups).fit()
    assert np.isfinite(fitted.estimate(score='ATTE').value)


class RejectGroupLeakage(BaseEstimator, RegressorMixin):
    def fit(self, X, y):
        self.seen_ = set(X[:, 0])
        self.mean_ = float(np.mean(y))
        return self

    def predict(self, X):
        assert self.seen_.isdisjoint(X[:, 0]), 'A training cluster leaked into prediction rows'
        return np.full(len(X), self.mean_)


@pytest.mark.parametrize('n_rep', [1, 3])
@pytest.mark.parametrize('n_jobs', [1, 2])
def test_learners_never_predict_on_training_clusters(n_rep, n_jobs):
    data, groups = sample()
    data.df['x'] = groups.astype(float)
    result = model(data=data, cluster_groups=groups, ml_g=RejectGroupLeakage(),
                   ml_m=RejectGroupLeakage(), n_rep=n_rep, n_jobs=n_jobs).fit().estimate()
    assert np.isfinite(result.value)


@pytest.mark.parametrize('n_rep', [1, 3])
@pytest.mark.parametrize('store', [False, True])
def test_membership_and_result_ownership_fit_snapshot(n_rep, store):
    data, labels = sample()
    groups = pd.Series(labels, index=data.df.index)
    fitted = model(data=data, cluster_groups=groups, n_rep=n_rep, store_diagnostics=store).fit()
    initial = fitted.estimate()
    groups[:] = -1
    fitted.cluster_groups = None
    fitted.random_state = 88
    data.df['y'] += 100
    fresh = fitted.estimate()
    assert fresh.value == initial.value
    assert fresh.model_options['std_error'] == initial.model_options['std_error']
    assert fresh.model_options['n_clusters'] == 40
    if n_rep == 1 and store:
        initial.diagnostic_data.psi[:] = 99
        np.testing.assert_allclose(fitted.estimate().diagnostic_data.psi, fitted.psi_)
    if n_rep > 1:
        initial.repetition_estimates[0].model_options['n_clusters'] = 1
        assert fitted.estimate().repetition_estimates[0].model_options['n_clusters'] == 40


@pytest.mark.parametrize('n_rep', [1, 3])
def test_failed_refit_preserves_fit_and_transitions_clear_stale_state(n_rep):
    fitted = model(n_rep=n_rep).fit()
    previous = fitted.estimate()
    fitted.cluster_groups = np.ones(len(fitted._y))
    with pytest.raises(ValueError):
        fitted.fit()
    assert fitted.estimate().value == previous.value
    fitted.cluster_groups = None
    fitted.fit()
    with pytest.raises(NotFittedError):
        _ = fitted.coef
    assert fitted._fit_cluster_codes_ is None
    assert not hasattr(fitted, 'n_clusters_')
    assert not hasattr(fitted, 'cluster_split_seed_')
    assert 'inference' not in fitted.estimate().model_options
    _, groups = sample()
    fitted.cluster_groups = groups
    fitted.fit()
    assert fitted.estimate().model_options['n_clusters'] == 40


@pytest.mark.parametrize('n_rep', [1, 3])
@pytest.mark.parametrize('operation', ['GATE', 'GATET', 'CATE', 'sensitivity', 'elements'])
def test_uncertified_cluster_operations_reject(n_rep, operation):
    fitted = model(n_rep=n_rep).fit()
    fitted.estimate()
    with pytest.raises(NotImplementedError, match='Cluster|Repeated'):
        if operation in ('GATE', 'GATET'):
            fitted.estimate(score=operation)
        elif operation == 'CATE':
            fitted.predict_cate(np.ones((3, 1)))
        elif operation == 'sensitivity':
            fitted.sensitivity_analysis(0.1, 0.1)
        else:
            fitted._sensitivity_element_est()


def test_baseline_low_signal_guard_uses_cluster_covariance():
    data, groups = sample()
    # Within-group perfectly correlated baseline shocks; iid SE understates them.
    d = np.tile([0, 1], 100)
    groups = np.repeat(np.arange(20), 10)
    shocks = np.repeat(np.tile([-1.0, 1.0], 10), 10)
    frame = pd.DataFrame(dict(x=np.arange(200), d=d, y=0.2+shocks+0.7*d))
    data = CausalData(df=frame, outcome='y', treatment='d', confounders=['x'])
    fitted = model(data=data, cluster_groups=groups).fit()
    fitted.g0_hat_ = np.full(200, 0.2)
    fitted.g1_hat_ = np.full(200, 0.9)
    fitted.m_hat_ = np.full(200, 0.5)
    with pytest.warns(RuntimeWarning, match='Relative effect baseline'):
        result = fitted.estimate()
    assert np.isnan(result.value_relative)


def test_custom_weights_and_binary_outcomes():
    data, groups = sample(binary=True)
    result = model(data=data, cluster_groups=groups,
                   ml_g=LogisticRegression(max_iter=300)).fit().estimate()
    assert np.isfinite(result.value)
    weights = np.linspace(0.7, 1.3, len(groups))
    fitted = model(data=data, cluster_groups=groups, weights=weights,
                   ml_g=LogisticRegression(max_iter=300), normalize_ipw=True).fit()
    with pytest.warns(RuntimeWarning, match='approximate'):
        result = fitted.estimate()
    assert result.model_options['se_approx_hajek']
    assert result.model_options['se_approx_weight_norm']
    np.testing.assert_allclose(fitted.se[0], reference_se(fitted.psi_, groups))
    with pytest.raises(ValueError, match='ATTE'):
        fitted.estimate(score='ATTE')


def test_cluster_variance_is_row_weighted_and_handles_numerical_failure():
    codes = np.array([0, 0, 0, 1, 2])
    influence = np.array([3.0, 3.0, 3.0, -4.0, -5.0])
    np.testing.assert_allclose(cluster_standard_error(influence, codes), reference_se(influence, codes), rtol=1e-14)
    with pytest.raises(RuntimeError):
        cluster_standard_error(np.array([1e308, -1e308]), np.array([0, 1]))
    with pytest.raises(RuntimeError):
        cluster_standard_error(np.array([np.nan, 1]), np.array([0, 1]))
    with pytest.raises(ValueError, match='match'):
        cluster_standard_error(np.ones(2), codes)


@pytest.mark.parametrize('score', ['ATE', 'ATTE'])
def test_unequal_size_target_is_observation_weighted(score):
    groups = np.repeat(np.arange(3), [2, 10, 8])
    effects = np.repeat([0.0, 1.0, 3.0], [2, 10, 8])
    d = np.tile([0, 1], 10)
    data = CausalData(df=pd.DataFrame(dict(x=effects, d=d, y=10+effects*d)),
                      outcome='y', treatment='d', confounders=['x'])
    fitted = model(data=data, cluster_groups=groups, n_folds=3).fit()
    # Hold fitted nuisance arrays at their oracle values to isolate the public
    # moment and target from any learner approximation.
    fitted.g0_hat_ = np.full(20, 10.0)
    fitted.g1_hat_ = 10 + effects
    fitted.m_hat_ = np.full(20, 0.5)
    result = fitted.estimate(score=score)
    np.testing.assert_allclose(result.value, 1.7)
    assert result.value != np.mean([0, 1, 3])
    np.testing.assert_allclose(result.model_options['std_error'], reference_se(fitted.psi_, groups))


@pytest.mark.parametrize('n_rep', [1, 3])
def test_label_renaming_preserves_partitions_and_result(n_rep):
    _, groups = sample()
    first = model(n_rep=n_rep).fit()
    second = model(n_rep=n_rep, cluster_groups=[f'label-{1000-int(g)}' for g in groups]).fit()
    assert first.estimate().value == second.estimate().value
    assert first.estimate().model_options['std_error'] == second.estimate().model_options['std_error']


def test_failure_in_later_repetition_keeps_previous_complete_fit(monkeypatch):
    fitted = model(n_rep=3).fit()
    result = fitted.estimate()
    from causalis.scenarios.unconfoundedness import model as module
    original = module.cluster_splits
    calls = []

    def fail_second(*args):
        calls.append(1)
        if len(calls) == 2:
            raise ValueError('Injected second partition failure')
        return original(*args)

    monkeypatch.setattr(module, 'cluster_splits', fail_second)
    with pytest.raises(ValueError, match='second partition'):
        fitted.fit()
    assert fitted.estimate().value == result.value
    assert fitted.estimate().model_options['std_error'] == result.model_options['std_error']


@pytest.mark.parametrize('n_rep', [1, 3])
@pytest.mark.parametrize('operation', ['GATE', 'GATET', 'CATE'])
def test_exported_adapters_cannot_bypass_cluster_restrictions(n_rep, operation):
    fitted = model(n_rep=n_rep).fit()
    from causalis.scenarios.gate import estimate_gate_from_irm, estimate_gatet_from_irm
    from causalis.scenarios.uplift import predict_cate
    with pytest.raises(NotImplementedError, match='Cluster'):
        if operation == 'CATE':
            predict_cate(fitted, np.ones((3, 1)))
        else:
            adapter = estimate_gate_from_irm if operation == 'GATE' else estimate_gatet_from_irm
            adapter(fitted, groups=None)
