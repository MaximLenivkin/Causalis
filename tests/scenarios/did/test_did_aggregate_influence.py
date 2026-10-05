"""Empirical refits test the complete-pair population aggregation functional."""

import numpy as np
import pandas as pd
import pytest

from causalis.data_contracts import PanelDataDID
from causalis.scenarios.did import CallawaySantAnnaDID
from causalis.scenarios.did.model import _aggregate_scores


def _panel(missing=False, noisy=False):
    periods = pd.period_range("2020-01", periods=5, freq="M")
    rows = []
    for unit in range(15):
        cohort, tau = (1, 2.) if unit < 4 else (2, 10.) if unit < 9 else (99, 0.)
        for t, time in enumerate(periods):
            if missing and ((unit == 0 and t == 3) or (unit == 4 and t == 4) or (unit == 12 and t == 1)):
                continue
            active = t >= cohort
            noise = .23 * t * ((unit % 3) - 1) if noisy else 0.
            rows.append(dict(unit=unit, time=time, d=int(active),
                             y=30 + unit + .3 * t + tau * active + noise))
    return PanelDataDID(df=pd.DataFrame(rows), y="y", unit_col="unit",
                        time_col="time", treated_time="d")


def _empirical_refit(weights, cells, unit_ids, diagnostics, *, kind):
    """Refit intercept-only cell means and aggregation under a weighted empirical law.

    This uses normalized means directly; it does not implement an influence formula.
    """
    positions = {unit: j for j, unit in enumerate(unit_ids)}
    cell_values, cell_counts = [], []
    for cell_id in cells.cell_id:
        diag = diagnostics[diagnostics.cell_id == cell_id]
        mass = weights[[positions[unit] for unit in diag.unit]]
        treated = diag.is_treated_cohort.to_numpy(dtype=bool)
        delta = diag.delta_y.to_numpy()
        cell_values.append(np.average(delta[treated], weights=mass[treated]) -
                           np.average(delta[~treated], weights=mass[~treated]))
        cell_counts.append(mass[treated].sum())
    cell_weights = np.ones(len(cells)) if kind == "cohort" else np.asarray(cell_counts)
    return np.average(cell_values, weights=cell_weights)


@pytest.mark.parametrize("kind", ["simple", "cohort", "calendar", "event"])
@pytest.mark.parametrize("missing", [False, True])
@pytest.mark.parametrize("noisy", [False, True])
def test_aggregate_scores_and_public_se_match_unit_contamination_refits(kind, missing, noisy):
    model = CallawaySantAnnaDID(control_group="never_treated").fit(_panel(missing, noisy))
    estimate = model.estimate()
    diag = estimate.diagnostics["unit_level"]
    unit_ids = list(estimate.diagnostics["influence_scores"].index)
    positions = {unit: j for j, unit in enumerate(unit_ids)}
    treated_positions = {
        cell_id: np.asarray([positions[unit] for unit in group.loc[group.is_treated_cohort == 1, "unit"]])
        for cell_id, group in diag.groupby("cell_id")
    }
    table, scores, _ = _aggregate_scores(model._att_gt, model._score_matrix, kind=kind,
                                         treated_unit_positions=treated_positions)
    source = model._att_gt
    epsilon = 1e-5
    n = len(unit_ids)
    for column, row in table.iterrows():
        cells = source
        if kind == "cohort":
            cells = cells[cells.cohort == row.cohort]
        elif kind == "calendar":
            cells = cells[cells.time == row.time]
        elif kind == "event":
            cells = cells[cells.event_time == row.event_time]
        weights = np.full(n, 1 / n)
        assert row.estimate == pytest.approx(_empirical_refit(weights, cells, unit_ids, diag, kind=kind))
        derivatives = []
        for unit in range(n):
            point_mass = np.eye(1, n, unit).ravel()
            plus = (1 - epsilon) * weights + epsilon * point_mass
            minus = (1 + epsilon) * weights - epsilon * point_mass
            derivatives.append((_empirical_refit(plus, cells, unit_ids, diag, kind=kind) -
                                _empirical_refit(minus, cells, unit_ids, diag, kind=kind)) / (2 * epsilon))
        np.testing.assert_allclose(scores[:, column], derivatives, atol=2e-7, rtol=2e-7)
        assert estimate.aggregates[kind].iloc[column].se == pytest.approx(np.linalg.norm(derivatives) / n, abs=2e-8)


@pytest.mark.parametrize("missing", [False, True])
def test_unit_order_and_diagnostic_output_choice_do_not_change_aggregate_inference(missing):
    panel = _panel(missing, noisy=True)
    permuted = PanelDataDID(df=panel.df_analysis().sample(frac=1., random_state=4), y="y",
                            unit_col="unit", time_col="time", treated_time="d")
    first = CallawaySantAnnaDID(control_group="never_treated").fit(panel).estimate()
    second = CallawaySantAnnaDID(control_group="never_treated").fit(permuted).estimate(diagnostic_data=False)
    for kind in ["simple", "cohort", "calendar", "event"]:
        np.testing.assert_allclose(first.aggregates[kind][["estimate", "se"]], second.aggregates[kind][["estimate", "se"]], atol=1e-12)


def _oracle_share_simulation(replications=600, n=600):
    rng = np.random.default_rng(4704)
    estimates, ses = [], []
    true_effect = 5.2  # q=[.3,.3,.4], 3 cells with tau=2 and 2 with tau=10
    for _ in range(replications):
        cohort = rng.choice(3, size=n, p=[.3, .3, .4])
        membership = {j: np.flatnonzero(cohort == (j >= 3)) for j in range(5)}
        cells = pd.DataFrame(dict(cell_id=range(5), att=[2.] * 3 + [10.] * 2,
                                  n_treated=[len(membership[j]) for j in range(5)],
                                  is_post_treatment=True))
        table, scores, _ = _aggregate_scores(cells, np.zeros((n, 5)), kind="simple",
                                             treated_unit_positions=membership)
        estimates.append(table.estimate.iloc[0])
        ses.append(np.linalg.norm(scores[:, 0]) / n)
    estimates, ses = np.asarray(estimates), np.asarray(ses)
    return dict(seed=4704, replications=replications, n=n, true_effect=true_effect,
                mean_estimate=float(estimates.mean()), empirical_sd=float(estimates.std(ddof=1)),
                rms_se=float(np.sqrt(np.mean(ses ** 2))),
                coverage=float(np.mean(np.abs(estimates - true_effect) <= 1.959963984540054 * ses)))


def test_population_share_oracle_coverage_is_not_degenerate():
    result = _oracle_share_simulation()
    assert .91 < result["coverage"] < .99
    assert .9 < result["rms_se"] / result["empirical_sd"] < 1.1
