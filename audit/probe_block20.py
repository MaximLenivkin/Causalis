"""Exact finite-fit compatibility and unchanged-function evidence for B20."""
from datetime import datetime, timezone
import ast
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '98d5478a36b5fbb051c863db4599cbc0bc9a8bbf'
PATHS = [
    'causalis/data_contracts/_duplicate_columns.py',
    'causalis/data_contracts/causaldata.py',
    'causalis/scenarios/_fit_state.py',
    'causalis/scenarios/unconfoundedness/model.py',
    'causalis/scenarios/multi_unconfoundedness/model.py',
    'causalis/scenarios/iv/model.py',
    'tests/data/test_duplicate_screening.py',
    'tests/inference/test_data_snapshot_contracts.py',
]


def worker():
    import warnings
    import causalis
    import numpy as np
    from tests.inference.test_nuisance_prediction_contract import dataset, estimator
    assert Path(causalis.__file__).resolve().is_relative_to(Path.cwd())
    def digest(value):
        array = np.asarray(value)
        if array.dtype.kind in 'biufc':
            payload = str(array.shape).encode() + str(array.dtype).encode() + array.tobytes()
        else:
            payload = repr(value).encode()
        return hashlib.sha256(payload).hexdigest()
    result = {}
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        for kind in ['binary', 'multi', 'iv']:
            for store in ([False, True] if kind != 'iv' else [True]):
                for normalized in [False, True]:
                    for jobs in [1, 2]:
                        data = dataset(kind)
                        original = data.df.copy(deep=True)
                        model = estimator(kind, data, n_jobs=jobs)
                        if kind != 'iv':
                            model.store_diagnostics = store
                        model.normalize_ipw = normalized
                        key = f'{kind}/{store}/{normalized}/{jobs}'
                        signatures = {name: str(inspect.signature(getattr(type(model), name)))
                                      for name in ['__init__', 'fit', 'estimate']}
                        model.fit()
                        fit = {name: digest(getattr(model, name))
                               for name in ['g0_hat_', 'g1_hat_', 'm_hat_', 'g_hat_', 'r_hat0_',
                                            'r_hat1_', 'folds_', '_full_sample_folds_', 'y_', 'd_', 'z_',
                                            'X_', '_y', '_d', '_X'] if hasattr(model, name)}
                        inference = {}
                        for score in (['LATE'] if kind == 'iv' else ['ATE', 'ATTE']):
                            estimate = model.estimate(score=score)
                            payload = {name: digest(getattr(estimate, name)) for name in
                                       ['value', 'p_value', 'ci_lower_absolute', 'ci_upper_absolute',
                                        'outcome', 'treatment', 'confounders']}
                            payload.update({name: digest(getattr(model, name)) for name in
                                            ['coef_', 'se_', 'psi_', 'psi_a_', 'psi_b_']})
                            diag = estimate.diagnostic_data
                            if diag is not None:
                                payload.update({'diagnostic/' + name: digest(value)
                                                for name, value in diag.__dict__.items()
                                                if isinstance(value, np.ndarray)})
                            inference[score] = payload
                        assert data.df.equals(original)
                        result[key] = dict(signatures=signatures, fit=fit, inference=inference)
    return result


def functions(source):
    output = {}
    def walk(node, prefix=''):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                key = prefix + child.name
                if not isinstance(child, ast.ClassDef):
                    output[key] = ast.dump(child, include_attributes=False)
                walk(child, key + '.')
            else:
                walk(child, prefix)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                node.body.pop(0)
    walk(tree)
    return output


def main():
    env = os.environ.copy()
    env.update(MPLBACKEND='Agg', MPLCONFIGDIR=str(ROOT / '.venv/matplotlib'),
               OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    command = [str(ROOT / '.venv/bin/python'), str(Path(__file__).resolve()), '--worker']
    with tempfile.TemporaryDirectory(prefix='causalis-b20-compat-', dir='/private/tmp') as temp:
        checkout = Path(temp) / 'baseline'
        subprocess.run(['git', 'worktree', 'add', '--detach', str(checkout), BASELINE],
                       cwd=ROOT, check=True, capture_output=True)
        try:
            env['PYTHONPATH'] = str(checkout)
            before = json.loads(subprocess.check_output(command, cwd=checkout, env=env, text=True))
        finally:
            subprocess.run(['git', 'worktree', 'remove', '--force', str(checkout)], cwd=ROOT, check=True)
    env['PYTHONPATH'] = str(ROOT)
    after = json.loads(subprocess.check_output(command, cwd=ROOT, env=env, text=True))
    assert before == after, 'Finite valid compatibility mismatch'
    allowed = {
        PATHS[0]: set(), PATHS[1]: {'CausalData._column_value_signature'},
        PATHS[3]: {'IRM.fit', 'IRM._build_estimate_diagnostic_data', 'IRM._build_causal_estimate', 'IRM.confint'},
        PATHS[4]: {'MultiTreatmentIRM.fit', 'MultiTreatmentIRM._store_fit_sample',
                  'MultiTreatmentIRM._build_estimate_diagnostic_data', 'MultiTreatmentIRM.estimate',
                  'MultiTreatmentIRM.confint'},
        PATHS[5]: {'IIVM.fit', 'IIVM.estimate'},
    }
    checked = []
    for path, excluded in allowed.items():
        baseline = subprocess.check_output(['git', 'show', BASELINE + ':' + path], cwd=ROOT, text=True)
        old = functions(baseline)
        new = functions((ROOT / path).read_text())
        for key, value in old.items():
            if key not in excluded:
                assert new[key] == value, (path, key)
                checked.append(path + ':' + key)
    result = dict(baseline=BASELINE, observed_at=datetime.now(timezone.utc).isoformat(),
                  original_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  exact_fit_pairs=len(after), exact_inference_pairs=sum(len(v['inference']) for v in after.values()),
                  unchanged_functions=checked, input_frames_unchanged=True,
                  source_sha256={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in PATHS},
                  synthetic_in_memory_only=True, configuration_digests=after,
                  limitations=['Private diagnostic model links remain live.',
                               'Sensitivity and external learner/callback side effects are not certified.'])
    (ROOT/'audit/block20_probe_result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:result[k] for k in ['exact_fit_pairs','exact_inference_pairs','input_frames_unchanged']}))
    print('Unchanged functions:',len(checked))


if __name__ == '__main__':
    if '--worker' in sys.argv:
        print(json.dumps(worker(), sort_keys=True))
    else:
        main()
