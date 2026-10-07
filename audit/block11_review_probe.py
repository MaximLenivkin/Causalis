"""Independent complete-schema and exact old/new binary/IV references."""
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import types
import warnings

import numpy as np
import pandas as pd

from causalis.dgp.causaldata.base import CausalDatasetGenerator as Binary
from causalis.dgp.causaldata_instrumental.base import InstrumentalGenerator as IV


BASELINE = "4d6b8143db7a93c1a7eba371fcd144878d80c896"
ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ["causalis/dgp/causaldata/base.py", "causalis/dgp/causaldata_instrumental/base.py"]
BINARY_ORACLES = ["m", "m_obs", "tau_link", "g0", "g1", "cate"]
IV_ORACLES = ["m", "r_obs", "r_z0", "r_z1", "g_z0", "g_z1", "iv_first_stage",
              "iv_reduced_form", "late_x", "late", "tau_link", "g_d0", "g_d1", "cate"]


def frozen_classes():
    binary = types.ModuleType("block11_review_frozen_binary")
    sys.modules[binary.__name__] = binary
    text = subprocess.check_output(["git", "show", f"{BASELINE}:{LIBRARY[0]}"], text=True)
    exec(compile(text, f"{BASELINE}:{LIBRARY[0]}", "exec"), binary.__dict__)
    iv = types.ModuleType("block11_review_frozen_iv")
    sys.modules[iv.__name__] = iv
    text = subprocess.check_output(["git", "show", f"{BASELINE}:{LIBRARY[1]}"], text=True)
    original = sys.modules["causalis.dgp.causaldata.base"]
    try:
        sys.modules["causalis.dgp.causaldata.base"] = binary
        exec(compile(text, f"{BASELINE}:{LIBRARY[1]}", "exec"), iv.__dict__)
    finally:
        sys.modules["causalis.dgp.causaldata.base"] = original
    assert issubclass(iv.InstrumentalGenerator, binary.CausalDatasetGenerator)
    return binary.CausalDatasetGenerator, iv.InstrumentalGenerator


def sampling_options(path):
    if path == "default":
        return {"k": 2}, 2
    if path == "custom":
        return {"confounder_specs": [{"name": "β feature"}, {"name": "feature 2"}],
                "x_sampler": lambda n, k, s: np.column_stack((np.linspace(-1., 1., n), np.linspace(.2, .6, n)))}, 2
    specs = [{"name": "feature", "dist": "normal"},
             {"name": "segment", "dist": "categorical", "categories": ["base", "mid", "top"], "probs": [2, 5, 3]}]
    return {"confounder_specs": specs, "use_copula": path == "copula",
            "copula_corr": np.array([[1., -.35], [-.35, 1.]])}, 3


def valid_frames(old_binary, old_iv):
    entries = []
    for old_class, new_class, families in [
        (old_binary, Binary, ["continuous", "binary", "poisson", "gamma", "tweedie_gamma", "tweedie_lognormal"]),
        (old_iv, IV, ["continuous", "binary", "poisson", "gamma"]),
    ]:
        for family in families:
            for path in ["default", "independent", "copula", "custom"]:
                for oracle in [False, True]:
                    options, width = sampling_options(path)
                    outcome = "tweedie" if family.startswith("tweedie") else family
                    kwargs = dict(seed=731, outcome_type=outcome, include_oracle=oracle,
                                  beta_y=np.linspace(.03, .09, width), beta_d=np.linspace(.02, .04, width),
                                  alpha_y=.1, theta=.25, sigma_y=.6, target_d_rate=.4,
                                  u_strength_y=.2, u_strength_d=.3, **options)
                    if family.startswith("tweedie"):
                        kwargs["pos_dist"] = family.split("_")[1]
                        kwargs["u_strength_zi"] = .1
                    if path != "default":
                        kwargs.update(g_y=lambda x: .03 * np.tanh(x[:, 0]),
                                      g_d=lambda x: .02 * np.tanh(x[:, -1]),
                                      tau=lambda x: .25 + .01 * np.tanh(x[:, 0]))
                    if new_class is IV:
                        kwargs.update(instrument_name="Encouragement β", beta_z=np.linspace(.01, .03, width),
                                      g_z=lambda x: .02 * np.tanh(x[:, 0]))
                    old, new = old_class(**kwargs), new_class(**kwargs)
                    for generation in range(2):
                        expected, actual = old.generate(30), new.generate(30)
                        pd.testing.assert_frame_equal(expected, actual, check_exact=True)
                        assert actual.columns.is_unique
                        assert actual["d"].isin([0., 1.]).all()
                        if new_class is IV:
                            assert actual["Encouragement β"].isin([0., 1.]).all()
                        np.testing.assert_array_equal(old.rng.random(10), new.rng.random(10))
                    entries.append({"family": family, "class": new_class.__name__, "sampling": path,
                                    "oracle": oracle, "generations": 2, "exact_frame_dtypes_schema_next10rng": True})
    return entries


