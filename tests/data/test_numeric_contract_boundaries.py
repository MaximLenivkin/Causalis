"""Regression coverage for real, finite numeric data contract boundaries."""

import warnings

import numpy as np
import pandas as pd
import pytest

from causalis.data_contracts import (
    CausalData,
    IVCausalData,
    MultiCausalData,
    PanelDataDID,
    PanelDataSCM,
)


def _cross_section():
    return pd.DataFrame(
        {
            "y": [1.5, 3.0, 2.0, 5.0, 2.5, 7.0],
            "d": [0, 1, 0, 1, 0, 1],
            "z": [0, 0, 1, 1, 0, 1],
            "x": [2.0, 1.0, 4.0, 3.0, 6.0, 5.0],
            "c": [1, 0, 1, 0, 1, 0],
        }
    )


def _cross_contract(kind, df):
    if kind == "multi":
        return MultiCausalData(
            df=df, outcome="y", treatment_names=["c", "d"],
            control_treatment="c", confounders=["x"],
        )
    kwargs = dict(df=df, outcome="y", treatment="d", confounders=["x"])
    if kind == "iv":
        return IVCausalData(**kwargs, instruments="z")
    return CausalData(**kwargs)


def _panel():
    times = pd.period_range("2020-01", periods=3, freq="M")
    return pd.DataFrame(
        [
            {"unit": unit, "time": time, "y": float(10 * unit_i + time_i),
             "d": int(unit == "T" and time_i >= 1), "x": float(3 * unit_i + time_i)}
            for unit_i, unit in enumerate(["T", "C1", "C2"])
            for time_i, time in enumerate(times)
        ]
    )


def _panel_contract(kind, df):
    kwargs = dict(df=df, y="y", unit_col="unit", time_col="time", treated_time="d")
    if kind == "did":
        return PanelDataDID(**kwargs, covariates=["x"])
    return PanelDataSCM(**kwargs)


@pytest.mark.parametrize("kind", ["binary", "iv", "multi"])
@pytest.mark.parametrize("column", ["y", "x"])
@pytest.mark.parametrize("value", [np.inf, -np.inf])
def test_cross_section_rejects_infinite_analysis_values(kind, column, value):
    df = _cross_section()
    df.loc[0, column] = value
    original = df.copy(deep=True)

    with pytest.raises(ValueError, match=rf"'{column}'.*finite"):
        _cross_contract(kind, df)
    pd.testing.assert_frame_equal(df, original)


@pytest.mark.parametrize("value", [np.inf, -np.inf, "inf", "-inf"])
def test_scm_rejects_infinite_outcome_after_numeric_coercion(value):
    df = _panel()
    df["y"] = df["y"].astype(object)
    df.loc[0, "y"] = value
    original = df.copy(deep=True)

    with pytest.raises(ValueError, match="'y'.*finite"):
        _panel_contract("scm", df)
    pd.testing.assert_frame_equal(df, original)


_CROSS_COMPLEX_ROLES = [
    ("binary", "y"), ("binary", "x"), ("binary", "d"),
    ("iv", "y"), ("iv", "x"), ("iv", "d"), ("iv", "z"),
    ("multi", "y"), ("multi", "x"), ("multi", "d"), ("multi", "c"),
]


@pytest.mark.parametrize("kind,column", _CROSS_COMPLEX_ROLES)
@pytest.mark.parametrize("imaginary", [0.0, 2.0])
def test_cross_section_rejects_complex_before_lossy_conversion(kind, column, imaginary):
    df = _cross_section()
    df[column] = df[column].astype(np.complex128) + imaginary * 1j
    original = df.copy(deep=True)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(ValueError, match=rf"'{column}'.*real"):
            _cross_contract(kind, df)
    assert not any(w.category.__name__ == "ComplexWarning" for w in caught)
    pd.testing.assert_frame_equal(df, original)


@pytest.mark.parametrize("kind,column", [("did", "y"), ("did", "x"), ("did", "d"),
                                         ("scm", "y"), ("scm", "d")])
@pytest.mark.parametrize("imaginary", [0.0, 2.0])
def test_panel_rejects_complex_before_lossy_conversion(kind, column, imaginary):
    df = _panel()
    df[column] = df[column].astype(np.complex128) + imaginary * 1j
    original = df.copy(deep=True)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(ValueError, match=rf"'{column}'.*real"):
            _panel_contract(kind, df)
    assert not any(w.category.__name__ == "ComplexWarning" for w in caught)
    pd.testing.assert_frame_equal(df, original)


@pytest.mark.parametrize("kind", ["did", "scm"])
def test_panel_rejects_complex_treatment_in_object_column(kind):
    df = _panel()
    df["d"] = df["d"].astype(object)
    df.loc[0, "d"] = 0j

    with pytest.raises(ValueError, match="'d'.*real"):
        _panel_contract(kind, df)


@pytest.mark.parametrize("kind,column", [("did", "y"), ("did", "x"), ("scm", "y")])
def test_panel_rejects_zero_imaginary_analysis_values_in_object_column(kind, column):
    df = _panel()
    df[column] = df[column].astype(object)
    df.loc[0, column] = complex(df.loc[0, column])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(ValueError, match=rf"'{column}'.*real"):
            _panel_contract(kind, df)
    assert not any(w.category.__name__ == "ComplexWarning" for w in caught)


@pytest.mark.parametrize("kind", ["binary", "iv", "multi"])
@pytest.mark.parametrize("dtype", ["Float64", "Int64"])
def test_cross_section_preserves_finite_nullable_real_columns(kind, dtype):
    df = _cross_section()
    df["y"] = pd.Series([1, 3, 2, 5, 4, 7], dtype=dtype)
    df["x"] = df["x"].astype(dtype)
    df["d"] = df["d"].astype("boolean")
    df["z"] = df["z"].astype("boolean")
    df["c"] = df["c"].astype("boolean")
    original = df.copy(deep=True)

    data = _cross_contract(kind, df)

    pd.testing.assert_series_equal(data.df["y"], df["y"])
    pd.testing.assert_series_equal(data.df["x"], df["x"])
    assert data.df["d"].dtype == np.dtype("int8")
    pd.testing.assert_frame_equal(df, original)


@pytest.mark.parametrize("kind", ["did", "scm"])
@pytest.mark.parametrize("dtype", ["Float64", "Int64", "string"])
def test_panels_preserve_finite_real_and_numeric_string_support(kind, dtype):
    df = _panel()
    df["y"] = df["y"].astype(dtype)
    df["x"] = df["x"].astype(dtype)
    df["d"] = df["d"].astype("boolean")
    original = df.copy(deep=True)

    data = _panel_contract(kind, df)

    assert np.allclose(data.df["y"].to_numpy(dtype=float), original["y"].to_numpy(dtype=float))
    assert data.df["d"].dtype == np.dtype("int64")
    pd.testing.assert_frame_equal(df, original)
