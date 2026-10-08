"""Independent score-test, complete-set, ownership and real IIVM oracles."""
from dataclasses import FrozenInstanceError

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.exceptions import NotFittedError

from causalis.data_contracts import IVCausalData
from causalis.scenarios.iv import IIVM, WeakIVInference, WeakIVResult
from causalis.scenarios.iv.weak import _quadratic_set


def signals(seed=7, n=100, stage=.5):
    rng = np.random.default_rng(seed)
    d = stage + rng.normal(size=n)
    y = 1.7 * d + rng.normal(size=n)
    return y, d


@pytest.mark.parametrize('coefficients,kind,intervals', [
    ((1, -3, 2), 'bounded', ((1., 2.),)),
    ((-1, 3, -2), 'two-rays', ((-np.inf, 1.), (2., np.inf))),
    ((1, -2, 1), 'singleton', ((1., 1.),)),
    ((-1, 2, -1), 'all-real', ((-np.inf, np.inf),)),
    ((1, 0, 1), 'empty', ()),
    ((-1, 0, -1), 'all-real', ((-np.inf, np.inf),)),
    ((0, 2, -4), 'half-line', ((-np.inf, 2.),)),
    ((0, -2, 4), 'half-line', ((2., np.inf),)),
    ((0, 0, 0), 'all-real', ((-np.inf, np.inf),)),
    ((0, 0, -1), 'all-real', ((-np.inf, np.inf),)),
    ((0, 0, 1), 'empty', ()),
    ((1, 0, -4), 'bounded', ((-2., 2.),)),
    ((-1, 0, 4), 'two-rays', ((-np.inf, -2.), (2., np.inf))),
])
def test_all_quadratic_geometries(coefficients, kind, intervals):
    actual_kind, actual = _quadratic_set(*coefficients)
    assert actual_kind == kind
    np.testing.assert_allclose(actual, intervals)
    for theta in np.linspace(-5, 5, 101):
        a, b, c = coefficients
        assert any(lo <= theta <= hi for lo, hi in actual) == (a*theta**2+b*theta+c <= 0)


@pytest.mark.parametrize('scale', [1e-100, 1., 1e100])
@pytest.mark.parametrize('stage', [0., .02, .5, 2.])
@pytest.mark.parametrize('null', [-2., 0., 1.7])
def test_direct_centered_score_and_covariance_oracle(scale, stage, null):
    y, d = signals(stage=stage)
    result = WeakIVInference(y*scale, d*scale).infer(alpha=.1, null=null)
    score = y-null*d
    expected_stat = np.mean(score)**2 / (np.var(score, ddof=1)/len(score))
    assert result.statistic == pytest.approx(expected_stat)
    assert result.p_value == pytest.approx(2*norm.sf(np.sqrt(expected_stat)))
    assert result.numerator == pytest.approx(np.mean(y)*scale)
    assert result.denominator == pytest.approx(np.mean(d)*scale)
    assert result.critical_value == pytest.approx(norm.isf(.05))
    cov = np.cov(np.stack([y, d]), ddof=1)/len(y)
    for theta in np.linspace(-30, 30, 601):
        mean = np.mean(y)-theta*np.mean(d)
        var = cov[0, 0]-2*theta*cov[0, 1]+theta**2*cov[1, 1]
        assert result.contains(float(theta)) == (mean**2 <= norm.isf(.05)**2*var)
    for lo, hi in result.confidence_set:
        for edge in (lo, hi):
            if np.isfinite(edge):
                mean = np.mean(y)-edge*np.mean(d)
                var = cov[0, 0]-2*edge*cov[0, 1]+edge**2*cov[1, 1]
                assert mean**2 == pytest.approx(norm.isf(.05)**2*var, abs=1e-10)
                assert result.contains(edge)


def test_known_orthogonal_signals_produce_all_real_and_two_rays():
    y = np.array([-1., -1., 1., 1.])
    d = np.array([-1., 1., -1., 1.])
    assert WeakIVInference(y, d).infer().set_type == 'all-real'
    result = WeakIVInference(y+5, d).infer()
    assert result.set_type == 'two-rays'
    edge = np.sqrt(25/(norm.isf(.025)**2/3)-1)
    np.testing.assert_allclose(result.confidence_set, ((-np.inf, -edge), (edge, np.inf)))
    assert not result.contains(0.)