def family_names(old_binary, old_iv):
    entries = []
    cases = [
        (old_binary, Binary, {"confounder_specs": [{"name": "r_obs"}, {"name": "g_d0"}]}),
        (old_binary, Binary, {"include_oracle": False, "confounder_specs": [{"name": "m"}, {"name": "cate"}]}),
        (old_iv, IV, {"confounder_specs": [{"name": "m_obs"}, {"name": "g0"}, {"name": "g1"}]}),
        (old_iv, IV, {"instrument_name": "m_obs", "confounder_specs": [{"name": "g0"}, {"name": "g1"}]}),
        (old_iv, IV, {"include_oracle": False, "instrument_name": "m", "confounder_specs": [{"name": "late"}, {"name": "g_z0"}]}),
        (old_iv, IV, {"instrument_name": " ", "confounder_specs": [{"name": "\t"}]}),
    ]
    for old_class, new_class, supplied in cases:
        kwargs = dict(seed=731, **supplied)
        old, new = old_class(**kwargs), new_class(**kwargs)
        for _ in range(2):
            pd.testing.assert_frame_equal(old.generate(30), new.generate(30), check_exact=True)
            np.testing.assert_array_equal(old.rng.random(10), new.rng.random(10))
        entries.append({"class": new_class.__name__, "instrument_name": supplied.get("instrument_name", "z"),
                        "oracle": supplied.get("include_oracle", True),
                        "confounders": [s["name"] for s in supplied["confounder_specs"]],
                        "exact_frame_next10rng": True})
    return entries


def rejected_schemas(old_binary, old_iv):
    cases = []
    for old_class, new_class, oracles in [(old_binary, Binary, BINARY_ORACLES), (old_iv, IV, IV_ORACLES)]:
        for name in ["y", "d"] + (["z"] if new_class is IV else []) + oracles:
            cases.append((old_class, new_class, {"confounder_specs": [{"name": name, "dist": "normal"}]}, name))
        cases.append((old_class, new_class, {"confounder_specs": [{"name": "same"}, {"name": "same"}]}, "same"))
    for name in IV_ORACLES:
        cases.append((old_iv, IV, {"instrument_name": name, "k": 0}, name))
    cases.extend([
        (old_binary, Binary, {"confounder_specs": [{"name": "m", "dist": "categorical", "categories": ["base", "obs"]}]}, "m_obs"),
        (old_iv, IV, {"confounder_specs": [{"name": "r", "dist": "categorical", "categories": ["base", "z0"]}]}, "r_z0"),
        (old_iv, IV, {"instrument_name": "segment_top", "confounder_specs": [{"name": "segment", "dist": "categorical", "categories": ["base", "top"]}]}, "segment_top"),
        (old_iv, IV, {"instrument_name": "x1", "k": 1}, "x1"),
    ])
    entries = []
    for old_class, new_class, supplied, name in cases:
        old = old_class(seed=731, **supplied).generate(30)
        try:
            new_class(seed=731, **supplied).generate(30)
        except ValueError as exc:
            assert name in str(exc)
            entries.append({"class": new_class.__name__, "column": name, "baseline_returned_raw_frame": True,
                            "new_status": "ValueError", "message": str(exc)})
        else:
            raise AssertionError(f"Did not reject {new_class.__name__}: {name}")
    return entries


