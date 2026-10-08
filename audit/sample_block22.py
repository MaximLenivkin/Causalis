"""Seeded synthetic iid finite-sample check; aggregate evidence only."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import time

os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from causalis.data_contracts import CausalData
from causalis.scenarios.unconfoundedness import IRM

ROOT = Path(__file__).resolve().parents[1]


def main():
    started = time.perf_counter()
    values = {'ATE': [], 'ATTE': []}
    errors = {'ATE': [], 'ATTE': []}
    coverage = {'ATE': 0, 'ATTE': 0}
    truth, repetitions, n = 0.7, 200, 600
    seed = 92217
    rng = np.random.default_rng(seed)
    for _ in range(repetitions):
        x = rng.normal(size=n)
        d = rng.binomial(1, 1 / (1 + np.exp(-0.4 * x)))
        y = 4 + 0.6 * x + truth * d + rng.normal(size=n)
        sample = CausalData(df=pd.DataFrame({'x': x, 'd': d, 'y': y}),
                            outcome='y', treatment='d', confounders=['x'])
        model = IRM(sample, ml_g=LinearRegression(), ml_m=LogisticRegression(max_iter=300),
                    n_folds=3, n_rep=3, random_state=17, store_diagnostics=False).fit()
        for score in values:
            result = model.estimate(score=score)
            values[score].append(result.value)
            errors[score].append(result.model_options['std_error'])
            coverage[score] += int(result.ci_lower_absolute <= truth <= result.ci_upper_absolute)
    payload = dict(dgp='iid normal X; logistic assignment; linear Y with constant effect and independent normal noise',
                   seed=seed, synthetic_samples=repetitions, rows_per_sample=n, split_repetitions=3,
                   n_folds=3, split_seed=17, truth=truth,
                   observed_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                   elapsed_seconds=time.perf_counter()-started, scores={},
                   limitations=['One favorable specified DGP and learner pair.',
                                'Coverage Monte Carlo SE about 0.015 at 95%; no universal coverage or stability guarantee.'])
    for score in values:
        sd = float(np.std(values[score], ddof=1))
        payload['scores'][score] = dict(mean_estimate=float(np.mean(values[score])), empirical_sd=sd,
                                        mean_se=float(np.mean(errors[score])), mean_se_over_empirical_sd=float(np.mean(errors[score])/sd),
                                        covered=coverage[score], coverage_95=coverage[score]/repetitions)
    (ROOT/'audit/block22_sampling_result.json').write_text(json.dumps(payload,indent=2))
    print(json.dumps(payload,indent=2))


if __name__ == '__main__':
    main()
