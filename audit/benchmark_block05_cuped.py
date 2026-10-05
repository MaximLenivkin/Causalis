"""Controlled B05 fit-only benchmark: invoke in fresh single-thread processes.

Pass --source to prepend an extracted baseline package before imports.
Construction and estimation are outside the timed fit. Both workers generate
identical inputs. This is a small regression benchmark, not a global rating.
"""
import argparse
import json
from pathlib import Path
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(args.source.resolve() if args.source else ROOT))

import numpy as np
import pandas as pd
from causalis.data_contracts import RctCausalData
from causalis.scenarios.cuped import CUPEDModel

rng = np.random.default_rng(2781)
n = 12000
d = np.arange(n) % 2
x = rng.normal(size=(n, 4))
frame = pd.DataFrame(x, columns=[f"x{i}" for i in range(4)])
frame["d"] = d
for j in range(32):
    frame[f"y{j}"] = 20 + (j+1)/10 * d + x @ np.array([1., -.3, .6, .2]) + rng.normal(size=n)
records = []
for m in (1, 8, 32):
    names = [f"y{j}" for j in range(m)]
    data = RctCausalData.from_df(frame, "d", names, [f"x{i}" for i in range(4)])
    # Warm libraries and the same shape once before timing.
    CUPEDModel().fit(data, covariates=data.confounders_names, run_checks=True)
    seconds = []
    for _ in range(3):
        started = time.perf_counter()
        model = CUPEDModel().fit(data, covariates=data.confounders_names, run_checks=True)
        seconds.append(time.perf_counter() - started)
    estimates = model.estimate()
    children = [model] if m == 1 else [model._comparison_models[name]["d"] for name in names]
    records.append(dict(n=n, covariates=4, outcomes=m, cov_type="HC2", checks=True,
                        fit_seconds=seconds, median_fit_seconds=float(np.median(seconds)),
                        ate=[float(np.asarray(child._result.params)[1]) for child in children],
                        se=[float(np.asarray(child._result.bse)[1]) for child in children]))
result = dict(source=str(args.source.resolve() if args.source else ROOT),
              library_file=sys.modules["causalis.scenarios.cuped.model"].__file__,
              seed=2781, repetitions=3, native_threads=1, construction_timed=False,
              estimate_timed=False, cases=records)
args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
