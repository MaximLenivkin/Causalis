"""Independent B12 wrapper, conversion, full-frame and RNG references."""
from contextlib import contextmanager
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
BASELINE = "eb6dfe23f0a97991b6e3d6109febc1b0170e128d"
MODULES = [
    "causalis.dgp.base",
    "causalis.dgp.causaldata.base",
    "causalis.dgp.causaldata.preperiod",
    "causalis.dgp.causaldata_instrumental.base",
    "causalis.dgp.multicausaldata.base",
    "causalis.dgp.causaldata.functional",
    "causalis.dgp.causaldata_instrumental.functional",
    "causalis.dgp.multicausaldata.functional",
    "causalis.dgp.rct_causal_data",
    "causalis.scenarios.classic_rct.dgp",
    "causalis.scenarios.cuped.dgp",
]
CURRENT = {name: importlib.import_module(name) for name in MODULES}
SOURCE_PATHS = [name.replace(".", "/") + ".py" for name in MODULES]


@contextmanager
def overlay(graph):
    saved = {name: sys.modules.get(name) for name in graph}
    try:
        sys.modules.update(graph)
        yield
    finally:
        for name, module in saved.items():
            if module is None:
                del sys.modules[name]
            else:
                sys.modules[name] = module


def freeze_graph():
    graph = {}
    for number, (name, path) in enumerate(zip(MODULES, SOURCE_PATHS)):
        module = types.ModuleType("block12_review_frozen_" + str(number))
        module.__package__ = name.rsplit(".", 1)[0]
        sys.modules[module.__name__] = module
        source = subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT, text=True)
        with overlay(graph):
            exec(compile(source, f"{BASELINE}:{path}", "exec"), module.__dict__)
        graph[name] = module
    assert issubclass(graph[MODULES[3]].InstrumentalGenerator,
                      graph[MODULES[1]].CausalDatasetGenerator)
    assert graph[MODULES[5]].CausalDatasetGenerator is graph[MODULES[1]].CausalDatasetGenerator
    assert graph[MODULES[6]].InstrumentalGenerator is graph[MODULES[3]].InstrumentalGenerator
    assert graph[MODULES[5]]._add_ancillary_info is graph[MODULES[0]]._add_ancillary_info
    return graph


def as_result(result):
    if isinstance(result, pd.DataFrame):
        return result, {"kind": "raw"}
    return result.df, {"kind": type(result).__name__, **result.model_dump(exclude={"df"})}


def capture_call(graph, module_name, function_name, kwargs):
    captured = []
    real_default_rng = np.random.default_rng
    def tracked(*args, **kw):
        rng = real_default_rng(*args, **kw)
        if not any(rng is existing for existing in captured):
            captured.append(rng)
        return rng
    np.random.default_rng = tracked
    try:
        with overlay(graph):
            result = getattr(graph[module_name], function_name)(**kwargs)
    finally:
        np.random.default_rng = real_default_rng
    frame, metadata = as_result(result)
    states = [json.dumps(rng.bit_generator.state, sort_keys=True) for rng in captured]
    next_draws = [rng.random(10) for rng in captured]
    return frame, metadata, states, next_draws


def sampling(path, iv=False):
    if path == "default":
        return {"k": 2}
    if path == "custom":
        return {"confounder_specs": [{"name": "β feature"}, {"name": "feature two"}],
                "x_sampler": lambda n, k, seed: np.column_stack((np.linspace(-1., 1., n),
                                                                np.sin(np.arange(n))))}
    specs = [{"name": "baseline feature", "dist": "normal"},
             {"name": "segment", "dist": "categorical", "categories": ["base", "mid", "top"],
              "probs": [.3, .4, .3]}]
    result = {"confounder_specs": specs}
    if path == "copula":
        result.update(use_copula=True, copula_corr=np.array([[1., -.3], [-.3, 1.]]))
    return result


