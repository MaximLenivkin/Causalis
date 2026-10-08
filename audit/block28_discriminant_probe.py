"""A tiny finite linear coefficient must not become a tangent through squaring."""
import json
import subprocess
from pathlib import Path
from causalis.scenarios.iv.weak import _quadratic_set

root = Path(__file__).resolve().parents[1]
try:
    actual = _quadratic_set(1., 1e-200, 0.)
    payload = dict(status='returned', set_type=actual[0], intervals=actual[1])
except RuntimeError as error:
    payload = dict(status='rejected', error=str(error))
payload.update(source=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
               coefficients=[1., 1e-200, 0.], exact_factored_roots=[-1e-200, 0.])
print(json.dumps(payload, indent=2))
