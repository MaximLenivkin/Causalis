"""Independent finite-support risks, held-out fit spies and ownership contracts."""
from dataclasses import FrozenInstanceError, asdict

import numpy as np
import pandas as pd
import pytest
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin, clone
from sklearn.dummy import DummyRegressor
from sklearn.exceptions import NotFittedError
from sklearn.linear_model import LinearRegression, LogisticRegression

from causalis.data_contracts import CausalData
from causalis.scenarios.unconfoundedness import IRM
from causalis.scenarios.uplift import DRLearner, RLearner, HeldOutCATEValidation, CATEValidationResult


class Propensity(ClassifierMixin, BaseEstimator):
    def __init__(self, correct=True):
        self.correct = correct

    def fit(self, X, y):
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X):
        e = .4+.2*X[:, 0] if self.correct else np.full(len(X), .5)
        return np.column_stack([1-e, e])


def support(offset=0, noise=False):
    x = np.repeat([-1., 1.], 100)
    d = np.r_[np.ones(20), np.zeros(80), np.ones(60), np.zeros(40)]
    y = 10+3*x+d*(.4+.2*x)
    if noise:
        y = y+np.tile([-1., 1.], 100)
    frame = pd.DataFrame(dict(x=x, y=y, d=d, uid=np.arange(200)+offset))
    return CausalData(df=frame, outcome='y', treatment='d', confounders=['x'], user_id='uid')


def source(diagnostics=True, correct_g=True, correct_e=True, **kwargs):
    return IRM(support(), ml_g=LinearRegression() if correct_g else DummyRegressor(strategy='constant', constant=5),
               ml_m=Propensity(correct_e), n_folds=3, random_state=18,
               store_diagnostics=diagnostics, **kwargs).fit()


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
@pytest.mark.parametrize('diagnostics', [False, True])
@pytest.mark.parametrize('noise', [False, True])
def test_independent_support_oracle_metrics(learner, diagnostics, noise):
    val = HeldOutCATEValidation(learner()).fit(source(diagnostics))
    result = val.evaluate(support(1000, noise))
    assert isinstance(result, CATEValidationResult)
    assert (result.n, result.n_control, result.n_treated) == (200, 120, 80)
    assert result.mean_cate == pytest.approx(.4)
    assert result.mean_dr_signal == pytest.approx(.4)
    assert result.dr_gain_vs_zero == pytest.approx(.2)
    assert result.dr_loss == pytest.approx((1/.16+1/.24)/2 if noise else 0, abs=1e-24 if not noise else 1e-12)
    assert result.r_loss == pytest.approx(float(noise), abs=1e-12)
    assert result.outcome_mse_control == pytest.approx(float(noise), abs=1e-12)
    assert result.outcome_mse_treated == pytest.approx(float(noise), abs=1e-12)
    assert result.propensity_brier == pytest.approx(.2)
    entropy = -(.2*np.log(.2)+.8*np.log(.8)+.6*np.log(.6)+.4*np.log(.4))/2
    assert result.propensity_log_loss == pytest.approx(entropy)
    assert (result.propensity_min, result.propensity_max, result.n_propensity_clipped) == (.2, .6000000000000001, 0)
    with pytest.raises(FrozenInstanceError):
        result.n = 0
    assert all(np.isfinite(v) for v in asdict(result).values())


@pytest.mark.parametrize('correct_g,correct_e', [(True, True), (False, True), (True, False)])
def test_dr_gain_equals_true_risk_reduction_with_either_correct_pilot(correct_g, correct_e):
    irm = source(correct_g=correct_g, correct_e=correct_e)
    true = HeldOutCATEValidation().fit(irm).evaluate(support(1000, noise=True))
    constant = HeldOutCATEValidation(DRLearner(DummyRegressor(strategy='constant', constant=.4))).fit(irm).evaluate(support(1000, noise=True))
    # Known true effects .2/.6: MSE(constant)=.04, MSE(true)=0.
    # Shared pseudo-outcome noise cancels in risk differences.
    assert true.dr_gain_vs_zero == pytest.approx(.2)
    assert constant.dr_gain_vs_zero == pytest.approx(.16)
    assert constant.dr_loss-true.dr_loss == pytest.approx(.04)
    assert true.dr_loss > 0  # Absolute proxy loss is not measured CATE MSE.