def wrapper_fixtures():
    cases = []
    binary, iv, multi = MODULES[5:8]
    for family in ["normal", "binary", "poisson", "gamma"]:
        for oracle in [False, True]:
            for pre, ancillary in [(False, False), (False, True), (True, False), (True, True)]:
                for converted in [False, True]:
                    kw = dict(n=256, random_state=731, outcome_type=family, include_oracle=oracle,
                              add_pre=pre, add_ancillary=ancillary, deterministic_ids=True,
                              return_causal_data=converted, **sampling("independent"))
                    cases.append((binary, "generate_rct", kw))
    for path in ["default", "custom"]:
        for pre in [False, True]:
            for converted in [False, True]:
                cases.append((binary, "generate_rct", dict(n=256, random_state=731, outcome_type="normal",
                    add_pre=pre, add_ancillary=True, deterministic_ids=True, return_causal_data=converted,
                    **sampling(path))))
    for family in ["continuous", "binary", "poisson", "gamma"]:
        for oracle in [False, True]:
            for ancillary in [False, True]:
                for converted in [False, True]:
                    for path in ["independent", "copula", "custom"]:
                        cases.append((iv, "generate_iv_data", dict(n=256, random_state=731,
                            outcome_type=family, include_oracle=oracle, add_ancillary=ancillary,
                            deterministic_ids=True, return_causal_data=converted,
                            instrument_name="Encouragement β", **sampling(path))))
    for family in ["continuous", "binary", "poisson", "gamma", "tweedie"]:
        for oracle in [False, True]:
            for ancillary in [False, True]:
                cases.append((binary, "obs_linear_effect", dict(n=256, random_state=731,
                    outcome_type=family, include_oracle=oracle, add_ancillary=ancillary,
                    deterministic_ids=True, **sampling("independent"))))
    for function in ["make_cuped_tweedie", "generate_cuped_binary"]:
        for pre in [False, True]:
            for oracle in [False, True]:
                for converted in [False, True]:
                    cases.append((binary, function, dict(n=512, seed=731, add_pre=pre,
                        include_oracle=oracle, return_causal_data=converted)))
    for function in ["generate_classic_rct", "classic_rct_gamma"]:
        for pre in [False, True]:
            for converted in [False, True]:
                cases.append((binary, function, dict(n=256, random_state=731, add_pre=pre,
                    add_ancillary=True, deterministic_ids=True, return_causal_data=converted)))
    for family in ["continuous", "binary", "poisson", "gamma"]:
        for oracle in [False, True]:
            for converted in [False, True]:
                for path in ["default", "copula", "custom"]:
                    cases.append((multi, "generate_multitreatment", dict(n=256, random_state=731,
                        outcome_type=family, include_oracle=oracle, return_causal_data=converted,
                        d_names=["control β", "active one", "active two"], **sampling(path))))
    for encoding in ["one_hot", "binary"]:
        for user_id in [False, True]:
            for oracle in [False, True]:
                for converted in [False, True]:
                    cases.append((MODULES[8], "generate_rct_causal_data", dict(n=256, seed=731,
                        n_treatments=2 if encoding == "binary" else 3, treatment_encoding=encoding,
                        include_user_id=user_id, include_oracle=oracle, return_causal_data=converted,
                        outcome_specs=[{"name": "result " + family, "outcome_type": family}
                                       for family in ["continuous", "binary", "poisson", "gamma"]])))
    for function in ["generate_classic_rct_26", "classic_rct_gamma_26"]:
        for pre in [False, True]:
            for ancillary in [False, True]:
                for converted in [False, True]:
                    cases.append((MODULES[9], function, dict(n=256, seed=731, add_pre=pre,
                        add_ancillary=ancillary, deterministic_ids=True, return_causal_data=converted)))
    for function in ["generate_cuped_tweedie_26", "make_cuped_binary_26"]:
        for pre in [False, True]:
            for converted in [False, True]:
                cases.append((MODULES[10], function, dict(n=512, seed=731, add_pre=pre,
                    return_causal_data=converted)))
    return cases


