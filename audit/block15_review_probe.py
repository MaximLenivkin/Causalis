"""Independent public B15 default references and adaptive Gaussian-q probes."""
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import importlib
import inspect
import json
import math
from pathlib import Path
import subprocess
import sys
import types
import warnings
from unittest.mock import patch
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
from scipy.integrate import quad
from scipy.special import softmax, ndtr

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "71f6a619b04e0ab8fab388fb95b7d0f3d6631b96"
NAMES = ["causalis.dgp.base", "causalis.dgp.multicausaldata.base",
         "causalis.dgp.multicausaldata.functional", "causalis.scenarios.multi_unconfoundedness.dgp"]
PATHS = [name.replace(".", "/") + ".py" for name in NAMES]
UNCHANGED = [PATHS[0], PATHS[3], "causalis/dgp/multicausaldata/__init__.py",
             "causalis/data_contracts/multicausaldata.py", "causalis/data_contracts/__init__.py"]
CURRENT = {name: importlib.import_module(name) for name in NAMES}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def blob(commit, path):
    return subprocess.check_output(["git", "show", commit + ":" + path], cwd=ROOT)


@contextmanager
def overlay(graph):
    saved_modules = {name: sys.modules.get(name) for name in graph}
    saved_attrs = []
    def change(owner, name, value):
        saved_attrs.append((owner, name, name in vars(owner), vars(owner).get(name)))
        setattr(owner, name, value)
    try:
        sys.modules.update(graph)
        for name, module in graph.items():
            parent, leaf = name.rsplit(".", 1)
            change(sys.modules[parent], leaf, module)
        package = sys.modules["causalis.dgp.multicausaldata"]
        if NAMES[1] in graph:
            change(package, "MultiCausalDatasetGenerator", graph[NAMES[1]].MultiCausalDatasetGenerator)
        if NAMES[2] in graph:
            change(package, "generate_multitreatment", graph[NAMES[2]].generate_multitreatment)
        yield
    finally:
        for owner, name, existed, value in reversed(saved_attrs):
            if existed:
                setattr(owner, name, value)
            else:
                delattr(owner, name)
        for name, value in saved_modules.items():
            if value is None:
                del sys.modules[name]
            else:
                sys.modules[name] = value


def freeze():
    graph = {}
    for index, (name, path) in enumerate(zip(NAMES, PATHS)):
        module = types.ModuleType("block15_frozen_" + str(index))
        module.__package__ = name.rsplit(".", 1)[0]
        sys.modules[module.__name__] = module
        with overlay(graph):
            exec(compile(blob(BASELINE, path), BASELINE + ":" + path, "exec"), module.__dict__)
        graph[name] = module
    assert graph[NAMES[1]]._gaussian_copula is graph[NAMES[0]]._gaussian_copula
    assert graph[NAMES[2]].MultiCausalDatasetGenerator is graph[NAMES[1]].MultiCausalDatasetGenerator
    assert graph[NAMES[3]].generate_multitreatment is graph[NAMES[2]].generate_multitreatment
    return graph


def exact(left, right, label="reference"):
    if isinstance(left, pd.DataFrame):
        pd.testing.assert_frame_equal(left, right, check_exact=True, obj=label)
    elif isinstance(left, np.ndarray):
        assert left.dtype == right.dtype and left.shape == right.shape, label
        np.testing.assert_array_equal(left, right, err_msg=label)
    elif isinstance(left, dict):
        assert left.keys() == right.keys(), label
        for key in left:
            exact(left[key], right[key], label + "." + str(key))
    elif isinstance(left, (tuple, list)):
        assert type(left) is type(right) and len(left) == len(right), label
        for a, b in zip(left, right):
            exact(a, b, label)
    elif isinstance(left, float) and np.isnan(left):
        assert np.isnan(right), label
    else:
        assert left == right, (label, left, right)


@contextmanager
def capture_rng():
    original, streams = np.random.default_rng, []
    def factory(*args, **kwargs):
        stream = original(*args, **kwargs)
        streams.append(stream)
        return stream
    np.random.default_rng = factory
    try:
        yield streams
    finally:
        np.random.default_rng = original


def rng_values(streams):
    return [(stream.bit_generator.state, stream.random(10)) for stream in streams]


