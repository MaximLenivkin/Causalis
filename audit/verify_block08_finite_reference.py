"""Independent B07/B08 seeded finite-contract and RNG comparison."""
from pathlib import Path
import json
import subprocess
import sys
import types
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from causalis.dgp.multicausaldata.base import MultiCausalDatasetGenerator as Current

name = '_b08_legacy_multicausal_generator'
module = types.ModuleType(name)
sys.modules[name] = module
source = subprocess.check_output(
    ['git', 'show', 'b33922f1c0db8885ae9e8e071c45fc46de5205b6:causalis/dgp/multicausaldata/base.py'], cwd=ROOT,
).decode('utf-8')
exec(compile(source, name, 'exec'), module.__dict__)
Legacy = module.MultiCausalDatasetGenerator
rows = []
for family in ('continuous', 'binary', 'poisson', 'gamma'):
    for oracle in (False, True):
        for custom in (False, True):
            kwargs = dict(k=2, seed=731, outcome_type=family, include_oracle=oracle,
                          u_strength_d=.3, u_strength_y=.7, target_d_rate=[.2, .3, .5],
                          beta_y=np.array([.2, -.1]), beta_d=np.array([.1, .2]))
            if custom:
                kwargs.update(g_y=lambda X: .1 * X[:, 0] ** 2,
                              g_d=lambda X: .1 * np.sin(X[:, 1]),
                              tau=lambda X: (.2 * X[:, 0])[:, None])
            old, new = Legacy(**kwargs), Current(**kwargs)
            left, right = old.generate(120), new.generate(120)
            np.testing.assert_array_equal(left.columns, right.columns)
            np.testing.assert_array_equal(left.to_numpy(), right.to_numpy())
            np.testing.assert_array_equal(old.rng.random(10), new.rng.random(10))
            rows.append(dict(family=family, include_oracle=oracle, custom_callbacks=custom,
                             schema_equal=True, values_exact=True, next_rng_draws_exact=True))
result = dict(baseline='b33922f1c0db8885ae9e8e071c45fc46de5205b6',
              tested_source_checkpoint=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode('utf-8').strip(),
              configurations=rows,
              verified=len(rows), issues=[])
(ROOT / 'audit/block08_finite_reference_result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(verified=len(rows), issues=[])))