def exact_wrappers(old, baseline_only=False):
    rows = []
    for number, (module, function, kw) in enumerate(wrapper_fixtures()):
        expected, expected_meta, states, draws = capture_call(old, module, function, kw)
        assert expected.columns.is_unique, (function, kw)
        if not baseline_only:
            actual, actual_meta, actual_states, actual_draws = capture_call(CURRENT, module, function, kw)
            pd.testing.assert_frame_equal(expected, actual, check_exact=True)
            assert expected_meta == actual_meta, (function, expected_meta, actual_meta)
            assert states == actual_states, function
            assert len(draws) == len(actual_draws), function
            for left, right in zip(draws, actual_draws):
                np.testing.assert_array_equal(left, right)
        rows.append({"case": number, "module": module, "wrapper": function,
                     "family": kw.get("outcome_type", function), "oracle": kw.get("include_oracle", True),
                     "pre": kw.get("add_pre", False), "ancillary": kw.get("add_ancillary", False),
                     "converted": kw.get("return_causal_data", False), "columns": list(expected.columns),
                     "tracked_rngs": len(draws), "exact_frame_schema_dtypes_metadata_next10rng": not baseline_only})
    return rows


def exact_core_conversion(old):
    rows = []
    for module_name, class_name, method, families in [
        (MODULES[1], "CausalDatasetGenerator", "to_causal_data",
         ["continuous", "binary", "poisson", "gamma", "tweedie", "tweedie_lognormal"]),
        (MODULES[3], "InstrumentalGenerator", "to_iv_causal_data", ["continuous", "binary", "poisson", "gamma"]),
    ]:
        for family in families:
            for oracle in [False, True]:
                for path in ["default", "independent", "copula", "custom"]:
                    kw = dict(seed=731, outcome_type="tweedie" if family.startswith("tweedie") else family,
                              include_oracle=oracle, **sampling(path))
                    if family == "tweedie_lognormal":
                        kw["pos_dist"] = "lognormal"
                    if class_name == "InstrumentalGenerator":
                        kw["instrument_name"] = "Encouragement β"
                    with overlay(old):
                        before = getattr(old[module_name], class_name)(**kw)
                    after = getattr(CURRENT[module_name], class_name)(**kw)
                    for _ in range(2):
                        with overlay(old):
                            expected, expected_meta = as_result(getattr(before, method)(256))
                        actual, actual_meta = as_result(getattr(after, method)(256))
                        pd.testing.assert_frame_equal(expected, actual, check_exact=True)
                        assert expected_meta == actual_meta
                        np.testing.assert_array_equal(before.rng.random(10), after.rng.random(10))
                    rows.append({"class": class_name, "family": family, "oracle": oracle,
                                 "sampling": path, "generations": 2,
                                 "exact_frame_schema_dtypes_metadata_next10rng": True})
    return rows


def expect_value_error(action, label, name=None):
    try:
        action()
    except ValueError as exc:
        if name is not None:
            assert repr(name) in str(exc) or str(name) in str(exc), (label, str(exc))
        return {"case": label, "status": "ValueError", "message": str(exc)}
    raise AssertionError("Expected ValueError: " + label)