def test_zero_denominator_signal_and_constant_strong_stage():
    y = np.array([-1., 0., 1., 2.])
    assert WeakIVInference(y, np.zeros(4)).infer().set_type == 'all-real'
    assert WeakIVInference(y+10, np.zeros(4)).infer().set_type == 'empty'
    result = WeakIVInference(y, np.ones(4)).infer()
    critical = norm.isf(.025)*np.std(y, ddof=1)/2
    np.testing.assert_allclose(result.confidence_set, ((y.mean()-critical, y.mean()+critical),))


def test_stable_roots_and_no_linear_tolerance():
    kind, intervals = _quadratic_set(1e-100, -1, 1)
    assert kind == 'bounded'
    assert intervals[0][0] == pytest.approx(1)
    assert intervals[0][1] == pytest.approx(1e100)
    assert _quadratic_set(-1e-100, -1, 1)[0] == 'two-rays'


@pytest.mark.parametrize('values', [([], []), ([1], [2]), ([[1, 2]], [1, 2]),
                                    ([1, 2], [1, 2, 3]), ([1, 1], [2, 2]), ([0, 0], [0, 0])])
def test_shape_and_degenerate_signals(values):
    with pytest.raises(ValueError):
        WeakIVInference(*values)


@pytest.mark.parametrize('position', [0, 1])
@pytest.mark.parametrize('bad', [[1+0j, 2+0j], np.array([1+0j, 2], dtype=object),
                                [1, np.nan], [1, np.inf], [1, -np.inf]])
def test_raw_reality_and_finiteness(position, bad):
    values = [[1., 2.], [2., 1.]]
    values[position] = bad
    with pytest.raises((ValueError, RuntimeError)):
        WeakIVInference(*values)


@pytest.mark.parametrize('name,bad', [('alpha', 0), ('alpha', 1), ('alpha', True),
    ('alpha', '0.05'), ('alpha', np.nan), ('alpha', 1j), ('null', np.inf),
    ('null', 1+0j), ('null', True), ('null', '1'), ('null', [1])])
def test_inference_scalar_guards(name, bad):
    with pytest.raises(ValueError):
        WeakIVInference(*signals()).infer(**{name: bad})


def test_zero_null_score_variance_and_numerical_failures():
    d = np.arange(1., 5.)
    with pytest.raises(ValueError, match='variance'):
        WeakIVInference(2*d, d).infer(null=2.)
    with pytest.raises(RuntimeError):
        _quadratic_set(1e-320, -1., 1.)
    with pytest.raises(RuntimeError):
        _quadratic_set(1e-320, 1e308, 1.)
    with pytest.raises(RuntimeError):
        WeakIVInference(*signals()).infer(alpha=np.nextafter(0., 1.))
    with pytest.raises(RuntimeError, match='underflow'):
        WeakIVInference([1e300, -1e300], [1e-200, -1e-200])


def test_owned_snapshot_results_and_rng():
    y, d = signals()
    state = np.random.get_state()
    inference = WeakIVInference(y, d)
    result = inference.infer()
    y[:] = 0
    d[:] = 0
    assert inference.infer() == result
    with pytest.raises(FrozenInstanceError):
        result.set_type = 'all-real'
    frame = result.summary()
    frame.loc[0, 'numerator'] = 999
    assert result.summary().loc[0, 'numerator'] == result.numerator
    assert isinstance(result, WeakIVResult)
    assert all(not isinstance(v, np.ndarray) for v in result.__dict__.values())
    after = np.random.get_state()
    assert state[0] == after[0] and state[2:] == after[2:]
    np.testing.assert_array_equal(state[1], after[1])
    for bad in (np.inf, np.nan, True, '1', 1+0j):
        with pytest.raises(ValueError):
            result.contains(bad)