def test_both_wrong_pilots_do_not_certify_true_risk():
    val = HeldOutCATEValidation(DRLearner(DummyRegressor(strategy='constant', constant=.4))).fit(source(correct_g=False, correct_e=False))
    result = val.evaluate(support(1000))
    assert result.dr_gain_vs_zero != pytest.approx(.16)


class FitSpy(RegressorMixin, BaseEstimator):
    events = []

    def __init__(self, fail=False, mutate=False):
        self.fail = fail
        self.mutate = mutate

    def fit(self, X, y, sample_weight=None):
        type(self).events.append(('fit', X.copy(), y.copy()))
        if self.fail:
            raise RuntimeError('owned model failed')
        self.model_ = LinearRegression().fit(X, y, sample_weight=sample_weight)
        if self.mutate:
            X[:] = 700
            y[:] = 700
        return self

    def predict(self, X):
        type(self).events.append(('predict', X.copy()))
        result = self.model_.predict(X)
        if self.mutate:
            X[:] = 800
        return result


class PropensitySpy(ClassifierMixin, BaseEstimator):
    events = []

    def fit(self, X, y):
        type(self).events.append(('fit', X.copy()))
        self.model_ = LogisticRegression().fit(X, y)
        self.classes_ = self.model_.classes_
        return self

    def predict_proba(self, X):
        type(self).events.append(('predict', X.copy()))
        return self.model_.predict_proba(X)


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
def test_all_owned_training_excludes_validation_and_evaluate_never_fits(learner):
    irm = source()
    irm.ml_g = FitSpy()
    irm.ml_m = PropensitySpy()
    val = HeldOutCATEValidation(learner(FitSpy())).fit(irm)
    held = support(1000)
    held.df['x'] *= .9  # Make held-out features distinguishable from training.
    held_before = held.df.copy(deep=True)
    FitSpy.events.clear()
    PropensitySpy.events.clear()
    result = val.evaluate(held)
    assert result.n == 200
    assert len(FitSpy.events) == 3
    assert all(event[0] == 'predict' for event in FitSpy.events)
    assert [event[0] for event in PropensitySpy.events] == ['predict']
    pd.testing.assert_frame_equal(held.df, held_before)
    # Arm pilots are full-training refits, not the discarded cross-fit models.
    FitSpy.events.clear()
    val.fit(irm)
    events = FitSpy.events
    assert [event[0] for event in events] == ['fit', 'fit', 'fit']
    assert [len(event[1]) for event in events] == [200, 120, 80]
    assert all(set(event[1][:, 0]) == {-1., 1.} for event in events)
    assert not hasattr(irm, '_uplift_g0_model_')


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
def test_owned_fit_and_predict_arrays_preserve_source_and_validation(learner):
    irm = source()
    original = irm.data.df.copy(deep=True)
    irm.ml_g = FitSpy(mutate=True)
    val = HeldOutCATEValidation(learner(FitSpy(mutate=True))).fit(irm)
    pd.testing.assert_frame_equal(irm.data.df, original)
    held = support(1000)
    before = held.df.copy(deep=True)
    val.evaluate(held)
    pd.testing.assert_frame_equal(held.df, before)


def test_template_cloning_snapshot_and_failed_refit_retention():
    irm = source()
    template = DRLearner(FitSpy())
    val = HeldOutCATEValidation(template).fit(irm)
    held = support(1000)
    expected = val.evaluate(held)
    assert not hasattr(template, 'model_')
    assert not hasattr(irm.ml_g, 'coef_')
    assert not hasattr(irm.ml_m, 'classes_')
    irm.data.df['y'] += 10
    irm.fit()
    irm.overlap_threshold = .49
    irm.ml_g = FitSpy(fail=True)
    with pytest.raises(RuntimeError, match='owned model failed'):
        val.fit(irm)
    assert val.evaluate(held) == expected
    irm.ml_g = LinearRegression()
    val.fit(irm)
    assert val.evaluate(held).outcome_mse_control > 90
    assert val._threshold_ == .01  # Actual fit-time overlap setting.
    assert isinstance(clone(val), HeldOutCATEValidation)
    assert not hasattr(clone(val), 'learner_')


