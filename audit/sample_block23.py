"""Seeded clustered synthetic sampling check; retain statistical aggregates only."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LinearRegression, LogisticRegression
from causalis.data_contracts import CausalData
from causalis.scenarios.unconfoundedness import IRM

ROOT = Path(__file__).resolve().parents[1]


def main():
    started = time.perf_counter()
    rng = np.random.default_rng(233841)
    draws, clusters, truth = 400, 80, 0.7
    summaries = {(n_rep, score): dict(values=[], errors=[], iid_errors=[], coverage=0, iid_coverage=0)
                 for n_rep in (1, 3) for score in ('ATE', 'ATTE')}
    for _ in range(draws):
        sizes = rng.integers(4, 13, size=clusters)
        groups = np.repeat(np.arange(clusters), sizes)
        d = np.repeat(rng.binomial(1, 0.5, clusters), sizes)
        x = rng.normal(size=len(groups))
        shock = np.repeat(rng.normal(size=clusters), sizes)
        y = 10 + 0.6*x + truth*d + shock + rng.normal(scale=0.3, size=len(groups))
        sample = CausalData(df=pd.DataFrame(dict(x=x, d=d, y=y)),
                            outcome='y', treatment='d', confounders=['x'])
        fitted = IRM(sample, ml_g=LinearRegression(), ml_m=LogisticRegression(max_iter=300),
                     cluster_groups=groups, n_folds=4, n_rep=3, random_state=17,
                     store_diagnostics=False).fit()
        for score in ('ATE', 'ATTE'):
            result = fitted.estimate(score=score)
            partitions = fitted._fit_repetitions_
            estimates = result.repetition_estimates
            iid_errors = [float(model.psi_.std(ddof=1)/len(groups)**0.5) for model in partitions]
            for n_rep in (1, 3):
                item = estimates[0] if n_rep == 1 else result
                iid_error = iid_errors[0] if n_rep == 1 else float(np.sqrt(np.median(
                    [se**2+(effect.value-result.value)**2 for se, effect in zip(iid_errors, estimates)])))
                record = summaries[(n_rep, score)]
                record['values'].append(item.value)
                record['errors'].append(item.model_options['std_error'])
                record['iid_errors'].append(iid_error)
                record['coverage'] += int(item.ci_lower_absolute <= truth <= item.ci_upper_absolute)
                record['iid_coverage'] += int(abs(item.value-truth) <= norm.ppf(0.975)*iid_error)
    payload = dict(seed=233841, synthetic_samples=draws, clusters_per_sample=clusters,
                   cluster_size_range=[4, 12], n_folds=4, split_seed=17, truth=truth,
                   dgp='Independent clusters; sizes independent of assignment/shocks; cluster-randomized Bernoulli(.5) treatment; iid normal X; Y=10+.6X+.7D+cluster N(0,1)+iid N(0,.3^2)',
                   iid_comparator='Same cluster-disjoint nuisance fits and point estimates; replace each cluster SE with iid row IF SE, then same repeated aggregation',
                   observed_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                   source_sha256={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
                                  for path in ('causalis/scenarios/unconfoundedness/model.py',
                                               'causalis/scenarios/unconfoundedness/_cluster.py',
                                               'causalis/scenarios/unconfoundedness/_repeated.py')},
                   elapsed_seconds=time.perf_counter()-started, scores={},
                   limitations=['One favorable DGP/learner pair with 80 independent clusters; not a small-G guarantee.',
                                'Coverage MC SE around .011 at 95%; iid comparator isolates variance misspecification.'])
    for (n_rep, score), record in summaries.items():
        sd = float(np.std(record['values'], ddof=1))
        payload['scores'][f'{score}_rep{n_rep}'] = dict(
            mean_estimate=float(np.mean(record['values'])), empirical_sd=sd,
            mean_se=float(np.mean(record['errors'])),
            mean_se_over_empirical_sd=float(np.mean(record['errors'])/sd),
            covered=record['coverage'], coverage_95=record['coverage']/draws,
            iid_mean_se=float(np.mean(record['iid_errors'])),
            iid_mean_se_over_empirical_sd=float(np.mean(record['iid_errors'])/sd),
            iid_covered=record['iid_coverage'], iid_coverage_95=record['iid_coverage']/draws)
    (ROOT/'audit/block23_sampling_result.json').write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
