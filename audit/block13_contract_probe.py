"""Independent synthetic scenario-namespace evidence at the B13 baseline.

Pinned DGP blobs and explicitly rebound imports isolate this probe from working
tree edits. Retained evidence contains schema/role/count/error metadata only.
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
BASELINE = "9f0a63c42308ca886d92dc73d8d8d9611d5b2c31"
N, SEED = 256, 731
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
    "classic": "causalis/scenarios/classic_rct/dgp.py",
    "iv_scenario": "causalis/scenarios/iv/dgp.py",
    "cuped": "causalis/scenarios/cuped/dgp.py",
}
ORACLES = ("m", "m_obs", "tau_link", "g0", "g1", "cate")


def blob(path):
    return subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT)


def frozen_modules():
    modules = {}
    for key, path in PATHS.items():
        source = blob(path).decode("utf-8")
        bindings = {
            "from causalis.dgp.base import": "from _block13_contract_shared import",
            "from causalis.dgp.causaldata.base import CausalDatasetGenerator":
                "from _block13_contract_binary import CausalDatasetGenerator",
            "from .base import CausalDatasetGenerator":
                "from _block13_contract_binary import CausalDatasetGenerator",
            "from .preperiod import": "from _block13_contract_preperiod import",
            "from causalis.dgp.causaldata.preperiod import": "from _block13_contract_preperiod import",
            "from causalis.dgp.causaldata.functional import": "from _block13_contract_binary_wrapper import",
            "from causalis.dgp.causaldata_instrumental import InstrumentalGenerator":
                "from _block13_contract_iv import InstrumentalGenerator",
        }
        for old, new in bindings.items():
            source = source.replace(old, new)
        module = types.ModuleType("_block13_contract_" + key)
        module.__package__ = "causalis.dgp.causaldata" if key == "binary_wrapper" else None
        sys.modules[module.__name__] = module
        exec(compile(source, f"{BASELINE}:{path}", "exec"), module.__dict__)
        modules[key] = module
    assert modules["iv"].InstrumentalGenerator.__bases__[0] is modules["binary"].CausalDatasetGenerator
    assert modules["classic"].generate_classic_rct is modules["binary_wrapper"].generate_classic_rct
    assert modules["classic"].classic_rct_gamma is modules["binary_wrapper"].classic_rct_gamma
    assert modules["iv_scenario"].InstrumentalGenerator is modules["iv"].InstrumentalGenerator
    assert modules["cuped"].make_cuped_tweedie is modules["binary_wrapper"].make_cuped_tweedie
    return modules


def summarize(obj):
    frame = obj if isinstance(obj, pd.DataFrame) else obj.df
    result = {
        "status": "returned", "rows": len(frame), "columns": [str(c) for c in frame.columns],
        "duplicate_columns": [str(c) for c in frame.columns[frame.columns.duplicated()]],
        "dtypes": [str(dtype) for dtype in frame.dtypes],
    }
    if "user_id" in frame.columns and isinstance(frame["user_id"], pd.Series):
        result["user_id_numeric"] = bool(pd.api.types.is_numeric_dtype(frame["user_id"]))
        result["user_id_unique_count"] = int(frame["user_id"].nunique())
    if not isinstance(obj, pd.DataFrame):
        result.update(contract_class=type(obj).__name__, selected_confounders=list(obj.confounders),
                      user_id_role=obj.user_id_name, outcome_role=obj.outcome_name)
        if hasattr(obj, "instruments_names"):
            result["instrument_roles"] = list(obj.instruments_names)
    return result


def record(group, case, call, **settings):
    result = {"group": group, "case": case, "settings": settings}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            result.update(summarize(call()))
        except Exception as error:
            # Strip Pydantic's input-frame repr, retaining diagnostic and roles.
            result.update(status="raised", exception=type(error).__name__,
                          message=str(error).split(" [type=", 1)[0])
    result["warning_count"] = len(caught)
    return result


def main():
    with warnings.catch_warnings(record=True) as load_warnings:
        warnings.simplefilter("always")
        m = frozen_modules()
    classic = m["classic"]
    funcs = (("binary26", classic.generate_classic_rct_26), ("gamma26", classic.classic_rct_gamma_26))
    records = []

    for add_pre in (False, True):
        for ancillary in (False, True):
            for oracle in (False, True):
                for contract in (False, True):
                    kw = dict(n=N, seed=SEED, add_pre=add_pre, pre_name="conversion",
                              add_ancillary=ancillary, include_oracle=oracle, return_causal_data=contract)
                    records.append(record("binary_outcome_rename", str(kw), lambda kw=kw:
                        classic.generate_classic_rct_26(**kw), **kw))

    for family, fn in funcs:
        for add_pre in (False, True):
            for ancillary in (False, True):
                for contract in (False, True):
                    kw = dict(n=N, seed=SEED, add_pre=add_pre, pre_name="user_id",
                              add_ancillary=ancillary, return_causal_data=contract, include_oracle=False)
                    records.append(record("scenario_identifier_collision", family + "_" + str(kw),
                        lambda kw=kw, fn=fn: fn(**kw), family=family, **kw))

    for family, fn in funcs:
        for name in ORACLES:
            for contract in (False, True):
                kw = dict(n=N, seed=SEED, add_pre=True, pre_name=name, add_ancillary=False,
                          include_oracle=False, return_causal_data=contract)
                records.append(record("disabled_oracle_pre_feature", family + "_" + name + "_" + str(contract),
                    lambda kw=kw, fn=fn: fn(**kw), family=family, **kw))

    # Invalid low-level core/feature overlaps already rejected by B12; these
    # controls distinguish shared guards from new late-scenario collisions.
    for family, fn in funcs:
        for name in ("y", "d", "platform_ios", "country_usa", "source_paid"):
            records.append(record("upstream_collision_control", family + "_" + name, lambda name=name, fn=fn:
                fn(n=N, seed=SEED, add_pre=True, pre_name=name, add_ancillary=False,
                   include_oracle=False, return_causal_data=False), family=family, pre_name=name))

    # Both scenarios always add/retain actual ID, but conversion is renamed
    # only by the binary scenario. Gamma conversion-named pre remains valid.
    for family, fn in funcs:
        for name in ("y_pre", "  ", np.str_("literal_pre"), "conversion"):
            for add_pre in (False, True):
                if family == "binary26" and name == "conversion" and add_pre:
                    continue
                kw = dict(n=N, seed=SEED, add_pre=add_pre, pre_name=name, add_ancillary=False,
                          include_oracle=False, return_causal_data=True)
                records.append(record("literal_allowed_control", family + "_" + repr(name) + "_" + str(add_pre),
                    lambda kw=kw, fn=fn: fn(**kw), family=family, pre_name=str(name), add_pre=add_pre))

    # No caller-selectable outcome/treatment/instrument names are exposed by
    # this fixed-schema IV scenario; verify both raw and normalized contracts.
    for oracle in (False, True):
        for contract in (False, True):
            for deterministic in (False, True):
                kw = dict(n=N, seed=SEED, include_oracle=oracle, return_causal_data=contract,
                          deterministic_ids=deterministic)
                records.append(record("iv_fixed_schema_control", str(kw), lambda kw=kw:
                    m["iv_scenario"].generate_offer_iv_26(**kw), **kw))

    for add_pre in (False, True):
        for name in ("y", "user_id", "_latent_A", "safe_pre"):
            kw = dict(n=N, seed=SEED, add_pre=add_pre, pre_name=name,
                      include_oracle=False, return_causal_data=False)
            records.append(record("cuped_existing_guard_control", str(kw), lambda kw=kw:
                m["cuped"].generate_cuped_tweedie_26(**kw), **kw))

    # Underlying helpers share numerical DGP but perform no scenario rename
    # or always-added ID; these names remain valid at that lower layer.
    for name in ("conversion", "user_id", "m"):
        records.append(record("underlying_wrapper_control", name, lambda name=name:
            m["binary_wrapper"].generate_classic_rct(n=N, random_state=SEED,
                add_pre=True, pre_name=name, add_ancillary=False, include_oracle=False,
                return_causal_data=False), pre_name=name))

    contracts = {}
    for path in ("causalis/data_contracts/causaldata.py", "causalis/data_contracts/iv_causal_data.py"):
        actual, frozen = (ROOT / path).read_bytes(), blob(path)
        contracts[path] = {"baseline_sha256": hashlib.sha256(frozen).hexdigest(),
                           "current_sha256": hashlib.sha256(actual).hexdigest(), "unchanged": actual == frozen}
    assert all(item["unchanged"] for item in contracts.values())
    exports = {}
    for path in ("causalis/dgp/__init__.py", "causalis/dgp/causaldata/__init__.py",
                 "causalis/data_contracts/__init__.py", "causalis/scenarios/classic_rct/__init__.py",
                 "causalis/scenarios/iv/__init__.py"):
        source = blob(path)
        exports[path] = {"baseline_sha256": hashlib.sha256(source).hexdigest(),
                         "relevant_lines": [line for line in source.decode("utf-8").splitlines()
                             if any(s in line for s in ("generate_classic_rct_26", "classic_rct_gamma_26",
                                                       "generate_offer_iv_26", "from . import dgp"))]}
    output = {
        "evidence_kind": "frozen_baseline_only", "baseline_sha": BASELINE,
        "observed_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "python_version": sys.version, "synthetic_only": True, "n": N, "seed": SEED,
        "baseline_source_sha256": {p: hashlib.sha256(blob(p)).hexdigest() for p in PATHS.values()},
        "unchanged_imported_contracts": contracts, "pinned_export_inventory": exports,
        "load_warnings": [{"category": item.category.__name__, "message": str(item.message),
                           "filename": item.filename, "lineno": item.lineno} for item in load_warnings],
        "bindings_verified": True, "records_count": len(records), "records": records,
        "limits": ["Baseline observations only; no candidate tests or CI counts",
                   "No individual observations retained", "Fixed-schema IV/CUPED are unchanged controls"],
    }
    path = ROOT / "audit/block13_contract_result.json"
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"baseline_sha": BASELINE, "records": len(records), "result": path.name}))


if __name__ == "__main__":
    main()