@pytest.mark.parametrize('offset', [0, 199])
def test_overlapping_identities_reject_before_predictions(offset):
    val = HeldOutCATEValidation(DRLearner(FitSpy())).fit(source())
    FitSpy.events.clear()
    with pytest.raises(ValueError, match='overlap'):
        val.evaluate(support(offset))
    assert not FitSpy.events


def test_restarted_dataframe_index_is_allowed_but_relabelled_identities_are_caller_responsibility():
    val = HeldOutCATEValidation().fit(source())
    # Both tables have RangeIndex(200), but stable identities differ.
    assert val.evaluate(support(1000)).n == 200


@pytest.mark.parametrize('which', ['source', 'validation'])
@pytest.mark.parametrize('bad', ['missing', 'duplicate', 'null'])
def test_stable_unique_nonmissing_identity_contract(which, bad):
    irm = source()
    held = support(1000)
    data = irm.data if which == 'source' else held
    if bad == 'missing':
        data.user_id_name = None
    elif bad == 'duplicate':
        data.df.loc[1, 'uid'] = data.df.loc[0, 'uid']
    else:
        data.df['uid'] = data.df['uid'].astype(float)
        data.df.loc[0, 'uid'] = np.nan
    with pytest.raises((ValueError, RuntimeError)):
        if which == 'source':
            if bad == 'missing':
                # Genuine source without IDs, not changed fit roles.
                irm = IRM(CausalData(df=support().df.drop(columns='uid'), outcome='y', treatment='d', confounders=['x']),
                          ml_g=LinearRegression(), ml_m=Propensity(), n_folds=3).fit()
            HeldOutCATEValidation().fit(irm)
        else:
            HeldOutCATEValidation().fit(irm).evaluate(held)


@pytest.mark.parametrize('field', ['x', 'y', 'd'])
@pytest.mark.parametrize('bad', ['complex', 'object_complex', 'nan', 'inf'])
def test_validation_raw_reality_and_finiteness(field, bad):
    held = support(1000)
    if bad in ('complex', 'object_complex'):
        held.df[field] = held.df[field].astype(complex if bad == 'complex' else object)
        held.df.loc[0, field] = 1+0j
    else:
        held.df[field] = held.df[field].astype(float)
        held.df.loc[0, field] = np.nan if bad == 'nan' else np.inf
    with pytest.raises((ValueError, RuntimeError), match='real|finite'):
        HeldOutCATEValidation().fit(source()).evaluate(held)


@pytest.mark.parametrize('change', ['outcome_role', 'treatment_role', 'id_role', 'features', 'duplicate_columns', 'empty', 'constant_d', 'nonbinary_d'])
def test_schema_and_sample_validation(change):
    held = support(1000)
    if change == 'outcome_role': held.outcome_name = 'wrong'
    elif change == 'treatment_role': held.treatment_name = 'wrong'
    elif change == 'id_role': held.user_id_name = 'wrong'
    elif change == 'features': held.confounders_names = ['other']
    elif change == 'duplicate_columns': held.df.columns = ['x', 'x', 'd', 'uid']
    elif change == 'empty': held.df = held.df.iloc[:0]
    elif change == 'constant_d': held.df['d'] = 1
    elif change == 'nonbinary_d': held.df.loc[0, 'd'] = 2
    with pytest.raises(ValueError):
        HeldOutCATEValidation().fit(source()).evaluate(held)


class BadPredict:
    def __init__(self, bad):
        self.bad = bad

    def predict(self, X):
        if self.bad == 'wide': return np.ones((len(X), 2))
        if self.bad == 'short': return np.ones(len(X)-1)
        if self.bad == 'scalar': return .5
        if self.bad == 'complex': return np.full(len(X), .5+0j)
        if self.bad == 'object_complex': return np.full(len(X), .5+0j, dtype=object)
        if self.bad == 'nan': return np.full(len(X), np.nan)
        if self.bad == 'inf': return np.full(len(X), np.inf)
        return np.full(len(X), float(self.bad))


