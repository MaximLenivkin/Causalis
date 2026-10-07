"""Public numerical failure policy and independent custom-ATE normalization."""
import numpy as np
import pytest

from tests.inference.test_nuisance_prediction_contract import ConstantRegressor, dataset, estimator


@pytest.mark.parametrize('kind,score', [('binary', 'ATE'), ('binary', 'ATTE'),
                                        ('multi', 'ATE'), ('multi', 'ATTE'), ('iv', 'LATE')])
@pytest.mark.parametrize('normalize', [False, True])
@pytest.mark.parametrize('value', [1e155, -1e155, 1e307, -1e308])
def test_public_estimate_rejects_overflow_from_finite_predictions(kind, normalize, score, value):
    model = estimator(kind, dataset(kind), g=ConstantRegressor(value))
    model.normalize_ipw = normalize
    model.fit()
    with pytest.raises(RuntimeError, match='score/inference arithmetic'):
        model.estimate(score=score)
    assert not hasattr(model, 'coef_')
    assert not hasattr(model, 'result_')


@pytest.mark.parametrize('normalize', [False, True])
@pytest.mark.parametrize('propensity', [0., 1.])
def test_binary_near_boundary_propensity_fails_explicitly(normalize, propensity):
    model = estimator('binary', dataset('binary'), g=ConstantRegressor(2.),
                      m=ConstantRegressor(propensity))
    model.normalize_ipw = normalize
    model.overlap_threshold = np.nextafter(0., 1.)
    model.fit()
    with pytest.raises(RuntimeError, match='score/inference arithmetic'):
        model.estimate()


@pytest.mark.parametrize('normalize', [False, True])
@pytest.mark.parametrize('propensity', [1e-10, 1. - 1e-10])
def test_custom_ate_near_boundary_matches_independent_fixed_normalization(normalize, propensity):
    data = dataset('binary')
    n = len(data.df)
    weights = np.linspace(.5, 1.5, n)
    weights_bar = np.linspace(1.5, .5, n)
    model = estimator('binary', data, g=ConstantRegressor(2.), m=ConstantRegressor(propensity))
    model.normalize_ipw = normalize
    model.overlap_threshold = 1e-12
    model.weights = dict(weights=weights, weights_bar=weights_bar)
    model.fit()
    with pytest.warns(RuntimeWarning):
        result = model.estimate()
    y, d = model._resolve_estimation_targets()
    h1, h0 = d / model.m_hat_, (1 - d) / (1 - model.m_hat_)
    if normalize:
        h1, h0 = h1 / h1.mean(), h0 / h0.mean()
    signal = weights_bar / weights.mean() * (y - 2.) * (h1 - h0)
    theta = signal.mean()
    influence = signal - theta
    se = np.sqrt(np.dot(influence, influence) / (n * (n - 1)))
    assert result.value == pytest.approx(theta, rel=2e-14)
    np.testing.assert_allclose(model.psi_, influence, rtol=2e-14, atol=16 * np.finfo(float).eps * np.max(np.abs(signal)))
    assert model.se_[0] == pytest.approx(se, rel=2e-14)


@pytest.mark.parametrize('mean', [1.01e-12, 1e-6])
def test_custom_weights_bar_division_overflow_is_rejected(mean):
    model = estimator('binary', dataset('binary'), g=ConstantRegressor(2.))
    model.weights = dict(weights=np.full(len(model.data.df), mean),
                         weights_bar=np.full(len(model.data.df), 1e308))
    model.fit()
    with pytest.raises(ValueError, match='normalized.*finite'):
        model.estimate()
    assert not hasattr(model, 'coef_')


@pytest.mark.parametrize('mean', [0., 1e-13, 1e-12])
def test_existing_custom_weight_mean_floor_is_preserved(mean):
    model = estimator('binary', dataset('binary'))
    model.weights = np.full(len(model.data.df), mean)
    with pytest.raises(ValueError, match='positive finite mean'):
        model.fit()


@pytest.mark.parametrize('kind', ['binary', 'multi', 'iv'])
@pytest.mark.parametrize('normalize', [False, True])
def test_ordinary_finite_inference_remains_available(kind, normalize):
    model = estimator(kind, dataset(kind), g=ConstantRegressor(2.))
    model.normalize_ipw = normalize
    result = model.fit().estimate()
    assert np.all(np.isfinite(result.value))
    assert np.all(np.isfinite(model.se_))
    assert np.all(np.isfinite(model.psi_))


class ArmMeanRegressor(ConstantRegressor):
    def fit(self, X, y):
        self.value = float(np.mean(y))
        return self


@pytest.mark.parametrize('kind', ['binary', 'multi'])
@pytest.mark.parametrize('score', ['ATE', 'ATTE'])
@pytest.mark.parametrize('baseline', [1e-200, 1e155])
def test_relative_arithmetic_overflow_does_not_publish_partial_core(kind, score, baseline):
    from causalis.data_contracts import CausalData, MultiCausalData
    data = dataset(kind)
    frame = data.get_df()
    if kind == 'binary':
        frame['y'] = baseline + frame['d'] * (1. if baseline < 1 else baseline * .01)
        data = CausalData.from_df(frame, 'd', 'y', ['x'])
    else:
        frame['y'] = baseline + frame['d1'] * (1. if baseline < 1 else baseline * .01)
        data = MultiCausalData.from_df(frame, outcome='y', treatment_names=['d0', 'd1', 'd2'],
                                      confounders=['x'], control_treatment='d0')
    model = estimator(kind, data, g=ArmMeanRegressor())
    if kind == 'binary':
        model.relative_baseline_min = 0.
    model.fit()
    with pytest.raises(RuntimeError, match='score/inference arithmetic'):
        model.estimate(score=score)
    assert not hasattr(model, 'coef_')