def settings(family, variant, calls):
    args = dict(n_treatments=3, k=2, seed=15137, outcome_type=family,
                alpha_y=-.4, theta=[0, .4, -.2], d_names=["control", "test A", "λ"],
                beta_y=[.1, -.2], beta_d=[[0, 0], [.2, -.1], [-.1, .2]])
    supplied = None
    if variant == "zero_iid":
        args["assignment_policy"] = "iid"
    elif variant == "latent":
        args.update(u_strength_d=[-.5, 1., 2.], u_strength_y=.3)
    elif variant == "supplied":
        args.update(u_strength_d=[.1, .7, -.5], u_strength_y=.3)
        supplied = np.linspace(-3, 3, 48).reshape(1, -1)
    elif variant == "calibrated":
        args.update(target_d_rate=[.2, .3, .5], u_strength_d=[0, 1, -1])
    elif variant == "callbacks":
        def callback(name, value):
            def invoke(x):
                calls.append(name)
                return value(x)
            return invoke
        args.update(g_y=callback("g_y", lambda x: .07 * x[:, 0] ** 2),
                    g_d=[None, callback("g_d1", lambda x: .03 * x[:, 1]),
                         callback("g_d2", lambda x: np.array([.02]))],
                    tau=[None, callback("tau1", lambda x: .03 * x[:, 0]),
                         callback("tau2", lambda x: np.full(len(x), -.05))],
                    u_strength_d=[0, .4, -.3])
    elif variant == "copula_categorical":
        args.update(confounder_specs=[{"name": "category", "dist": "categorical", "categories": [0, 1, 2]},
                                      {"name": "normal", "dist": "normal"}], use_copula=True,
                    copula_corr=[[1, .3], [.3, 1]], beta_y=[.1, -.2, .05],
                    beta_d=[[0, 0, 0], [.2, -.1, .1], [-.1, .2, .1]])
    elif variant == "custom":
        def sampler(n, k, seed):
            calls.append("sampler")
            return np.random.default_rng(seed).normal(size=(n, k))
        args.update(x_sampler=sampler, u_strength_d=.5, u_strength_y=.2)
    elif variant == "disabled_oracle_names":
        args.update(include_oracle=False, confounder_specs=[{"name": "m_marginal_control"}, {"name": "g_control"}])
    return args, supplied


def default_references(old):
    references = []
    variants = ["zero_iid", "latent", "supplied", "calibrated", "callbacks",
                "copula_categorical", "custom", "disabled_oracle_names"]
    for family in ("continuous", "binary", "poisson", "gamma"):
        for variant in variants:
            outputs, randomness, callbacks = [], [], []
            for graph in (old, CURRENT):
                call_log = []
                args, supplied = settings(family, variant, call_log)
                with overlay(graph), capture_rng() as streams:
                    gen = graph[NAMES[1]].MultiCausalDatasetGenerator(**args)
                    frames = [gen.generate(48, U=supplied) for _ in range(2)]
                    outputs.append(frames)
                    randomness.append(rng_values(streams))
                callbacks.append(call_log)
            exact(outputs[0], outputs[1], "default complete frames")
            exact(randomness[0], randomness[1], "default all RNG streams")
            exact(callbacks[0], callbacks[1], "default callback counts/order")
            references.append(dict(surface="generator", family=family, variant=variant, calls=2))
        for oracle in (False, True):
            for surface in ("functional_raw", "functional_contract", "to_multicausal_data"):
                outputs, randomness = [], []
                for graph in (old, CURRENT):
                    with overlay(graph), capture_rng() as streams:
                        if surface == "to_multicausal_data":
                            gen = graph[NAMES[1]].MultiCausalDatasetGenerator(k=2, outcome_type=family,
                                                                           seed=15371, include_oracle=oracle)
                            values = [gen.to_multicausal_data(48) for _ in range(2)]
                        else:
                            values = [graph[NAMES[2]].generate_multitreatment(n=48, k=2, outcome_type=family,
                                      random_state=15371 + iteration, include_oracle=oracle,
                                      return_causal_data=surface == "functional_contract", target_d_rate=[.2, .4, .4])
                                      for iteration in range(2)]
                        outputs.append([v if isinstance(v, pd.DataFrame) else v.model_dump(mode="python") for v in values])
                        randomness.append(rng_values(streams))
                exact(outputs[0], outputs[1], "default wrapper frame/contract metadata")
                exact(randomness[0], randomness[1], "default wrapper RNG")
                references.append(dict(surface=surface, family=family, oracle=oracle, calls=2))
    return references


