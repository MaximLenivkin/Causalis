"""Synthetic aggregate-only DiD exact-zero and studentization contract proof.

Baseline and current source snapshots execute in separate module namespaces;
original fixture is always frozen. No package-module overlay is performed.
"""
from __future__ import annotations

from collections import Counter
import copy
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import types
import warnings

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "dbded76ecf8a207aad2094903b8f015fed8ae5d6"
FIXTURE = "tests/scenarios/did/refutation/test_did_post_inference_diagnostics.py"
MODEL = "causalis/scenarios/did/model.py"
POST = "causalis/scenarios/did/refutation/post_inference.py"
CONTRACTS = (
    "causalis/data_contracts/_did_comparison_units.py",
    "causalis/data_contracts/panel_data_did.py",
    "causalis/data_contracts/panel_did_estimate.py",
)
for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[name] = "1"
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".venv/matplotlib"))
os.environ.setdefault("MPLBACKEND", "Agg")
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd


def blob(path, revision=BASELINE):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def scalar_safe(value):
    if isinstance(value, dict):
        return {str(k): scalar_safe(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [scalar_safe(v) for v in value]
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def load(name, source, label, path):
    module = types.ModuleType(name)
    sys.modules[name] = module
    exec(compile(source.decode("utf-8"), label + ":" + path, "exec"), module.__dict__)
    return module


def load_variant(label, model_bytes, post_bytes, fixture_bytes):
    prefix = "_block14_contract_" + label
    model = load(prefix + "_model", model_bytes, label, MODEL)
    post = load(prefix + "_post", post_bytes, label, POST)
    source = fixture_bytes.decode("utf-8").replace(
        "from causalis.scenarios.did import (",
        "from " + prefix + "_model import CallawaySantAnnaDID\nfrom " + prefix + "_post import (",
    ).replace("    CallawaySantAnnaDID,\n", "")
    for plot_name in ("plot_did_influence_concentration", "plot_did_post_inference_event_study"):
        source = source.replace("    " + plot_name + ",\n", "")
    source += "\nfrom causalis.scenarios.did import plot_did_influence_concentration, plot_did_post_inference_event_study\n"
    fixture = load(prefix + "_fixture", source.encode("utf-8"), label, FIXTURE)
    assert fixture.CallawaySantAnnaDID is model.CallawaySantAnnaDID
    assert fixture.run_did_post_inference_diagnostics is post.run_did_post_inference_diagnostics
    return model, post, fixture


def original_fixture_run(label, modules, source_bytes):
    model_module, post, fixture = modules
    called = set()
    def profile(frame, event, _arg):
        if event != "call":
            return
        filename = frame.f_code.co_filename
        if filename.startswith(label + ":"):
            path = filename.split(":", 1)[1]
            if path.startswith("causalis/"):
                called.add(path)
        else:
            prefix = str(ROOT) + os.sep
            if not filename.startswith(prefix):
                return
            path = filename[len(prefix):]
            if path.startswith("causalis/"):
                called.add(path)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sys.setprofile(profile)
        try:
            panel = fixture._panel()
            model = model_module.CallawaySantAnnaDID(
                control_group="never_treated", include_pre_periods=True, base_period="varying",
                min_treated_per_cell=1, min_control_per_cell=1, min_control_ess=1.0,
                max_propensity_clip_share=1.0, max_condition_number=1e12, diagnostic_data=True,
            ).fit(panel)
            estimate = model.estimate(diagnostic_data=True)
            report = fixture._relaxed_report(panel, estimate)
            cells = post.did_post_inference_cell_table(estimate)
            post.did_influence_table(estimate)
            post.did_cluster_influence_table(panel, estimate)
            try:
                fixture.test_post_inference_report_accepts_panel_and_estimate()
            except AssertionError:
                original_test = {"status": "failed", "exception": "AssertionError", "observed_overall_flag": report.loc[0, "flag"]}
            else:
                original_test = {"status": "passed"}
        finally:
            sys.setprofile(None)
    local = estimate.diagnostics["unit_level"]
    proof = []
    for row in cells.to_dict("records"):
        cell = local.loc[local["cell_id"] == row["cell_id"]]
        design = np.column_stack([np.ones(len(cell)), cell["x"].to_numpy(dtype=float)])
        control = cell["is_treated_cohort"].to_numpy() == 0
        delta = cell["delta_y"].to_numpy(dtype=float)
        beta, fitted = model_module._fit_outcome_regression(design, delta, control)
        expected_att = 0.0 if not row["is_post_treatment"] else (2.0 if str(row["cohort"]) == "2020-04" else 3.0)
        score = model._score_matrix[:, int(row["cell_id"])]
        proof.append({
            "cell_id": int(row["cell_id"]), "cohort": str(row["cohort"]), "time": str(row["time"]),
            "is_post_treatment": bool(row["is_post_treatment"]), "n_control": int(control.sum()),
            "n_parameters": int(design.shape[1]), "control_rank": int(np.linalg.matrix_rank(design[control])),
            "control_delta_min": float(delta[control].min()), "control_delta_max": float(delta[control].max()),
            "beta": beta.tolist(), "max_abs_control_residual": float(np.max(np.abs(delta[control] - fitted[control]))),
            "max_abs_influence": float(np.max(np.abs(score))),
            "att": row["att"], "se": row["se"], "t_stat": row["t_stat"],
            "exact_mathematical_att": expected_att, "exact_mathematical_cell_variance": 0.0,
            "absolute_att_error": abs(float(row["att"]) - expected_att),
        })
    actual_hashes = {path: hashlib.sha256(source_bytes[path]).hexdigest() for path in sorted(called)}
    return panel, estimate, {
        "label": label, "original_nodeid": FIXTURE + "::test_post_inference_report_accepts_panel_and_estimate",
        "bindings": {"model_module": model_module.__name__, "fixture_module": fixture.__name__,
                     "post_module": post.__name__, "fixture_model_class_module": fixture.CallawaySantAnnaDID.__module__,
                     "fixture_report_function_module": fixture.run_did_post_inference_diagnostics.__module__,
                     "model_class_identity": fixture.CallawaySantAnnaDID is model_module.CallawaySantAnnaDID,
                     "report_function_identity": fixture.run_did_post_inference_diagnostics is post.run_did_post_inference_diagnostics},
        "original_frozen_test": original_test, "overall_flag": report.loc[0, "flag"],
        "report_rows": report.to_dict("records"), "cell_proof": proof,
        "runtime_called_package_sha256": actual_hashes,
        "runtime_paths": sorted(called), "warnings": dict(Counter(type(x.message).__name__ for x in caught)),
    }


def regression_references(variants):
    records = []
    design = np.array([[1., -.3], [1., .8], [1., .5], [1., .7]])
    control = np.array([False, False, True, True])
    cases = []
    for c in (0.0, 1.0, -2.0, 2.0**-500, 2.0**500):
        cases.append(("exact_constant_full_rank_" + str(c), design, np.full(4, c), True))
    cases.append(("tiny_treated_departures", design, np.array([1. + 1e-12, 1. - 2e-12, 1., 1.]), True))
    cases.append(("representably_near_constant_control", design,
                  np.array([.3, .8, 1., np.nextafter(1., 2.)]), False))
    cases.append(("nonconstant_control", design, np.array([.3, .8, .7, 1.2]), False))
    deficient = np.array([[1., 2.], [1., 3.], [1., 1.], [1., 1.]])
    cases.append(("rank_deficient_constant_control", deficient, np.ones(4), False))
    nonunit = design.copy()
    nonunit[:, 0] = 2.0
    cases.append(("nonunit_intercept_constant_control", nonunit, np.ones(4), False))
    cases.append(("zero_column_private_helper", np.empty((4, 0)), np.ones(4), False))
    for name, x, delta, exact_unique in cases:
        old_beta, old_fit = variants["baseline"][0]._fit_outcome_regression(x, delta, control)
        new_beta, new_fit = variants["current"][0]._fit_outcome_regression(x, delta, control)
        records.append({
            "case": name, "exact_unique_constant_solution": exact_unique,
            "control_rank": int(np.linalg.matrix_rank(x[control])) if x.shape[1] else 0,
            "parameters": int(x.shape[1]),
            "baseline_beta": old_beta.tolist(), "current_beta": new_beta.tolist(),
            "predictions_exact_equal": bool(np.array_equal(old_fit, new_fit)),
            "coefficients_exact_equal": bool(np.array_equal(old_beta, new_beta)),
            "current_control_residual_max": float(np.max(np.abs(delta[control] - new_fit[control]))),
            "current_treated_residual_abs_sum": float(np.sum(np.abs(delta[~control] - new_fit[~control]))),
        })
        if exact_unique:
            assert new_beta[0] == delta[control][0]
            assert np.array_equal(new_beta[1:], np.zeros(len(new_beta) - 1))
        else:
            assert np.array_equal(old_beta, new_beta)
            assert np.array_equal(old_fit, new_fit)
    # Independent direct NumPy evidence for rejected global-centering policy.
    x = deficient
    raw_beta = np.linalg.lstsq(x[control], np.ones(2), rcond=None)[0]
    centered_beta = np.linalg.lstsq(x[control], np.zeros(2), rcond=None)[0]
    centered_beta[0] += 1.0
    centering = {
        "control_rank": 1, "parameters": 2, "minimum_norm_beta": raw_beta.tolist(),
        "centered_intercept_beta": centered_beta.tolist(),
        "treated_prediction_absolute_difference_sum": float(np.sum(np.abs((x @ raw_beta - x @ centered_beta)[~control]))),
    }
    return records, centering


def statistic_references(variants, base_panel, base_estimate):
    pairs = [(0., 0.), (1., 0.), (-1., 0.), (1e-17, 0.), (1., -1.),
             (1., np.nan), (1., np.inf), (np.nan, 1.), (np.inf, 1.),
             (1e-300, 1e-300), (1e-12, 1e-20), (-1e-12, 1e-20), (0., 1e-300), (1., 1e-320)]
    rows = []
    for label, (_, post, fixture) in variants.items():
        with np.errstate(over="ignore", invalid="ignore"):
            values = post._safe_t_stat(pd.Series([p[0] for p in pairs]), pd.Series([p[1] for p in pairs]))
        model_module = variants[label][0]
        rows.append({"label": label, "pairs": [{"att": a, "se": s, "t_stat": t,
                      "normal_p_value": model_module._normal_p_value(a, s)}
            for (a, s), t in zip(pairs, values)]})
    mixtures = []
    for name, att, se in (("zero_se_zero_att", 0., 0.), ("zero_se_nonzero_att", 1., 0.),
                          ("nan_se", 0., np.nan), ("negative_se", 0., -1.),
                          ("infinite_se", 0., np.inf), ("infinite_att", np.inf, 1.),
                          ("overflow_finite_ratio", 1., 1e-320)):
        for label, (_, post, fixture) in variants.items():
            estimate = copy.deepcopy(base_estimate)
            mask = ~estimate.att_gt["is_post_treatment"].astype(bool)
            estimate.att_gt.loc[mask, "att"] = 0.0
            estimate.att_gt.loc[mask, "se"] = 1.0
            first = estimate.att_gt.index[mask][0]
            estimate.att_gt.loc[first, "att"] = att
            estimate.att_gt.loc[first, "se"] = se
            with np.errstate(over="ignore", invalid="ignore"):
                report = fixture._relaxed_report(base_panel, estimate)
            check = report.loc[report["test"] == "fitted_pre_period_placebo"].iloc[0]
            mixtures.append({"label": label, "case": name, "flag": check["flag"], "value": check["value"],
                             "message": check["message"]})
    return rows, mixtures


def nondegenerate_prototype(variants):
    records = []
    for label, (model_module, post, fixture) in variants.items():
        rng = np.random.default_rng(731)
        times = pd.period_range("2020-01", periods=6, freq="M")
        rows = []
        for group_index, cohort in enumerate(("2020-04", "2020-05", None)):
            for j, x in enumerate((-.8, -.1, .55, 1.0)):
                unit = "synthetic_" + str(group_index) + "_" + str(j)
                shocks = rng.normal(0., .3, len(times))
                for t, time in enumerate(times):
                    treated = cohort is not None and time >= pd.Period(cohort, freq="M")
                    rows.append({"unit": unit, "time": time, "y": 10. + 5. * group_index + j + t
                                 + shocks[t] + (2. + group_index if treated else 0.),
                                 "d": int(treated), "x": x + .01 * t, "cluster": unit})
        panel = fixture.PanelDataDID(df=pd.DataFrame(rows), y="y", unit_col="unit", time_col="time",
                                     treated_time="d", covariates=["x"], cluster_col="cluster")
        model = model_module.CallawaySantAnnaDID(control_group="never_treated", include_pre_periods=True,
            base_period="varying", min_treated_per_cell=1, min_control_per_cell=1, min_control_ess=1.,
            max_propensity_clip_share=1., max_condition_number=1e12, diagnostic_data=True).fit(panel)
        estimate = model.estimate(diagnostic_data=True)
        report = fixture._relaxed_report(panel, estimate)
        cells = post.did_post_inference_cell_table(estimate)
        pre = cells.loc[~cells["is_post_treatment"].astype(bool)]
        records.append({"label": label, "evidence_kind": "independent_fixture_prototype_not_public_test",
                        "units": 12, "controls": 4, "clusters": 12, "periods": 6,
                        "overall_flag": report.loc[0, "flag"], "min_pre_se": float(pre["se"].min()),
                        "max_abs_pre_t": float(pre["abs_t_stat"].max()),
                        "all_pre_se_positive_finite": bool((np.isfinite(pre["se"]) & (pre["se"] > 0)).all()),
                        "non_green_rows": report.loc[report["flag"] != "GREEN"].to_dict("records")})
    return records


def unavailable_inference_references(variants, panel, estimate):
    bootstrap = []
    cached = []
    for label, (model, post, fixture) in variants.items():
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            table = model._add_inference(
                pd.DataFrame({"att": [0., 0.]}), np.zeros((6, 2)), estimate_col="att",
                clusters=np.array([0, 0, 1, 1, 2, 2]), alpha=.05,
                bootstrap_replications=16, rng=np.random.default_rng(731), simultaneous=True)
        bootstrap.append({"label": label, "case": "all_zero_scores_simultaneous_bootstrap",
                          "aggregate_rows": table.to_dict("records"),
                          "warning_count": len(caught), "warnings": [str(x.message) for x in caught]})
        for missing in ("att", "se"):
            altered = copy.deepcopy(estimate)
            altered.att_gt["t_stat"] = 0.0
            altered.att_gt["abs_t_stat"] = 0.0
            altered.att_gt.drop(columns=[missing], inplace=True)
            report = fixture._relaxed_report(panel, altered)
            check = report.loc[report["test"] == "fitted_pre_period_placebo"].iloc[0]
            cells = post.did_post_inference_cell_table(altered)
            cached.append({"label": label, "missing_column": missing, "flag": check["flag"],
                           "value": check["value"], "all_t_statistics_nan": bool(cells["t_stat"].isna().all())})
    return bootstrap, cached


def main():
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    frozen = {p: blob(p) for p in (MODEL, POST, FIXTURE, *CONTRACTS)}
    current = {p: (ROOT / p).read_bytes() for p in (MODEL, POST, *CONTRACTS)}
    assert all(current[p] == frozen[p] for p in CONTRACTS)
    variants = {"baseline": load_variant("baseline", frozen[MODEL], frozen[POST], frozen[FIXTURE]),
                "current": load_variant("current", current[MODEL], current[POST], frozen[FIXTURE])}
    base_panel, base_estimate, baseline_run = original_fixture_run("baseline", variants["baseline"], frozen)
    _, _, current_run = original_fixture_run("current", variants["current"], current)
    for cell in current_run["cell_proof"]:
        assert cell["absolute_att_error"] == 0.0
        assert cell["max_abs_influence"] == 0.0
        assert cell["se"] == 0.0
        assert np.isnan(cell["t_stat"])
    regressions, centering = regression_references(variants)
    statistics, mixtures = statistic_references(variants, base_panel, base_estimate)
    bootstrap, cached = unavailable_inference_references(variants, base_panel, base_estimate)
    output = {
        "baseline_sha": BASELINE, "observed_head": head,
        "current_source_sha": head if all(current[p] == blob(p, head) for p in (MODEL, POST)) else None,
        "current_source_kind": "committed" if all(current[p] == blob(p, head) for p in (MODEL, POST)) else "working_tree_snapshot",
        "baseline_source_sha256": {p: hashlib.sha256(b).hexdigest() for p, b in frozen.items()},
        "current_source_sha256": {p: hashlib.sha256(b).hexdigest() for p, b in current.items()},
        "fixture_always_frozen": True, "imports_verified": True, "global_package_overlays": False,
        "python": sys.version, "platform": platform.platform(),
        "dependencies": {p: importlib.metadata.version(p) for p in ("numpy", "pandas", "scipy", "pydantic")},
        "original_fixture": {"baseline": baseline_run, "current": current_run},
        "regression_references": regressions, "rank_deficient_centering_counterexample": centering,
        "safe_t_stat_references": statistics, "mixed_valid_invalid_pre_reports": mixtures,
        "degenerate_bootstrap_references": bootstrap,
        "missing_payload_cached_stat_reports": cached,
        "nondegenerate_fixture_prototype": nondegenerate_prototype(variants),
        "individual_rows_saved": False,
        "limits": ["Synthetic aggregate-only mathematical/numerical proof, not pytest/integration counts",
                   "Current snapshot may be uncommitted; exact hashes identify actually loaded source",
                   "Old fixture still warrants caution after numerical solution is exact"],
    }
    path = ROOT / "audit/block14_contract_result.json"
    path.write_text(json.dumps(scalar_safe(output), indent=2, allow_nan=False) + "\n")
    print(json.dumps({"baseline": BASELINE, "current_source_kind": output["current_source_kind"],
                      "baseline_flag": baseline_run["overall_flag"], "current_flag": current_run["overall_flag"],
                      "regression_references": len(regressions), "statistic_pairs_each": len(statistics[0]["pairs"]),
                      "mixed_reports": len(mixtures), "result": path.name}))


if __name__ == "__main__":
    main()
