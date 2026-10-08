"""Independent covariance, Gaussian-draw oracles and supported IRM integration."""
from dataclasses import FrozenInstanceError

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm
from sklearn.linear_model import LinearRegression, LogisticRegression

from causalis.data_contracts import CausalData
from causalis.inference import InferenceFamily
from causalis.scenarios.unconfoundedness import IRM


def family():
    return InferenceFamily([.8, -.1], [[1, 2], [-1, 1], [2, -2], [-2, -1]], ['a', 'b'])


def test_independent_sample_mean_covariance_and_bonferroni_oracle():
    observations = np.array([[1, 2], [3, -1], [-2, 0], [4, 3], [2, -2.]])
    model = InferenceFamily(observations.mean(0), observations, ['a', 'b'])
    expected = np.cov(observations, rowvar=False, ddof=1) / len(observations)
    np.testing.assert_allclose(model.covariance, expected)
    result = model.infer(alpha=.1, null=[.2, -.3])
    se = np.sqrt(np.diag(expected))
    p = 2 * norm.sf(np.abs((observations.mean(0) - [.2, -.3]) / se))
    np.testing.assert_allclose(result.std_errors, se)
    np.testing.assert_allclose(result.p_values, p)
    np.testing.assert_allclose(result.adjusted_p_values, np.minimum(1, 2*p))
    np.testing.assert_allclose(result.ci_lower, observations.mean(0) - norm.isf(.1/4)*se)
    assert result.n_boot == 0 and result.random_state is None


@pytest.mark.parametrize('draws', [99, 256, 257, 999])
@pytest.mark.parametrize('alpha', [.05, .2, .5])
def test_max_t_independent_gaussian_covariance_and_order_statistic_oracle(draws, alpha):
    influence = np.array([[1., 2], [-1, 1], [2, -2], [-2, -1]])
    # Direct covariance-normalized perturbation, not production normalization.
    se = np.sqrt(np.diag(np.cov(influence, rowvar=False))/4)
    weights = np.random.default_rng(172).standard_normal((draws, 4))
    t = weights @ influence / np.sqrt(4*3) / se
    maxima = np.max(np.abs(t), axis=1)
    expected_critical = sorted(maxima)[int(np.ceil((1-alpha)*(draws+1)))-1]
    result = family().infer(method='max-t', alpha=alpha, n_boot=draws, random_state=172)
    assert result.critical_value == pytest.approx(expected_critical)
    expected_p = [(1+sum(maxima >= abs(v/s)))/(draws+1) for v, s in zip([.8, -.1], se)]
    np.testing.assert_allclose(result.adjusted_p_values, expected_p)
    assert result.summary().is_significant.tolist() == [p <= alpha for p in expected_p]


@pytest.mark.parametrize('sign', [-1, 1])
def test_perfectly_dependent_family_uses_single_multiplier_critical_value(sign):
    x = np.array([-2., -1, 1, 2])
    single = InferenceFamily([.1], x[:, None], ['one']).infer(method='max-t', random_state=18)
    duplicate = InferenceFamily([.1, .1*sign], np.column_stack([x, sign*x]), ['a', 'b'])
    result = duplicate.infer(method='max-t', random_state=18)
    assert result.critical_value == pytest.approx(single.critical_value)
    np.testing.assert_allclose(result.adjusted_p_values, single.adjusted_p_values[0])
    assert np.linalg.matrix_rank(duplicate.covariance) == 1


@pytest.mark.parametrize('method', ['bonferroni', 'max-t'])
def test_linear_contrast_matches_direct_mean_inference_and_column_permutation(method):
    x = np.array([[1., 2], [-1, 1], [2, -2], [-2, -1]])
    L = np.array([[1, -1], [.25, .75]])
    actual = family().contrast(L, ['diff', 'weighted']).infer(method=method, random_state=18)
    direct = InferenceFamily([.9, .125], x@L.T, ['diff', 'weighted']).infer(method=method, random_state=18)
    assert actual == direct
    permuted = InferenceFamily([-.1, .8], x[:, ::-1], ['b', 'a']).infer(method=method, random_state=18)
    original = family().infer(method=method, random_state=18)
    np.testing.assert_allclose(permuted.adjusted_p_values, original.adjusted_p_values[::-1])
    assert permuted.critical_value == pytest.approx(original.critical_value)


