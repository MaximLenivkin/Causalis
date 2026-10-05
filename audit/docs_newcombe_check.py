"""Independent numerical check of the documented Newcombe method; no source edits."""
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / "audit" / ".mplconfig"))
sys.path.insert(0, str(Path.cwd()))
import numpy as np
import pandas as pd
from statsmodels.stats.proportion import confint_proportions_2indep
from causalis.data_contracts import CausalData
from causalis.scenarios.classic_rct.inference.conversion_ztest import conversion_ztest

data = CausalData(
    df=pd.DataFrame({"d": [0] * 100 + [1] * 100,
                     "y": [1] * 10 + [0] * 90 + [1] * 20 + [0] * 80}),
    treatment="d", outcome="y", confounders=[],
)
actual = conversion_ztest(data, ci_method="newcombe")["absolute_ci"]
reference = confint_proportions_2indep(20, 100, 10, 100, method="newcomb", compare="diff")
result = {
    "case": {"x1": 20, "n1": 100, "x0": 10, "n0": 100, "alpha": 0.05},
    "causalis_newcombe": list(actual),
    "statsmodels_newcomb": list(reference),
    "same_interval": bool(np.allclose(actual, reference)),
}
Path("audit/docs_newcombe_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