def adaptive_reference(intercepts, slopes):
    """Scalar QUADPACK, independent softmax, Decimal crossing geometry.

    Wider reference intervals use different transition offsets from runtime.
    Each arm has its own adaptive/error calculation; no vector helper is reused.
    """
    a, b = np.asarray(intercepts, float), np.asarray(slopes, float)
    points = {0.0}
    with localcontext() as context:
        context.prec = 80
        for i in range(len(a)):
            for j in range(i):
                da = Decimal.from_float(float(a[j])) - Decimal.from_float(float(a[i]))
                db = Decimal.from_float(float(b[i])) - Decimal.from_float(float(b[j]))
                if db == 0:
                    continue
                crossing, width = da / db, Decimal(1) / abs(db)
                for offset in (Decimal(0), Decimal(-128), Decimal(-8), Decimal(8), Decimal(128)):
                    z = float(crossing + offset * width)
                    if -12 < z < 12:
                        points.add(z)
    values, errors = [], []
    for arm in range(len(a)):
        def integrand(z):
            with np.errstate(over="ignore", under="ignore"):
                logits = (a - a.max()) + (b - b[0]) * z
                return float(softmax(logits)[arm] * math.exp(-.5 * z*z) / math.sqrt(2 * math.pi))
        value, error = quad(integrand, -12, 12, points=sorted(points), epsabs=2e-12, epsrel=2e-12, limit=1000)
        values.append(value)
        errors.append(error)
    return np.asarray(values), errors


def public_q(intercepts, slopes, U=0.):
    k = len(intercepts)
    gen = CURRENT[NAMES[1]].MultiCausalDatasetGenerator(n_treatments=k, k=0, seed=15137,
              alpha_d=intercepts, u_strength_d=slopes, include_marginal_propensity=True, assignment_policy="iid")
    frame = gen.generate(1, U=U)
    return frame[["m_marginal_" + name for name in gen.d_names]].iloc[0].to_numpy(), frame


def numerical_references():
    cases = []
    for strength in (0., .1, 1., 2., 5., 10., 50., 1e3, 1e6):
        for k in (2, 3, 5):
            a = np.linspace(-.8, 1.1, k)
            b = np.linspace(-strength, strength, k)
            cases.append(("symmetric_%s_%s" % (k, strength), a, b))
    cases.extend([
        ("equal_common_slope", np.array([-.5, .2, .9]), np.full(3, 1e5)),
        ("B07_reference", np.zeros(3), np.array([0., 1., 1.])),
        ("narrow_middle", np.array([-10., 0., -10.]), np.array([-1e6, 0., 1e6])),
        ("rare_narrow_middle", np.array([0., -10., 0.]), np.array([-1e6, 0., 1e6])),
        ("offset_narrow_middle", np.array([299990., 0., -300010.]), np.array([-1e6, 0., 1e6])),
        ("tails_at_six", np.array([0., -6e4]), np.array([0., 1e4])),
        ("nearly_equal_slopes", np.array([-1., .2, .7]), np.array([1., 1. + 1e-12, 1. - 1e-12])),
    ])
    results = []
    for label, a, b in cases:
        q, _ = public_q(a, b)
        ref, err = adaptive_reference(a, b)
        maximum = float(np.max(np.abs(q - ref)))
        assert maximum < 1e-10, (label, q, ref, maximum, err)
        assert np.isfinite(q).all() and (q >= 0).all() and (q <= 1).all()
        assert abs(q.sum() - 1) < 2e-15
        results.append(dict(case=label, intercepts=a.tolist(), slopes=b.tolist(), q=q.tolist(),
                            reference=ref.tolist(), max_abs_error=maximum, reference_error_estimates=err))
    a, b = np.array([-.5, .2, .9]), np.array([-.4, .7, 2.])
    q, _ = public_q(a, b)
    invariants = []
    for label, shifted_a, shifted_b, perm in [
        ("common_intercept", a + 128., b, None), ("common_slope", a, b + 128., None),
        ("sign_reversal", a, -b, None), ("permutation", a[[2, 0, 1]], b[[2, 0, 1]], [2, 0, 1])]:
        changed, _ = public_q(shifted_a, shifted_b)
        np.testing.assert_allclose(changed, q if perm is None else q[perm], atol=2e-13, rtol=0)
        invariants.append(label)
    huge, _ = public_q([0., -1e306], [0., 1e306])
    np.testing.assert_allclose(huge, [ndtr(1.), ndtr(-1.)], atol=1e-12, rtol=0)
    outside, _ = public_q([1e308, -1e308], [-5e306, 5e306])
    np.testing.assert_allclose(outside, [1., 0.], atol=1e-12, rtol=0)
    return {"adaptive_cases": results, "invariants": invariants,
            "huge_finite_step_reference": huge.tolist(), "overflow_crossing_outside_domain": outside.tolist()}