def test_input_covariance_and_result_ownership_and_global_rng_preservation():
    values = np.array([.1, .2])
    x = np.array([[1., 2], [-1, 1], [2, -2], [-2, -1]])
    model = InferenceFamily(values, x, ['a', 'b'])
    expected = model.infer(method='max-t', random_state=18)
    values[:] = 0; x[:] = 0
    covariance = model.covariance; covariance[:] = 0
    np.random.seed(17)
    before = np.random.get_state()
    assert model.infer(method='max-t', random_state=18) == expected
    after = np.random.get_state()
    assert before[0] == after[0] and before[2:] == after[2:]
    np.testing.assert_array_equal(before[1], after[1])
    with pytest.raises(FrozenInstanceError):
        expected.alpha = .4
    table = expected.summary(); table.iloc[0, 0] = 99
    assert expected.summary().iloc[0, 0] == .1


@pytest.mark.parametrize('scale', [1e-100, .01, 1., 1e100])
def test_centering_and_scale_equivariance(scale):
    x = np.array([[-2., -1], [-1, 2], [1, 1], [2, -2]])
    base = InferenceFamily([.1, .2], x, ['a', 'b']).infer(method='max-t', random_state=18)
    scaled = InferenceFamily(np.array([.1, .2])*scale, (x+10)*scale, ['a', 'b'])
    result = scaled.infer(method='max-t', random_state=18)
    assert result.critical_value == pytest.approx(base.critical_value)
    np.testing.assert_allclose(result.std_errors, np.array(base.std_errors)*scale, rtol=1e-12, atol=0)
    np.testing.assert_allclose(result.adjusted_p_values, base.adjusted_p_values)


@pytest.mark.parametrize('values,influence,names', [
    ([], np.empty((3, 0)), []), ([1], [[1]], ['a']),
    ([[1]], [[1], [2]], ['a']), ([1, 2], [[1], [2]], ['a', 'b']),
    ([1], [1, 2], ['a']), ([1], [[1], [1]], ['a']),
    ([1], [[1], [2]], 'a'), ([1], [[1], [2]], ['']),
    ([1, 2], [[1, 2], [2, 3]], ['a', 'a']),
    ([1], [[1], [2]], [1]), ([1], [[1], [2]], []),
])
def test_shape_variance_and_name_guards(values, influence, names):
    with pytest.raises(ValueError):
        InferenceFamily(values, influence, names)


@pytest.mark.parametrize('bad', [np.nan, np.inf, 1+0j, complex(1, 2)])
@pytest.mark.parametrize('target', ['values', 'influence', 'null', 'contrast'])
def test_real_finite_guards(bad, target):
    with pytest.raises((ValueError, RuntimeError)):
        if target == 'values': InferenceFamily([bad], [[1], [2]], ['a'])
        elif target == 'influence': InferenceFamily([1], [[bad], [2]], ['a'])
        elif target == 'null': family().infer(null=bad)
        else: family().contrast([[bad, 1]], ['c'])


@pytest.mark.parametrize('options', [
    {'alpha': 0}, {'alpha': 1}, {'alpha': True}, {'alpha': np.nan}, {'alpha': '0.05'},
    {'method': 'holm'}, {'null': [0]}, {'null': [[0, 0]]},
    {'n_boot': True}, {'n_boot': 98}, {'n_boot': 100.5}, {'random_state': -1},
    {'random_state': True}, {'random_state': 1.2}, {'random_state': 2**32},
    {'n_boot': 99, 'alpha': .001},
])
def test_inference_request_guards(options):
    with pytest.raises(ValueError):
        family().infer(**{'method': 'max-t', **options})


def test_resolution_boundary_and_nulls_do_not_move_intervals():
    model = family()
    zero = model.infer(method='max-t', n_boot=99, alpha=.01, random_state=18)
    other = model.infer(method='max-t', n_boot=99, alpha=.01, random_state=18, null=[.8, -.1])
    assert zero.ci_lower == other.ci_lower and zero.ci_upper == other.ci_upper
    assert other.adjusted_p_values == (1., 1.)
    assert all(p >= .01 for p in zero.adjusted_p_values)


@pytest.mark.parametrize('matrix', [[1, -1], [[1]], [], [[0, 0]]])
def test_contrast_guards(matrix):
    with pytest.raises(ValueError): family().contrast(matrix, ['contrast'])


