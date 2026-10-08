"""Compare original/current single-partition contracts in owned synthetic copies."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '1409e95cf0cfb0cb1f9ab8541eefc25b3cbe1342'


def child(source, output):
    sys.path.insert(0, str(source))
    import numpy as np
    import pandas as pd
    from sklearn.linear_model import LinearRegression, LogisticRegression
    from causalis.data_contracts import CausalData
    from causalis.scenarios.unconfoundedness import IRM
    results = []
    for binary in (False, True):
        for normalize in (False, True):
            for store in (False, True):
                for n_rep, weighted in ((1, False), (1, True), (3, False), (3, True)):
                    rng = np.random.default_rng(917)
                    x = rng.normal(size=180)
                    d = rng.binomial(1, 1 / (1 + np.exp(-0.3 * x)))
                    y = 4 + x / 3 + d / 2 + rng.normal(size=len(x))
                    if binary:
                        y = rng.binomial(1, 1 / (1 + np.exp(-(-0.4 + x / 3 + d / 2))))
                    data = CausalData(df=pd.DataFrame({'x': x, 'd': d, 'y': y}),
                                      outcome='y', treatment='d', confounders=['x'])
                    model = IRM(data=data, ml_g=(LogisticRegression(max_iter=300) if binary else LinearRegression()),
                                ml_m=LogisticRegression(max_iter=300), n_folds=3, n_rep=n_rep,
                                random_state=13, normalize_ipw=normalize, store_diagnostics=store,
                                weights=np.linspace(0.7, 1.3, len(x)) if weighted else None).fit()
                    partitions = getattr(model, '_fit_repetitions_', (model,))
                    fit = [{name: getattr(partition, name) for name in
                            ('g0_hat_', 'g1_hat_', 'm_hat_', 'folds_', 'm_hat_raw_', '_y', '_d')}
                           for partition in partitions]
                    estimates = []
                    for score in ('ATE', 'ATTE'):
                        if weighted and score == 'ATTE':
                            try:
                                model.estimate(score=score, alpha=0.1)
                            except ValueError as error:
                                payload = {'expected_rejection': str(error)}
                            else:
                                raise AssertionError('Weighted ATTE unexpectedly accepted')
                        else:
                            result = model.estimate(score=score, alpha=0.1)
                            payload = result.model_dump()
                            payload.pop('time')
                        estimates.append(payload)
                    results.append({'config': [binary, normalize, store, n_rep, weighted],
                                    'fit': fit, 'estimates': estimates})
    # Public baseline feature probe; no patched baseline files or mixed helpers.
    try:
        IRM(data=data, ml_g=LinearRegression(), ml_m=LogisticRegression(max_iter=300),
            n_folds=3, cluster_groups=np.arange(len(x)) // 6, random_state=13).fit().estimate()
        feature = {'status': 'supported'}
    except TypeError as error:
        feature = {'status': 'unsupported', 'error': str(error)}

    def encode(value):
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.generic):
            return value.item()
        raise TypeError(type(value))
    output.write_text(json.dumps({'iid_partitions': results, 'cluster_feature': feature},
                                 sort_keys=True, default=encode), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--child-root', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.child_root:
        child(args.child_root, args.output)
        return
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    with tempfile.TemporaryDirectory(prefix='causalis-b23-probe-') as owned:
        folder = Path(owned)
        baseline, current = folder / 'baseline', folder / 'current'
        baseline.mkdir()
        archive = subprocess.check_output(['git', 'archive', BASELINE, 'causalis'], cwd=ROOT)
        with tarfile.open(fileobj=io.BytesIO(archive)) as files:
            files.extractall(baseline, filter='data')
        shutil.copytree(ROOT / 'causalis', current / 'causalis', ignore=shutil.ignore_patterns('__pycache__'))
        if (ROOT / 'causalis/_version.py').exists():
            shutil.copy2(ROOT / 'causalis/_version.py', baseline / 'causalis/_version.py')
        outputs = []
        for label, source in [('baseline', baseline), ('current', current)]:
            path = folder / f'{label}.json'
            completed = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                                       '--child-root', str(source), '--output', str(path)],
                                      env=env, text=True, capture_output=True, check=False)
            (ROOT / f'audit/block23_{label}_probe_checks.log').write_text(
                completed.stdout + completed.stderr, encoding='utf-8')
            completed.check_returncode()
            outputs.append(json.loads(path.read_text()))
        # Stable NaN representations compare exactly as JSON strings.
        first = json.dumps(outputs[0]['iid_partitions'], sort_keys=True)
        second = json.dumps(outputs[1]['iid_partitions'], sort_keys=True)
        assert first == second, 'iid single/repeated behavior changed'
        assert outputs[0]['cluster_feature']['status'] == 'unsupported'
        assert outputs[1]['cluster_feature']['status'] == 'supported'
        payload = dict(baseline=BASELINE, observed_head=subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            exact_iid_fit_configuration_pairs=len(outputs[0]['iid_partitions']),
            exact_iid_estimate_pairs=48,
            exact_unsupported_weighted_atte_rejections=16,
            baseline_feature=outputs[0]['cluster_feature'], current_feature=outputs[1]['cluster_feature'],
            compared_payload_sha256=hashlib.sha256(first.encode()).hexdigest(),
            source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                           for path in (ROOT/'causalis/scenarios/unconfoundedness/model.py',
                                        ROOT/'causalis/scenarios/unconfoundedness/_repeated.py',
                                        ROOT/'causalis/scenarios/unconfoundedness/_cluster.py',
                                        ROOT/'causalis/data_contracts/__init__.py')},
            temporary_copies_removed=False)
    payload['temporary_copies_removed'] = not Path(owned).exists()
    (ROOT/'audit/block23_probe_result.json').write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
