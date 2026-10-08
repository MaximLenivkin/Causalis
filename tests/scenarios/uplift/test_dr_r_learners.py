"""Synthetic conditional moments, independent R-loss oracle and API contracts."""
import numpy as np
import pandas as pd
import pytest
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin
from sklearn.dummy import DummyRegressor
from sklearn.exceptions import NotFittedError
from sklearn.linear_model import LinearRegression, LogisticRegression

from causalis.data_contracts import CausalData
from causalis.scenarios.unconfoundedness import IRM
from causalis.scenarios.uplift import DRLearner, RLearner


class KnownPropensity(ClassifierMixin, BaseEstimator):
    def __init__(self, correct=True):
        self.correct = correct

    def fit(self, X, y):
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X):
        e = .4 + .2 * X[:, 0] if self.correct else np.full(len(X), .5)
        return np.column_stack([1 - e, e])


def support_irm(correct_g=True, correct_e=True, diagnostics=True, **kwargs):
    # Exact conditional law: 100 observations per x, P(D=1|x)=.2/.6.
    x = np.repeat([-1., 1.], 100)
    d = np.r_[np.ones(20), np.zeros(80), np.ones(60), np.zeros(40)]
    y = 10 + 3*x + d*(.4 + .2*x)
    data = CausalData(df=pd.DataFrame(dict(x=x, y=y, d=d)), outcome='y', treatment='d', confounders=['x'])
    return IRM(data, ml_g=LinearRegression() if correct_g else DummyRegressor(strategy='constant', constant=5),
               ml_m=KnownPropensity(correct_e), n_folds=3, random_state=18,
               store_diagnostics=diagnostics, **kwargs).fit()


def noise_irm(binary=False, diagnostics=True, **kwargs):
    rng = np.random.default_rng(172)
    X = rng.normal(size=(240, 2))
    e = 1/(1+np.exp(-.3*X[:, 0]))
    d = rng.binomial(1, e)
    y = 10 + X[:, 0] + d*(.7+.2*X[:, 1]) + rng.normal(size=len(d))
    if binary:
        y = rng.binomial(1, 1/(1+np.exp(-(.3*X[:, 0]+.5*d))))
    frame = pd.DataFrame(dict(a=X[:, 0], b=X[:, 1], y=y, d=d), index=np.arange(240)+100)
    data = CausalData(df=frame, outcome='y', treatment='d', confounders=['a', 'b'])
    return IRM(data, ml_g=LogisticRegression() if binary else LinearRegression(),
               ml_m=LogisticRegression(), n_folds=3, random_state=11,
               store_diagnostics=diagnostics, **kwargs).fit()


@pytest.mark.parametrize('correct_g,correct_e', [(True, True), (True, False), (False, True)])
@pytest.mark.parametrize('diagnostics', [False, True])
def test_dr_conditional_moments_recover_effect_if_either_nuisance_is_correct(correct_g, correct_e, diagnostics):
    irm = support_irm(correct_g, correct_e, diagnostics)
    result = DRLearner().fit(irm).predict(pd.DataFrame({'x': [-1, 1]}))
    # Independent oracle is the known potential-outcome contrast, not a
    # reconstruction of implementation's pseudo-outcome arithmetic.
    np.testing.assert_allclose(result, [.2, .6], atol=2e-13)


def test_dr_both_wrong_negative_control_and_r_population_projection():
    irm = support_irm(False, False)
    assert np.max(np.abs(DRLearner().fit(irm).predict([[-1], [1]]) - [.2, .6])) > 1
    irm = support_irm()
    dr = DRLearner(DummyRegressor()).fit(irm).predict([[0]])[0]
    r = RLearner(DummyRegressor()).fit(irm).predict([[0]])[0]
    assert dr == pytest.approx(.4)
    # E[var(D|X)*tau]/E[var(D|X)], distinct from average tau.
    assert r == pytest.approx((.16*.2 + .24*.6)/(.16+.24))


