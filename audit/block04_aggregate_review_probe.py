"""Independent finite differences of the empirical complete-pair mixture.

This audit-only check does not import the estimator or its aggregation helper.
It perturbs the empirical probability measure, recomputes all mixture counts
and the entire ratio, and compares with the independently derived derivative.
"""

from __future__ import annotations

import json

import numpy as np


def check_case(*, unbalanced: bool, moving_cells: bool) -> dict[str, object]:
    n = 11
    complete_treated = np.zeros((n, 5))
    complete_treated[:3, :3] = 1.0
    complete_treated[3:7, 3:] = 1.0
    if unbalanced:
        complete_treated[0, 1] = 0.0
        complete_treated[2, 2] = 0.0
        complete_treated[3, 3] = 0.0
        complete_treated[5:7, 4] = 0.0

    theta = np.array([2.0, 4.0, -1.0, 7.0, 11.0])
    p0 = np.full(n, 1.0 / n)
    # An independent linear empirical functional for each cell supplies a
    # nonzero cell derivative as well as the independently moving cell weights.
    h = np.sin(np.arange(n * 5).reshape(n, 5) * 0.7)
    h -= p0 @ h
    if not moving_cells:
        h[:] = 0.0

    def functional(probability: np.ndarray) -> float:
        q = probability @ complete_treated
        cell_effect = theta + probability @ h
        return float(np.dot(q, cell_effect) / np.sum(q))

    q0 = p0 @ complete_treated
    total_mass = float(np.sum(q0))
    aggregate = functional(p0)
    fixed_weight_component = h @ (q0 / total_mass)
    weight_component = complete_treated @ (theta - aggregate) / total_mass
    influence = fixed_weight_component + weight_component

    # Central differences stay inside the probability simplex: epsilon is less
    # than each empirical mass, so both contaminated measures are positive.
    eps = 1e-6
    numeric = np.empty(n)
    for i in range(n):
        atom = np.zeros(n)
        atom[i] = 1.0
        direction = atom - p0
        numeric[i] = (functional(p0 + eps * direction) - functional(p0 - eps * direction)) / (2 * eps)

    error = float(np.max(np.abs(numeric - influence)))
    assert error < 3e-8, (unbalanced, moving_cells, error)
    assert abs(float(p0 @ influence)) < 1e-14

    # Deliberately wrong full-cohort indicators are the original complete-case
    # counts' incompatible derivative when cells have different missing pairs.
    whole_cohort = np.zeros_like(complete_treated)
    whole_cohort[:3, :3] = 1.0
    whole_cohort[3:7, 3:] = 1.0
    wrong_weight_component = (whole_cohort - p0 @ whole_cohort) @ (theta - aggregate) / total_mass
    wrong_error = float(np.max(np.abs(numeric - fixed_weight_component - wrong_weight_component)))
    if unbalanced:
        assert wrong_error > 1.0

    return {
        "case": "unbalanced" if unbalanced else "balanced",
        "moving_cell_functionals": moving_cells,
        "n_units": n,
        "complete_treated_counts": complete_treated.sum(axis=0).astype(int).tolist(),
        "aggregate": aggregate,
        "maximum_contamination_derivative_error": error,
        "maximum_error_with_whole_cohort_instead_of_complete_pair_derivative": wrong_error,
        "influence_mean": float(p0 @ influence),
    }


if __name__ == "__main__":
    results = [
        check_case(unbalanced=unbalanced, moving_cells=moving_cells)
        for unbalanced in (False, True)
        for moving_cells in (False, True)
    ]
    print(json.dumps({"status": "passed", "cases": results}, indent=2))