def namespace_checks():
    binary = CURRENT[MODULES[5]]
    iv = CURRENT[MODULES[6]]
    shared = CURRENT[MODULES[0]]
    preperiod = CURRENT[MODULES[2]]
    rows = []
    for name, _ in shared._ANCILLARY_COLUMN_ROLES:
        df = pd.DataFrame({"y": [0., 1., 2.], "d": [0., 1., 0.],
                           "feature": [-1., 0., 1.], name: [7., 8., 9.]})
        expected = df.copy(deep=True)
        rng = np.random.default_rng(731)
        old_state = json.dumps(rng.bit_generator.state, sort_keys=True)
        rows.append(expect_value_error(lambda: shared._add_ancillary_info(
            df, 3, rng, True, ["feature"]), "ancillary_direct_" + name, name))
        pd.testing.assert_frame_equal(expected, df, check_exact=True)
        assert json.dumps(rng.bit_generator.state, sort_keys=True) == old_state
        for wrapper, module in [("generate_rct", binary), ("obs_linear_effect", binary),
                                ("generate_iv_data", iv)]:
            kw = dict(n=128, confounder_specs=[{"name": name}], add_ancillary=True,
                      deterministic_ids=True, include_oracle=False)
            if wrapper == "generate_rct":
                kw["add_pre"] = False
            rows.append(expect_value_error(lambda m=module, f=wrapper, k=kw: getattr(m, f)(**k),
                                           wrapper + "_ancillary_" + name, name))
    for name in ["y", "d", "baseline feature", "m", "user_id", "age"]:
        kw = dict(n=128, outcome_type="normal", confounder_specs=[{"name": "baseline feature"}],
                  add_pre=True, pre_name=name, add_ancillary=name in ["user_id", "age"],
                  deterministic_ids=True, include_oracle=True)
        rows.append(expect_value_error(lambda k=kw: binary.generate_rct(**k), "rct_pre_" + name, name))
    for name in [None, "", ["unhashable"]]:
        rows.append(expect_value_error(lambda name=name: binary.generate_rct(
            n=128, add_pre=True, pre_name=name, add_ancillary=False), "rct_invalid_pre_" + repr(name)))
    for name in ["y", "d", "tenure_months", "m", "_latent_A"]:
        rows.append(expect_value_error(lambda name=name: binary.make_cuped_tweedie(
            n=128, pre_name=name, include_oracle=True, return_causal_data=False),
            "tweedie_pre_" + name, name))
    for name in ["y", "d", "m"]:
        rows.append(expect_value_error(lambda name=name: binary.generate_cuped_binary(
            n=128, pre_name=name, include_oracle=True, return_causal_data=False),
            "binary_cuped_pre_" + name, name))
    for name in ["age", "user_id"]:
        rows.append(expect_value_error(lambda name=name: iv.generate_iv_data(
            n=128, instrument_name=name, add_ancillary=True, deterministic_ids=True,
            include_oracle=False), "iv_instrument_ancillary_" + name, name))
    for callback in [False, True]:
        df = pd.DataFrame({"y": np.arange(12.) ** 2, "d": [0.] * 6 + [1.] * 6})
        rng = np.random.default_rng(731)
        state = json.dumps(rng.bit_generator.state, sort_keys=True)
        called = []
        def builder(frame):
            called.append(True)
            frame["pre"] = 123.
            return np.arange(12.)
        if not callback:
            df["pre"] = 456.
        rows.append(expect_value_error(lambda: preperiod.add_preperiod_covariate(
            df, "y", "d", "pre", builder, preperiod.PreCorrSpec(target_corr=.4), rng),
            "pre_helper_callback_collision" if callback else "pre_helper_early_collision", "pre"))
        assert json.dumps(rng.bit_generator.state, sort_keys=True) == state
        assert called == [True] if callback else called == []
        assert df["pre"].eq(123. if callback else 456.).all()
    return rows


def selected_metadata(result, confounders, user_id=None, instrument=None):
    assert result.df.columns.is_unique
    assert result.confounders_names == confounders, (result.confounders_names, confounders)
    assert result.user_id_name == user_id
    if instrument is not None:
        assert result.instruments == [instrument], result.instruments


