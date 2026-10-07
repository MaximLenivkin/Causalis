"""Read-only frozen-baseline binary/IV namespace and container probes."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import types
import warnings

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "4d6b8143db7a93c1a7eba371fcd144878d80c896"
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".venv/matplotlib"))
os.environ.setdefault("MPLBACKEND", "Agg")
sys.path.insert(0, str(ROOT))

import numpy as np


def snapshot(path):
    return subprocess.check_output(
        ["git", "show", f"{BASELINE}:{path}"], cwd=ROOT, text=True
    )


def load_module(name, source, package=None):
    module = types.ModuleType(name)
    module.__package__ = package
    sys.modules[name] = module
    exec(compile(source, name, "exec"), module.__dict__)
    return module


def classes():
    binary = load_module("_block11_contract_binary", snapshot("causalis/dgp/causaldata/base.py"))
    source = snapshot("causalis/dgp/causaldata_instrumental/base.py")
    source = source.replace(
        "from causalis.dgp.causaldata.base import CausalDatasetGenerator",
        "from _block11_contract_binary import CausalDatasetGenerator",
    )
    iv = load_module("_block11_contract_iv", source)
    return binary.CausalDatasetGenerator, iv.InstrumentalGenerator


def main():
    binary, iv = classes()
    containers = []
    for family, klass in (("binary", binary), ("iv", iv)):
        for oracle in (False, True):
            for label, n, sampler in (
                ("nested_list_n30_k0", 30, lambda n, k, seed: [[] for _ in range(n)]),
                ("empty_list_n0_k0", 0, lambda n, k, seed: []),
                ("empty_1d_array_n0_k0", 0, lambda n, k, seed: np.empty(0)),
                ("one_dimensional_n30_k0", 30, lambda n, k, seed: np.arange(n, dtype=float)),
            ):
                record = {"family": family, "include_oracle": oracle, "case": label, "n": n}
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    try:
                        frame = klass(k=0, x_sampler=sampler, seed=731,
                                      include_oracle=oracle).generate(n)
                        record.update(status="returned", columns=list(frame.columns), rows=len(frame))
                    except Exception as error:
                        record.update(status="raised", exception=type(error).__name__, message=str(error))
                record["warnings"] = sorted(set(str(item.message) for item in caught))
                containers.append(record)
    collisions = []
    for family, klass in (("binary", binary), ("iv", iv)):
        oracles = ("m", "m_obs", "tau_link", "g0", "g1", "cate") if family == "binary" else (
            "m", "r_obs", "r_z0", "r_z1", "g_z0", "g_z1", "iv_first_stage",
            "iv_reduced_form", "late_x", "late", "tau_link", "g_d0", "g_d1", "cate",
        )
        settings = [
            ("confounder_outcome", {"confounder_specs": [{"name": "y"}]}),
            ("confounder_treatment", {"confounder_specs": [{"name": "d"}]}),
            ("duplicate_scalar", {"confounder_specs": [{"name": "age"}, {"name": "age"}]}),
            ("expanded_duplicate", {"confounder_specs": [
                {"name": "cat", "dist": "categorical", "categories": [0, 1]}, {"name": "cat_1"}]}),
            ("expanded_stringification", {"confounder_specs": [
                {"name": "cat", "dist": "categorical", "categories": [0, 1, "1"]}]}),
        ]
        settings += [("confounder_oracle_" + name, {"confounder_specs": [{"name": name}]})
                     for name in oracles]
        if family == "iv":
            settings += [
                ("confounder_instrument", {"confounder_specs": [{"name": "z"}]}),
                ("expanded_instrument", {"instrument_name": "cat_1", "confounder_specs": [
                    {"name": "cat", "dist": "categorical", "categories": [0, 1]}]}),
            ]
            settings += [("instrument_oracle_" + name, {"instrument_name": name}) for name in oracles]
        for label, kwargs in settings:
            with warnings.catch_warnings(record=True):
                frame = klass(k=0, seed=731, **kwargs).generate(30)
            record = {"family": family, "case": label, "status": "returned",
                      "columns": list(frame.columns), "rows": len(frame),
                      "nonbinary_treatment_values": int((~frame["d"].isin([0., 1.])).sum())}
            if family == "iv":
                instrument = kwargs.get("instrument_name", "z")
                record["instrument_name"] = instrument
                record["nonbinary_instrument_values"] = int((~frame[instrument].isin([0., 1.])).sum())
            collisions.append(record)

    def frozen_wrapper(name, path, old_import, new_import, package):
        return load_module(name, snapshot(path).replace(old_import, new_import), package)

    binary_wrapper = frozen_wrapper(
        "_block11_contract_binary_wrapper", "causalis/dgp/causaldata/functional.py",
        "from .base import CausalDatasetGenerator", "from _block11_contract_binary import CausalDatasetGenerator",
        "causalis.dgp.causaldata",
    )
    iv_wrapper = frozen_wrapper(
        "_block11_contract_iv_wrapper", "causalis/dgp/causaldata_instrumental/functional.py",
        "from .base import InstrumentalGenerator", "from _block11_contract_iv import InstrumentalGenerator",
        "causalis.dgp.causaldata_instrumental",
    )
    wrapper_residuals = []
    for label, call in (
        ("rct_pre_name_y", lambda: binary_wrapper.generate_rct(
            n=30, random_state=731, outcome_type="normal", pre_name="y",
            add_pre=True, add_ancillary=False, return_causal_data=False)),
        ("rct_pre_name_y_even_disabled", lambda: binary_wrapper.generate_rct(
            n=30, random_state=731, outcome_type="normal", pre_name="y",
            add_pre=False, add_ancillary=False, return_causal_data=False)),
        ("iv_instrument_user_id_ordering", lambda: iv_wrapper.generate_iv_data(
            n=30, random_state=731, k=0, instrument_name="user_id", include_oracle=False,
            add_ancillary=False, return_causal_data=False)),
        ("iv_disabled_oracle_instrument_m_ordering", lambda: iv_wrapper.generate_iv_data(
            n=30, random_state=731, k=0, instrument_name="m", include_oracle=False,
            add_ancillary=False, return_causal_data=False)),
        ("iv_ancillary_age_overwrite", lambda: iv_wrapper.generate_iv_data(
            n=30, random_state=731, confounder_specs=[{"name": "age"}], include_oracle=False,
            add_ancillary=True, deterministic_ids=True, return_causal_data=False)),
    ):
        try:
            frame = call()
            wrapper_residuals.append({"case": label, "status": "returned", "columns": list(frame.columns),
                                      "duplicate_column_names": list(frame.columns[frame.columns.duplicated()]),
                                      "age_dtype": str(frame["age"].dtype) if "age" in frame else None})
        except Exception as error:
            wrapper_residuals.append({"case": label, "status": "raised",
                                      "exception": type(error).__name__, "message": str(error)})
    payload = {"baseline": BASELINE, "mode": "frozen_baseline_only",
               "note": "Pinned binary/IV and functional modules; IV inheritance rebound to frozen binary class in memory.",
               "containers": containers, "namespace_cases": collisions,
               "wrapper_residuals_outside_core_generator_scope": wrapper_residuals,
               "individual_observed_client_records": False}
    (ROOT / "audit/block11_contract_result.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"baseline": BASELINE, "namespace_cases": len(collisions),
                      "containers": [{k: row[k] for k in ("family", "include_oracle", "case", "status")}
                                     for row in containers], "wrapper_residuals": wrapper_residuals}, indent=2))


if __name__ == "__main__":
    main()