def additive_references():
    results = []
    for family in ("continuous", "binary", "poisson", "gamma"):
        for variant in ("latent", "supplied", "calibrated", "callbacks", "copula_categorical"):
            outputs, randomness, callbacks = [], [], []
            for enabled in (False, True):
                call_log = []
                args, supplied = settings(family, variant, call_log)
                args["include_marginal_propensity"] = enabled
                with capture_rng() as streams:
                    gen = CURRENT[NAMES[1]].MultiCausalDatasetGenerator(**args)
                    frames = [gen.generate(48, U=supplied) for _ in range(2)]
                    outputs.append(frames)
                    randomness.append(rng_values(streams))
                callbacks.append(call_log)
            marginal_names = ["m_marginal_" + name for name in args["d_names"]]
            for old_frame, enabled_frame in zip(outputs[0], outputs[1]):
                assert list(enabled_frame.columns) == list(old_frame.columns) + marginal_names
                pd.testing.assert_frame_equal(old_frame, enabled_frame.drop(columns=marginal_names), check_exact=True)
            exact(randomness[0], randomness[1], "enabled/default RNG")
            exact(callbacks[0], callbacks[1], "enabled/default callbacks")
            results.append(dict(family=family, variant=variant, calls=2))
    return results


def rejection_references():
    cls = CURRENT[NAMES[1]].MultiCausalDatasetGenerator
    result = []
    cases = {"flag_conflict": dict(include_oracle=False, include_marginal_propensity=True),
             "flag_integer": dict(include_marginal_propensity=1),
             "flag_text": dict(include_marginal_propensity="False"),
             "flag_none": dict(include_marginal_propensity=None),
             "treatment_collision": dict(d_names=["a", "m_marginal_a"], include_marginal_propensity=True),
             "confounder_collision": dict(d_names=["a", "b"], confounder_specs=[{"name": "m_marginal_a"}], include_marginal_propensity=True),
             "categorical_collision": dict(d_names=["a", "b"], confounder_specs=[{"name": "m_marginal", "dist": "categorical", "categories": ["base", "a"]}], include_marginal_propensity=True)}
    for label, args in cases.items():
        try:
            cls(**dict(n_treatments=2, k=0, seed=1, **args)).generate(12)
        except ValueError as error:
            result.append(dict(case=label, rejected=True, message=str(error)))
        else:
            raise AssertionError(label)
    for label in ("bad_flag", "conflicting_flag", "late_callback_collision"):
        gen = cls(n_treatments=2, k=0, seed=1)
        gen.generate(12)
        if label == "bad_flag":
            gen.include_marginal_propensity = "True"
        elif label == "conflicting_flag":
            gen.include_oracle = False
            gen.include_marginal_propensity = True
        else:
            gen.confounder_specs = [{"name": "m_marginal_d_0"}]
            def toggle(x):
                gen.include_marginal_propensity = True
                return 0.
            gen.g_y = toggle
        try:
            gen.generate(12)
        except ValueError as error:
            result.append(dict(case=label, rejected=True, message=str(error)))
        else:
            raise AssertionError(label)
    for label, a, b in [("unsupported_geometry", [0., 0.], [-1e308, 1e308])]:
        try:
            public_q(a, b)
        except ValueError as error:
            result.append(dict(case=label, rejected=True, message=str(error)))
        else:
            raise AssertionError(label)
    return result


