"""Validate matched fit benchmark inputs and summarize the actual measurements."""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
before = json.loads((HERE / "block05_benchmark_before.json").read_text(encoding="utf-8"))
after = json.loads((HERE / "block05_benchmark_after.json").read_text(encoding="utf-8"))
for key in ("seed", "repetitions", "native_threads", "construction_timed", "estimate_timed"):
    assert before[key] == after[key]
cases = []
for old, new in zip(before["cases"], after["cases"], strict=True):
    for key in ("n", "covariates", "outcomes", "cov_type", "checks"):
        assert old[key] == new[key]
    np.testing.assert_allclose(old["ate"], new["ate"], rtol=1e-11, atol=1e-11)
    np.testing.assert_allclose(old["se"], new["se"], rtol=1e-11, atol=1e-11)
    cases.append(dict(outcomes=old["outcomes"], before_seconds=old["median_fit_seconds"],
                      after_seconds=new["median_fit_seconds"],
                      speedup=old["median_fit_seconds"]/new["median_fit_seconds"],
                      max_ate_difference=float(np.max(np.abs(np.array(old["ate"])-new["ate"]))),
                      max_se_difference=float(np.max(np.abs(np.array(old["se"])-new["se"])))))
result = dict(baseline_commit="bb31a4b", cases=cases, workers="Sequential fresh processes",
              limits=["12000 rows,4 covariates,HC2,checks=True; only this RCT design",
                      "One warmup and3 repetitions; medians are local observations, not a guaranteed speedup",
                      "Input construction,estimate() and memory consumption are not timed or benchmarked",
                      "No comparison with a different library or dependency version matrix"])
(HERE / "block05_benchmark_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
