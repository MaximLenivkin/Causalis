"""Cluster inference must use independent clusters and coherent score covariance."""

import itertools

import numpy as np
import pandas as pd
import pytest

from causalis.data_contracts import PanelDataDID
from causalis.scenarios.did import CallawaySantAnnaDID
from causalis.scenarios.did.model import _draw_multiplier_weights, _variance_from_scores


def _panel(cluster_count):
    periods = pd.period_range("2020-01", periods=2, freq="M")
    rows = []
    for unit in range(12):
        treated = unit < 6
        for t, time in enumerate(periods):
            rows.append(dict(unit=unit, time=time, d=int(treated and t == 1),
                             y=unit + t * (2 * treated + (unit % 4) / 3),
                             cluster=unit % cluster_count))
    return PanelDataDID(df=pd.DataFrame(rows), y="y", unit_col="unit",
                        time_col="time", treated_time="d", cluster_col="cluster")


@pytest.mark.parametrize("replications", [0, 2, 199])
@pytest.mark.parametrize("override", [False, True])
def test_one_cluster_rejected_for_all_public_inference_paths(replications, override):
    model = CallawaySantAnnaDID(bootstrap_replications=0 if override else replications).fit(_panel(1))
    kwargs = {"bootstrap_replications": replications} if override else {}
    with pytest.raises(ValueError, match="at least two clusters"):
        model.estimate(**kwargs)


@pytest.mark.parametrize("override", [False, True])
def test_single_bootstrap_replication_rejected(override):
    with pytest.raises(ValueError, match="0 or at least 2"):
        if override:
            CallawaySantAnnaDID().fit(_panel(3)).estimate(bootstrap_replications=1)
        else:
            CallawaySantAnnaDID(bootstrap_replications=1)


class _EnumeratedDraws:
    """Enumerate all sign patterns instead of using a Monte Carlo tolerance."""

    def choice(self, values, size):
        rows, clusters = size
        draws = np.asarray(list(itertools.product(values, repeat=clusters)))
        assert draws.shape == (rows, clusters)
        return draws


def test_cluster_multiplier_exact_covariance_matches_analytic_finite_cluster_formula():
    clusters = np.asarray(["z", "z", "a", "b", "b", "b"], dtype=object)
    # Nonzero column sums deliberately test the centered-cluster formula too.
    scores = np.asarray([[2., 1.], [3., -2.], [-1., 4.], [5., 0.], [-2., 3.], [1., 2.]])
    weights = _draw_multiplier_weights(n_units=6, clusters=clusters,
                                      replications=8, rng=_EnumeratedDraws())
    shifts = weights @ scores / 6
    actual = shifts.T @ shifts / len(shifts)
    cluster_scores = np.vstack([scores[clusters == name].sum(axis=0) for name in ["z", "a", "b"]])
    centered = cluster_scores - cluster_scores.mean(axis=0)
    expected = (3 / 2) * centered.T @ centered / 36
    np.testing.assert_allclose(actual, expected, atol=1e-14)
    np.testing.assert_allclose(np.diag(actual), [_variance_from_scores(scores[:, j], clusters) for j in range(2)])
    np.testing.assert_array_equal(weights[:, 0], weights[:, 1])
    np.testing.assert_array_equal(weights[:, 3], weights[:, 4])


def test_valid_cluster_bootstrap_reproducible_and_includes_population_share_uncertainty():
    model = CallawaySantAnnaDID(random_state=9).fit(_panel(3))
    analytical = model.estimate()
    first = model.estimate(bootstrap_replications=2000)
    second = model.estimate(bootstrap_replications=2000)
    pd.testing.assert_frame_equal(first.att_gt, second.att_gt)
    pd.testing.assert_frame_equal(first.aggregates["simple"], second.aggregates["simple"])
    assert first.inference == "clustered_multiplier_bootstrap"
    assert first.se == pytest.approx(analytical.se, rel=.05)
    assert np.isfinite(first.att_gt["sim_ci_lower"]).all()
