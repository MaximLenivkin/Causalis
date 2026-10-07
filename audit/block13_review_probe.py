"""Independent B13 scenario namespace and full old/current references."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import types
import warnings

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BASELINE = "9f0a63c42308ca886d92dc73d8d8d9611d5b2c31"
MODULES = [
    "causalis.dgp.base", "causalis.dgp.causaldata.base", "causalis.dgp.causaldata.preperiod",
    "causalis.dgp.causaldata_instrumental.base", "causalis.dgp.causaldata.functional",
    "causalis.dgp.causaldata_instrumental.functional", "causalis.scenarios.classic_rct.dgp",
    "causalis.scenarios.cuped.dgp", "causalis.scenarios.iv.dgp",
]
PATHS = [name.replace(".", "/") + ".py" for name in MODULES]
ALIAS_PACKAGES = ["causalis/dgp/__init__.py", "causalis/dgp/causaldata/__init__.py",
                  "causalis/data_contracts/__init__.py"]
CURRENT = {name: importlib.import_module(name) for name in MODULES}
ORACLES = ["m", "m_obs", "tau_link", "g0", "g1", "cate"]


@contextmanager
def overlay(graph):
    modules = {name: sys.modules.get(name) for name in graph}
    attributes = []
    def set_attribute(owner, name, value):
        old = vars(owner).get(name)
        existed = name in vars(owner)
        attributes.append((owner, name, old, existed))
        setattr(owner, name, value)
    try:
        sys.modules.update(graph)
        for name, module in graph.items():
            parent, leaf = name.rsplit(".", 1)
            if parent in sys.modules:
                set_attribute(sys.modules[parent], leaf, module)
        for module, names, packages in [
            (MODULES[1], ["CausalDatasetGenerator"], ["causalis.dgp.causaldata", "causalis.dgp"]),
            (MODULES[3], ["InstrumentalGenerator", "IVCausalDatasetGenerator"],
             ["causalis.dgp.causaldata_instrumental", "causalis.dgp"]),
            (MODULES[6], ["generate_classic_rct_26", "classic_rct_gamma_26"],
             ["causalis.dgp.causaldata", "causalis.dgp", "causalis.data_contracts"]),
        ]:
            if module in graph:
                for name in names:
                    for package in packages:
                        set_attribute(sys.modules[package], name, getattr(graph[module], name))
        yield
    finally:
        for owner, name, value, existed in reversed(attributes):
            if existed:
                setattr(owner, name, value)
            else:
                delattr(owner, name)
        for name, value in modules.items():
            if value is None:
                del sys.modules[name]
            else:
                sys.modules[name] = value


def freeze_graph():
    graph = {}
    for number, (name, path) in enumerate(zip(MODULES, PATHS)):
        module = types.ModuleType("block13_frozen_" + str(number))
        module.__package__ = name.rsplit(".", 1)[0]
        sys.modules[module.__name__] = module
        text = subprocess.check_output(["git", "show", BASELINE + ":" + path], cwd=ROOT, text=True)
        with overlay(graph):
            exec(compile(text, BASELINE + ":" + path, "exec"), module.__dict__)
        graph[name] = module
    assert graph[MODULES[3]].InstrumentalGenerator.__bases__[0] is graph[MODULES[1]].CausalDatasetGenerator
    assert graph[MODULES[4]].CausalDatasetGenerator is graph[MODULES[1]].CausalDatasetGenerator
    assert graph[MODULES[6]].generate_classic_rct is graph[MODULES[4]].generate_classic_rct
    assert graph[MODULES[6]]._deterministic_ids is graph[MODULES[0]]._deterministic_ids
    assert graph[MODULES[8]].InstrumentalGenerator is graph[MODULES[3]].InstrumentalGenerator
    return graph


def capture(graph, module, function, kwargs, alias=None):
    captured = []
    real = np.random.default_rng
    def tracked(*args, **kw):
        rng = real(*args, **kw)
        if not any(rng is previous for previous in captured):
            captured.append(rng)
        return rng
    np.random.default_rng = tracked
    try:
        with overlay(graph):
            function_object = (getattr(importlib.import_module(alias), function)
                               if alias else getattr(graph[module], function))
            result = function_object(**kwargs)
    finally:
        np.random.default_rng = real
    if isinstance(result, pd.DataFrame):
        frame, metadata = result, {"kind": "DataFrame"}
    else:
        frame, metadata = result.df, {"kind": type(result).__name__, **result.model_dump(exclude={"df"})}
    return frame, metadata, [json.dumps(r.bit_generator.state, sort_keys=True) for r in captured], [r.random(10) for r in captured]


def fixtures():
    cases = []
    for function in ["generate_classic_rct_26", "classic_rct_gamma_26"]:
        for pre in [False, True]:
            for ancillary in [False, True]:
                for oracle in [False, True]:
                    for converted in [False, True]:
                        for dependence in [False, True]:
                            kw = dict(n=384, seed=731, add_pre=pre, add_ancillary=ancillary,
                                deterministic_ids=True, include_oracle=oracle, return_causal_data=converted,
                                outcome_depends_on_x=dependence)
                            cases.append((MODULES[6], function, kw, None))
        for pre_name in ["β baseline", " ", np.str_("baseline 2")]:
            for converted in [False, True]:
                cases.append((MODULES[6], function, dict(n=384, seed=731, add_pre=True, pre_name=pre_name,
                    include_oracle=True, add_ancillary=False, return_causal_data=converted), None))
        for converted in [False, True]:
            for alias in ["causalis.dgp", "causalis.dgp.causaldata", "causalis.data_contracts"]:
                cases.append((MODULES[6], function, dict(n=384, seed=731, add_pre=True, add_ancillary=True,
                    deterministic_ids=True, return_causal_data=converted, include_oracle=True), alias))
        for converted in [False, True]:
            kw = dict(n=384, seed=731, add_pre=True, add_ancillary=False, return_causal_data=converted,
                beta_y=[.2, -.1, .3], g_y=lambda x: .1 * np.sin(x[:, 0]),
                x_sampler=lambda n,k,seed: np.column_stack((np.linspace(-1.,1.,n),
                                                            np.sin(np.arange(n)), np.cos(np.arange(n)))))
            cases.append((MODULES[6], function, kw, None))
    for oracle in [False, True]:
        for converted in [False, True]:
            for deterministic in [False, True]:
                cases.append((MODULES[8], "generate_offer_iv_26", dict(n=384, seed=731,
                    include_oracle=oracle, return_causal_data=converted, deterministic_ids=deterministic), None))
    for function in ["generate_cuped_tweedie_26", "make_cuped_binary_26"]:
        for pre in [False, True]:
            for oracle in [False, True]:
                for converted in [False, True]:
                    cases.append((MODULES[7], function, dict(n=512, seed=731, add_pre=pre,
                        include_oracle=oracle, return_causal_data=converted), None))
    return cases


def exact_valid(old):
    rows = []
    for number, (module, function, kw, alias) in enumerate(fixtures()):
        expected, meta, states, draws = capture(old, module, function, kw, alias)
        actual, actual_meta, actual_states, actual_draws = capture(CURRENT, module, function, kw, alias)
        assert expected.columns.is_unique and actual.columns.is_unique
        pd.testing.assert_frame_equal(expected, actual, check_exact=True)
        assert meta == actual_meta and states == actual_states
        assert len(draws) == len(actual_draws)
        for left, right in zip(draws, actual_draws):
            np.testing.assert_array_equal(left, right)
        rows.append({"case": number, "module": module, "function": function, "alias": alias,
                     "pre": kw["add_pre"] if "add_pre" in kw else None,
                     "ancillary": kw.get("add_ancillary"), "oracle": kw.get("include_oracle", False),
                     "converted": kw["return_causal_data"], "columns": list(actual.columns),
                     "tracked_rngs": len(draws), "exact_frame_dtypes_schema_metadata_state_next10rng": True})
    return rows


def rejection_checks(old):
    module = CURRENT[MODULES[6]]
    rows = []
    for function, names in [("generate_classic_rct_26", ["conversion", "user_id"]),
                            ("classic_rct_gamma_26", ["user_id"])]:
        for name in names:
            for ancillary in [False, True]:
                for converted in [False, True]:
                    kw = dict(n=128, seed=731, add_pre=True, pre_name=name, include_oracle=False,
                              add_ancillary=ancillary, return_causal_data=converted)
                    calls=[]
                    underlying_name = "generate_classic_rct" if function.startswith("generate") else "classic_rct_gamma"
                    original = getattr(module, underlying_name)
                    def forbidden(**kw):
                        calls.append(True)
                        raise AssertionError("Underlying generator called on a known scenario collision")
                    setattr(module, underlying_name, forbidden)
                    try:
                        try:
                            getattr(module,function)(**kw)
                        except ValueError as exc:
                            assert repr(name) in str(exc) and "collid" in str(exc)
                            assert not calls
                            rows.append({"function":function,"name":name,"ancillary":ancillary,
                                         "converted":converted,"before_underlying":True,"message":str(exc)})
                        else:
                            raise AssertionError("Scenario collision accepted")
                    finally:
                        setattr(module, underlying_name, original)
    original = module.generate_classic_rct
    frame = pd.DataFrame({"y": [0.,1.,0.,1.], "d": [0.,0.,1.,1.], "conversion": [3.,4.,5.,6.]})
    expected = frame.copy(deep=True)
    calls=[]
    def bad_builder(**kw):
        return frame
    module.generate_classic_rct = bad_builder
    real_rng = np.random.default_rng
    def forbidden_rng(*args,**kw):
        calls.append(True)
        raise AssertionError("ID RNG used before checking late rename")
    np.random.default_rng = forbidden_rng
    try:
        try:
            module.generate_classic_rct_26(n=4,return_causal_data=False)
        except ValueError as exc:
            assert "conversion" in str(exc) and not calls
            pd.testing.assert_frame_equal(frame,expected,check_exact=True)
            rows.append({"function":"generate_classic_rct_26","actual_builder_namespace":"conversion",
                         "before_id_rng_and_rename":True,"message":str(exc)})
        else:
            raise AssertionError("Actual late rename collision accepted")
    finally:
        np.random.default_rng=real_rng
        module.generate_classic_rct=original
    return rows


def permitted_names(old):
    rows=[]
    for function in ["generate_classic_rct_26","classic_rct_gamma_26"]:
        for name in ORACLES:
            for ancillary in [False,True]:
                kw=dict(n=384,seed=731,add_pre=True,pre_name=name,include_oracle=False,
                        add_ancillary=ancillary,deterministic_ids=True,return_causal_data=True)
                frame,meta,_,_=capture(CURRENT,MODULES[6],function,kw)
                assert name in meta['confounders_names'] and meta['user_id_name']=='user_id'
                expected,expected_meta,_,_=capture(CURRENT,MODULES[6],function,{**kw,'pre_name':'baseline'})
                pd.testing.assert_frame_equal(frame.rename(columns={name:'baseline'}),expected,check_exact=True)
                assert [c if c!=name else 'baseline' for c in meta['confounders_names']]==expected_meta['confounders_names']
                old_frame,old_meta,_,_=capture(old,MODULES[6],function,kw)
                assert name not in old_meta['confounders_names']
                rows.append({'function':function,'actual_pre':name,'ancillary':ancillary,
                             'preserved_feature_and_renamed_frame':True,'baseline_dropped_feature':True})
        for name in ['user_id','conversion','y','m',None,'',['unused']]:
            kw=dict(n=384,seed=731,add_pre=False,add_ancillary=False,
                    deterministic_ids=True,return_causal_data=False,pre_name=name)
            left,meta,states,draws=capture(CURRENT,MODULES[6],function,kw)
            right,right_meta,right_states,right_draws=capture(CURRENT,MODULES[6],function,{k:v for k,v in kw.items() if k!='pre_name'})
            pd.testing.assert_frame_equal(left,right,check_exact=True)
            assert meta==right_meta and states==right_states
            for a,b in zip(draws,right_draws):np.testing.assert_array_equal(a,b)
            rows.append({'function':function,'unused_pre':repr(name),'ignored_values_schema_rng':True})
    for converted in [False,True]:
        kw=dict(n=384,seed=731,add_pre=True,pre_name='conversion',add_ancillary=False,return_causal_data=converted)
        left,meta,states,draws=capture(old,MODULES[6],'classic_rct_gamma_26',kw)
        right,right_meta,right_states,right_draws=capture(CURRENT,MODULES[6],'classic_rct_gamma_26',kw)
        pd.testing.assert_frame_equal(left,right,check_exact=True)
        assert meta==right_meta and states==right_states
        for a,b in zip(draws,right_draws):np.testing.assert_array_equal(a,b)
        rows.append({'function':'classic_rct_gamma_26','actual_pre':'conversion','converted':converted,
                     'literal_name_available_and_exact_baseline':True})
    return rows


def main():
    with warnings.catch_warnings(record=True) as compiler_warnings:
        warnings.simplefilter('always')
        old=freeze_graph()
    result={'baseline':BASELINE,'reviewed_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'scope':'baseline to working tree','observed_at_utc':datetime.now(timezone.utc).isoformat(),
            'frozen_module_sha256':{p:hashlib.sha256(subprocess.check_output(['git','show',BASELINE+':'+p],cwd=ROOT)).hexdigest() for p in PATHS},
            'current_library_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in PATHS}}
    result['frozen_compile_warnings']=[{'category':w.category.__name__,'message':str(w.message),
                                      'filename':w.filename,'lineno':w.lineno} for w in compiler_warnings]
    result['alias_package_sha256']={}
    for path in ALIAS_PACKAGES:
        original=subprocess.check_output(['git','show',BASELINE+':'+path],cwd=ROOT)
        assert original==(ROOT/path).read_bytes(),path
        result['alias_package_sha256'][path]=hashlib.sha256(original).hexdigest()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        result['valid_configs']=exact_valid(old)
        result['namespace_rejections']=rejection_checks(old)
        result['permitted_names']=permitted_names(old)
        result['public_constructor_signatures_unchanged']=all(str(inspect.signature(getattr(old[MODULES[6]],name)))==str(inspect.signature(getattr(CURRENT[MODULES[6]],name))) for name in ['generate_classic_rct_26','classic_rct_gamma_26'])
        assert result['public_constructor_signatures_unchanged']
        result['warnings']=sorted(set(str(w.message) for w in caught))
    result['issues']=[]
    tests=ROOT/'tests/data/test_scenario_namespace_contract.py'
    if tests.exists():result['current_test_module_sha256']=hashlib.sha256(tests.read_bytes()).hexdigest()
    (ROOT/'audit/block13_review_probe.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:len(result[k]) for k in ['valid_configs','namespace_rejections','permitted_names','warnings','issues']}))


if __name__=='__main__':main()