@pytest.mark.parametrize('binary', [False, True])
@pytest.mark.parametrize('diagnostics', [False, True])
def test_r_matches_direct_residual_design_least_squares(binary, diagnostics):
    irm = noise_irm(binary=binary, diagnostics=diagnostics)
    X = irm.data.X.to_numpy()
    A = np.column_stack([np.ones(len(X)), X])
    e = irm.m_hat_
    residual_y = irm._y - ((1-e)*irm.g0_hat_ + e*irm.g1_hat_)
    # Solve residual loss directly, without dividing outcomes by D-e or
    # calling another sample_weight adapter.
    residual_design = A*(irm._d-e)[:, None]
    beta = np.linalg.lstsq(residual_design, residual_y, rcond=None)[0]
    query = np.array([[.2, -.7], [1.1, .4]])
    actual = RLearner().fit(irm).predict(query)
    np.testing.assert_allclose(actual, np.column_stack([np.ones(2), query])@beta, atol=1e-12)


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
def test_new_data_noiseless_oracle_recovery(learner):
    irm = support_irm()
    query = np.array([[-.9], [-.3], [.8]])
    np.testing.assert_allclose(learner().fit(irm).predict(query), .4+.2*query[:, 0], atol=1e-12)


class Capture(RegressorMixin, BaseEstimator):
    def __init__(self, fail=False, bad=None):
        self.fail = fail
        self.bad = bad

    def fit(self, X, y, sample_weight=None):
        if self.fail:
            raise RuntimeError('final fit failed')
        self.X_ = np.array(X, copy=True)
        self.y_ = np.array(y, copy=True)
        self.weights_ = None if sample_weight is None else sample_weight.copy()
        return self

    def predict(self, X):
        n = len(X)
        if self.bad == 'complex': return np.full(n, 2+0j)
        if self.bad == 'object_complex': return np.full(n, 2+0j, dtype=object)
        if self.bad == 'nan': return np.full(n, np.nan)
        if self.bad == 'inf': return np.full(n, np.inf)
        if self.bad == 'wide': return np.ones((n, 2))
        if self.bad == 'scalar': return 2.
        if self.bad == 'short': return np.ones(n+1)
        if self.bad == 'column': return np.full((n, 1), 2.)
        if self.bad == 'strings': return np.full(n, '2')
        return np.full(n, 2.)


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
@pytest.mark.parametrize('normalize', [False, True])
@pytest.mark.parametrize('score', ['ATE', 'ATTE'])
def test_source_score_and_ipw_normalization_do_not_change_conditional_target(learner, normalize, score):
    irm = support_irm(normalize_ipw=normalize)
    irm.estimate(score=score)
    result = learner(Capture()).fit(irm)
    template = result.ml_tau
    assert not hasattr(template, 'X_')
    assert result.n_training_samples_ == 200
    assert result.n_features_in_ == 1
    assert tuple(result.feature_names_in_) == ('x',)
    assert result.model_ is not template
    if learner is DRLearner:
        assert result.model_.weights_ is None
        assert result.model_.y_.mean() == pytest.approx(.4)
    else:
        np.testing.assert_allclose(result.model_.weights_, (irm._d-irm.m_hat_)**2)
    np.testing.assert_array_equal(result.nuisance_folds_, irm._full_sample_folds_)
    assert not np.shares_memory(result.nuisance_folds_, irm._full_sample_folds_)