def permitted_names_and_conversion():
    binary = CURRENT[MODULES[5]]
    iv = CURRENT[MODULES[6]]
    rows = []
    for name in ["m", "m_obs", "tau_link", "g0", "g1", "cate", "user_id"]:
        specs = [{"name": name}, {"name": "ordinary feature"}]
        result = binary.generate_rct(n=256, outcome_type="normal", include_oracle=False,
            add_pre=False, add_ancillary=False, confounder_specs=specs, return_causal_data=True)
        selected_metadata(result, [name, "ordinary feature"])
        rows.append({"case": "rct_disabled_role_" + name, "confounders": result.confounders_names,
                     "user_id": result.user_id_name})
        core = CURRENT[MODULES[1]].CausalDatasetGenerator(seed=731, confounder_specs=specs,
                                                         include_oracle=False).to_causal_data(256)
        selected_metadata(core, [name, "ordinary feature"])
    for name in ["m", "r_obs", "g_z0", "cate", "user_id", "m_obs", "g0", "g1"]:
        specs = [{"name": name}, {"name": "ordinary feature"}]
        result = iv.generate_iv_data(n=256, include_oracle=False, add_ancillary=False,
            confounder_specs=specs, return_causal_data=True)
        selected_metadata(result, [name, "ordinary feature"], instrument="z")
        rows.append({"case": "iv_available_feature_" + name, "confounders": result.confounders_names,
                     "user_id": result.user_id_name})
        core = CURRENT[MODULES[3]].InstrumentalGenerator(seed=731, confounder_specs=specs,
                                                        include_oracle=False).to_iv_causal_data(256)
        selected_metadata(core, [name, "ordinary feature"], instrument="z")
    for name in ["m", "user_id", "m_obs", " "]:
        for oracle in [False, True] if name in ["user_id", "m_obs", " "] else [False]:
            result = iv.generate_iv_data(n=256, instrument_name=name, include_oracle=oracle,
                confounder_specs=[{"name": "ordinary feature"}], return_causal_data=True)
            selected_metadata(result, ["ordinary feature"], instrument=name)
            raw = iv.generate_iv_data(n=256, instrument_name=name, include_oracle=oracle,
                confounder_specs=[{"name": "ordinary feature"}], return_causal_data=False)
            assert raw.columns.is_unique
            rows.append({"case": "iv_available_instrument_" + repr(name), "oracle": oracle,
                         "columns": list(raw.columns), "user_id": result.user_id_name})
    for name in ["y", "d", "m", "user_id", "ordinary feature", None, "", ["unused"]]:
        raw = binary.generate_rct(n=128, outcome_type="normal", include_oracle=False,
            add_pre=False, pre_name=name, add_ancillary=False,
            confounder_specs=[{"name": "ordinary feature"}])
        assert list(raw.columns) == ["y", "d", "ordinary feature"]
        rows.append({"case": "disabled_pre_name_" + repr(name), "columns": list(raw.columns)})
    for pre_name in ["m", "user_id", "age", " "]:
        result = binary.generate_rct(n=256, outcome_type="normal", include_oracle=False,
            add_pre=True, pre_name=pre_name, add_ancillary=False,
            confounder_specs=[{"name": "ordinary feature"}], return_causal_data=True)
        selected_metadata(result, ["ordinary feature", pre_name])
        rows.append({"case": "available_pre_name_" + repr(pre_name), "confounders": result.confounders_names})
    return rows


