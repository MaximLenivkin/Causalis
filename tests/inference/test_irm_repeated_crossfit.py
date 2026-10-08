"""Synthetic public-contract checks for repeated binary IRM."""
import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.exceptions import NotFittedError
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import StratifiedKFold

from causalis.data_contracts import CausalData, RepeatedCausalEstimate
from causalis.scenarios.unconfoundedness import IRM
from causalis.scenarios.unconfoundedness._repeated import median_inference


def data(seed=31, binary=False):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=240)
    d = rng.binomial(1, 1 / (1 + np.exp(-0.4 * x)))
    y = 5 + 0.5 * x + 0.7 * d + rng.normal(size=len(x))
    if binary:
        y = rng.binomial(1, 1 / (1 + np.exp(-(-0.5 + 0.4 * x + 0.6 * d))))
    return CausalData(df=pd.DataFrame({'x': x, 'y': y, 'd': d}),
                      outcome='y', treatment='d', confounders=['x'])


def model(n_rep=3, **kwargs):
    options = dict(data=data(), ml_g=LinearRegression(),
                   ml_m=LogisticRegression(max_iter=300),
                   n_folds=3, n_rep=n_rep, random_state=19)
    options.update(kwargs)
    return IRM(**options)


def reference(values, errors, alpha):
    # Python sorting and scalar arithmetic, independent of production helper.
    def median(items):
        ordered = sorted(items)
        n = len(ordered)
        return ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
    value = median(values)
    se = median([error * error + (effect - value) * (effect - value)
                 for effect, error in zip(values, errors)]) ** 0.5
    return value, se, value - norm.ppf(1 - alpha / 2) * se, value + norm.ppf(1 - alpha / 2) * se


@pytest.mark.parametrize('n_rep', [2, 3, 4])
@pytest.mark.parametrize('score', ['ATE', 'ATTE'])
@pytest.mark.parametrize('normalize', [False, True])
def test_public_repetitions_match_independent_single_fits(n_rep, score, normalize):
    fitted = model(n_rep=n_rep, normalize_ipw=normalize).fit()
    result = fitted.estimate(score=score, alpha=0.1)
    assert isinstance(result, RepeatedCausalEstimate)
    assert result.model == 'RepeatedIRM'
    assert result.diagnostic_data is None
    assert result.model_options['aggregation'] == 'median_variance'
    assert len(result.repetition_estimates) == n_rep
    singles = [model(n_rep=1, random_state=seed, normalize_ipw=normalize).fit().estimate(score=score, alpha=0.1)
               for seed in result.repetition_seeds]
    values = [r.value for r in singles]
    errors = [r.model_options['std_error'] for r in singles]
    value, se, low, high = reference(values, errors, 0.1)
    np.testing.assert_allclose([result.value, fitted.se[0], result.ci_lower_absolute,
                                result.ci_upper_absolute], [value, se, low, high], rtol=1e-14)
    np.testing.assert_allclose(result.p_value, 2 * norm.sf(abs(value / se)))
    assert result.is_significant == (result.p_value < 0.1)
    assert fitted.coef[0] == result.value
    assert fitted.pvalues[0] == result.p_value
    pd.testing.assert_frame_equal(fitted.summary, result.summary())
    np.testing.assert_allclose(fitted.confint(alpha=0.1).to_numpy(), [[low, high]])
    np.testing.assert_array_equal(fitted.folds_repetitions_,
                                 np.column_stack([r.diagnostic_data.folds for r in singles]))
    # Check each underlying moment/IF directly, not just single-fit parity.
    for item, single in zip(result.repetition_estimates, singles):
        diag = item.diagnostic_data
        assert item.value == single.value
        y, d = diag.y, diag.d
        g0, g1, m = diag.g0_hat, diag.g1_hat, diag.m_hat
        if score == 'ATE':
            a, b = d / m, (1 - d) / (1 - m)
            if normalize:
                a, b = a / a.mean(), b / b.mean()
            signal = g1 - g0 + a * (y - g1) - b * (y - g0)
            influence = signal - signal.mean()
        else:
            signal = d / d.mean() * (y - g0) - (1 - d) * m / (1 - m) / d.mean() * (y - g0)
            influence = signal - signal.mean() * d / d.mean()
        np.testing.assert_allclose(item.value, signal.mean(), rtol=1e-13)
        np.testing.assert_allclose(item.model_options['std_error'], influence.std(ddof=1) / len(y)**0.5)
    rel_value, rel_se, rel_low, rel_high = reference(
        [r.value_relative for r in singles],
        [(r.ci_upper_relative - r.ci_lower_relative) / (2 * norm.ppf(0.95)) for r in singles], 0.1)
    np.testing.assert_allclose([result.value_relative, fitted.se_relative_[0],
                                result.ci_lower_relative, result.ci_upper_relative],
                               [rel_value, rel_se, rel_low, rel_high], rtol=1e-13)