@pytest.mark.parametrize('stage', ['g0', 'g1', 'propensity', 'effect'])
@pytest.mark.parametrize('bad', ['wide', 'short', 'scalar', 'complex', 'object_complex', 'nan', 'inf'])
def test_invalid_owned_model_predictions_reject(stage, bad):
    val = HeldOutCATEValidation().fit(source())
    if stage.startswith('g'):
        models = list(val.outcome_models_)
        models[int(stage[-1])] = BadPredict(bad)
        val.outcome_models_ = tuple(models)
    elif stage == 'propensity': val.propensity_model_ = BadPredict(bad)
    else: val.learner_.model_ = BadPredict(bad)
    with pytest.raises((ValueError, RuntimeError)):
        val.evaluate(support(1000))


@pytest.mark.parametrize('probability', [-.1, 1.1])
def test_out_of_range_propensities_reject_without_repair(probability):
    val = HeldOutCATEValidation().fit(source())
    val.propensity_model_ = BadPredict(probability)
    with pytest.raises(ValueError, match=r'\[0, 1\]'):
        val.evaluate(support(1000))


@pytest.mark.parametrize('probability', [0., 1.])
def test_boundary_propensity_clipping_and_raw_metrics(probability):
    val = HeldOutCATEValidation().fit(source())
    val.propensity_model_ = BadPredict(probability)
    result = val.evaluate(support(1000))
    assert result.n_propensity_clipped == 200
    assert result.propensity_min == result.propensity_max == probability
    assert result.propensity_brier == pytest.approx(.4 if probability == 0 else .6)
    assert np.isfinite(result.propensity_log_loss)
    val._threshold_ = 0
    with pytest.raises(ValueError, match='strictly inside'):
        val.evaluate(support(1000))


@pytest.mark.parametrize('field', ['y', 'g0', 'effect'])
def test_overflow_is_not_a_successful_report(field):
    val = HeldOutCATEValidation().fit(source())
    held = support(1000)
    if field == 'y': held.df['y'] = 1e308
    elif field == 'g0': val.outcome_models_ = (BadPredict(1e308), val.outcome_models_[1])
    else: val.learner_.model_ = BadPredict(1e308)
    with pytest.raises(RuntimeError, match='arithmetic'):
        val.evaluate(held)


def test_wrong_types_and_unfitted_contracts():
    with pytest.raises(NotFittedError): HeldOutCATEValidation().evaluate(support(1000))
    with pytest.raises(TypeError): HeldOutCATEValidation().fit(object())
    with pytest.raises(TypeError): HeldOutCATEValidation(LinearRegression()).fit(source())
    with pytest.raises(NotFittedError): HeldOutCATEValidation().fit(IRM(support(), ml_g=LinearRegression(), ml_m=Propensity()))
    with pytest.raises(TypeError): HeldOutCATEValidation().fit(source()).evaluate(pd.DataFrame())


@pytest.mark.parametrize('context', ['repeated', 'cluster', 'drop', 'weighted'])
def test_unsupported_source_contexts_reject(context):
    kwargs = dict(n_rep=2) if context == 'repeated' else dict(cluster_groups=np.repeat(np.arange(20), 10)) if context == 'cluster' else dict(overlap_policy='drop') if context == 'drop' else dict(weights=np.ones(200))
    with pytest.raises(NotImplementedError):
        HeldOutCATEValidation().fit(source(**kwargs))


def binary_sample(offset=0):
    rng = np.random.default_rng(56+offset)
    x = rng.normal(size=240)
    d = rng.binomial(1, .5, 240)
    y = rng.binomial(1, 1/(1+np.exp(-(.3*x+.4*d))))
    return CausalData(df=pd.DataFrame(dict(x=x, y=y, d=d, uid=np.arange(240)+offset)),
                      outcome='y', treatment='d', confounders=['x'], user_id='uid')