@pytest.fixture
def fitted():
    rng = np.random.default_rng(19)
    x = rng.normal(size=200)
    z = rng.binomial(1, .5, size=200)
    d = rng.binomial(1, 1/(1+np.exp(-(.2+z+.3*x))))
    y = 2*d+x+rng.normal(size=200)
    data = IVCausalData.from_df(pd.DataFrame(dict(x=x,y=y,d=d,z=z)),
                              outcome='y', treatment='d', instruments='z', confounders=['x'])
    return IIVM(data, ml_g=LinearRegression(), ml_m=LogisticRegression(),
                ml_r=LogisticRegression(), n_folds=2, random_state=11).fit()


def test_real_fitted_adapter_manual_scores_and_no_callbacks(fitted, monkeypatch):
    model = fitted
    def bomb(*args, **kwargs):
        raise AssertionError('inference invoked learner or source estimation')
    monkeypatch.setattr(model, 'estimate', bomb)
    monkeypatch.setattr(model, 'fit', bomb)
    for learner in (model.ml_g, model.ml_m, model.ml_r):
        monkeypatch.setattr(learner, 'fit', bomb)
        monkeypatch.setattr(learner, 'predict', bomb)
    before = model.__dict__.copy()
    inference = WeakIVInference.from_iivm(model)
    result = model.estimate_weak_iv(null=2.)
    w1, w0 = model.z_/model.m_hat_, (1-model.z_)/(1-model.m_hat_)
    y = model.g_hat1_-model.g_hat0_+w1*(model.y_-model.g_hat1_)-w0*(model.y_-model.g_hat0_)
    d = model.r_hat1_-model.r_hat0_+w1*(model.d_-model.r_hat1_)-w0*(model.d_-model.r_hat0_)
    assert result == WeakIVInference(y, d).infer(null=2.)
    assert model.__dict__.keys() == before.keys()
    assert all(model.__dict__[key] is value for key, value in before.items())
    assert not hasattr(model, 'coef_')
    # IIVM's successful-fit arrays own the data; live data changes are irrelevant.
    model.data.df.loc[:, 'y'] = 10000
    assert model.estimate_weak_iv(null=2.) == result
    model.y_[:] = 0
    model.g_hat0_[:] = 0
    assert inference.infer(null=2.) == result


def test_wald_state_preserved_and_zero_first_stage_bypassed(fitted):
    old = fitted.estimate()
    state = fitted.__dict__.copy()
    fitted.estimate_weak_iv()
    assert all(fitted.__dict__[key] is value for key, value in state.items())
    assert fitted.result_ is old
    # Constant treatment signal with exactly zero mean, so Wald must refuse.
    fitted.d_[:] = fitted.z_
    fitted.r_hat0_[:] = .5
    fitted.r_hat1_[:] = .5
    fitted.m_hat_[:] = .5
    fitted.z_[:] = 0
    fitted.d_ = np.full(len(fitted.y_), .5)  # retain raw nonbinary values
    with pytest.raises(ValueError, match='binary'):
        fitted.estimate_weak_iv()
    fitted.d_[:] = 0
    fitted.r_hat0_[:] = 0
    fitted.r_hat1_[:] = 0
    with pytest.raises(ValueError, match='first stage'):
        fitted.estimate()
    assert np.isfinite(fitted.estimate_weak_iv().statistic)


@pytest.mark.parametrize('attribute,value', [('normalize_ipw', True), ('n_rep', 2), ('trimming_rule', 'drop')])
def test_context_guards(fitted, attribute, value):
    setattr(fitted, attribute, value)
    with pytest.raises(NotImplementedError):
        fitted.estimate_weak_iv()


@pytest.mark.parametrize('attribute,value', [('m_hat_', 0.), ('m_hat_', 1.),
    ('r_hat0_', -.1), ('r_hat1_', 1.1), ('d_', 2), ('z_', 2),
    ('y_', np.nan), ('g_hat0_', np.inf), ('r_hat1_', 1+0j)])