def test_arithmetic_overflow_fails_without_a_partial_result():
    with pytest.raises(RuntimeError):
        InferenceFamily([1], [[1e308], [-1e308]], ['a'])
    with pytest.raises(RuntimeError):
        family().infer(null=1.7e308)
    with pytest.raises(RuntimeError):
        family().contrast([[1e308, -1e308]], ['overflow'])
    assert family().infer().n_observations == 4


def irm_pair(**kwargs):
    rng = np.random.default_rng(713)
    x = rng.normal(size=180)
    d = rng.binomial(1, 1/(1+np.exp(-.2*x)))
    noise = rng.normal(size=(180, 2))
    frame = pd.DataFrame(dict(id=np.arange(180), x=x, d=d,
                              y1=x+.4*d+noise[:, 0], y2=2*x-.2*d+noise[:, 1]))
    models = {}
    for i, outcome in enumerate(['y1', 'y2']):
        data = CausalData(df=frame.copy(), outcome=outcome, treatment='d',
                          confounders=['x'], user_id='id')
        models[outcome] = IRM(data, ml_g=LinearRegression(), ml_m=LogisticRegression(),
                              n_folds=3, random_state=18+i, **kwargs).fit()
    return models


@pytest.mark.parametrize('score', ['ATE', 'ATTE'])
@pytest.mark.parametrize('diagnostics', [False, True])
def test_real_irm_matches_scalar_effect_covariance_and_preserves_source(score, diagnostics):
    models = irm_pair(store_diagnostics=diagnostics)
    estimates = [m.estimate(score=score) for m in models.values()]
    states = [dict(m.__dict__) for m in models.values()]
    family_model = InferenceFamily.from_irm(models, score=score)
    result = family_model.infer()
    np.testing.assert_allclose(result.estimates, [e.value for e in estimates])
    np.testing.assert_allclose(result.std_errors, [e.model_options['std_error'] for e in estimates])
    influences = np.column_stack([m.psi_ for m in models.values()])
    np.testing.assert_allclose(family_model.covariance, np.cov(influences, rowvar=False)/180)
    for model, state in zip(models.values(), states):
        assert model.__dict__.keys() == state.keys()
        for key in state: assert model.__dict__[key] is state[key]
    # Model/data/config changes after snapshot cannot affect family inference.
    for model in models.values():
        model.g0_hat_[:] = 0
        model.data.df.loc[0, model.data.outcome_name] += 100
        model.normalize_ipw = True
    assert family_model.infer() == result


def test_irm_adapter_never_fits_predicts_or_creates_scalar_cache(monkeypatch):
    models = irm_pair()
    def forbidden(*args, **kwargs): raise AssertionError('unexpected fit/predict/estimate')
    for model in models.values():
        monkeypatch.setattr(model, 'fit', forbidden)
        monkeypatch.setattr(model, 'estimate', forbidden)
        monkeypatch.setattr(model.ml_g, 'fit', forbidden)
        monkeypatch.setattr(model.ml_m, 'predict_proba', forbidden)
    result = InferenceFamily.from_irm(models).infer(method='max-t', random_state=18)
    assert result.n_observations == 180
    assert all(not hasattr(m, 'coef_') for m in models.values())


@pytest.mark.parametrize('change', ['order', 'ids', 'duplicates', 'null_ids', 'treatment', 'y', 'x', 'roles', 'complex'])
def test_irm_alignment_and_stale_sample_guards(change):
    models = irm_pair()
    model = models['y2']
    if change == 'order': model.data.df = model.data.df.iloc[::-1].copy()
    elif change == 'ids': model.data.df.loc[0, 'id'] = 999
    elif change == 'duplicates': model.data.df.loc[0, 'id'] = 1
    elif change == 'null_ids': model.data.df['id'] = model.data.df.id.astype(float); model.data.df.loc[0, 'id'] = np.nan
    elif change == 'treatment': model.data.df.loc[0, 'd'] = 1-model.data.df.loc[0, 'd']
    elif change == 'y': model.data.df.loc[0, 'y2'] += 1
    elif change == 'x': model.data.df.loc[0, 'x'] += 1
    elif change == 'roles': model.data.outcome_name = 'y1'
    else: model.data.df['y2'] = model.data.df.y2.astype(complex)
    with pytest.raises((ValueError, RuntimeError)):
        InferenceFamily.from_irm(models)