@pytest.mark.parametrize('learner', [DRLearner, RLearner])
def test_real_binary_classifier_pipeline_and_factual_metrics(learner):
    irm = IRM(binary_sample(), ml_g=LogisticRegression(), ml_m=LogisticRegression(), n_folds=3, random_state=8).fit()
    val = HeldOutCATEValidation(learner()).fit(irm)
    held = binary_sample(1000)
    result = val.evaluate(held)
    X = held.X.to_numpy()
    d = held.treatment.to_numpy()
    y = held.outcome.to_numpy()
    # Production classifier adapter agrees with independent sklearn scorers.
    from sklearn.metrics import mean_squared_error, brier_score_loss, log_loss
    for arm in (0, 1):
        model = LogisticRegression().fit(irm.data.X.to_numpy()[irm._d == arm], irm._y[irm._d == arm])
        predicted = model.predict_proba(X[d == arm])[:, 1]
        actual = result.outcome_mse_control if arm == 0 else result.outcome_mse_treated
        assert actual == pytest.approx(mean_squared_error(y[d == arm], predicted))
    e = val.propensity_model_.predict_proba(X)[:, 1]
    assert result.propensity_brier == pytest.approx(brier_score_loss(d, e))
    assert result.propensity_log_loss == pytest.approx(log_loss(d, e))
    held.df['y'] = 0
    assert np.isfinite(val.evaluate(held).dr_loss)
    held.df['y'] = held.df['y'].astype(float)
    held.df.loc[0, 'y'] = .2
    with pytest.raises(ValueError, match='binary validation'):
        val.evaluate(held)
    held.df['y'] = 0
    val.outcome_models_ = (BadPredict(1.1), val.outcome_models_[1])
    with pytest.raises(ValueError, match='Binary outcome predictions'):
        val.evaluate(held)


def test_single_class_training_arm_is_a_constant_pilot():
    data = binary_sample()
    data.df.loc[data.df.d == 0, 'y'] = 0
    irm = IRM(data, ml_g=LogisticRegression(), ml_m=LogisticRegression(), n_folds=3, random_state=8).fit()
    val = HeldOutCATEValidation().fit(irm)
    result = val.evaluate(binary_sample(1000))
    assert np.isfinite(result.dr_loss)
    np.testing.assert_array_equal(val.outcome_models_[0].predict([[0], [1]]), [0, 0])


def test_actual_external_oof_source_rejects_before_owned_training():
    irm = source()
    predictions = {'g0': irm.g0_hat_.copy(), 'g1': irm.g1_hat_.copy(), 'm': irm.m_hat_.copy()}
    folds = irm._full_sample_folds_.copy()
    training = [[np.flatnonzero(folds != fold).tolist() for fold in range(3)]]
    manifest = irm.make_oof_manifest(predictions, folds=folds, training_indices=training, split_seeds=[18])
    irm.fit(external_predictions=predictions, oof_manifest=manifest)
    FitSpy.events.clear()
    with pytest.raises(NotImplementedError, match='external'):
        HeldOutCATEValidation(DRLearner(FitSpy())).fit(irm)
    assert not FitSpy.events


@pytest.mark.parametrize('change', ['y', 'X', 'index', 'roles'])
@pytest.mark.parametrize('diagnostics', [False, True])
def test_changed_source_sample_rejects_before_callbacks(change, diagnostics):
    irm = source(diagnostics)
    if change == 'y': irm.data.df['y'] += 1
    elif change == 'X': irm.data.df['x'] += .1
    elif change == 'index': irm.data.df.index = irm.data.df.index[::-1]
    else: irm.data.confounders_names = []
    FitSpy.events.clear()
    with pytest.raises((ValueError, RuntimeError)):
        HeldOutCATEValidation(DRLearner(FitSpy())).fit(irm)
    assert not FitSpy.events


def test_scalar_estimate_and_existing_t_cache_are_unchanged():
    irm = source()
    before = irm.estimate()
    t = irm.predict_cate(pd.DataFrame({'x': [-.5, .5]}))
    cache = irm._uplift_g0_model_, irm._uplift_g1_model_
    HeldOutCATEValidation().fit(irm).evaluate(support(1000))
    after = irm.estimate()
    assert before.value == after.value
    assert before.ci_lower_absolute == after.ci_lower_absolute
    assert before.ci_upper_absolute == after.ci_upper_absolute
    assert cache == (irm._uplift_g0_model_, irm._uplift_g1_model_)
    np.testing.assert_array_equal(t, irm.predict_cate(pd.DataFrame({'x': [-.5, .5]})))


