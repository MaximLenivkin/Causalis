"""Exact Gaussian KDE must not require an observation-by-grid allocation."""

import importlib
import tracemalloc
from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest
from scipy.stats import gaussian_kde


plots = importlib.import_module("causalis.shared.outcome_plots")


def _dense_reference(x, xs, h):
    """Original dense estimator, independent of the production block loops."""
    x = np.asarray(x, float)
    if not x.size:
        return np.zeros_like(xs)
    if x.size < 2 or np.std(x) < 1e-12:
        h = max(h, 1e-3)
        return np.exp(-0.5 * ((xs - np.mean(x)) / h) ** 2) / (
            np.sqrt(2 * np.pi) * h
        )
    return (
        np.exp(-0.5 * ((xs[None, :] - x[:, None]) / h) ** 2)
        / (np.sqrt(2 * np.pi) * h)
    ).mean(axis=0)


@pytest.mark.parametrize("budget", [16, 128, 8192, 8 * 1024 * 1024])
@pytest.mark.parametrize("kind", ["normal", "skewed", "separated"])
def test_exact_kde_matches_dense_across_block_sizes(kind, budget):
    rng = np.random.default_rng(647)
    if kind == "normal":
        x = rng.normal(size=47)
    elif kind == "skewed":
        x = rng.lognormal(size=47)
    else:
        x = np.concatenate([rng.normal(-8, 0.1, 24), rng.normal(8, 0.1, 23)])
    xs = np.linspace(-12, 12, 53)
    h = plots._silverman_bandwidth(x)
    x_before, xs_before = x.copy(), xs.copy()

    actual = plots._kde_unbounded(x, xs, h, max_work_bytes=budget)

    np.testing.assert_allclose(actual, _dense_reference(x, xs, h), rtol=2e-14, atol=2e-15)
    np.testing.assert_array_equal(x, x_before)
    np.testing.assert_array_equal(xs, xs_before)


@pytest.mark.parametrize("budget", [128, 8192, 8 * 1024 * 1024])
def test_kde_matches_scipy_with_the_same_absolute_bandwidth(budget):
    x = np.random.default_rng(61).normal(size=97)
    xs = np.linspace(-4, 4, 83)
    h = plots._silverman_bandwidth(x)
    # scipy's scalar bw_method multiplies the ddof=1 sample standard deviation.
    oracle = gaussian_kde(x, bw_method=h / np.std(x, ddof=1))(xs)

    actual = plots._kde_unbounded(x, xs, h, max_work_bytes=budget)

    np.testing.assert_allclose(actual, oracle, rtol=2e-13, atol=2e-15)


@pytest.mark.parametrize("budget", [128, 4096])
def test_kde_row_permutation_only_changes_summation_roundoff(budget):
    rng = np.random.default_rng(481)
    x = rng.normal(size=151)
    xs = np.linspace(-5, 5, 113)
    h = plots._silverman_bandwidth(x)
    expected = plots._kde_unbounded(x, xs, h, max_work_bytes=budget)

    actual = plots._kde_unbounded(rng.permutation(x), xs, h, max_work_bytes=budget)

    np.testing.assert_allclose(actual, expected, rtol=2e-14, atol=2e-15)


@pytest.mark.parametrize("x", [np.array([]), np.array([4.0]), np.full(7, 4.0),
                              np.array([4.0, 4.0 + 1e-13])])
def test_empty_single_and_nearly_constant_semantics_are_preserved(x):
    xs = np.linspace(3.98, 4.02, 41)
    h = plots._silverman_bandwidth(x)

    actual = plots._kde_unbounded(x, xs, h, max_work_bytes=16)

    np.testing.assert_array_equal(actual, _dense_reference(x, xs, h))


def test_kde_empty_grid_preserves_empty_float_output():
    actual = plots._kde_unbounded(np.array([1.0, 2.0]), np.array([]), 0.3)
    assert actual.shape == (0,)
    assert actual.dtype == np.dtype(float)


def test_kde_extreme_grid_keeps_zero_tails_and_infinite_nan_behavior():
    x = np.array([-1.0, 0.0, 1.0])
    xs = np.array([-np.inf, -1e308, -3.0, 0.0, 3.0, 1e308, np.inf, np.nan])
    with np.errstate(over="ignore", invalid="ignore"):
        actual = plots._kde_unbounded(x, xs, 0.1, max_work_bytes=32)
        expected = _dense_reference(x, xs, 0.1)
    np.testing.assert_allclose(actual, expected, rtol=2e-14, atol=0, equal_nan=True)
    np.testing.assert_array_equal(actual[[0, 1, 5, 6]], np.zeros(4))


@pytest.mark.parametrize("budget", [15, 0, -32, 32.0, True, np.bool_(True), "32", None])
def test_invalid_private_memory_budget_is_rejected(budget):
    with pytest.raises(ValueError, match="integer of at least 16 bytes"):
        plots._kde_unbounded(np.array([1.0, 2.0]), np.array([1.0]), 0.3,
                             max_work_bytes=budget)