class FoldSpy(RegressorMixin, BaseEstimator):
    calls = []

    def fit(self, X, y):
        self.ids_ = set(X[:, 1])
        self.value_ = float(np.mean(y))
        type(self).calls.append(('fit', set(self.ids_)))
        return self

    def predict(self, X):
        assert not (set(X[:, 1]) & self.ids_), 'Held-out nuisance row used in training'
        type(self).calls.append(('predict', set(X[:, 1])))
        return np.full(len(X), self.value_)


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
def test_fold_exclusion_no_nuisance_retraining_no_rng_draw(learner):
    FoldSpy.calls = []
    rng = np.random.default_rng(7)
    x = rng.normal(size=120)
    data = CausalData(df=pd.DataFrame(dict(x=x, row=np.arange(120), y=3+x, d=np.tile([0, 1], 60))),
                      outcome='y', treatment='d', confounders=['x', 'row'])
    irm = IRM(data, ml_g=FoldSpy(), ml_m=KnownPropensity(False), n_folds=3, random_state=11).fit()
    calls = list(FoldSpy.calls)
    assert len([c for c in calls if c[0] == 'fit']) == 6
    state = np.random.get_state()
    learner().fit(irm).predict([[.1, 124]])
    after = np.random.get_state()
    assert state[0] == after[0] and np.array_equal(state[1], after[1]) and state[2:] == after[2:]
    assert FoldSpy.calls == calls
    assert not hasattr(irm, '_uplift_g0_model_')


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
def test_predictor_owns_schema_and_survives_source_mutation_refit_and_config_change(learner):
    irm = noise_irm()
    fitted = learner().fit(irm)
    query = pd.DataFrame(dict(a=[.4, .1], b=[-.2, .9]))
    expected = fitted.predict(query)
    irm.g0_hat_[:] = 999
    irm.m_hat_[:] = .8
    irm.data.df['y'] += 10
    irm.data.df.rename(columns={'a': 'z'}, inplace=True)
    irm.data.confounders_names = ['z', 'b']
    irm.ml_g = DummyRegressor()
    irm.fit()
    fitted.set_params(ml_tau=DummyRegressor())
    np.testing.assert_array_equal(fitted.predict(query), expected)
    np.testing.assert_array_equal(fitted.predict(query[['b', 'a']].assign(extra='ignored')), expected)


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
def test_failed_refit_retains_old_predictor_and_success_replaces_it(learner):
    irm = support_irm()
    fitted = learner(Capture()).fit(irm)
    old = fitted.model_
    fitted.set_params(ml_tau=Capture(fail=True))
    with pytest.raises(RuntimeError, match='final fit failed'):
        fitted.fit(irm)
    assert fitted.model_ is old
    np.testing.assert_array_equal(fitted.predict([[1]]), [2])
    fitted.set_params(ml_tau=LinearRegression())
    fitted.fit(irm)
    assert fitted.model_ is not old
    np.testing.assert_allclose(fitted.predict([[1]]), [.6], atol=1e-12)


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
@pytest.mark.parametrize('change', ['y', 'X', 'index', 'roles'])
@pytest.mark.parametrize('diagnostics', [False, True])
def test_modified_source_sample_or_roles_reject_before_final_fit(learner, change, diagnostics):
    irm = support_irm(diagnostics=diagnostics)
    if change == 'y': irm.data.df['y'] += 1
    if change == 'X': irm.data.df['x'] += .1
    if change == 'index': irm.data.df.index = irm.data.df.index[::-1]
    if change == 'roles':
        irm.data.df['new_y'] = irm.data.df['y']
        irm.data.outcome_name = 'new_y'
    with pytest.raises(RuntimeError, match='data|roles'):
        learner(Capture(fail=True)).fit(irm)


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
@pytest.mark.parametrize('unsupported', ['repeated', 'cluster', 'external', 'drop', 'weights'])
def test_unsupported_fitted_context_rejects_before_final_fit(learner, unsupported):
    kwargs = {}
    if unsupported == 'repeated': kwargs['n_rep'] = 2
    if unsupported == 'cluster': kwargs['cluster_groups'] = np.repeat(np.arange(40), 5)
    if unsupported == 'drop': kwargs['overlap_policy'] = 'drop'
    if unsupported == 'weights': kwargs['weights'] = np.ones(200)
    irm = support_irm(**kwargs)
    if unsupported == 'external':
        predictions = {'g0': irm.g0_hat_.copy(), 'g1': irm.g1_hat_.copy(), 'm': irm.m_hat_.copy()}
        folds = irm._full_sample_folds_.copy()
        training = [[np.flatnonzero(folds != fold).tolist() for fold in range(3)]]
        manifest = irm.make_oof_manifest(predictions, folds=folds, training_indices=training, split_seeds=[18])
        irm.fit(external_predictions=predictions, oof_manifest=manifest)
    with pytest.raises(NotImplementedError): learner(Capture(fail=True)).fit(irm)


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
def test_guards_use_fit_configuration_even_when_constructor_parameters_change(learner):
    irm = support_irm()
    irm.set_params(n_rep=2, cluster_groups=np.zeros(200), weights=np.ones(200), overlap_policy='drop')
    np.testing.assert_allclose(learner().fit(irm).predict([[1]]), [.6], atol=1e-12)
    irm = support_irm(weights=np.ones(200))
    irm.weights = None
    with pytest.raises(NotImplementedError, match='weight'): learner().fit(irm)


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
@pytest.mark.parametrize('bad', ['complex', 'object_complex', 'nan', 'inf', 'wide', 'scalar', 'short'])
def test_final_prediction_validation(learner, bad):
    fitted = learner(Capture(bad=bad)).fit(support_irm())
    with pytest.raises((ValueError, RuntimeError)): fitted.predict([[0], [1]])


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
@pytest.mark.parametrize('output', ['column', 'strings', None])
def test_real_prediction_column_numeric_strings_and_no_binary_bounds(learner, output):
    fitted = learner(Capture(bad=output)).fit(noise_irm(binary=True))
    np.testing.assert_array_equal(fitted.predict([[0, 1], [1, 0]]), [2, 2])


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
@pytest.mark.parametrize('bad', [np.array([[1+0j]]), np.array([[1+0j]], dtype=object),
                                [[np.nan]], [[np.inf]], [[1, 2]], [1, 2], 1, [[[1]]]])
