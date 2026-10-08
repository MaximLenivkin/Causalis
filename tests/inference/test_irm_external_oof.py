"""Synthetic external predictions, declared leakage and fit ownership contracts."""
from copy import deepcopy
import json

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import StratifiedKFold, KFold

from causalis.data_contracts import CausalData
from causalis.scenarios.unconfoundedness import IRM
from causalis.scenarios.gate.model import estimate_gate_from_irm, estimate_gatet_from_irm
from causalis.scenarios.uplift.model import predict_cate


class Bomb:
    def fit(self, *args, **kwargs):
        raise AssertionError('External fit must not fit a learner')

    def predict(self, *args, **kwargs):
        raise AssertionError('External fit must not predict with a learner')

    def get_params(self, *args, **kwargs):
        raise AssertionError('External fit must not inspect a learner')

    def set_params(self, *args, **kwargs):
        raise AssertionError('External fit must not configure a learner')


def fixture(repetitions=1, cluster=False, binary=False, duplicate=False):
    rng = np.random.default_rng(43)
    groups = np.repeat(np.arange(30), 8)
    x = rng.normal(size=len(groups))
    d = np.tile([0, 1], len(groups)//2)
    y = rng.binomial(1, .65, len(x)) if binary else 10 + .7*d + .4*x + rng.normal(size=len(x))
    index = np.repeat(np.arange(len(x)//2), 2) if duplicate else np.arange(len(x)) + 100
    data = CausalData(df=pd.DataFrame(dict(x=x, d=d, y=y), index=index),
                      outcome='y', treatment='d', confounders=['x'])
    model = IRM(data, ml_g=Bomb(), ml_m=Bomb(), n_folds=3, n_rep=repetitions,
                random_state=None, cluster_groups=groups if cluster else None)
    predictions = {name: [] for name in ('g0', 'g1', 'm')}
    fold_columns, training = [], []
    seeds = [17 + rep for rep in range(repetitions)]
    for seed in seeds:
        if cluster:
            partition = []
            for _, held in KFold(3, shuffle=True, random_state=seed).split(np.arange(30)):
                mask = np.isin(groups, held)
                partition.append((np.flatnonzero(~mask), np.flatnonzero(mask)))
        else:
            partition = list(StratifiedKFold(3, shuffle=True, random_state=seed).split(x[:, None], d))
        arrays = {name: np.empty(len(x)) for name in predictions}
        folds = np.empty(len(x), dtype=int)
        for fold, (train, test) in enumerate(partition):
            folds[test] = fold
            for arm, name in ((0, 'g0'), (1, 'g1')):
                subset = train[d[train] == arm]
                learner = LogisticRegression() if binary else LinearRegression()
                learner.fit(x[subset, None], y[subset])
                arrays[name][test] = (learner.predict_proba(x[test, None])[:, 1] if binary
                                      else learner.predict(x[test, None]))
            learner = LogisticRegression().fit(x[train, None], d[train])
            arrays['m'][test] = learner.predict_proba(x[test, None])[:, 1]
        for name in predictions:
            predictions[name].append(arrays[name])
        fold_columns.append(folds)
        training.append([train.tolist() for train, _ in partition])
    predictions = {name: values[0] if repetitions == 1 else np.column_stack(values)
                   for name, values in predictions.items()}
    folds = fold_columns[0] if repetitions == 1 else np.column_stack(fold_columns)
    manifest = model.make_oof_manifest(predictions, folds=folds,
                                      training_indices=training, split_seeds=seeds)
    return model, predictions, manifest, groups


@pytest.mark.parametrize('score', ['ATE', 'ATTE'])
@pytest.mark.parametrize('normalize', [False, True])
@pytest.mark.parametrize('cluster', [False, True])
@pytest.mark.parametrize('binary', [False, True])
@pytest.mark.parametrize('store', [False, True])
def test_external_absolute_relative_independent_oracle(score, normalize, cluster, binary, store):
    model, predictions, manifest, groups = fixture(cluster=cluster, binary=binary)
    model.normalize_ipw = normalize
    model.fit(external_predictions=predictions, oof_manifest=manifest, store_diagnostics=store)
    result = model.estimate(score=score, alpha=.1)
    y, d = model._y, model._d
    g0, g1, m = (predictions[name] for name in ('g0', 'g1', 'm'))
    if score == 'ATE':
        h1, h0 = d/m, (1-d)/(1-m)
        if normalize:
            h1, h0 = h1/h1.mean(), h0/h0.mean()
        signal = g1-g0 + h1*(y-g1)-h0*(y-g0)
        theta = signal.mean()
        influence = signal-theta
        baseline_signal = g0+h0*(y-g0)
        baseline = baseline_signal.mean()
        baseline_if = baseline_signal-baseline
    else:
        w = d/d.mean()
        signal = w*(y-g0)-(1-d)*m/(1-m)/d.mean()*(y-g0)
        theta = signal.mean()
        influence = signal-w*theta
        baseline_signal = w*g0+(1-d)*m/(1-m)/d.mean()*(y-g0)
        baseline = baseline_signal.mean()
        baseline_if = baseline_signal-w*baseline
    def error(values):
        if not cluster:
            return np.std(values, ddof=1)/np.sqrt(len(values))
        centered = values-values.mean()
        totals = [sum(centered[groups == group]) for group in np.unique(groups)]
        return np.sqrt(30/29*sum(value**2 for value in totals))/len(values)
    se = error(influence)
    relative_se = error(100*(influence/baseline-theta*baseline_if/baseline**2))
    z = norm.ppf(.95)
    np.testing.assert_allclose([result.value, model.se[0], result.p_value,
                               result.ci_lower_absolute, result.ci_upper_absolute],
                              [theta, se, 2*norm.sf(abs(theta/se)), theta-z*se, theta+z*se], rtol=1e-12, atol=2e-16)
    np.testing.assert_allclose([result.value_relative, model.se_relative_[0],
                               result.ci_lower_relative, result.ci_upper_relative],
                              [100*theta/baseline, relative_se,
                               100*theta/baseline-z*relative_se, 100*theta/baseline+z*relative_se], rtol=1e-12)
    assert result.model_options['nuisance_source'] == 'external_oof'
    assert result.model_options['oof_split_seed'] == 17
    assert model.feature_importance_ is None
    assert (result.diagnostic_data is not None) == store
    assert model.folds_ is None if not store else np.array_equal(model.folds_, manifest['folds'])
    if cluster:
        assert result.model_options['cluster_split'] == 'external_manifest'


@pytest.mark.parametrize('repetitions', [1, 2, 3, 4])
@pytest.mark.parametrize('cluster', [False, True])
@pytest.mark.parametrize('score', ['ATE', 'ATTE'])
def test_internal_external_replay_and_repeated_aggregation(repetitions, cluster, score):
    supplied, predictions, manifest, _ = fixture(repetitions, cluster)
    params = supplied.get_params(deep=False)
    internal = IRM(**dict(params, ml_g=LinearRegression(), ml_m=LogisticRegression(), random_state=17)).fit()
    children = internal._fit_repetitions_ if repetitions > 1 else [internal]
    predictions = {name: children[0].__dict__[attr].copy() if repetitions == 1 else
                   np.column_stack([child.__dict__[attr] for child in children])
                   for name, attr in [('g0', 'g0_hat_'), ('g1', 'g1_hat_'), ('m', 'm_hat_')]}
    folds = children[0].folds_.copy() if repetitions == 1 else internal.folds_repetitions_.copy()
    training = [[np.flatnonzero(child.folds_ != fold).tolist() for fold in range(3)] for child in children]
    seeds = list(internal.repetition_seeds_) if repetitions > 1 else [17]
    manifest = supplied.make_oof_manifest(predictions, folds=folds, training_indices=training, split_seeds=seeds)
    external = supplied.fit(external_predictions=predictions, oof_manifest=manifest).estimate(score=score)
    original = internal.estimate(score=score)
    for name in ['value', 'p_value', 'value_relative', 'ci_lower_absolute', 'ci_upper_absolute',
                 'ci_lower_relative', 'ci_upper_relative']:
        np.testing.assert_array_equal(getattr(external, name), getattr(original, name))
    np.testing.assert_array_equal(supplied.se, internal.se)
    np.testing.assert_array_equal(supplied.se_relative_, internal.se_relative_)
    if repetitions > 1:
        assert external.repetition_seeds == seeds
        assert 'oof_split_seed' not in external.model_options
        assert external.diagnostic_data is None
        effects = np.array([result.value for result in external.repetition_estimates])
        errors = np.array([result.model_options['std_error'] for result in external.repetition_estimates])
        assert external.value == np.median(effects)
        np.testing.assert_allclose(supplied.se[0], np.sqrt(np.median(errors**2+(effects-external.value)**2)))


@pytest.mark.parametrize('repetitions', [1, 3])
@pytest.mark.parametrize('cluster', [False, True])
def test_owned_input_manifest_json_and_rng(repetitions, cluster):
    model, predictions, manifest, _ = fixture(repetitions, cluster)
    state = np.random.get_state()
    portable = json.loads(json.dumps(manifest))
    model.fit(external_predictions=predictions, oof_manifest=portable, store_diagnostics=False)
    result = model.estimate()
    expected = result.value, model.se[0]
    for array in predictions.values():
        array[:] = 0
    portable['folds'][0] = 99
    portable['training_indices'][0][0][:] = [0]
    portable['sample']['n_obs'] = 1
    portable['split_seeds'][0] = 99
    model.data.df.loc[:, 'y'] = -100
    if cluster:
        model.cluster_groups[:] = 0
    again = model.estimate()
    np.testing.assert_array_equal([again.value, model.se[0]], expected)
    now = np.random.get_state()
    assert state[0] == now[0] and state[2:] == now[2:]
    np.testing.assert_array_equal(state[1], now[1])


@pytest.mark.parametrize('duplicate', [False, True])
@pytest.mark.parametrize('repetitions', [1, 3])
def test_pandas_exact_order_and_detached_factory(duplicate, repetitions):
    model, predictions, manifest, _ = fixture(repetitions, duplicate=duplicate)
    pandas_predictions = {name: (pd.Series(value, index=model.data.df.index) if repetitions == 1 else
                                pd.DataFrame(value, index=model.data.df.index)) for name, value in predictions.items()}
    model.fit(external_predictions=pandas_predictions, oof_manifest=manifest)
    bad = dict(pandas_predictions)
    bad['g0'] = bad['g0'].iloc[::-1]
    with pytest.raises(ValueError, match='index'):
        model.fit(external_predictions=bad, oof_manifest=manifest)


@pytest.mark.parametrize('change', ['missing', 'unknown', 'version', 'roles', 'sample', 'hash', 'n_rep',
                                   'fold_float', 'fold_bool', 'fold_negative', 'fold_missing', 'fold_shape',
                                   'train_duplicate', 'train_leak', 'train_float', 'train_missing',
                                   'seed_bool', 'seed_float', 'seed_negative', 'seed_large', 'seed_missing'])
def test_manifest_rejections_preserve_previous_fit(change):
    model, predictions, manifest, _ = fixture()
    model.fit(external_predictions=predictions, oof_manifest=manifest)
    value = model.estimate().value
    bad = deepcopy(manifest)
    if change == 'missing': del bad['sample']
    elif change == 'unknown': bad['mystery'] = 1
    elif change == 'version': bad['schema_version'] = True
    elif change == 'roles': bad['roles']['outcome'] = 'wrong'
    elif change == 'sample': bad['sample']['y_hash'] = 'wrong'
    elif change == 'hash': bad['prediction_hashes']['g0'] = 'wrong'
    elif change == 'n_rep': bad['n_rep'] = 2
    elif change == 'fold_float': bad['folds'] = np.array(bad['folds'], dtype=float)
    elif change == 'fold_bool': bad['folds'] = np.array(bad['folds'], dtype=bool)
    elif change == 'fold_negative': bad['folds'][0] = -1
    elif change == 'fold_missing': bad['folds'] = [0] * len(bad['folds'])
    elif change == 'fold_shape': bad['folds'] = [bad['folds']]
    elif change == 'train_duplicate': bad['training_indices'][0][0][0] = bad['training_indices'][0][0][1]
    elif change == 'train_leak': bad['training_indices'][0][0][0] = bad['folds'].index(0)
    elif change == 'train_float': bad['training_indices'][0][0] = np.array(bad['training_indices'][0][0], dtype=float)
    elif change == 'train_missing': bad['training_indices'] = []
    elif change == 'seed_bool': bad['split_seeds'] = [True]
    elif change == 'seed_float': bad['split_seeds'] = [17.0]
    elif change == 'seed_negative': bad['split_seeds'] = [-1]
    elif change == 'seed_large': bad['split_seeds'] = [2**32]
    elif change == 'seed_missing': bad['split_seeds'] = []
    with pytest.raises(ValueError):
        model.fit(external_predictions=predictions, oof_manifest=bad)
    assert model.estimate().value == value


@pytest.mark.parametrize('change', ['missing', 'extra', 'scalar', 'column', 'row', 'wrong_n', 'complex',
                                   'object_complex', 'nan', 'infinity', 'm_low', 'm_high'])
def test_prediction_validation_before_clipping(change):
    model, predictions, manifest, _ = fixture()
    if change == 'missing': del predictions['g1']
    elif change == 'extra': predictions['extra'] = predictions['g0']
    elif change == 'scalar': predictions['g0'] = 1
    elif change == 'column': predictions['g0'] = predictions['g0'][:, None]
    elif change == 'row': predictions['g0'] = predictions['g0'][None, :]
    elif change == 'wrong_n': predictions['g0'] = predictions['g0'][:-1]
    elif change == 'complex': predictions['g0'] = predictions['g0'].astype(complex)
    elif change == 'object_complex': predictions['g0'] = predictions['g0'].astype(object); predictions['g0'][0] = 1+0j
    elif change == 'nan': predictions['g0'][0] = np.nan
    elif change == 'infinity': predictions['g0'][0] = np.inf
    elif change == 'm_low': predictions['m'][0] = -.1
    elif change == 'm_high': predictions['m'][0] = 1.1
    with pytest.raises((ValueError, RuntimeError)):
        model.fit(external_predictions=predictions, oof_manifest=manifest)
    assert not hasattr(model, 'g0_hat_')


@pytest.mark.parametrize('change', ['rows', 'y', 'd', 'x', 'index', 'roles'])
def test_sample_mutation_rejects_before_fit(change):
    model, predictions, manifest, _ = fixture()
    if change == 'rows': model.data.df = model.data.df.iloc[::-1]
    elif change in ('y', 'd', 'x'): model.data.df.loc[model.data.df.index[0], change] += 1 if change != 'd' else 1
    elif change == 'index': model.data.df.index = np.arange(len(model.data.df))
    elif change == 'roles': manifest['roles']['confounders'] = ['wrong']
    with pytest.raises(ValueError):
        model.fit(external_predictions=predictions, oof_manifest=manifest)


def test_cluster_leakage_membership_and_one_arm_complement():
    model, predictions, manifest, _ = fixture(cluster=True)
    bad = deepcopy(manifest)
    # Keep complete fold coverage and update complements, but split one cluster.
    bad['folds'][0] = (bad['folds'][0]+1)%3
    bad['training_indices'] = [[np.flatnonzero(np.array(bad['folds']) != fold).tolist() for fold in range(3)]]
    with pytest.raises(ValueError, match='cluster'):
        model.fit(external_predictions=predictions, oof_manifest=bad)
    model.cluster_groups[0] = 999
    with pytest.raises(ValueError, match='cluster_hash'):
        model.fit(external_predictions=predictions, oof_manifest=manifest)
    model, predictions, manifest, _ = fixture()
    d = model.data.df.d.to_numpy()
    folds = np.where(d == 1, 0, (np.arange(len(d))//2)%2+1)
    with pytest.raises(ValueError, match='both treatment arms'):
        model.make_oof_manifest(predictions, folds=folds,
                               training_indices=[[np.flatnonzero(folds != fold) for fold in range(3)]],
                               split_seeds=[17])


@pytest.mark.parametrize('method', ['gate', 'gatet', 'cate', 'sensitivity', 'element', 'direct_gate', 'direct_gatet', 'direct_cate'])
def test_unsupported_entrypoints(method):
    model, predictions, manifest, _ = fixture()
    model.fit(external_predictions=predictions, oof_manifest=manifest)
    model.estimate()
    calls = dict(gate=lambda: model.estimate(score='GATE'), gatet=lambda: model.estimate(score='GATET'),
                 cate=lambda: model.predict_cate(model.data.df[['x']]),
                 sensitivity=lambda: model.sensitivity_analysis(.01, .01), element=lambda: model._sensitivity_element_est(),
                 direct_gate=lambda: estimate_gate_from_irm(model, groups=None),
                 direct_gatet=lambda: estimate_gatet_from_irm(model, groups=None),
                 direct_cate=lambda: predict_cate(model, model.data.df[['x']]))
    with pytest.raises((ValueError, NotImplementedError), match='External OOF'):
        calls[method]()


@pytest.mark.parametrize('mode', ['pred_only', 'manifest_only', 'drop', 'fixed'])
def test_configuration_rejections(mode):
    model, predictions, manifest, _ = fixture()
    if mode == 'drop': model.overlap_policy = 'drop'
    if mode == 'fixed': model._fixed_fold_assignments_ = np.array(manifest['folds'])
    with pytest.raises(ValueError):
        model.fit(external_predictions=None if mode == 'manifest_only' else predictions,
                  oof_manifest=None if mode == 'pred_only' else manifest)


def test_binary_probabilities_endpoints_and_numeric_strings():
    model, predictions, manifest, _ = fixture(binary=True)
    predictions['g0'][0] = 1.1
    with pytest.raises(ValueError, match='probabilities'):
        model.make_oof_manifest(predictions, folds=manifest['folds'], training_indices=manifest['training_indices'], split_seeds=[17])
    predictions['g0'][0] = 1
    predictions['m'][:2] = [0, 1]
    predictions = {name: values.astype(str) for name, values in predictions.items()}
    manifest = model.make_oof_manifest(predictions, folds=manifest['folds'], training_indices=manifest['training_indices'], split_seeds=[17])
    model.fit(external_predictions=predictions, oof_manifest=manifest)
    assert model.overlap_n_clipped_ == 2
    np.testing.assert_array_equal(model.m_hat_[:2], [.01, .99])


def test_external_internal_refit_lifecycle_and_bad_late_repetition():
    model, predictions, manifest, _ = fixture(3)
    model.fit(external_predictions=predictions, oof_manifest=manifest)
    old = model.estimate().value
    bad = deepcopy(manifest)
    bad['training_indices'][2][2][0] = -1
    with pytest.raises(ValueError): model.fit(external_predictions=predictions, oof_manifest=bad)
    assert model.estimate().value == old
    model.ml_g, model.ml_m, model.random_state = LinearRegression(), LogisticRegression(), 17
    model.fit()
    assert not model._fit_external_oof_ and not hasattr(model, '_fit_oof_manifest_')
    assert not hasattr(model, 'coef_')
    assert 'nuisance_source' not in model.estimate().model_options
    model.fit(external_predictions=predictions, oof_manifest=manifest)
    assert not hasattr(model, 'coef_')
    assert model.estimate().value == old


def test_custom_weight_policy_unchanged():
    model, predictions, manifest, _ = fixture()
    model.weights = np.linspace(.5, 1.5, len(model.data.df))
    model.normalize_ipw = True
    model.fit(external_predictions=predictions, oof_manifest=manifest)
    with pytest.warns(RuntimeWarning, match='approximate'):
        result = model.estimate()
    assert np.isfinite(result.value)
    with pytest.raises(ValueError): model.estimate(score='ATTE')


@pytest.mark.parametrize('field,value', [('n_rep', True), ('n_rep', 1.0),
                                       ('n_folds', 3.0), ('schema_version', 2)])
def test_manifest_schema_types(field, value):
    model, predictions, manifest, _ = fixture()
    manifest[field] = value
    with pytest.raises(ValueError): model.fit(external_predictions=predictions, oof_manifest=manifest)


@pytest.mark.parametrize('repetitions', [1, 3])
def test_factory_detaches_inputs_and_prediction_hash_catches_reorder(repetitions):
    model, predictions, manifest, _ = fixture(repetitions)
    folds = np.asarray(manifest['folds'])
    training = deepcopy(manifest['training_indices'])
    seeds = list(manifest['split_seeds'])
    owned = model.make_oof_manifest(predictions, folds=folds, training_indices=training, split_seeds=seeds)
    folds[:] = -1
    training[0][0][0] = -1
    seeds[0] = 0
    assert owned == manifest
    predictions['g0'] = predictions['g0'][::-1].copy()
    with pytest.raises(ValueError, match='prediction_hashes'):
        model.fit(external_predictions=predictions, oof_manifest=manifest)


@pytest.mark.parametrize('repetitions', [1, 3])
def test_relative_undefined_and_seed_metadata(repetitions):
    model, predictions, manifest, _ = fixture(repetitions)
    model.relative_baseline_min = 1e6
    model.random_state = 987
    model.fit(external_predictions=predictions, oof_manifest=manifest)
    result = model.estimate()
    assert np.isnan(result.value_relative) and np.isnan(model.se_relative_[0])
    assert np.isfinite(result.value) and np.isfinite(model.se[0])
    children = model._fit_repetitions_ if repetitions > 1 else [model]
    for rep, child in enumerate(children):
        assignment = manifest['folds'] if repetitions == 1 else np.asarray(manifest['folds'])[:, rep]
        np.testing.assert_array_equal(child.folds_, assignment)
        assert child.estimate().model_options['oof_split_seed'] == manifest['split_seeds'][rep]


def test_factory_support_guard_is_retained():
    model, predictions, manifest, _ = fixture()
    model.data.df.loc[:, 'd'] = 0
    model.data.df.loc[model.data.df.index[:2], 'd'] = 1
    with pytest.raises(ValueError, match='minimum treatment class count'):
        model.make_oof_manifest(predictions, folds=manifest['folds'],
                                training_indices=manifest['training_indices'], split_seeds=[17])


def test_training_indices_accept_permutation_but_not_subset():
    model, predictions, manifest, _ = fixture()
    for train in manifest['training_indices'][0]: train.reverse()
    model.fit(external_predictions=predictions, oof_manifest=manifest)
    manifest['training_indices'][0][0].pop()
    with pytest.raises(ValueError): model.fit(external_predictions=predictions, oof_manifest=manifest)


@pytest.mark.parametrize('column', ['x', 'y'])
@pytest.mark.parametrize('value', [np.nan, np.inf])
def test_external_finite_sample_required(column, value):
    model, predictions, manifest, _ = fixture()
    model.data.df.loc[model.data.df.index[0], column] = value
    with pytest.raises(ValueError, match='finite'):
        model.fit(external_predictions=predictions, oof_manifest=manifest)