def test_numpy_integer_memory_budget_is_accepted():
    actual = plots._kde_unbounded(np.array([1.0, 2.0]), np.array([1.0]), 0.3,
                                 max_work_bytes=np.int64(32))
    assert np.isfinite(actual).all()


def test_kernel_work_arrays_and_every_pair_stay_within_budget(monkeypatch):
    x = np.arange(37, dtype=float)
    xs = np.linspace(-1, 38, 113)
    h = 0.3
    expected = _dense_reference(x, xs, h)
    allocations, pair_counts = [], []
    original_empty, original_subtract = np.empty, np.subtract

    def tracked_empty(shape, *args, **kwargs):
        result = original_empty(shape, *args, **kwargs)
        allocations.append(result)
        return result

    def tracked_subtract(left, right, *args, **kwargs):
        result = original_subtract(left, right, *args, **kwargs)
        pair_counts.append(result.size)
        assert kwargs["out"] is result
        return result

    monkeypatch.setattr(plots.np, "empty", tracked_empty)
    monkeypatch.setattr(plots.np, "subtract", tracked_subtract)
    actual = plots._kde_unbounded(x, xs, h, max_work_bytes=512)

    assert len(allocations) == 2  # One reusable kernel block and one sum vector.
    assert sum(array.nbytes for array in allocations) <= 512
    assert allocations[0].shape[0] < x.size
    assert allocations[0].shape[1] < xs.size
    assert sum(pair_counts) == x.size * xs.size  # Every pair evaluated once.
    np.testing.assert_allclose(actual, expected, rtol=2e-14, atol=2e-15)


def test_traced_peak_avoids_dense_allocation_for_large_n():
    x = np.random.default_rng(827).normal(size=20_000)
    xs = np.linspace(-5, 5, 801)
    budget = 128 * 1024
    tracemalloc.start()
    try:
        result = plots._kde_unbounded(x, xs, 0.3, max_work_bytes=budget)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert np.isfinite(result).all()
    # Allow linear std scratch and NumPy iterator/reduction buffers, besides
    # the explicit budget and output. One dense matrix alone is 122 MiB here.
    assert peak < 8 * x.size + budget + 16 * xs.size + 256 * 1024
    assert peak < x.size * xs.size * 8 / 100


def test_constant_bump_work_array_also_stays_within_budget(monkeypatch):
    xs = np.linspace(3.9, 4.1, 103)
    x = np.full(7, 4.0)
    expected = _dense_reference(x, xs, 1e-6)
    allocations = []
    original_empty = np.empty

    def tracked_empty(shape, *args, **kwargs):
        result = original_empty(shape, *args, **kwargs)
        allocations.append(result)
        return result

    monkeypatch.setattr(plots.np, "empty", tracked_empty)
    actual = plots._kde_unbounded(x, xs, 1e-6, max_work_bytes=16)
    assert len(allocations) == 1
    assert allocations[0].nbytes <= 16
    np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize("density", [True, False])
def test_public_plot_keeps_grid_filter_bandwidth_and_count_scaling(monkeypatch, density):
    y = np.linspace(-3, 4, 60)
    y[[1, 31]] = np.inf
    y[[2, 32]] = np.nan
    frame = pd.DataFrame({"d": np.repeat([0, 1], 30), "y": y})
    data = SimpleNamespace(df=frame, treatment="d", outcome="y")
    captured = []
    original = plots._kde_unbounded

    def capture(x, xs, h):
        captured.append((x.copy(), xs.copy(), h))
        return original(x, xs, h, max_work_bytes=128)

    monkeypatch.setattr(plots, "_kde_unbounded", capture)
    figure = plots.outcome_plot_dist(data, bins=11, density=density, clip=(0.1, 0.9))
    lines = [line for line in figure.axes[0].lines if "(KDE)" in line.get_label()]
    lo, hi = np.quantile(frame.y.dropna().to_numpy(), [0.1, 0.9])
    assert len(captured) == len(lines) == 2
    for treatment, ((x, xs, h), line) in enumerate(zip(captured, lines)):
        expected_x = frame.loc[frame.d == treatment, "y"].to_numpy()
        expected_x = expected_x[np.isfinite(expected_x)]
        np.testing.assert_array_equal(x, expected_x)
        np.testing.assert_array_equal(xs, np.linspace(lo, hi, 800))
        assert h == plots._silverman_bandwidth(expected_x)
        expected_density = _dense_reference(x, xs, h)
        if not density:
            expected_density *= x.size * (hi - lo) / 11
        np.testing.assert_array_equal(line.get_xdata(), xs)
        np.testing.assert_allclose(line.get_ydata(), expected_density, rtol=2e-14, atol=2e-15)