def boundary_main():
    result_path = ROOT / "audit/block15_review_result.json"
    result = json.loads(result_path.read_text())
    starting = {path: digest((ROOT / path).read_bytes()) for path in PATHS[1:3]}
    assert starting == result["source_sha256"]
    policy = {"observed_at": datetime.now(timezone.utc).isoformat(), "projections": [],
              "failure_modes": [], "accepted_numpy_booleans": [], "inherited_extreme_warnings": []}
    cls = CURRENT[NAMES[1]].MultiCausalDatasetGenerator
    for oracle in (False, True):
        for surface in ("functional", "to_multicausal_data"):
            for name in ("m_marginal_a", "m_marginal_unemitted"):
                args = dict(n_treatments=2, d_names=["a", "b"], include_oracle=oracle,
                            confounder_specs=[{"name": name}], include_marginal_propensity=False)
                if surface == "functional":
                    data = CURRENT[NAMES[2]].generate_multitreatment(n=24, return_causal_data=True, **args)
                else:
                    data = cls(seed=15137, **args).to_multicausal_data(24)
                assert data.confounders == [name]
                assert name in data.df.columns and np.std(data.df[name]) > 0
                policy["projections"].append(dict(surface=surface, oracle=oracle, feature=name))
    for surface in ("functional", "to_multicausal_data"):
        args = dict(n_treatments=2, d_names=["a", "b"], confounder_specs=[{"name": "feature"}],
                    include_marginal_propensity=True)
        data = (CURRENT[NAMES[2]].generate_multitreatment(n=24, return_causal_data=True, **args)
                if surface == "functional" else cls(seed=15137, **args).to_multicausal_data(24))
        assert data.confounders == ["feature"]
        # MultiCausalData intentionally projects away all oracle columns.
        assert not any(name.startswith("m_marginal_") for name in data.df.columns)
        ordinary_args = dict(args, include_marginal_propensity=False)
        ordinary = (CURRENT[NAMES[2]].generate_multitreatment(n=24, return_causal_data=True, **ordinary_args)
                    if surface == "functional" else cls(seed=15137, **ordinary_args).to_multicausal_data(24))
        exact(ordinary.model_dump(mode="python"), data.model_dump(mode="python"), "enabled contract projection")
        policy["projections"].append(dict(surface=surface, oracle=True, enabled=True, feature="feature"))
    for value in (np.bool_(False), np.bool_(True)):
        frame = cls(n_treatments=2, k=0, seed=15137, include_marginal_propensity=value).generate(12)
        assert ("m_marginal_d_0" in frame) == bool(value)
        policy["accepted_numpy_booleans"].append(bool(value))
    failures = [
        ("unsuccessful_status", np.array([.2, .3, .5]), 1e-12, False),
        ("large_error", np.array([.2, .3, .5]), 1e-4, True),
        ("nonfinite_error", np.array([.2, .3, .5]), np.nan, True),
        ("nonfinite_probability", np.array([.2, np.nan, .5]), 1e-12, True),
        ("negative_probability", np.array([-.1, .6, .5]), 1e-12, True),
        ("probability_over_one", np.array([1.1, -.1, 0.]), 1e-12, True),
        ("invalid_total_mass", np.array([.2, .3, .4]), 1e-12, True),
    ]
    for label, probability, error, success in failures:
        mock_result = (probability, error, types.SimpleNamespace(success=success))
        with patch.object(CURRENT[NAMES[1]], "quad_vec", return_value=mock_result) as backend:
            try:
                public_q([0., .1, -.2], [0., 1., -1.])
            except ValueError as exc:
                assert "converge" in str(exc) and backend.call_count == 1
                policy["failure_modes"].append(dict(case=label, error=str(exc)))
            else:
                raise AssertionError(label)
    rng = np.random.default_rng(15179)
    with patch.object(CURRENT[NAMES[1]], "quad_vec") as backend:
        try:
            public_q(rng.normal(size=48), np.linspace(-2, 2, 48))
        except ValueError as exc:
            assert "budget" in str(exc) and backend.call_count == 0
            policy["failure_modes"].append(dict(case="subdivision_budget", error=str(exc)))
        else:
            raise AssertionError("subdivision budget")
    values = [public_q([-.4, .3, .8], [0., .7, -1.], U=u)[0] for u in (-4., 0., 4.)]
    for value in values[1:]:
        np.testing.assert_array_equal(value, values[0])
    policy["supplied_U_q_exact_invariance"] = True
    # Isolate inherited _softmax overflow warnings, preserving the default path.
    frames, streams_out = [], []
    for enabled in (False, True):
        with warnings.catch_warnings(record=True) as captured, capture_rng() as streams:
            warnings.simplefilter("always")
            gen = cls(n_treatments=2, k=0, seed=15137, alpha_d=[1e308, -1e308],
                      u_strength_d=[-5e306, 5e306], assignment_policy="iid", include_marginal_propensity=enabled)
            frames.append(gen.generate(1, U=0.))
            streams_out.append(rng_values(streams))
        policy["inherited_extreme_warnings"].append({"enabled": enabled,
            "records": [{"message": str(w.message), "category": w.category.__name__,
                         "filename": w.filename, "line": w.lineno} for w in captured]})
    pd.testing.assert_frame_equal(frames[0], frames[1].drop(columns=["m_marginal_d_0", "m_marginal_d_1"]), check_exact=True)
    exact(streams_out[0], streams_out[1], "huge finite inherited RNG")
    a, b = [x["records"] for x in policy["inherited_extreme_warnings"]]
    assert a == b and len(a) == 2 and all("overflow encountered in subtract" == x["message"] for x in a)
    assert starting == {path: digest((ROOT / path).read_bytes()) for path in PATHS[1:3]}
    policy["source_sha256"] = starting
    policy["issues"] = []
    result["bounded_policy_review"] = policy
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"projection_cases": len(policy["projections"]), "failure_cases": len(policy["failure_modes"]),
                      "supplied_U_invariance": True, "numpy_booleans": policy["accepted_numpy_booleans"],
                      "inherited_warnings_per_disabled_enabled": len(a), "issues": []}))


