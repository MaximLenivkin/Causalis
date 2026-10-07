"""Read-only B12 wrapper/conversion probes against an exact frozen baseline.

Only synthetic schema, role, count and error evidence is retained. No generated
individual observations are written. This is independent baseline evidence,
not a candidate or integration test result.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import types
import warnings

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "eb6dfe23f0a97991b6e3d6109febc1b0170e128d"
N = 80
SEED = 731
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".venv/matplotlib"))
os.environ.setdefault("MPLBACKEND", "Agg")
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

PATHS = {
    "shared": "causalis/dgp/base.py",
    "preperiod": "causalis/dgp/causaldata/preperiod.py",
    "binary": "causalis/dgp/causaldata/base.py",
    "binary_wrapper": "causalis/dgp/causaldata/functional.py",
    "iv": "causalis/dgp/causaldata_instrumental/base.py",
    "iv_wrapper": "causalis/dgp/causaldata_instrumental/functional.py",
    "multi": "causalis/dgp/multicausaldata/base.py",
    "multi_wrapper": "causalis/dgp/multicausaldata/functional.py",
}
BINARY_ORACLES = ("m", "m_obs", "tau_link", "g0", "g1", "cate")
IV_ORACLES = (
    "m", "r_obs", "r_z0", "r_z1", "g_z0", "g_z1", "iv_first_stage",
    "iv_reduced_form", "late_x", "late", "tau_link", "g_d0", "g_d1", "cate",
)
ANCILLARY = ("user_id", "age", "cnt_trans", "platform_Android", "platform_iOS", "invited_friend")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def frozen_modules():
    sources = {
        key: subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT, text=True)
        for key, path in PATHS.items()
    }
    modules = {}
    for key in ("shared", "preperiod", "binary", "iv", "binary_wrapper", "iv_wrapper", "multi", "multi_wrapper"):
        source = sources[key]
        source = source.replace("from causalis.dgp.base import", "from _block12_contract_shared import")
        source = source.replace(
            "from causalis.dgp.causaldata.base import CausalDatasetGenerator",
            "from _block12_contract_binary import CausalDatasetGenerator",
        )
        source = source.replace(
            "from .base import CausalDatasetGenerator",
            "from _block12_contract_binary import CausalDatasetGenerator",
        )
        source = source.replace(
            "from .base import InstrumentalGenerator",
            "from _block12_contract_iv import InstrumentalGenerator",
        )
        source = source.replace(
            "from .base import MultiCausalDatasetGenerator",
            "from _block12_contract_multi import MultiCausalDatasetGenerator",
        )
        source = source.replace("from .preperiod import", "from _block12_contract_preperiod import")
        name = "_block12_contract_" + key
        module = types.ModuleType(name)
        if key == "binary_wrapper":
            module.__package__ = "causalis.dgp.causaldata"
        elif key == "iv_wrapper":
            module.__package__ = "causalis.dgp.causaldata_instrumental"
        elif key == "multi_wrapper":
            module.__package__ = "causalis.dgp.multicausaldata"
        sys.modules[name] = module
        exec(compile(source, f"{BASELINE}:{PATHS[key]}", "exec"), module.__dict__)
        modules[key] = module
    return modules, sources


def summarize(obj):
    frame = obj if isinstance(obj, pd.DataFrame) else obj.df
    result = {
        "status": "returned", "rows": len(frame),
        "columns": [None if c is None else str(c) for c in frame.columns],
        "column_label_types": [type(c).__name__ for c in frame.columns],
        "duplicate_columns": [str(c) for c in frame.columns[frame.columns.duplicated()]],
        "dtypes": [str(dtype) for dtype in frame.dtypes],
    }
    if not isinstance(obj, pd.DataFrame):
        result.update(
            contract_class=type(obj).__name__,
            selected_confounders=list(obj.confounders),
            user_id_role=getattr(obj, "user_id_name", getattr(obj, "user_id", None)),
        )
        if hasattr(obj, "instruments_names"):
            result["instrument_roles"] = list(obj.instruments_names)
    for col in ("d", "z", *ANCILLARY):
        if col in frame.columns and isinstance(frame[col], pd.Series):
            if pd.api.types.is_numeric_dtype(frame[col]):
                result.setdefault("nonbinary_value_counts", {})[col] = int((~frame[col].isin([0, 1])).sum())
    return result


def record(group, label, call, **settings):
    result = {"group": group, "case": label, "settings": settings}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            result.update(summarize(call()))
        except Exception as error:
            # Pydantic appends a abbreviated input-frame repr; retain the
            # diagnostic without that repr, so the evidence contains no rows.
            message = str(error).split(" [type=", 1)[0]
            result.update(status="raised", exception=type(error).__name__, message=message)
    result["warning_count"] = len(caught)
    return result


def main():
    modules, sources = frozen_modules()
    binary = modules["binary"].CausalDatasetGenerator
    iv = modules["iv"].InstrumentalGenerator
    multi = modules["multi"].MultiCausalDatasetGenerator
    rct = modules["binary_wrapper"].generate_rct
    iv_data = modules["iv_wrapper"].generate_iv_data
    multi_data = modules["multi_wrapper"].generate_multitreatment
    shared = modules["shared"]
    pre = modules["preperiod"]
    records = []

    # A pre_name argument has an emitted role only when add_pre=True.
    for name in ("y", "d", "m", "x1"):
        for add_pre in (False, True):
            records.append(record("rct_pre_name", f"{name}_pre_{add_pre}", lambda name=name, add_pre=add_pre:
                rct(n=N, random_state=SEED, outcome_type="normal", k=1,
                    add_pre=add_pre, pre_name=name, add_ancillary=False),
                pre_name=name, add_pre=add_pre))
    for name in (None, "", ["unused"]):
        records.append(record("rct_unused_pre_name", repr(name), lambda name=name:
            rct(n=N, random_state=SEED, outcome_type="normal", k=1,
                add_pre=False, pre_name=name, add_ancillary=False), pre_name=repr(name)))
    for name in ANCILLARY:
        records.append(record("rct_pre_ancillary", name, lambda name=name:
            rct(n=N, random_state=SEED, outcome_type="normal", k=1,
                pre_name=name, add_pre=True, add_ancillary=True, deterministic_ids=True), pre_name=name))

    # Enabled ancillary fields must not replace actual confounders or instrument.
    for name in ANCILLARY:
        for family, wrapper in (("binary", rct), ("iv", iv_data)):
            kwargs = dict(n=N, random_state=SEED, confounder_specs=[{"name": name}],
                          include_oracle=False, add_ancillary=True, deterministic_ids=True)
            if family == "binary":
                kwargs.update(outcome_type="normal", add_pre=False)
            records.append(record("ancillary_confounder", family + "_" + name,
                                  lambda kwargs=kwargs, wrapper=wrapper: wrapper(**kwargs), family=family, name=name))
        records.append(record("ancillary_instrument", name, lambda name=name:
            iv_data(n=N, random_state=SEED, k=1, instrument_name=name,
                    include_oracle=False, add_ancillary=True, deterministic_ids=True), name=name))
        records.append(record("ancillary_helper", name, lambda name=name:
            shared._add_ancillary_info(
                pd.DataFrame({"y": np.arange(N, dtype=float), "d": np.arange(N) % 2,
                              name: np.linspace(-1, 1, N)}), N,
                np.random.default_rng(SEED), True, [name]), name=name))

    # Disabled oracle tokens remain actual features and/or legal instrument names.
    for name in BINARY_ORACLES + ("user_id",):
        specs = [{"name": name}]
        records.append(record("binary_conversion", name, lambda specs=specs:
            binary(seed=SEED, include_oracle=False, confounder_specs=specs).to_causal_data(N), name=name))
        records.append(record("rct_conversion", name, lambda specs=specs:
            rct(n=N, random_state=SEED, outcome_type="normal", include_oracle=False,
                confounder_specs=specs, add_pre=False, add_ancillary=False, return_causal_data=True), name=name))
    for name in ("m", "g0"):
        records.append(record("rct_disabled_oracle_pre", name, lambda name=name:
            rct(n=N, random_state=SEED, outcome_type="normal", include_oracle=False,
                confounder_specs=[{"name": name}], beta_y=[0.5], add_pre=True, add_ancillary=False), name=name))
    for name in IV_ORACLES + ("user_id",):
        specs = [{"name": name}]
        records.append(record("iv_conversion", name, lambda specs=specs:
            iv(seed=SEED, include_oracle=False, confounder_specs=specs).to_iv_causal_data(N), name=name))
        records.append(record("iv_wrapper_conversion", name, lambda specs=specs:
            iv_data(n=N, random_state=SEED, include_oracle=False, confounder_specs=specs,
                    return_causal_data=True), name=name))
        records.append(record("iv_disabled_oracle_instrument", name, lambda name=name:
            iv_data(n=N, random_state=SEED, include_oracle=False, k=1, instrument_name=name), name=name))
    records.append(record("iv_user_id_instrument_contract", "instrument_user_id", lambda:
        iv_data(n=N, random_state=SEED, include_oracle=False, k=1, instrument_name="user_id", return_causal_data=True)))
    for oracle in (False, True):
        records.append(record("iv_inherited_binary_conversion", str(oracle), lambda oracle=oracle:
            iv(seed=SEED, include_oracle=oracle, k=1).to_causal_data(N), include_oracle=oracle))

    # Existing multi conversion uses actual confounder_names_, providing a control.
    for name in ("m_0", "g_0", "g_1", "cate_1", "user_id"):
        specs = [{"name": name}]
        records.append(record("multi_conversion_control", name, lambda specs=specs:
            multi(seed=SEED, include_oracle=False, confounder_specs=specs).to_multicausal_data(N), name=name))
        records.append(record("multi_wrapper_control", name, lambda specs=specs:
            multi_data(n=N, random_state=SEED, include_oracle=False, confounder_specs=specs,
                       return_causal_data=True), name=name))

    # Standalone preperiod helper must not overwrite caller columns.
    for name in ("y", "d", "x1", None, "", 42, np.str_("valid_pre"), "   "):
        records.append(record("preperiod_helper", repr(name), lambda name=name:
            pre.add_preperiod_covariate(
                df=pd.DataFrame({"y": np.arange(N, dtype=float), "d": np.arange(N) % 2,
                                 "x1": np.linspace(-1, 1, N)}), y_col="y", d_col="d", pre_name=name,
                base_builder=lambda frame: frame["x1"].to_numpy(), spec=pre.PreCorrSpec(),
                rng=np.random.default_rng(SEED)), pre_name=repr(name)))
    def mutated_pre():
        def builder(frame):
            frame["y_pre"] = np.full(N, -999.0)
            return frame["x1"].to_numpy()
        return pre.add_preperiod_covariate(
            pd.DataFrame({"y": np.arange(N, dtype=float), "d": np.arange(N) % 2,
                          "x1": np.linspace(-1, 1, N)}), "y", "d", "y_pre", builder,
            pre.PreCorrSpec(), np.random.default_rng(SEED))
    records.append(record("preperiod_callback", "new_name_added_in_builder", mutated_pre))

    # Late IV oracle callbacks run after core-frame assembly; mutable settings
    # do not reliably describe that frame during conversion.
    for mutation in ("instrument_name", "include_oracle"):
        def late_conversion(mutation=mutation):
            calls = [0]
            def g_y(X):
                calls[0] += 1
                if calls[0] == 2:
                    if mutation == "instrument_name":
                        gen.instrument_name = "y"
                    else:
                        gen.include_oracle = False
                return np.zeros(np.shape(X)[0])
            gen = iv(seed=SEED, include_oracle=True, k=1, g_y=g_y)
            return gen.to_iv_causal_data(N)
        records.append(record("iv_late_mutation", mutation, late_conversion))

    for helper in ("make_cuped_tweedie", "generate_cuped_binary"):
        for add_pre in (False, True):
            records.append(record("cuped_direct_pre", helper + "_y_" + str(add_pre), lambda helper=helper, add_pre=add_pre:
                getattr(modules["binary_wrapper"], helper)(n=N, seed=SEED, add_pre=add_pre,
                    pre_name="y", include_oracle=False, return_causal_data=False), helper=helper, add_pre=add_pre))
    records.append(record("tweedie_latent_name_collision", "pre_name_latent_A", lambda:
        modules["binary_wrapper"].make_cuped_tweedie(n=N, seed=SEED, pre_name="_latent_A",
            include_oracle=True, return_causal_data=False)))
    records.append(record("ancillary_id_control", "rct_explicitly_added_id", lambda:
        rct(n=N, random_state=SEED, outcome_type="normal", k=1, add_pre=False,
            deterministic_ids=True, return_causal_data=True)))
    records.append(record("ancillary_id_control", "iv_explicitly_added_id", lambda:
        iv_data(n=N, random_state=SEED, k=1, add_ancillary=True, deterministic_ids=True,
                return_causal_data=True)))

    hashes = {}
    for key, path in PATHS.items():
        exact = subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT)
        hashes[path] = hashlib.sha256(exact).hexdigest()
    unchanged_contracts = {}
    for path in ("causalis/data_contracts/causaldata.py", "causalis/data_contracts/iv_causal_data.py",
                 "causalis/data_contracts/multicausaldata.py"):
        exact = subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT)
        unchanged_contracts[path] = {
            "baseline_sha256": hashlib.sha256(exact).hexdigest(),
            "current_sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
            "unchanged": exact == (ROOT / path).read_bytes(),
        }
    assert all(item["unchanged"] for item in unchanged_contracts.values())
    output = {
        "evidence_kind": "frozen_baseline_only", "baseline_sha": BASELINE,
        "observed_head": git("rev-parse", "HEAD"), "python_version": sys.version,
        "synthetic_only": True, "n": N, "seed": SEED,
        "baseline_source_sha256": hashes, "unchanged_imported_contracts": unchanged_contracts,
        "records_count": len(records), "records": records,
        "limits": ["No candidate or integration counts", "No generated individual rows retained",
                   "Data-contract modules imported from workspace and verified byte-identical to baseline"],
    }
    path = ROOT / "audit/block12_contract_result.json"
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"baseline": BASELINE, "records": len(records), "result": str(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