def callback_and_snapshot_checks():
    rows = []
    cls = CURRENT[MODULES[3]].InstrumentalGenerator
    for changed in ["include_oracle", "instrument_name", "both"]:
        holder, calls = {}, []
        def callback(x):
            calls.append(True)
            if len(calls) == 2:
                if changed in ["include_oracle", "both"]:
                    holder["gen"].include_oracle = False
                if changed in ["instrument_name", "both"]:
                    holder["gen"].instrument_name = "renamed after frame"
            return np.zeros(len(x))
        gen = cls(seed=731, k=2, g_y=callback, u_strength_d=0., u_strength_y=0.)
        holder["gen"] = gen
        result = gen.to_iv_causal_data(256)
        selected_metadata(result, ["x1", "x2"], instrument="z")
        assert any(name == "m" for name, role in gen._generated_column_roles)
        assert next(name for name, role in gen._generated_column_roles if role == "instrument") == "z"
        rows.append({"case": "iv_late_callback_" + changed, "callback_calls": len(calls),
                     "selected_instruments": result.instruments, "confounders": result.confounders_names})
    for module, class_name in [(MODULES[1], "CausalDatasetGenerator"), (MODULES[3], "InstrumentalGenerator")]:
        gen = getattr(CURRENT[module], class_name)(seed=731, k=2)
        assert gen._generated_confounder_names == () and gen._generated_column_roles == ()
        gen.generate(128)
        confounders, roles = gen._generated_confounder_names, gen._generated_column_roles
        gen.x_sampler = lambda n, k, seed: (_ for _ in ()).throw(RuntimeError("synthetic failure"))
        try:
            gen.generate(128)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Synthetic failure not raised")
        assert gen._generated_confounder_names == confounders and gen._generated_column_roles == roles
        rows.append({"case": class_name + "_failed_generate_preserves_previous_success", "passed": True})
    names, calls = ["sampled feature"], []
    class MutableSamplerIV(cls):
        def _sample_X(self, n):
            return np.linspace(-1., 1., n).reshape(n, 1), names
    def mutate_names(x):
        calls.append(True)
        if len(calls) == 2:
            names[0] = "renamed after frame"
        return np.zeros(len(x))
    gen = MutableSamplerIV(seed=731, k=1, g_y=mutate_names, u_strength_d=0., u_strength_y=0.)
    result = gen.to_iv_causal_data(256)
    selected_metadata(result, ["sampled feature"], instrument="z")
    assert gen._generated_confounder_names == ("sampled feature",)
    rows.append({"case": "iv_late_callback_mutates_sampler_names_list", "passed": True,
                 "actual_confounders": result.confounders_names, "mutated_external_list": names})
    return rows


def residual_checks(old):
    kw = dict(n=256, seed=731, add_pre=True, pre_name="conversion", add_ancillary=False,
              return_causal_data=False)
    baseline, _, _, _ = capture_call(old, MODULES[9], "generate_classic_rct_26", kw)
    current, _, _, _ = capture_call(CURRENT, MODULES[9], "generate_classic_rct_26", kw)
    pd.testing.assert_frame_equal(baseline, current, check_exact=True)
    assert list(current.columns).count("conversion") == 2
    return [{"case": "classic_rct_26_pre_name_conversion_late_rename", "out_of_scope": True,
             "baseline_and_current_columns": list(current.columns),
             "impact": "raw output duplicates conversion; contract rejects duplicate labels"}]


def wrapper_callback_and_helper_checks():
    rows = []
    iv = CURRENT[MODULES[6]]
    original = iv.InstrumentalGenerator
    for phase, target, ancillary, converted in [
        ("before_frame", "user_id", False, False),
        ("before_frame", "user_id", False, True),
        ("after_frame", "renamed after frame", True, False),
        ("after_frame", "renamed after frame", True, True),
    ]:
        holder, calls = {}, []
        def factory(**kw):
            holder["gen"] = original(**kw)
            return holder["gen"]
        def callback(x):
            calls.append(True)
            if len(calls) == (1 if phase == "before_frame" else 2):
                holder["gen"].instrument_name = target
                holder["gen"].include_oracle = False
            return np.zeros(len(x))
        iv.InstrumentalGenerator = factory
        try:
            result = iv.generate_iv_data(n=256, random_state=731, add_ancillary=ancillary,
                deterministic_ids=True, return_causal_data=converted,
                u_strength_d=0., u_strength_y=0.,
                **{"g_z" if phase == "before_frame" else "g_y": callback})
        finally:
            iv.InstrumentalGenerator = original
        frame = result.df if converted else result
        actual_instrument = target if phase == "before_frame" else "z"
        assert frame.columns.is_unique and actual_instrument in frame.columns
        if converted:
            selected_metadata(result, ["x1", "x2"] + (["age", "cnt_trans", "platform_Android",
                "platform_iOS", "invited_friend"] if ancillary else []),
                user_id="user_id" if ancillary else None, instrument=actual_instrument)
        elif phase == "after_frame":
            assert "m" in frame.columns and "g_d1" in frame.columns
        rows.append({"case": "wrapper_mutation_" + phase, "converted": converted,
                     "actual_instrument": actual_instrument, "columns": list(frame.columns), "passed": True})
    binary = CURRENT[MODULES[5]]
    generator = CURRENT[MODULES[1]].CausalDatasetGenerator(
        seed=731, outcome_type="tweedie", k=1, include_oracle=False)
    frame = generator.generate(128)
    calls = []
    def create_pre_in_callback(x):
        calls.append(True)
        frame["callback pre"] = -123.
        return np.zeros(len(x))
    generator.g_y = create_pre_in_callback
    rows.append(expect_value_error(lambda: binary._add_tweedie_pre(
        frame, 128, generator, ["x1"], target_corr=.2, pre_name="callback pre",
        A=np.zeros(128)), "tweedie_callback_cannot_overwrite_pre", "callback pre"))
    assert calls and frame["callback pre"].eq(-123.).all()
    return rows