def link_main(source):
    assert len(source) == 40 and all(c in "0123456789abcdef" for c in source)
    result_path = ROOT / "audit/block15_review_result.json"
    result = json.loads(result_path.read_text())
    test_path = "tests/data/test_multicausal_marginal_propensity.py"
    before = json.loads((ROOT / "audit/block15_oracle_baseline_test_result.json").read_text())
    focused = json.loads((ROOT / "audit/block15_oracle_focused_test_result.json").read_text())
    assert before["test_file_sha256"] == focused["test_file_sha256"]
    assert set(before["collected_case_ids"]) == set(focused["collected_case_ids"])
    assert before["counts"] == dict(tests=79, failures=74, errors=0, skipped=0, passed=5)
    assert focused["counts"] == dict(tests=79, failures=0, errors=0, skipped=0, passed=79)
    assert focused["source_sha256"] == result["source_sha256"]
    assert focused["public_generator_and_wrapper_aliases_verified"]
    assert focused["shared_helper_and_contract_bindings_verified"]
    expected = {**result["source_sha256"], **result["unchanged_dependency_sha256"],
                test_path: focused["test_file_sha256"]}
    extra_dependency = "causalis/data_contracts/_duplicate_columns.py"
    expected[extra_dependency] = digest(blob(BASELINE, extra_dependency))
    for path, expected_hash in expected.items():
        committed = blob(source, path)
        assert digest(committed) == expected_hash == digest((ROOT / path).read_bytes()), path
        if path in UNCHANGED or path == extra_dependency:
            assert committed == blob(BASELINE, path), path
    result["final_test_review"] = dict(observed_at=datetime.now(timezone.utc).isoformat(),
        test_path=test_path, test_sha256=focused["test_file_sha256"], tests_read=79,
        baseline_counts=before["counts"], focused_counts=focused["counts"],
        feature_absence_not_numerical_bug=True, final_case_ids_identical=True,
        public_and_shared_bindings_verified=True, issues=[])
    result["committed_source_linkage"] = dict(source_checkpoint=source,
        observed_at=datetime.now(timezone.utc).isoformat(), committed_file_sha256=expected,
        three_source_test_and_six_unchanged_dependency_paths_verified=True,
        initial_reference_provenance_preserved=True, full_runtime_references_repeated=False, issues=[])
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"committed_source": source, "verified_paths": len(expected), "final_tests": 79, "issues": []}))