@pytest.mark.parametrize('n_jobs', [1, 2])
def test_seed_prefix_fold_reference_and_local_rng(n_jobs):
    np.random.seed(1234)
    before = np.random.get_state()
    small = model(n_rep=2, n_jobs=n_jobs).fit()
    large = model(n_rep=4, n_jobs=n_jobs).fit()
    after = np.random.get_state()
    assert before[0] == after[0]
    np.testing.assert_array_equal(before[1], after[1])
    assert before[2:] == after[2:]
    assert small.repetition_seeds_ == large.repetition_seeds_[:2]
    assert small.repetition_seeds_[0] == 19
    np.testing.assert_array_equal(small.folds_repetitions_, large.folds_repetitions_[:, :2])
    assert not np.array_equal(large.folds_repetitions_[:, 0], large.folds_repetitions_[:, 1])
    for rep, seed in enumerate(large.repetition_seeds_):
        expected = np.empty(len(large._d), dtype=int)
        splitter = StratifiedKFold(n_splits=3, shuffle=True, random_state=seed)
        for fold, (_, held_out) in enumerate(splitter.split(np.zeros((len(expected), 1)), large._d)):
            expected[held_out] = fold
        np.testing.assert_array_equal(large.folds_repetitions_[:, rep], expected)
    first, again = large.estimate(), model(n_rep=4, n_jobs=n_jobs).fit().estimate()
    assert first.value == again.value
    assert first.model_options['std_error'] == again.model_options['std_error']


def test_parallel_matches_sequential():
    first = model(n_jobs=1).fit().estimate()
    second = model(n_jobs=2).fit().estimate()
    assert first.value == second.value
    assert first.model_options['std_error'] == second.model_options['std_error']


def test_none_seed_records_replayable_partitions_without_global_rng():
    np.random.seed(9)
    before = np.random.get_state()
    fitted = model(random_state=None).fit()
    after = np.random.get_state()
    np.testing.assert_array_equal(before[1], after[1])
    assert before[2:] == after[2:]
    result = fitted.estimate()
    for rep, seed in enumerate(result.repetition_seeds):
        single = model(n_rep=1, random_state=seed).fit().estimate()
        assert single.value == result.repetition_estimates[rep].value


@pytest.mark.parametrize('bad', [0, -1, 1.1, 2.0, True, False, '2', None, np.nan])
def test_invalid_repetition_counts(bad):
    with pytest.raises(ValueError, match='n_rep'):
        model(n_rep=bad)


@pytest.mark.parametrize('bad', [-1, 2**32, 1.5, True, np.random.RandomState(3)])
def test_invalid_repeated_seeds(bad):
    with pytest.raises(ValueError, match='random_state'):
        model(random_state=bad).fit()


def test_numpy_integer_count_and_seed():
    result = model(n_rep=np.int64(2), random_state=np.int64(4)).fit().estimate()
    assert result.repetition_seeds[0] == 4


@pytest.mark.parametrize('store', [True, False])
def test_fit_snapshot_detached_results_and_diagnostic_policy(store):
    fitted = model(store_diagnostics=store).fit()
    initial = fitted.estimate()
    fitted.data.df.loc[:, 'y'] += 1000
    fitted.data.outcome.name = 'renamed'
    fitted.n_rep = 1
    fitted.random_state = 88
    assert fitted.estimate().value == initial.value
    assert fitted.estimate().outcome == 'y'
    assert fitted.estimate().model_options['n_rep'] == 3
    assert (initial.repetition_estimates[0].diagnostic_data is not None) == store
    if store:
        initial.repetition_estimates[0].diagnostic_data.psi[:] = 99
        diag = fitted.diagnostics_
        diag['folds_repetitions'][:] = -9
        assert np.all(fitted.folds_repetitions_ >= 0)
    else:
        assert fitted.folds_repetitions_ is None
    initial.repetition_estimates[0].value = -99
    initial.repetition_seeds[0] = -99
    initial.model_options['repetition_std_errors'][0] = -99
    fresh = fitted.estimate()
    assert fresh.repetition_estimates[0].value != -99
    assert fresh.repetition_seeds[0] == 19