def test_scoring_rejects_invalid_reality_finiteness_or_geometry(learner, bad):
    fitted = learner().fit(support_irm())
    with pytest.raises((ValueError, RuntimeError)): fitted.predict(bad)


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
def test_scoring_schema_empty_and_single_row_contract(learner):
    fitted = learner().fit(noise_irm())
    with pytest.raises(ValueError, match='missing'): fitted.predict(pd.DataFrame(dict(a=[1])))
    with pytest.raises(ValueError, match='unique'): fitted.predict(pd.DataFrame([[1, 2, 3]], columns=['a', 'b', 'a']))
    assert fitted.predict(np.empty((0, 2))).shape == (0,)
    assert fitted.predict(pd.DataFrame(columns=['b', 'a'])).shape == (0,)
    np.testing.assert_array_equal(fitted.predict(['1', '2']), fitted.predict([[1., 2.]]))
    with pytest.raises(NotFittedError): learner().predict([[1]])
    with pytest.raises(TypeError, match='IRM'): learner().fit(np.zeros((3, 2)))
    with pytest.raises(NotFittedError): learner().fit(IRM())
    with pytest.raises(TypeError, match='regressor'): learner(LogisticRegression()).fit(support_irm())


class Unweighted(RegressorMixin, BaseEstimator):
    def fit(self, X, y): return self
    def predict(self, X): return np.zeros(len(X))


def test_r_requires_weighted_adapter_and_does_not_fallback():
    irm = support_irm()
    fitted = RLearner().fit(irm)
    old = fitted.model_
    fitted.set_params(ml_tau=Unweighted())
    with pytest.raises(TypeError, match='sample_weight'): fitted.fit(irm)
    assert fitted.model_ is old
    DRLearner(Unweighted()).fit(irm)


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
@pytest.mark.parametrize('bad', [0., 1., np.nan, np.inf, 1+0j])
def test_invalid_nuisance_propensity_rejects_before_final_fit(learner, bad):
    irm = support_irm()
    irm.m_hat_ = np.full(200, bad)
    with pytest.raises((ValueError, RuntimeError)): learner(Capture(fail=True)).fit(irm)


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
def test_nonfinite_pseudo_outcomes_reject_before_final_fit(learner):
    irm = support_irm()
    irm.g0_hat_ = np.full(200, np.finfo(float).max)
    irm.g1_hat_ = np.full(200, -np.finfo(float).max)
    with pytest.raises(RuntimeError, match='non-finite'): learner(Capture(fail=True)).fit(irm)