@pytest.mark.parametrize('options', [dict(n_rep=2), dict(normalize_ipw=True),
                                    dict(overlap_policy='drop'), dict(weights=np.ones(180)),
                                    dict(cluster_groups=np.repeat(np.arange(30), 6))])
def test_actual_unsupported_irm_fit_contexts(options):
    with pytest.raises(NotImplementedError): InferenceFamily.from_irm(irm_pair(**options))


@pytest.mark.parametrize('models,score', [({}, 'ATE'), ([], 'ATE'), ({'a': object()}, 'ATE'),
                                        ({'a': IRM()}, 'ATE'), ({'a': object()}, 'CATE')])
def test_adapter_type_and_fitted_guards(models, score):
    with pytest.raises((ValueError, TypeError)):
        InferenceFamily.from_irm(models, score=score)


def test_fresh_fitted_models_on_different_units_cannot_be_combined():
    models = irm_pair()
    models['y2'].data.df['id'] += 1000
    models['y2'].fit()
    with pytest.raises(ValueError, match='same ordered IDs'):
        InferenceFamily.from_irm(models)


@pytest.mark.parametrize('change', ['order', 'treatment'])
def test_fresh_refit_cannot_hide_between_model_misalignment(change):
    models = irm_pair()
    model = models['y2']
    if change == 'order': model.data.df = model.data.df.iloc[::-1].copy()
    else: model.data.df.loc[0, 'd'] = 1-model.data.df.loc[0, 'd']
    model.fit()
    with pytest.raises(ValueError, match='same ordered IDs'):
        InferenceFamily.from_irm(models)


def test_missing_ids_and_complex_object_mutations_reject():
    models = irm_pair()
    models['y2'].data.user_id_name = None
    with pytest.raises(ValueError): InferenceFamily.from_irm(models)
    models = irm_pair()
    models['y2'].data.df['y2'] = models['y2'].data.df.y2.astype(object)
    models['y2'].data.df.loc[0, 'y2'] = 1+0j
    with pytest.raises(ValueError): InferenceFamily.from_irm(models)


def test_actual_external_oof_adapter_rejection():
    model = irm_pair()['y1']
    predictions = {'g0': model.g0_hat_.copy(), 'g1': model.g1_hat_.copy(), 'm': model.m_hat_.copy()}
    folds = model._full_sample_folds_.copy()
    training = [[np.flatnonzero(folds != k).tolist() for k in range(model.n_folds)]]
    manifest = model.make_oof_manifest(predictions, folds=folds, training_indices=training, split_seeds=[18])
    model.fit(external_predictions=predictions, oof_manifest=manifest)
    with pytest.raises(NotImplementedError): InferenceFamily.from_irm({'external': model})


@pytest.mark.parametrize('bad', [np.zeros(180), np.ones(180), np.full(180, np.nan)])
def test_invalid_fitted_propensities_reject(bad):
    models = irm_pair()
    models['y1'].m_hat_ = bad
    with pytest.raises((ValueError, RuntimeError)): InferenceFamily.from_irm(models)


def test_gaussian_mean_family_bonferroni_fwer_smoke():
    # Known iid normal mean law, fixed two-hypothesis family. This checks one
    # reproducible oracle regime, not DML coverage or arbitrary nuisance rates.
    rng = np.random.default_rng(71)
    samples = rng.normal(size=(2000, 80, 2))
    rejected = sum(InferenceFamily(x.mean(0), x, ['a', 'b']).infer().summary().is_significant.any()
                   for x in samples)
    assert .025 < rejected/2000 < .085


def test_covariance_underflow_is_explicit_instead_of_zero_uncertainty():
    with pytest.raises(ValueError, match='underflowed'):
        InferenceFamily([0.], [[1e-200], [-1e-200]], ['small'])


def test_orthogonal_influences_match_known_independent_gaussian_maximum_law():
    x = np.array([[1., 1], [1, -1], [-1, 1], [-1, -1]])
    result = InferenceFamily([0, 0], x, ['a', 'b']).infer(
        method='max-t', n_boot=100000, random_state=177)
    # Conditional perturbations are independent standard normal variables;
    # P(max(|Z1|,|Z2|)<=c) = (2*Phi(c)-1)^2, derived independently.
    critical = norm.ppf((1+np.sqrt(.95))/2)
    assert result.critical_value == pytest.approx(critical, abs=.025)
    assert result.adjusted_p_values == (1., 1.)