def test_failed_refit_retains_complete_repeated_fit_and_success_clears_inference():
    fitted = model().fit()
    result = fitted.estimate()
    seeds = fitted.repetition_seeds_
    broken = data()
    broken.df.loc[:, 'd'] = 0
    with pytest.raises(ValueError):
        fitted.fit(broken)
    assert fitted.repetition_seeds_ == seeds
    assert fitted.coef[0] == result.value
    assert fitted.estimate().value == result.value
    fitted.fit(data(seed=32))
    with pytest.raises(NotFittedError):
        _ = fitted.coef
    assert fitted.estimate().value != result.value


def test_single_repeated_single_refit_has_no_stale_nuisances_or_inference():
    fitted = model(n_rep=1).fit()
    fitted.estimate()
    fitted.n_rep = 3
    fitted.fit()
    assert not hasattr(fitted, 'g0_hat_')
    assert not hasattr(fitted, 'psi_b_')
    assert fitted.estimate().model == 'RepeatedIRM'
    fitted.n_rep = 1
    fitted.fit()
    assert not hasattr(fitted, '_fit_repetitions_')
    assert not hasattr(fitted, 'folds_repetitions_')
    assert fitted.estimate().model == 'IRM'


@pytest.mark.parametrize('action', ['drop', 'fixed_folds', 'GATE', 'GATET', 'CATE', 'sensitivity', 'elements', 'signal'])
def test_unsupported_repeated_operations(action):
    fitted = model()
    if action == 'drop':
        fitted.overlap_policy = 'drop'
        with pytest.raises(ValueError, match='common sample'):
            fitted.fit()
        return
    if action == 'fixed_folds':
        fitted._fixed_fold_assignments_ = np.arange(240) % 3
        with pytest.raises(ValueError, match='fixed'):
            fitted.fit()
        return
    fitted.fit()
    with pytest.raises(NotImplementedError):
        if action in {'GATE', 'GATET'}:
            fitted.estimate(score=action)
        elif action == 'CATE':
            fitted.predict_cate(np.zeros((2, 1)))
        elif action == 'sensitivity':
            fitted.sensitivity_analysis(0.1, 0.1)
        elif action == 'elements':
            fitted._sensitivity_element_est()
        else:
            _ = fitted.orth_signal


@pytest.mark.parametrize('alpha', [0, 1, np.nan])
def test_invalid_alpha(alpha):
    with pytest.raises(ValueError, match='alpha'):
        model().fit().estimate(alpha=alpha)


def test_relative_undefined_in_any_repetition_is_not_omitted():
    fitted = model(relative_baseline_min=100).fit()
    with pytest.warns(RuntimeWarning, match='Relative'):
        result = fitted.estimate()
    assert np.isnan(result.value_relative)
    assert np.isnan(result.ci_lower_relative)
    assert np.isfinite(result.value)


@pytest.mark.parametrize('values,errors,expected', [
    ([0, 0, 0], [2, 2, 2], (0, 2)),
    ([1, 3, 100], [1, 1, 1], (3, 5**0.5)),
    ([1, 3], [2, 2], (2, 5**0.5)),
    ([0, 0], [0, 0], (0, 0)),
    ([1, 1], [0, 0], (1, 0)),
])
def test_scalar_policy_no_repetition_sample_size_factor(values, errors, expected):
    theta, se, _, p, low, high = median_inference(values, errors, 0.05)
    np.testing.assert_allclose([theta, se], expected)
    if se == 0:
        assert p == (1 if theta == 0 else 0)
    assert low <= high


@pytest.mark.parametrize('values,errors', [([np.nan], [1]), ([1], [np.inf]),
    ([1e308, -1e308], [1, 1]), ([1], [1e308]), ([1], [-1]), ([], []), ([1, 2], [1])])
def test_invalid_or_overflowed_aggregation_fails(values, errors):
    with pytest.raises((ValueError, RuntimeError)):
        median_inference(values, errors, 0.05)