def test_r_residual_square_underflow_is_not_silent_row_removal():
    irm = support_irm()
    irm.m_hat_[:] = np.nextafter(0., 1.)
    # y-q also nonzero, so ratio overflows first. Both are rejected safely.
    with pytest.raises((ValueError, RuntimeError)): RLearner(Capture(fail=True)).fit(irm)


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
def test_custom_final_estimator_cannot_mutate_source_training_arrays(learner):
    class Mutating(Capture):
        def fit(self, X, y, sample_weight=None):
            X[:] = 987
            y[:] = 876
            return super().fit(X, y, sample_weight)
    irm = support_irm()
    original = irm.data.df.copy(deep=True)
    g = irm.g0_hat_.copy()
    learner(Mutating()).fit(irm)
    pd.testing.assert_frame_equal(irm.data.df, original)
    np.testing.assert_array_equal(irm.g0_hat_, g)


@pytest.mark.parametrize('diagnostics', [False, True])
def test_binary_dr_conditional_risk_difference_with_correct_propensity(diagnostics):
    irm = support_irm()
    frame = irm.data.df.copy()
    frame['y'] = 0.
    # Exact Bernoulli conditional probabilities: control .2/.4, treated .5/.7.
    for x, d, ones in [(-1, 0, 16), (-1, 1, 10), (1, 0, 16), (1, 1, 42)]:
        rows = frame.index[(frame.x == x) & (frame.d == d)][:ones]
        frame.loc[rows, 'y'] = 1.
    data = CausalData(df=frame, outcome='y', treatment='d', confounders=['x'])
    irm = IRM(data, ml_g=DummyRegressor(strategy='constant', constant=.4),
              ml_m=KnownPropensity(), n_folds=3, random_state=18,
              store_diagnostics=diagnostics).fit()
    np.testing.assert_allclose(DRLearner().fit(irm).predict([[-1], [1]]), [.3, .3], atol=1e-12)


def test_r_rejects_zero_weights_even_when_transformed_targets_are_finite():
    irm = support_irm()
    irm.m_hat_[:] = 1e-200
    # Exactly zero outcome residual, avoiding division overflow so the
    # residual-square underflow guard is exercised independently.
    irm.g0_hat_ = irm._y.copy()
    irm.g1_hat_ = irm._y.copy()
    with pytest.raises(ValueError, match='underflowed'): RLearner(Capture(fail=True)).fit(irm)


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
def test_no_feature_source_rejects_and_failed_validation_preserves_fitted_predictor(learner):
    source = support_irm()
    fitted = learner().fit(source)
    old = fitted.model_
    no_features = support_irm()
    no_features.data.confounders_names = []
    with pytest.raises(ValueError, match='confounder'): fitted.fit(no_features)
    assert fitted.model_ is old
    np.testing.assert_allclose(fitted.predict([[1]]), [.6], atol=1e-12)


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
def test_primary_irm_estimate_and_lazy_t_learner_remain_identical(learner):
    irm = noise_irm()
    before = irm.estimate().model_dump()
    query = irm.data.X.iloc[:5]
    t_before = irm.predict_cate(query)
    g0 = irm.g0_hat_.copy()
    learner().fit(irm).predict(query)
    assert irm.estimate().model_dump() == before
    np.testing.assert_array_equal(irm.g0_hat_, g0)
    np.testing.assert_array_equal(irm.predict_cate(query), t_before)


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
@pytest.mark.parametrize('column', ['x', 'y'])
@pytest.mark.parametrize('object_dtype', [False, True])
def test_complex_mutation_of_source_cannot_pass_via_lossy_irm_conversion(learner, column, object_dtype):
    irm = support_irm()
    values = irm.data.df[column].to_numpy().astype(complex)
    irm.data.df[column] = values.astype(object) if object_dtype else values
    with pytest.raises(ValueError, match='real'):
        learner().fit(irm)
