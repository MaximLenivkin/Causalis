"""Print deterministic independent multi-ATT coverage evidence used by tests."""

import json
from pathlib import Path
import runpy

import numpy as np


def main():
    root = Path(__file__).resolve().parents[1]
    namespace = runpy.run_path(str(root / "tests/inference/test_multi_treatment_irm_ratio_if.py"))
    metrics = namespace["_oracle_interval_calibration"]()
    metrics["reported_to_empirical_sd"] = metrics["reported_sd"] / metrics["empirical_sd"]
    serializable = {key: value.tolist() if isinstance(value, np.ndarray) else value for key, value in metrics.items()}
    print(json.dumps(serializable, indent=2))


if __name__ == "__main__":
    main()
