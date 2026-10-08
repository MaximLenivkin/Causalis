"""Record the retained conservative row-support gate separately from pytest."""
import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.model_selection import KFold

from causalis.data_contracts import CausalData
from causalis.scenarios.unconfoundedness import IRM

ROOT = Path(__file__).resolve().parents[1]


class NoFit(BaseEstimator, RegressorMixin):
    def fit(self, X, y):
        raise AssertionError('The retained support guard must precede learner fitting')


groups = np.repeat(np.arange(20), 2)
d = np.zeros(40, dtype=int)
d[[0, 4]] = 1
data = CausalData(df=pd.DataFrame(dict(x=np.arange(40), d=d, y=10+0.7*d)),
                  outcome='y', treatment='d', confounders=['x'])
# In this specified split every training complement contains both arms, but
# the old input gate still requires at least n_folds rows in each arm.
for _, held_out in KFold(4, shuffle=True, random_state=13).split(np.arange(20)):
    assert np.unique(d[~np.isin(groups, held_out)]).size == 2
rejections = []
for repetitions in (1, 3):
    model = IRM(data, ml_g=NoFit(), ml_m=NoFit(), cluster_groups=groups,
                n_folds=4, n_rep=repetitions, random_state=13)
    try:
        model.fit()
    except ValueError as error:
        assert 'minimum treatment class count=2' in str(error)
        rejections.append(dict(n_rep=repetitions, error=str(error)))
    else:
        raise AssertionError('Retained conservative support gate was relaxed')
result = dict(tested_source_checkpoint=subprocess.check_output(
    ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    synthetic=True, training_arm_support_verified=True,
    minimum_rows_per_arm=2, n_folds=4, independent_clusters=20,
    rejected_before_fitting=rejections, pytest_cases_added=0,
    limitation='Inherited row count gate remains n_folds <= min treatment arm count, even if a group partition otherwise has both arms in every training complement')
(ROOT/'audit/block23_support_result.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