def test_validation_label_changes_never_change_fitted_predictions_or_global_rng():
    val = HeldOutCATEValidation().fit(source())
    held = support(1000)
    old_predictions = val.learner_.predict(held.X)
    np.random.seed(731)
    rng_before = np.random.get_state()
    before = val.evaluate(held)
    held.df['y'] += 3
    after = val.evaluate(held)
    rng_after = np.random.get_state()
    assert rng_before[0] == rng_after[0]
    np.testing.assert_array_equal(rng_before[1], rng_after[1])
    assert rng_before[2:] == rng_after[2:]
    assert after.mean_cate == before.mean_cate
    assert after.dr_loss != before.dr_loss
    np.testing.assert_array_equal(old_predictions, val.learner_.predict(held.X))


def test_nested_outer_refits_exclude_outer_validation_from_every_training_call():
    from sklearn.model_selection import KFold
    from sklearn.preprocessing import StandardScaler
    rng = np.random.default_rng(907)
    n = 180
    frame = pd.DataFrame(dict(x=rng.normal(size=n), marker=np.arange(n)/1000,
                              d=rng.binomial(1, .5, n), uid=np.arange(n)+3000))
    frame['y'] = 1+frame.x+frame.d*(.5+.1*frame.x)+rng.normal(size=n)
    full = CausalData(df=frame, outcome='y', treatment='d', confounders=['x', 'marker'], user_id='uid')
    for train, held in KFold(3, shuffle=True, random_state=25).split(frame):
        scaler = StandardScaler().fit(full.df.iloc[train][['x', 'marker']])
        train_frame, held_frame = full.df.iloc[train].copy(), full.df.iloc[held].copy()
        train_frame[['x', 'marker']] = scaler.transform(train_frame[['x', 'marker']])
        held_frame[['x', 'marker']] = scaler.transform(held_frame[['x', 'marker']])
        training = CausalData(df=train_frame, outcome='y', treatment='d', confounders=['x', 'marker'], user_id='uid')
        validation = CausalData(df=held_frame, outcome='y', treatment='d', confounders=['marker', 'x'], user_id='uid')
        FitSpy.events.clear()
        PropensitySpy.events.clear()
        irm = IRM(training, ml_g=FitSpy(), ml_m=PropensitySpy(), n_folds=3, random_state=16).fit()
        val = HeldOutCATEValidation(DRLearner(FitSpy())).fit(irm)
        fits = [event for event in FitSpy.events if event[0] == 'fit']
        assert len(fits) == 9  # Six fold arm fits + final effect + two evaluation arms.
        propensity_fits = [event for event in PropensitySpy.events if event[0] == 'fit']
        assert len(propensity_fits) == 4
        for event in fits+propensity_fits:
            assert not set(event[1][:, 1]) & set(held_frame.marker)
            assert set(event[1][:, 1]) <= set(train_frame.marker)
        FitSpy.events.clear()
        PropensitySpy.events.clear()
        original = val.evaluate(validation)
        assert all(event[0] == 'predict' for event in FitSpy.events)
        assert [event[0] for event in PropensitySpy.events] == ['predict']
        # Feature names, not validation's confounder order, determine predictions.
        validation.confounders_names = ['x', 'marker']
        assert val.evaluate(validation) == original


def test_r_loss_excess_is_overlap_weighted_true_risk_on_independent_support():
    irm = source()
    true = HeldOutCATEValidation(RLearner()).fit(irm).evaluate(support(1000))
    constant = HeldOutCATEValidation(RLearner(DummyRegressor(strategy='constant', constant=.4))).fit(irm).evaluate(support(1000))
    # Conditional error squared .04 at both x; overlap variances .16/.24.
    assert constant.r_loss-true.r_loss == pytest.approx((.16*.04+.24*.04)/2)
    assert constant.dr_loss-true.dr_loss == pytest.approx(.04)
