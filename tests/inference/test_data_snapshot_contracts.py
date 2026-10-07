"""Public duplicate, returned-diagnostics and fit publication contracts."""
from decimal import Decimal
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from sklearn.exceptions import NotFittedError

from causalis.data_contracts import CausalData, IVCausalData, MultiCausalData, RctCausalData
from tests.inference.test_nuisance_prediction_contract import dataset, estimator, ConstantRegressor


def duplicate_contract(kind, n, object_values, large_numeric=False):
    rng = np.random.default_rng(814)
    frame = pd.DataFrame({'y': np.arange(n, dtype=float) + 10, 'd': np.arange(n) % 2,
                          'z': (np.arange(n) // 2) % 2, 'x': rng.normal(size=n)})
    if large_numeric:
        frame['y'] = np.asarray([2**53 + 2 * i for i in range(n)], dtype=float)
    frame['uid'] = pd.Series(object_values, dtype=object)
    if kind == 'binary':
        return CausalData.from_df(frame, 'd', 'y', ['x'], user_id='uid')
    if kind == 'iv':
        return IVCausalData.from_df(frame, 'd', 'y', 'z', ['x'], user_id='uid')
    if kind == 'rct':
        return RctCausalData.from_df(frame, 'd', 'y', ['x'], user_id='uid')
    for k in range(3):
        frame[f'd{k}'] = (np.arange(n) % 3 == k).astype(int)
    return MultiCausalData.from_df(frame, outcome='y', treatment_names=['d0', 'd1', 'd2'],
                                  control_treatment='d0', confounders=['x'], user_id='uid')


@pytest.mark.parametrize('kind', ['binary', 'multi', 'iv', 'rct'])
@pytest.mark.parametrize('n', [12, 129])
@pytest.mark.parametrize('representation', ['integer', 'float', 'mixed', 'complex', 'decimal', 'fraction'])
def test_numeric_object_duplicates_are_rejected(kind, n, representation):
    values = [int(i + 10) if representation == 'integer' or representation == 'mixed' and i % 2
              else float(i + 10) for i in range(n)]
    converters = {'complex': complex, 'decimal': Decimal, 'fraction': Fraction}
    if representation in converters:
        values = [converters[representation](int(v)) for v in values]
    with pytest.raises(ValueError, match='identical values'):
        duplicate_contract(kind, n, values)


@pytest.mark.parametrize('kind', ['binary', 'multi', 'iv', 'rct'])
@pytest.mark.parametrize('difference', ['strings', 'unsampled_row', 'large_integer'])
def test_screening_never_establishes_duplicate_equality(kind, difference):
    n = 129
    values = [float(i + 10) for i in range(n)]
    if difference == 'strings':
        values = [str(int(v)) for v in values]
    elif difference == 'unsampled_row':
        values[1] += 0.5
    else:
        # Fingerprints may round large integer IDs; exact equality must not.
        values = [2**53 + 2 * i + 1 for i in range(n)]
    duplicate_contract(kind, n, values, large_numeric=difference == 'large_integer')


def estimate(model, kind, diagnostics=True):
    return model.estimate(**({'diagnostic_data': diagnostics} if kind == 'multi' else {}))


@pytest.mark.parametrize('kind', ['binary', 'multi', 'iv'])
@pytest.mark.parametrize('field', ['y', 'd', 'x', 'm_hat', 'g', 'folds', 'psi_b'])
def test_returned_diagnostics_own_arrays(kind, field):
    model = estimator(kind, dataset(kind))
    if kind != 'iv':
        model.store_diagnostics = True
    model.fit()
    first = estimate(model, kind)
    first_value = np.asarray(first.value).copy()
    diag = first.diagnostic_data
    name = ('g_hat' if kind == 'multi' else 'g0_hat') if field == 'g' else field
    original = getattr(diag, name).copy()
    getattr(diag, name)[...] = 0
    second = estimate(model, kind)
    np.testing.assert_array_equal(second.value, first_value)
    np.testing.assert_array_equal(getattr(second.diagnostic_data, name), original)
    getattr(second.diagnostic_data, name)[...] = 1
    np.testing.assert_array_equal(getattr(diag, name), np.zeros_like(original))


@pytest.mark.parametrize('kind', ['binary', 'multi', 'iv'])
@pytest.mark.parametrize('diagnostics', [False, True])
def test_fit_freezes_sample_and_schema_until_refit(kind, diagnostics):
    data = dataset(kind)
    model = estimator(kind, data)
    if kind != 'iv':
        model.store_diagnostics = diagnostics
    model.fit()
    first = estimate(model, kind, diagnostics)
    data.df.loc[:, 'y'] += 4
    # Assignment to role fields is currently part of the mutable contract API.
    if kind != 'multi':
        data.outcome_name = 'changed_y'
    # Rename consistently so this remains a valid new sample for refit.
    if kind == 'multi':
        data.outcome = 'changed_y'
    data.df.rename(columns={'y': 'changed_y'}, inplace=True)
    second = estimate(model, kind, diagnostics)
    np.testing.assert_array_equal(second.value, first.value)
    assert second.outcome == first.outcome == 'y'
    model.fit()
    third = estimate(model, kind, diagnostics)
    assert third.outcome == 'changed_y'
    fresh = estimator(kind, data)
    if kind != 'iv':
        fresh.store_diagnostics = diagnostics
    fresh.fit()
    np.testing.assert_array_equal(third.value, estimate(fresh, kind, diagnostics).value)
    np.testing.assert_array_equal(first.value, second.value)


@pytest.mark.parametrize('kind', ['binary', 'multi', 'iv'])
@pytest.mark.parametrize('stage', ['learner', 'configuration'])
def test_failed_refit_does_not_mix_samples(kind, stage):
    model = estimator(kind, dataset(kind)).fit()
    first = estimate(model, kind, False)
    new_data = dataset(kind)
    new_data.df.loc[:, 'y'] += 6
    if stage == 'learner':
        model.ml_g = ConstantRegressor(np.nan)
    else:
        model.n_folds = 1
    with pytest.raises((RuntimeError, ValueError)):
        model.fit(new_data)
    if kind == 'iv':
        with pytest.raises(NotFittedError):
            estimate(model, kind)
    else:
        np.testing.assert_array_equal(estimate(model, kind, False).value, first.value)
        assert model.data is not new_data


@pytest.mark.parametrize('kind', ['binary', 'multi', 'iv'])
def test_successful_refit_requires_new_inference(kind):
    model = estimator(kind, dataset(kind)).fit()
    first = estimate(model, kind, False)
    before = np.asarray(first.value).copy()
    new_data = dataset(kind)
    new_data.df.loc[:, 'y'] += 5
    model.fit(new_data)
    with pytest.raises(NotFittedError):
        _ = model.coef
    estimate(model, kind, False)
    np.testing.assert_array_equal(first.value, before)


@pytest.mark.parametrize('kind', ['binary', 'multi', 'iv'])
@pytest.mark.parametrize('role', ['treatment', 'confounder'])
def test_estimate_labels_and_diagnostic_feature_names_are_fit_snapshots(kind, role):
    data = dataset(kind)
    model = estimator(kind, data)
    if kind != 'iv':
        model.store_diagnostics = True
    model.fit()
    first = estimate(model, kind)
    if role == 'confounder':
        if kind == 'multi':
            data.confounders = ['changed_x']
        else:
            data.confounders_names = ['changed_x']
        data.df.rename(columns={'x': 'changed_x'}, inplace=True)
    elif kind == 'multi':
        data.treatment_names = ['d0', 'changed_d1', 'd2']
        data.df.rename(columns={'d1': 'changed_d1'}, inplace=True)
    else:
        data.treatment_name = 'changed_d'
        data.df.rename(columns={'d': 'changed_d'}, inplace=True)
    second = estimate(model, kind)
    assert second.treatment == first.treatment
    assert second.confounders == first.confounders
    if kind == 'multi':
        assert second.contrast_labels == first.contrast_labels
    if kind == 'iv':
        assert second.diagnostic_data.x_names == first.diagnostic_data.x_names
    model.fit()
    third = estimate(model, kind)
    assert (third.confounders != first.confounders if role == 'confounder'
            else third.treatment != first.treatment)


def test_iv_instrument_label_is_a_fit_snapshot():
    data = dataset('iv')
    model = estimator('iv', data).fit()
    first = model.estimate()
    data.instruments_names = ['changed_z']
    data.df.rename(columns={'z': 'changed_z'}, inplace=True)
    assert model.estimate().instrument == first.instrument == 'z'
    model.fit()
    assert model.estimate().instrument == 'changed_z'


def test_binary_failed_overlap_publication_keeps_previous_fit():
    model = estimator('binary', dataset('binary')).fit()
    first = model.estimate()
    old_y = model._y.copy()
    old_predictions = model.m_hat_.copy()
    model.ml_m = ConstantRegressor(0.2)
    model.overlap_policy = 'drop'
    model.overlap_threshold = 0.4
    new_data = dataset('binary')
    new_data.df.loc[:, 'y'] += 6
    with pytest.raises(ValueError, match='removed all observations'):
        model.fit(new_data)
    np.testing.assert_array_equal(model._y, old_y)
    np.testing.assert_array_equal(model.m_hat_, old_predictions)
    np.testing.assert_array_equal(model.estimate().value, first.value)


@pytest.mark.parametrize('kind', ['binary', 'multi', 'iv'])
def test_diagnostic_snapshots_survive_later_refit(kind):
    model = estimator(kind, dataset(kind))
    if kind != 'iv':
        model.store_diagnostics = True
    model.fit()
    first = estimate(model, kind)
    fields = {name: value.copy() for name, value in first.diagnostic_data.__dict__.items()
              if isinstance(value, np.ndarray)}
    new_data = dataset(kind)
    new_data.df.loc[:, 'y'] += 6
    model.fit(new_data)
    second = estimate(model, kind)
    for name, values in fields.items():
        np.testing.assert_array_equal(getattr(first.diagnostic_data, name), values)
        assert not np.shares_memory(getattr(first.diagnostic_data, name),
                                    getattr(second.diagnostic_data, name))
