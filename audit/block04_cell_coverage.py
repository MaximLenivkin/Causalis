"""Estimated-nuisance Monte Carlo for B04 cell inference (not a full pipeline benchmark)."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from scipy.special import expit

from causalis.scenarios.did.model import (
    _cell_influence_scores,
    _fit_logistic_propensity,
    _fit_outcome_regression,
)


def run(*, seed=48129, n=600, replications=600):
    records = []
    for kind in ("propensity_correct_outcome_misspecified", "outcome_correct_propensity_misspecified"):
        rng = np.random.default_rng(seed)
        estimates, standard_errors, old_standard_errors = [], [], []
        for _ in range(replications):
            x = rng.normal(size=n)
            design = np.column_stack([np.ones(n), x])
            if kind.startswith("propensity_correct"):
                p = expit(-0.15 + 0.8 * x)
                untreated_change = np.exp(0.6 * x)
            else:
                p = expit(-0.15 + 0.6 * x + 0.45 * x**2)
                untreated_change = 1.0 + 0.7 * x
            d = rng.binomial(1, p).astype(float)
            delta_y = untreated_change + rng.normal(size=n) + 2.0 * d
            gamma, fitted_p = _fit_logistic_propensity(design, d, clip=1e-6, ridge=0.0,
                                                       tol=1e-10, max_iter=1000)
            _, outcome = _fit_outcome_regression(design, delta_y, d == 0.0)
            wt = d / np.mean(d)
            odds = fitted_p * (1.0 - d) / (1.0 - fitted_p)
            wc = odds / np.mean(odds)
            residual = delta_y - outcome
            theta = float(np.mean((wt - wc) * residual))
            influence = _cell_influence_scores(design, d, residual, wt, wc, gamma,
                                                estimate_outcome=True, propensity_clip=1e-6,
                                                logit_ridge=0.0)
            old_influence = (wt - wc) * residual - wt * theta
            estimates.append(theta)
            standard_errors.append(np.linalg.norm(influence) / n)
            old_standard_errors.append(np.linalg.norm(old_influence) / n)
        estimates = np.asarray(estimates)
        standard_errors = np.asarray(standard_errors)
        old_standard_errors = np.asarray(old_standard_errors)
        empirical_sd = float(np.std(estimates, ddof=1))
        coverage = float(np.mean(np.abs(estimates - 2.0) <= 1.959963984540054 * standard_errors))
        record = {
            "dgp": kind, "seed": seed, "n": n, "replications": replications, "true_att": 2.0,
            "mean_att": float(np.mean(estimates)), "empirical_sd": empirical_sd,
            "mean_corrected_se": float(np.mean(standard_errors)),
            "rms_corrected_se": float(np.sqrt(np.mean(standard_errors**2))),
            "mean_old_se": float(np.mean(old_standard_errors)),
            "corrected_se_to_empirical_sd": float(np.mean(standard_errors) / empirical_sd),
            "old_se_to_empirical_sd": float(np.mean(old_standard_errors) / empirical_sd),
            "corrected_coverage": coverage,
            "old_coverage": float(np.mean(np.abs(estimates - 2.0) <= 1.959963984540054 * old_standard_errors)),
            "coverage_mcse": float(np.sqrt(coverage * (1.0 - coverage) / replications)),
        }
        records.append(record)
        print(json.dumps(record), flush=True)
    return records


if __name__ == "__main__":
    evidence = run()
    destination = Path(__file__).with_name("block04_cell_coverage.json")
    destination.write_text(json.dumps({"scope": "Cell DR estimator with estimated logistic MLE and control OLS; no ridge, no active clipping; fixed support and independent units. Does not validate arbitrary clusters, panel support selection, aggregation or clipping boundary inference.", "results": evidence}, indent=2) + "\n", encoding="utf-8")
