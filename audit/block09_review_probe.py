"""Independent, compact namespace probes; does not store generated rows."""
import json
import hashlib
import subprocess
import sys
import types
from pathlib import Path

import numpy as np

from causalis.dgp.multicausaldata.base import MultiCausalDatasetGenerator as Generator
from causalis.dgp.base import _gaussian_copula


BASELINE_SHA = "74145665127f8fa5a0bf038d769697ab880854b8"


def run(generator=Generator):
    cases = {
        "outcome_treatment": {"d_names": ["y", "arm"]},
        "duplicate_treatment": {"d_names": ["arm", "arm"]},
        "default_confounder_treatment": {"k": 1, "d_names": ["x1", "arm"]},
        "explicit_confounder_treatment": {"confounder_specs": [{"name": "d_0", "dist": "normal"}]},
        "explicit_confounder_outcome": {"confounder_specs": [{"name": "y", "dist": "normal"}]},
        "confounder_oracle": {"confounder_specs": [{"name": "g_d_0", "dist": "normal"}]},
        "duplicate_confounder": {"confounder_specs": [{"name": "z"}, {"name": "z"}]},
        "treatment_oracle": {"d_names": ["a", "m_a"]},
        "oracle_oracle": {"d_names": ["a", "obs_a"]},
        "categorical_treatment": {"confounder_specs": [{"name": "d", "dist": "categorical", "categories": [-1, 0]}]},
        "categorical_confounder": {"confounder_specs": [{"name": "c", "dist": "categorical", "categories": [0, 1]}, {"name": "c_1"}]},
        "categorical_oracle": {"confounder_specs": [{"name": "g_d", "dist": "categorical", "categories": [-1, 0]}]},
        "categorical_duplicate_formatted": {"confounder_specs": [{"name": "c", "dist": "categorical", "categories": ["base", 1, "1"]}]},
        "single_level_confounder": {"confounder_specs": [{"name": "c", "dist": "categorical", "categories": [0]}, {"name": "c__onlylevel"}]},
        "fallback_after_expansion": {"confounder_specs": [{"name": "c", "dist": "categorical", "categories": [0, 1, 2]}, {}, {"name": "x3"}]},
        "copula_scalar_confounder": {"use_copula": True, "confounder_specs": [{"name": "y", "dist": "normal"}]},
        "copula_categorical_after_numeric": {"use_copula": True, "confounder_specs": [{"name": "z", "dist": "normal"}, {"name": "g_d", "dist": "categorical", "categories": [-1, 0]}]},
        "custom_sampler_names": {"confounder_specs": [{"name": "y"}], "x_sampler": lambda n, k, s: np.arange(n*k).reshape(n, k)},
        "disabled_oracle_namespace_allowed": {"include_oracle": False, "d_names": ["a", "obs_a"]},
        "unused_control_cate_allowed": {"d_names": ["a", "cate_a"]},
        "custom_sampler_no_categorical_expansion": {"confounder_specs": [{"name": "safe", "dist": "categorical", "categories": [0, 1]}], "x_sampler": lambda n, k, s: np.arange(n*k).reshape(n, k)},
        "preexisting_copula_categorical_first": {"use_copula": True, "confounder_specs": [{"name": "safe", "dist": "categorical", "categories": [0, 1]}]},
    }
    result = {
        "baseline_sha": BASELINE_SHA,
        "source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "cases": {},
    }
    for label, settings in cases.items():
        try:
            gen = generator(**dict({"n_treatments": 2, "k": 0, "seed": 1}, **settings))
            frame = gen.generate(30)
            cols = list(frame.columns)
            result["cases"][label] = {
                "status": "returned_frame", "columns": cols,
                "expanded_confounder_names": gen.confounder_names_,
                "all_treatment_columns_present": all(name in cols for name in gen.d_names),
                "treatment_rows_one_hot": bool(frame[gen.d_names].sum(axis=1).eq(1).all()),
                "outcome_only_binary": bool(frame["y"].isin([0., 1.]).all()),
            }
        except Exception as error:
            result["cases"][label] = {"status": "exception", "type": type(error).__name__, "message": str(error)}
    return result


