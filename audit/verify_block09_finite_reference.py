"""Compare valid B08/B09 schemas, values and RNG on the exact recorded baseline."""
from pathlib import Path
import json
import subprocess
import sys
import types

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "74145665127f8fa5a0bf038d769697ab880854b8"
sys.path.insert(0, str(ROOT))
from causalis.dgp.multicausaldata.base import MultiCausalDatasetGenerator as Current

module_name = "_block09_baseline_generator"
module = types.ModuleType(module_name)
sys.modules[module_name] = module
source = subprocess.check_output(
    ["git", "show", f"{BASELINE}:causalis/dgp/multicausaldata/base.py"], cwd=ROOT
).decode("utf-8")
exec(compile(source, module_name, "exec"), module.__dict__)
Legacy = module.MultiCausalDatasetGenerator


def main():
    rows = []
    for family in ("continuous", "binary", "poisson", "gamma"):
        for oracle in (False, True):
            for custom in (False, True):
                for schema in ("default", "categorical", "copula", "custom_sampler"):
                    kwargs = dict(
                        k=2, seed=731, outcome_type=family, include_oracle=oracle,
                        u_strength_d=.3, u_strength_y=.7, target_d_rate=[.2, .3, .5],
                        beta_y=np.array([.2, -.1]), beta_d=np.array([.1, .2]),
                    )
                    if schema == "categorical":
                        kwargs.update(
                            d_names=["control arm", "β", "treatment__1"],
                            confounder_specs=[
                                {"name": "feature", "dist": "normal"},
                                {"name": "level", "dist": "categorical", "categories": ["base", "b"]},
                            ],
                        )
                    elif schema == "copula":
                        # Continuous marginals isolate schema compatibility from
                        # the separately recorded categorical-copula sampling bug.
                        kwargs.update(
                            confounder_specs=[
                                {"name": "feature", "dist": "normal"},
                                {"name": "amount", "dist": "uniform"},
                            ],
                            use_copula=True, copula_corr=np.array([[1., .3], [.3, 1.]]),
                        )
                    elif schema == "custom_sampler":
                        kwargs.update(
                            x_sampler=lambda n, k, seed: np.random.default_rng(seed).normal(size=(n, k)),
                            confounder_specs=[{"name": "z"}, {"name": "cate_d_0"}],
                        )
                    if custom:
                        kwargs.update(
                            g_y=lambda X: .1 * X[:, 0] ** 2,
                            g_d=lambda X: .1 * np.sin(X[:, 1]),
                            tau=lambda X: (.2 * X[:, 0])[:, None],
                        )
                    old, new = Legacy(**kwargs), Current(**kwargs)
                    for generation in (1, 2):
                        left, right = old.generate(120), new.generate(120)
                        pd.testing.assert_frame_equal(left, right, check_exact=True)
                        assert old.confounder_names_ == new.confounder_names_
                        np.testing.assert_array_equal(old.rng.random(10), new.rng.random(10))
                        rows.append(dict(
                            family=family, include_oracle=oracle, custom_callbacks=custom,
                            schema=schema, generation=generation, schema_equal=True,
                            values_exact=True, next_rng_draws_exact=True,
                        ))
    result = dict(
        baseline=BASELINE,
        tested_source_checkpoint=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT
        ).decode("utf-8").strip(),
        configurations=rows, verified=len(rows), issues=[],
        limitation="Valid schemas only; categorical copula correctness is a separate finding.",
    )
    (ROOT / "audit/block09_finite_reference_result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(dict(verified=len(rows), issues=[])))


if __name__ == "__main__":
    main()
