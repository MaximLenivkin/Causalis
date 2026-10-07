"""B17 exact-baseline compatibility and independent numerical evidence.

Uses only in-memory synthetic rows; persists aggregate errors, configs, counts,
source hashes and environment metadata, never generated observation arrays.
"""
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'aaeadd8'
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.venv/matplotlib'))
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from causalis.dgp.causaldata.base import CausalDatasetGenerator
from causalis.dgp.causaldata_instrumental.base import InstrumentalGenerator
from causalis.dgp._gaussian_joint import _gaussian_product_mean
from causalis.dgp._gaussian_outcome import _gaussian_outcome_mean


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def load(name, data):
    module = types.ModuleType(name)
    sys.modules[name] = module
    exec(compile(data, name, 'exec'), module.__dict__)
    return module


def main():
    paths = ['causalis/dgp/causaldata/base.py', 'causalis/dgp/causaldata_instrumental/base.py',
             'causalis/dgp/_gaussian_joint.py', 'causalis/dgp/_gaussian_outcome.py',
             'causalis/dgp/base.py', 'causalis/dgp/multicausaldata/base.py',
             'tests/data/test_gaussian_propensity_joint_means.py',
             'tests/data/test_gaussian_joint_accuracy_policy.py']
    baseline = git('rev-parse', BASELINE).decode().strip()
    old_binary = load('_b17_old_binary', git('show', f'{baseline}:{paths[0]}')).CausalDatasetGenerator
    iv_bytes = git('show', f'{baseline}:{paths[1]}').replace(
        b'from causalis.dgp.causaldata.base import CausalDatasetGenerator',
        b'from _b17_old_binary import CausalDatasetGenerator')
    old_iv = load('_b17_old_iv', iv_bytes).InstrumentalGenerator
    assert old_iv.__bases__ == (old_binary,)
    spec = importlib.util.spec_from_file_location('_b17_references', ROOT/paths[6])
    refs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(refs)
    pairs = []
    for current, old_class in ((CausalDatasetGenerator, old_binary), (InstrumentalGenerator, old_iv)):
        assert str(inspect.signature(current)) == str(inspect.signature(old_class))
        families = ['continuous', 'binary', 'poisson', 'gamma']
        if current is CausalDatasetGenerator:
            families += ['tweedie']
        for family in families:
            for sd, sy in ((0., 0.), (0., .5), (.5, 0.), (.5, -.7), (50., 10.)):
                for include in (False, True):
                    counts = [dict(y=0, d=0, zi=0), dict(y=0, d=0, zi=0)]
                    def callback(index, name):
                        def function(x):
                            counts[index][name] += 1
                            return 0.01*x[:, 0]**2
                        return function
                    kwargs = dict(k=2, beta_d=np.array([.3, -.2]), beta_y=np.array([.2, .1]),
                        alpha_y=-.4, theta=.7, alpha_d=-.3, u_strength_d=sd, u_strength_y=sy,
                        outcome_type=family, target_d_rate=.4, include_oracle=include,
                        tau=lambda x: .7+.1*x[:, 0], score_bounding=1.2,
                        propensity_sharpness=1.7, seed=921)
                    if family == 'tweedie':
                        kwargs.update(u_strength_zi=sd, tau_zi=lambda x: .2+.1*x[:, 0])
                    old = old_class(g_y=callback(0,'y'), g_d=callback(0,'d'), g_zi=callback(0,'zi'), **kwargs)
                    new = current(g_y=callback(1,'y'), g_d=callback(1,'d'), g_zi=callback(1,'zi'), **kwargs)
                    excluded = []
                    if include:
                        if current is InstrumentalGenerator:
                            if sd: excluded += ['r_z0', 'r_z1']
                            if sd or sy: excluded += ['g_z0', 'g_z1']
                            if sd: excluded += ['iv_first_stage']
                            if sd or sy: excluded += ['iv_reduced_form', 'late_x', 'late']
                        else:
                            if sd: excluded += ['m']
                            if family == 'tweedie' and (sd or sy): excluded += ['g0', 'g1', 'cate']
                    for repetition in range(2):
                        left, right = old.generate(11), new.generate(11)
                        pd.testing.assert_frame_equal(left.drop(columns=excluded), right.drop(columns=excluded), check_exact=True)
                        assert list(left.columns) == list(right.columns)
                        assert left.dtypes.equals(right.dtypes)
                        assert old.rng.bit_generator.state == new.rng.bit_generator.state
                        assert old.alpha_d == new.alpha_d
                        assert old._generated_column_roles == new._generated_column_roles
                        assert old._generated_confounder_names == new._generated_confounder_names
                        if include and current is InstrumentalGenerator:
                            np.testing.assert_array_equal(right['iv_first_stage'], right['r_z1']-right['r_z0'])
                            np.testing.assert_array_equal(right['iv_reduced_form'], right['g_z1']-right['g_z0'])
                            den = right['iv_first_stage'].to_numpy()
                            expected_late_x = np.divide(right['iv_reduced_form'], den,
                                out=np.full(len(den),np.nan), where=np.abs(den)>1e-12)
                            np.testing.assert_array_equal(right['late_x'],expected_late_x)
                            expected_late = (right['iv_reduced_form'].mean()/den.mean()
                                if abs(den.mean())>1e-12 else np.nan)
                            np.testing.assert_array_equal(right['late'],np.full(len(den),expected_late))
                        np.testing.assert_array_equal(old.rng.random(10), new.rng.random(10))
                    pairs.append(dict(generator=current.__name__, family=family, sd=sd, sy=sy,
                        include_oracle=include, frame_rng_pairs=2, callbacks=counts, corrected_columns=excluded))
    references = []
    configs = [(-5, 2, -5, 50), (0, -5, 0, 5), (-5, 50, -1, -10),
               (0, 1e6, 0, -1e6), (-1, .3, 19, 2), (.5, -3, -25, 10)]
    rng = np.random.default_rng(748)
    configs += [(float(rng.uniform(-6,6)), float(rng.uniform(-50,50)),
                 float(rng.uniform(-25,25)), float(rng.uniform(-20,20))) for _ in range(20)]
    for family in ('binary', 'gamma'):
        for a,s,b,t in configs:
            actual = float(_gaussian_product_mean(a,s,b,t,family))
            expected = refs.joint_reference(a,s,b,t,family)
            absolute = abs(actual-expected)
            relative = absolute/expected if expected else None
            assert absolute < 3e-11 if family == 'binary' else relative < 3e-10, (family,a,s,b,t,actual,expected,relative)
            references.append(dict(family=family,a=a,s=s,b=b,t=t,abs_error=absolute,rel_error=relative))
    repairs = []
    for label, old_value, value, expected in (
        ('binary m', float(old_binary(k=0,alpha_d=-5,u_strength_d=50,seed=3).generate(2)['m'].iloc[0]),
         float(_gaussian_outcome_mean(-5,50,'binary')), 2*refs.joint_reference(-5,50,0,0,'binary')),
        ('Tweedie g0', float(old_binary(k=0,outcome_type='tweedie',alpha_zi=-5,u_strength_zi=50,
             alpha_y=0,theta=0,seed=3).generate(2)['g0'].iloc[0]),
         float(_gaussian_product_mean(-5,50,0,0,'gamma')), 2*refs.joint_reference(-5,50,0,0,'binary')),
    ):
        repairs.append(dict(target=label,baseline=old_value,current=value,reference=expected,
                            old_abs_error=abs(old_value-expected),new_abs_error=abs(value-expected)))
    x, tau = np.empty((1,0)), np.ones(1)
    for z in (0,1):
        kwargs = dict(k=0,alpha_y=-5,theta=1,outcome_type='binary',u_strength_y=50,u_strength_d=2,seed=91)
        old_value = float(old_iv(**kwargs)._g_by_z(x,z,tau)[0])
        value = float(InstrumentalGenerator(**kwargs)._g_by_z(x,z,tau)[0])
        a = 1.25*z
        expected = refs.joint_reference(-a,-2,-5,50,'binary')+refs.joint_reference(a,2,-4,50,'binary')
        repairs.append(dict(target='IV joint g_by_z',z=z,baseline=old_value,current=value,reference=expected,
                            old_abs_error=abs(old_value-expected),new_abs_error=abs(value-expected)))
    unchanged = []
    for path in paths[3:6]:
        assert (ROOT/path).read_bytes() == git('show', f'{baseline}:{path}')
    for path, class_name, allowed in ((paths[0],'CausalDatasetGenerator',{'generate','oracle_nuisance'}),
                                      (paths[1],'InstrumentalGenerator',{'_r_by_z','_g_by_z'})):
        old_ast = ast.parse(git('show', f'{baseline}:{path}'))
        new_ast = ast.parse((ROOT/path).read_text())
        def methods(tree):
            cls = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name == class_name)
            return {n.name:ast.dump(n,include_attributes=False) for n in cls.body if isinstance(n,ast.FunctionDef)}
        old_methods,new_methods = methods(old_ast), methods(new_ast)
        assert set(old_methods) == set(new_methods)
        for name in old_methods:
            if name not in allowed:
                assert old_methods[name] == new_methods[name], name
                unchanged.append(f'{path}:{name}')
    payload = dict(baseline=baseline, process_head=git('rev-parse','HEAD').decode().strip(),
        observed_at_utc=datetime.now(timezone.utc).isoformat(), python=sys.version,
        source_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        compatibility=pairs, compatibility_frame_rng_pairs=sum(p['frame_rng_pairs'] for p in pairs),
        references=references, repairs=repairs, unchanged_methods=unchanged,
        limitations=['deterministic X callbacks only','estimated errors, no rare-tail relative certificate',
                     'failed generation does not roll back RNG or callbacks'])
    (ROOT/'audit/block17_probe_result.json').write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(dict(pairs=payload['compatibility_frame_rng_pairs'], references=len(references),
        max_binary_abs=max(r['abs_error'] for r in references if r['family']=='binary'),
        max_gamma_rel=max(r['rel_error'] for r in references if r['family']=='gamma'), repairs=repairs),indent=2))

if __name__ == '__main__':
    main()