def ci_main(run_id):
    """Review downloaded CI evidence without numerical probes, pytest or network."""
    result_path = ROOT / "audit/block15_review_result.json"
    result = json.loads(result_path.read_text())
    source = result["committed_source_linkage"]["source_checkpoint"]
    folder = ROOT / "audit/block15_ci_test_temp" / ("run-" + str(run_id))
    def read(path):
        return json.loads(path.read_text())
    def junit(path):
        tree = ET.parse(path).getroot()
        suites = list(tree.iter("testsuite"))
        counts = {key: sum(int(suite.get(key, "0")) for suite in suites)
                  for key in ("tests", "failures", "errors", "skipped")}
        counts["passed"] = counts["tests"] - sum(counts[key] for key in ("failures", "errors", "skipped"))
        cases = [case for suite in suites for case in suite.findall("testcase")]
        identities = {(case.get("classname"), case.get("name")) for case in cases}
        assert len(identities) == len(cases) == counts["tests"]
        assert all(case.find("failure") is None and case.find("error") is None and case.find("skipped") is None
                   for case in cases), str(path)
        return counts, identities
    status_path = folder / "run_status.json"
    summary_path = ROOT / "audit/block15_ci_result.json"
    status, summary = read(status_path), read(summary_path)
    focused = read(ROOT / "audit/block15_oracle_focused_test_result.json")
    local = read(ROOT / "audit/block15_integration_result.json")
    selected = read(ROOT / "audit/block15_integration_selection.json")
    previous = read(ROOT / "audit/block14_integration_selection.json")
    assert status["headSha"] == source and status["status"] == "completed" and status["conclusion"] == "success"
    assert status["observed_at"] == summary["snapshot_observed_at"]
    assert summary["tested_source_checkpoint"] == source and summary["run_id"] == run_id
    assert summary["matrix_verified"] and summary["verified_successful_jobs"] == 6 and not summary["issues"]
    assert summary["expected_tests_per_job"] == 2618
    assert local["tested_source_checkpoint"] == selected["environment"]["commit"] == source
    exclusions = previous["excluded_modules"]
    assert len(exclusions) == 7 and exclusions == selected["excluded_modules"] == summary["excluded_modules"]
    local_junit = ROOT / "audit/block15_integration_test_temp/junit.xml"
    local_counts, local_ids = junit(local_junit)
    assert local_counts == dict(tests=2618, failures=0, errors=0, skipped=0, passed=2618)
    assert all(local[key] == value for key, value in local_counts.items())
    focused_counts, focused_ids = junit(ROOT / focused["junit"])
    assert focused_counts == dict(tests=79, failures=0, errors=0, skipped=0, passed=79)
    assert len(focused_ids) == 79 and focused_ids.issubset(local_ids)
    assert focused_ids == {tuple(case.rsplit("::", 1)) for case in focused["collected_case_ids"]}
    for path, expected in result["committed_source_linkage"]["committed_file_sha256"].items():
        assert digest(blob(source, path)) == expected == digest((ROOT / path).read_bytes()), path
    jobs_by_id = {job["databaseId"]: job for job in status["jobs"]}
    assert len(jobs_by_id) == 6
    expected_configs = {("3.10", "latest"), ("3.10", "legacy"), ("3.11", "latest"),
                        ("3.12", "latest"), ("3.13", "latest"), ("3.14", "latest")}
    artifacts = sorted(path for path in folder.iterdir() if path.is_dir() and path.name.startswith("correctness-py"))
    assert len(artifacts) == 6
    jobs, actual_configs = [], set()
    for artifact in artifacts:
        minor, stack = artifact.name.removeprefix("correctness-py").split("-")
        actual_configs.add((minor, stack))
        selection = read(artifact / "selection.json")
        outcome = read(artifact / "result.json")
        env = selection["environment"]
        assert env["commit"] == source and env["python"].startswith(minor + ".")
        assert env["implementation"] == "CPython" and env["platform"].startswith("Linux")
        assert env["docs_build_environment"] == "false"
        assert selection["scope"] == outcome["scope"] == "correctness"
        assert not selection["selected_full_suite"] and not outcome["selected_full_suite"]
        assert not selection["collect_only"] and not outcome["collect_only"] and outcome["exit_code"] == 0
        assert selection["excluded_modules"] == exclusions
        argv = selection["pytest_args"]
        actual_ignores = [argv[index + 1] for index, value in enumerate(argv) if value == "--ignore"]
        assert actual_ignores == exclusions
        trimmed = [arg for arg in argv if not arg.startswith(("--basetemp=", "--junitxml="))]
        expected_argv = ["-q", "-p", "no:cacheprovider", "tests"]
        for path in exclusions:
            expected_argv.extend(["--ignore", path])
        assert trimmed == expected_argv, trimmed
        counts, identities = junit(artifact / "junit.xml")
        assert counts == local_counts and identities == local_ids
        assert focused_ids.issubset(identities)
        row = next(job for job in summary["jobs"] if (job["python_minor"], job["stack"]) == (minor, stack))
        assert row["environment"] == env and row["pytest_result"] == outcome and row["junit"] == counts
        run_job = jobs_by_id[row["job_id"]]
        assert run_job["status"] == "completed" and run_job["conclusion"] == "success" and run_job["name"] == row["name"]
        jobs.append(dict(artifact=artifact.name, job_id=row["job_id"], python_minor=minor, stack=stack,
                         environment=env, junit=counts, complete_case_count=len(identities),
                         full_case_set_equals_local=True, new_case_count=79, actual_pytest_args=argv,
                         artifact_sha256={name: digest((artifact / name).read_bytes())
                                          for name in ("selection.json", "result.json", "junit.xml")}))
    assert actual_configs == expected_configs
    result["ci_review"] = dict(observed_at=datetime.now(timezone.utc).isoformat(), run_id=run_id,
        run_url=summary["run_url"], source_checkpoint=source, snapshot_observed_at=status["observed_at"],
        matrix_verified=True, verified_jobs=6, expected_tests_per_job=2618,
        all_full_case_sets_equal_local=True, all_79_new_case_ids_each_job=True,
        seven_exclusions_unchanged_from_B14=True, actual_ignore_arguments_verified=True,
        source_hashes_verified_against_checkpoint=True,
        source_hash_basis="Reviewed committed Git blobs and working bytes; exact commit metadata in every CI selection.",
        local_junit_sha256=digest(local_junit.read_bytes()), run_status_sha256=digest(status_path.read_bytes()),
        ci_summary_sha256=digest(summary_path.read_bytes()), jobs=jobs, issues=[])
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"run_id": run_id, "matrix_verified": True, "full_case_sets_equal_local": True,
                      "jobs": [{"artifact": job["artifact"], "python": job["environment"]["python"],
                                "numpy": job["environment"]["packages"]["numpy"],
                                "scipy": job["environment"]["packages"]["scipy"], "tests": job["junit"]["tests"]}
                               for job in jobs], "issues": []}, indent=2))