def test_fitted_array_guards(fitted, attribute, value):
    setattr(fitted, attribute, np.full(len(fitted.y_), value))
    with pytest.raises((ValueError, RuntimeError)):
        fitted.estimate_weak_iv()


def test_adapter_type_and_unfitted():
    with pytest.raises(TypeError):
        WeakIVInference.from_iivm(object())
    with pytest.raises(NotFittedError):
        IIVM().estimate_weak_iv()


@pytest.mark.parametrize('stage', [0., .02, 1.])
def test_gaussian_iid_null_size_and_set_coverage_smoke(stage):
    rng = np.random.default_rng(810)
    accepted = 0
    for _ in range(1500):
        d = stage+rng.normal(size=80)
        y = 1.7*d+.4*(d-stage)+rng.normal(size=80)
        result = WeakIVInference(y, d).infer(null=1.7)
        assert result.contains(1.7) == (not result.is_significant)
        accepted += result.contains(1.7)
    assert .925 < accepted/1500 < .975


@pytest.mark.parametrize('complier_share', [0., .02, .4])
def test_binary_monotone_iv_oracle_coverage_smoke(complier_share):
    rng = np.random.default_rng(714)
    accepted = 0
    for _ in range(600):
        n = 500
        u = rng.uniform(size=n)
        z = rng.binomial(1, .5, size=n)
        d = (u < .3+complier_share*z).astype(float)
        # Latent U confounds D/Y, Z remains exogenous, exclusion holds.
        y = 2*d+3*(u-.5)+rng.normal(size=n)
        g0, g1 = .6, 2*(.3+complier_share)
        r0, r1 = .3, .3+complier_share
        phi_y = g1-g0+2*z*(y-g1)-2*(1-z)*(y-g0)
        phi_d = r1-r0+2*z*(d-r1)-2*(1-z)*(d-r0)
        result = WeakIVInference(phi_y, phi_d).infer(null=2.)
        accepted += result.contains(2.)
    assert .92 < accepted/600 < .98


def test_constant_tiny_stage_cannot_silently_change_set_geometry():
    with pytest.raises(RuntimeError, match='underflow'):
        WeakIVInference([-1., 0., 1., 2.], np.full(4, 1e-200)).infer()


@pytest.mark.parametrize('offset,scale', [(3., 2.), (-4., -.5), (0., -1.)])
def test_effect_coordinate_transformation(offset, scale):
    y, d = signals()
    original = WeakIVInference(y, d).infer(null=1.7)
    changed = WeakIVInference(scale*y+offset*d, d).infer(null=scale*1.7+offset)
    assert original.statistic == pytest.approx(changed.statistic)
    mapped = sorted(tuple(sorted((scale*lo+offset, scale*hi+offset)))
                    for lo, hi in original.confidence_set)
    np.testing.assert_allclose(changed.confidence_set, mapped)


def test_actual_normalized_fit_and_failed_refit_reject(fitted):
    fitted.normalize_ipw = True
    fitted.fit()
    with pytest.raises(NotImplementedError):
        fitted.estimate_weak_iv()
    fitted.normalize_ipw = False
    fitted.n_folds = 1000
    with pytest.raises(ValueError):
        fitted.fit()
    with pytest.raises(NotFittedError):
        fitted.estimate_weak_iv()


def test_real_fit_with_exactly_zero_first_stage():
    from sklearn.dummy import DummyClassifier, DummyRegressor
    n = 32
    frame = pd.DataFrame({'y': np.random.default_rng(38).normal(size=n),
                          'd': np.tile([0, 1, 1, 0], 8),
                          'z': np.tile([0, 0, 1, 1], 8)})
    data = IVCausalData.from_df(frame, outcome='y', treatment='d', instruments='z')
    model = IIVM(data, ml_g=DummyRegressor(), ml_r=DummyClassifier(strategy='prior'),
                 ml_m=DummyClassifier(strategy='prior'), n_folds=2, random_state=4).fit()
    result = model.estimate_weak_iv()
    assert result.denominator == 0
    assert np.isfinite(result.statistic)
    with pytest.raises(ValueError, match='first stage'):
        model.estimate()