def independent_checks(baseline_generator):
    valid = {
        "ordinary": {},
        "unicode_punctuation_names": {"d_names": ["контроль?", "тест _1"]},
        "tuple_names": {"d_names": ("a", "b")},
        "numpy_string_names": {"d_names": np.array(["a", "b"])},
        "whitespace_nonempty_names": {"d_names": [" ", "\t"]},
        "disabled_oracle_namespace": {"include_oracle": False, "d_names": ["a", "obs_a"], "confounder_specs": [{"name": "m_a"}]},
        "unused_control_cate": {"d_names": ["a", "cate_a"]},
        "categorical_expanded_with_fallback": {"confounder_specs": [{"name": "c", "dist": "categorical", "categories": [0, 1, 2]}, {}]},
        "categorical_single_level": {"confounder_specs": [{"name": "c", "dist": "categorical", "categories": [0]}]},
        "copula_noncategorical": {"use_copula": True, "confounder_specs": [{"name": "c"}, {}]},
        "sampler_categorical_no_expansion": {"confounder_specs": [{"name": "safe", "dist": "categorical", "categories": [0, 1]}], "x_sampler": lambda n, k, s: np.arange(n*k).reshape(n, k)},
    }
    checks = {"valid_reference": {}, "mutable_configuration": {}, "invalid_name_types": {}}
    for label, settings in valid.items():
        kwargs = dict({"n_treatments": 2, "k": 0, "seed": 5}, **settings)
        old = baseline_generator(**kwargs)
        current = Generator(**kwargs)
        try:
            for iteration in range(2):
                old_frame, current_frame = old.generate(30), current.generate(30)
                assert old_frame.equals(current_frame)
                assert list(old_frame.columns) == list(current_frame.columns)
                np.testing.assert_array_equal(old.rng.random(10), current.rng.random(10))
            checks["valid_reference"][label] = "exact frame, schema and next10RNG after each of two generates"
        except Exception as error:
            checks["valid_reference"][label] = f"{type(error).__name__}: {error}"
    for label in ["enable_oracles", "rename_treatment", "change_n_treatments", "append_treatment_name", "change_confounder_name"]:
        gen = Generator(n_treatments=2, d_names=["a", "obs_a"], k=0, include_oracle=False, seed=5)
        gen.generate(30)
        if label == "enable_oracles":
            gen.include_oracle = True
        elif label == "rename_treatment":
            gen.d_names[0] = "y"
        elif label == "change_n_treatments":
            gen.n_treatments = 3
        elif label == "append_treatment_name":
            gen.d_names.append("arm")
        else:
            gen.confounder_specs = [{"name": "y"}]
        try:
            gen.generate(30)
            checks["mutable_configuration"][label] = "unexpected success"
        except Exception as error:
            checks["mutable_configuration"][label] = {"type": type(error).__name__, "message": str(error)}
    for label, settings in {
        "arm_empty": {"d_names": ["a", ""]},
        "arm_none": {"d_names": ["a", None]},
        "arm_numeric": {"d_names": ["a", 1]},
        "arm_list": {"d_names": ["a", ["b"]]},
        "arm_dict": {"d_names": ["a", {"b": 1}]},
        "arm_scalar_string": {"d_names": "ab"},
        "confounder_list": {"confounder_specs": [{"name": ["z"]}]},
        "sampler_confounder_empty": {"confounder_specs": [{"name": ""}], "x_sampler": lambda n, k, s: np.ones((n, k))},
        "sampler_confounder_none": {"confounder_specs": [{"name": None}], "x_sampler": lambda n, k, s: np.ones((n, k))},
    }.items():
        try:
            Generator(**dict({"n_treatments": 2, "k": 0}, **settings)).generate(30)
            checks["invalid_name_types"][label] = "unexpected success"
        except Exception as error:
            checks["invalid_name_types"][label] = {"type": type(error).__name__, "message": str(error)}
    checks["source_sha"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    checks["baseline_sha"] = BASELINE_SHA
    checks["review_diff_sha256"] = hashlib.sha256(subprocess.check_output(["git", "diff", "HEAD", "--", "causalis/dgp/multicausaldata/base.py", "causalis/dgp/multicausaldata/functional.py"])).hexdigest()
    x, names = _gaussian_copula(np.random.default_rng(731), 1000,
                               [{"name": "z", "dist": "normal"},
                                {"name": "c", "dist": "categorical", "categories": [0, 1]}])
    checks["shared_helper_residual"] = {
        "location": "causalis/dgp/base.py:307", "n": 1000, "seed": 731,
        "latent_correlation": "identity", "names": names,
        "categorical_equals_previous_normal_positive_for_every_row": bool(np.array_equal(x[:, 1], (x[:, 0] > 0).astype(float))),
    }
    return checks


if __name__ == "__main__":
    baseline = types.ModuleType("block09_review_baseline_module")
    sys.modules[baseline.__name__] = baseline
    source = subprocess.check_output(["git", "show", f"{BASELINE_SHA}:causalis/dgp/multicausaldata/base.py"], text=True)
    exec(compile(source, f"{BASELINE_SHA}:causalis/dgp/multicausaldata/base.py", "exec"), baseline.__dict__)
    for label, generator in [("baseline", baseline.MultiCausalDatasetGenerator), ("patched", Generator)]:
        result = run(generator)
        path = Path(__file__).with_name(f"block09_review_{label}.json")
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({"version": label, "source_sha": result["source_sha"], "cases": {name: {key: value for key, value in case.items() if key not in {"columns", "expanded_confounder_names"}} for name, case in result["cases"].items()}}, indent=2))
    checks = independent_checks(baseline.MultiCausalDatasetGenerator)
    Path(__file__).with_name("block09_review_checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
    print(json.dumps(checks, indent=2))