def main():
    starting_hashes = {path: digest((ROOT / path).read_bytes()) for path in PATHS[1:3]}
    unchanged = {}
    for path in UNCHANGED:
        data = (ROOT / path).read_bytes()
        assert data == blob(BASELINE, path), path
        unchanged[path] = digest(data)
    old = freeze()
    for surface in (NAMES[1], NAMES[2]):
        before = inspect.signature(old[surface].MultiCausalDatasetGenerator if surface == NAMES[1] else old[surface].generate_multitreatment)
        current = inspect.signature(CURRENT[surface].MultiCausalDatasetGenerator if surface == NAMES[1] else CURRENT[surface].generate_multitreatment)
        assert list(current.parameters)[-1] == "include_marginal_propensity"
        assert current.parameters["include_marginal_propensity"].default is False
        assert list(current.parameters.items())[:-1] == list(before.parameters.items())
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = {"default_references": default_references(old), "numerical_references": numerical_references(),
                  "additive_references": additive_references(), "rejections": rejection_references()}
    assert starting_hashes == {path: digest((ROOT / path).read_bytes()) for path in PATHS[1:3]}, "source changed during review"
    result.update(baseline=BASELINE, reviewed_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  observed_at=datetime.now(timezone.utc).isoformat(), source_sha256=starting_hashes,
                  unchanged_dependency_sha256=unchanged, original_positional_parameters_preserved=True,
                  frozen_full_graph_bindings_verified=True, warnings=[str(w.message) for w in captured], issues=[])
    (ROOT / "audit/block15_review_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"default_configs": len(result["default_references"]), "default_reference_pairs": 2 * len(result["default_references"]),
                      "adaptive_q_cases": len(result["numerical_references"]["adaptive_cases"]),
                      "additive_configs": len(result["additive_references"]), "rejections": len(result["rejections"]),
                      "max_q_error": max(x["max_abs_error"] for x in result["numerical_references"]["adaptive_cases"]),
                      "warnings": result["warnings"], "issues": []}, indent=2))


if __name__ == "__main__":
    if "--boundaries" in sys.argv:
        boundary_main()
    elif "--link-source" in sys.argv:
        link_main(sys.argv[sys.argv.index("--link-source") + 1])
    elif "--review-ci" in sys.argv:
        ci_main(int(sys.argv[sys.argv.index("--review-ci") + 1]))
    else:
        main()