class SeenRows(RegressorMixin, BaseEstimator):
    """Reject prediction on training rows to expose leakage in actual fold fits."""
    def fit(self, X, y):
        self.seen_ = set(X[:, 0])
        self.mean_ = float(np.mean(y))
        return self

    def predict(self, X):
        assert not self.seen_.intersection(X[:, 0])
        return np.full(len(X), self.mean_)


def test_real_repeated_fits_keep_predictions_out_of_training_sample():
    result = model(ml_g=SeenRows(), ml_m=SeenRows()).fit().estimate()
    assert np.isfinite(result.value)


@pytest.mark.parametrize('score', ['ATE', 'ATTE'])
def test_binary_outcome_and_custom_weight_support(score):
    fitted = model(data=data(binary=True), ml_g=LogisticRegression(max_iter=300),
                   weights=np.linspace(0.5, 1.5, 240) if score == 'ATE' else None).fit()
    result = fitted.estimate(score=score)
    assert np.isfinite(result.value)
    assert result.model_options['se_approx_weight_norm'] == (score == 'ATE')
    assert result.n_treated + result.n_control == 240


def test_partial_undefined_relative_effect_is_not_dropped(monkeypatch):
    fitted = model().fit()
    child = fitted._fit_repetitions_[1]
    original = child._compute_relative_effect_stats

    def undefined(**kwargs):
        baseline, *_ = original(**kwargs)
        return baseline, np.nan, np.nan, np.nan, np.nan

    monkeypatch.setattr(child, '_compute_relative_effect_stats', undefined)
    result = fitted.estimate()
    assert np.isfinite(result.repetition_estimates[0].value_relative)
    assert np.isnan(result.repetition_estimates[1].value_relative)
    assert np.isnan(result.value_relative)
    assert np.isfinite(result.value)


def test_later_partition_failure_does_not_publish_partial_refit(monkeypatch):
    fitted = model().fit()
    old = fitted.estimate()
    old_repetitions = fitted._fit_repetitions_
    original = IRM._cross_fit_nuisances
    calls = []

    def fail_second(self, *args, **kwargs):
        calls.append(self.random_state)
        if len(calls) == 2:
            raise RuntimeError('second partition failed')
        return original(self, *args, **kwargs)

    monkeypatch.setattr(IRM, '_cross_fit_nuisances', fail_second)
    with pytest.raises(RuntimeError, match='second partition'):
        fitted.fit(data(seed=33))
    assert len(calls) == 2
    assert fitted._fit_repetitions_ is old_repetitions
    assert fitted.estimate().value == old.value


def test_seeded_supplied_learner_parameters_are_preserved():
    from sklearn.ensemble import RandomForestRegressor
    learner = RandomForestRegressor(n_estimators=5, max_depth=2, random_state=71, n_jobs=1)
    fitted = model(ml_g=learner).fit()
    first = fitted.estimate()
    assert learner.random_state == 71
    assert all(child.ml_g.random_state == 71 for child in fitted._fit_repetitions_)
    second = model(ml_g=learner).fit().estimate()
    assert first.value == second.value
    assert first.model_options['std_error'] == second.model_options['std_error']


class OracleOutcome(RegressorMixin, BaseEstimator):
    def fit(self, X, y):
        self.intercept_ = float(np.round(y[0] - 0.6 * X[0, 0]))
        return self

    def predict(self, X):
        return self.intercept_ + 0.6 * X[:, 0]


class HalfPropensity(RegressorMixin, BaseEstimator):
    def fit(self, X, y):
        return self

    def predict(self, X):
        return np.full(len(X), 0.5)


@pytest.mark.parametrize('score', ['ATE', 'ATTE'])
def test_public_oracle_repetitions_do_not_reduce_sampling_standard_error(score):
    rng = np.random.default_rng(85)
    x = rng.normal(size=240)
    d = rng.binomial(1, 0.5, size=len(x))
    y = 3 + 0.6 * x + d + rng.uniform(-0.49, 0.49, size=len(x))
    sample = CausalData(df=pd.DataFrame({'x': x, 'd': d, 'y': y}),
                        outcome='y', treatment='d', confounders=['x'])
    single = model(n_rep=1, data=sample, ml_g=OracleOutcome(), ml_m=HalfPropensity()).fit().estimate(score=score)
    repeated = model(n_rep=5, data=sample, ml_g=OracleOutcome(), ml_m=HalfPropensity()).fit().estimate(score=score)
    assert repeated.value == single.value
    assert repeated.model_options['std_error'] == single.model_options['std_error']