def mutation_checks():
    entries = []
    for cls, field in [(Binary, "g_y"), (IV, "g_z")]:
        holder = {}
        def callback(x):
            holder["gen"].include_oracle = True
            return np.zeros(len(x))
        gen = cls(seed=731, confounder_specs=[{"name": "m"}], include_oracle=False, **{field: callback})
        holder["gen"] = gen
        try:
            gen.generate(30)
        except ValueError as exc:
            assert "m" in str(exc)
            entries.append({"class": cls.__name__, "mutation": "enable_oracles_in_" + field,
                            "status": "ValueError", "message": str(exc)})
        else:
            raise AssertionError("Callback re-enabled a colliding oracle")
    holder = {}
    def change_instrument(x):
        holder["gen"].instrument_name = "y"
        return np.zeros(len(x))
    gen = IV(seed=731, k=1, g_z=change_instrument, include_oracle=False)
    holder["gen"] = gen
    try:
        gen.generate(30)
    except ValueError as exc:
        assert "y" in str(exc)
        entries.append({"class": "IV", "mutation": "instrument_y_in_g_z", "status": "ValueError", "message": str(exc)})
    else:
        raise AssertionError("Callback instrument overwrote outcome")
    for invalid in ["y", "d", "m", "", None, ["unhashable"]]:
        gen = IV(seed=731, k=0)
        gen.generate(30)
        gen.instrument_name = invalid
        try:
            gen.generate(30)
        except ValueError as exc:
            entries.append({"class": "IV", "mutation": repr(invalid), "status": "ValueError", "message": str(exc)})
        else:
            raise AssertionError("Mutated instrument passed fixed schema checks")
    for cls in [Binary, IV]:
        gen = cls(seed=731, confounder_specs=[{"name": "m"}], include_oracle=False)
        gen.generate(30)
        gen.include_oracle = True
        try:
            gen.generate(30)
        except ValueError as exc:
            entries.append({"class": cls.__name__, "mutation": "enable_oracles_between_calls", "status": "ValueError", "message": str(exc)})
        else:
            raise AssertionError("Enabled oracle replaced a sampled name")
    return entries


def zero_feature_containers(old_binary, old_iv):
    cases = [(Binary, old_binary, n, container, oracle)
             for n, container in [(30, "rows"), (0, "rows"), (0, "flat"), (30, "flat")]
             for oracle in [False, True]]
    cases += [(IV, old_iv, n, "rows", False) for n in [0, 30]]
    cases += [(IV, old_iv, n, "flat", oracle) for n in [0, 30] for oracle in [False, True]]
    entries = []
    for cls, old_cls, n, container, oracle in cases:
        sampler = lambda count, k, seed: ([[] for _ in range(count)] if container == "rows" else np.arange(count, dtype=float))
        options = dict(k=0, seed=731, x_sampler=sampler, include_oracle=oracle)
        if cls is IV:
            options["target_z_rate"] = None
        old, new = old_cls(**options), cls(**options)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            for _ in range(2):
                pd.testing.assert_frame_equal(old.generate(n), new.generate(n), check_exact=True)
                np.testing.assert_array_equal(old.rng.random(10), new.rng.random(10))
        entries.append({"class": cls.__name__, "n": n, "container": container, "oracle": oracle,
                        "generations": 2, "exact_frame_schema_next10rng": True})
    return entries


def wrapper_residuals():
    from causalis.dgp.causaldata_instrumental.functional import generate_iv_data
    frame = generate_iv_data(n=30, random_state=731, k=1, instrument_name="age",
                             include_oracle=False, add_ancillary=True, deterministic_ids=True)
    return [{"trigger": "generate_iv_data instrument_name='age', add_ancillary=True",
             "n": 30, "seed": 731, "include_oracle": False,
             "generated_instrument_binary": bool(frame["age"].isin([0., 1.]).all()),
             "nonbinary_instrument_count": int((~frame["age"].isin([0., 1.])).sum()),
             "scope": "separate optional ancillary wrapper overwrite; core IV generator name is valid"}]


def main():
    old_binary, old_iv = frozen_classes()
    result = {"baseline_sha": BASELINE,
              "reviewed_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "library_sha256": {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in LIBRARY},
              "current_test_module_sha256": hashlib.sha256((ROOT/"tests/data/test_binary_iv_namespace_contract.py").read_bytes()).hexdigest(),
              "valid_configurations": valid_frames(old_binary, old_iv),
              "family_specific_available_names": family_names(old_binary, old_iv),
              "rejected_schemas": rejected_schemas(old_binary, old_iv),
              "mutation_checks": mutation_checks(),
              "zero_confounder_containers": zero_feature_containers(old_binary, old_iv),
              "wrapper_residuals": wrapper_residuals(), "issues": []}
    Path(__file__).with_name("block11_review_probe.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"valid_configs": len(result["valid_configurations"]),
                      "family_name_configs": len(result["family_specific_available_names"]),
                      "rejected_schemas": len(result["rejected_schemas"]),
                      "mutation_checks": len(result["mutation_checks"]), "issues": []}, indent=2))


if __name__ == "__main__":
    main()