def constructor_checks(old):
    rows = []
    for module, name in [(MODULES[1], "CausalDatasetGenerator"), (MODULES[3], "InstrumentalGenerator")]:
        before, after = getattr(old[module], name), getattr(CURRENT[module], name)
        assert str(inspect.signature(before)) == str(inspect.signature(after))
        for field in ["_generated_confounder_names", "_generated_column_roles"]:
            settings = after.__dataclass_fields__[field]
            assert not settings.init and not settings.repr and not settings.compare
        rows.append({"class": name, "public_constructor_unchanged": True,
                     "private_fields_excluded_from_init_repr_compare": True})
    return rows


def main():
    baseline_only = "--baseline-only" in sys.argv
    partial = "--partial" in sys.argv
    frozen = freeze_graph()
    result = {"baseline": BASELINE, "reviewed_head": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "scope": "partial working tree review" if partial else (
            "baseline only" if baseline_only else "baseline to current working tree"),
        "frozen_module_sha256": {path: hashlib.sha256(subprocess.check_output(
            ["git", "show", f"{BASELINE}:{path}"], cwd=ROOT)).hexdigest() for path in SOURCE_PATHS},
        "current_library_sha256": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                                    for path in SOURCE_PATHS},
        "current_test_module_sha256": hashlib.sha256((ROOT / "tests/data/test_wrapper_namespace_contract.py").read_bytes()).hexdigest()}
    issues = []
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result["valid_wrapper_configs"] = exact_wrappers(frozen, baseline_only or partial)
        if partial or not baseline_only:
            result["valid_core_conversion_configs"] = exact_core_conversion(frozen)
        if not baseline_only and not partial:
            result["namespace_rejections"] = namespace_checks()
            result["permitted_names_and_conversion"] = permitted_names_and_conversion()
            result["callback_and_snapshot_checks"] = callback_and_snapshot_checks()
            result["residual_checks"] = residual_checks(frozen)
            result["wrapper_callback_and_helper_checks"] = wrapper_callback_and_helper_checks()
            result["constructor_checks"] = constructor_checks(frozen)
        if partial:
            try:
                result["callback_and_snapshot_checks"] = callback_and_snapshot_checks()
            except KeyError as exc:
                assert str(exc) == "'renamed after frame'"
                issues.append({"case": "iv_late_callback_mutates_sampler_names_list",
                               "status": "confirmed unresolved", "exception": type(exc).__name__,
                               "message": str(exc),
                               "impact": "snapshot captures renamed list after assembly; conversion KeyError"})
            result["residual_checks"] = residual_checks(frozen)
        result["warnings"] = sorted(set(str(w.message) for w in captured))
    result["issues"] = issues
    (ROOT / "audit/block12_review_probe.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"wrapper_configs": len(result["valid_wrapper_configs"]),
                      "core_conversion_configs": len(result.get("valid_core_conversion_configs", [])),
                      "baseline_only": baseline_only, "issues": result["issues"]}))


if __name__ == "__main__":
    main()
