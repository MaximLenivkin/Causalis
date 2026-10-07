"""Independent bounded numerical-policy probes and exact DiD references (B14)."""
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
BASELINE = "dbded76ecf8a207aad2094903b8f015fed8ae5d6"
SOURCE_PATHS = ["causalis/scenarios/did/model.py", "causalis/scenarios/did/refutation/post_inference.py"]
UNMODIFIED_DEPENDENCIES = [
    "causalis/data_contracts/_did_comparison_units.py",
    "causalis/data_contracts/panel_data_did.py",
    "causalis/data_contracts/panel_did_estimate.py",
    "causalis/data_contracts/__init__.py",
    "causalis/scenarios/did/refutation/diagnostics.py",
    "causalis/scenarios/did/__init__.py",
    "causalis/scenarios/did/refutation/__init__.py",
]
MODEL = importlib.import_module("causalis.scenarios.did.model")
POST = importlib.import_module("causalis.scenarios.did.refutation.post_inference")
from causalis.data_contracts import PanelDataDID


def sha(data):
    return hashlib.sha256(data).hexdigest()


def old_bytes(path):
    return subprocess.check_output(["git", "show", BASELINE + ":" + path], cwd=ROOT)


def frozen_module(path, name):
    module = types.ModuleType(name)
    module.__package__ = path[:-3].replace("/", ".").rsplit(".", 1)[0]
    sys.modules[name] = module  # Required by dataclass annotation resolution.
    exec(compile(old_bytes(path), BASELINE + ":" + path, "exec"), module.__dict__)
    return module


def exact(a, b, where="root"):
    if isinstance(a, pd.DataFrame):
        pd.testing.assert_frame_equal(a, b, check_exact=True, obj=where)
    elif isinstance(a, pd.Series):
        pd.testing.assert_series_equal(a, b, check_exact=True, obj=where)
    elif isinstance(a, np.ndarray):
        assert a.dtype == b.dtype and a.shape == b.shape, where
        np.testing.assert_array_equal(a, b, err_msg=where)
    elif isinstance(a, dict):
        assert a.keys() == b.keys(), where
        for key in a:
            if key != "created_at":
                exact(a[key], b[key], where + "." + str(key))
    elif isinstance(a, (tuple, list)):
        assert type(a) is type(b) and len(a) == len(b), where
        for index, (left, right) in enumerate(zip(a, b)):
            exact(left, right, where + "." + str(index))
    elif isinstance(a, float) and np.isnan(a):
        assert isinstance(b, float) and np.isnan(b), where
    else:
        assert a == b, (where, a, b)


@contextmanager
def rng_capture():
    original = np.random.default_rng
    streams = []
    def factory(*args, **kwargs):
        stream = original(*args, **kwargs)
        streams.append(stream)
        return stream
    np.random.default_rng = factory
    try:
        yield streams
    finally:
        np.random.default_rng = original


def rng_end(streams):
    # Read the state before advancing; the extra draws belong to this probe.
    return [(stream.bit_generator.state, stream.random(10)) for stream in streams]


def normal_panel(clustered=True, rank_deficient=False):
    rng = np.random.default_rng(141903)
    n = 48
    periods = pd.period_range("2020-01", periods=6, freq="M")
    x = rng.normal(size=(n, 2))
    noise = rng.normal(scale=0.4, size=(n, len(periods)))
    rows = []
    for i in range(n):
        start = 3 if i < 16 else 4 if i < 32 else 99
        for t, time in enumerate(periods):
            rows.append({"id": i, "time": time, "d": int(t >= start),
                         "y": 4.0 + i * 0.03 + t * (0.7 + 0.1 * x[i, 0])
                         + noise[i, t] + (1.7 + 0.2 * x[i, 1]) * (t >= start),
                         "x1": x[i, 0], "x2": x[i, 0] if rank_deficient else x[i, 1],
                         "cluster": i % 8})
    return PanelDataDID(df=pd.DataFrame(rows), y="y", unit_col="id", time_col="time",
                        treated_time="d", covariates=["x1", "x2"],
                        cluster_col="cluster" if clustered else None)


def saturated_panel():
    periods = pd.period_range("2020-01", periods=6, freq="M")
    units = {"A1": (3, 2.0, 10.0, 0.0, "north"), "A2": (3, 2.0, 11.0, .2, "north"),
             "B1": (4, 3.0, 20.0, 1.0, "south"), "B2": (4, 3.0, 21.0, 1.2, "south"),
             "C1": (99, 0.0, 30.0, .5, "control"), "C2": (99, 0.0, 31.0, .7, "control")}
    rows = [{"unit": unit, "time": period, "y": base + t + tau * (t >= start),
             "d": int(t >= start), "x": x + .01 * t, "cluster": cluster}
            for unit, (start, tau, base, x, cluster) in units.items()
            for t, period in enumerate(periods)]
    return PanelDataDID(df=pd.DataFrame(rows), y="y", unit_col="unit", time_col="time",
                        treated_time="d", covariates=["x"], cluster_col="cluster")


FIT_OPTIONS = dict(control_group="never_treated", include_pre_periods=True,
                   min_treated_per_cell=1, min_control_per_cell=1, min_control_ess=1.0,
                   max_propensity_clip_share=1.0, max_condition_number=1e12)
REPORT_OPTIONS = dict(min_control_ess=1.0, max_propensity_clip_share=1.0,
                      max_abs_weighted_smd=10.0, max_top_unit_influence_share=1.0,
                      max_top_cluster_influence_share=1.0, min_influence_ess=1.0,
                      max_abs_pretrend_t_stat=10.0, max_simple_cell_weight_share=1.0)


def regression_references(old):
    rng = np.random.default_rng(14319)
    x = rng.normal(size=(16, 3))
    control = np.arange(16) % 2 == 0
    changes, unchanged = [], []
    for form in ("intercept", "rank_deficient", "no_intercept", "scaled_intercept", "zero_columns"):
        design = {"intercept": np.column_stack([np.ones(16), x]),
                  "rank_deficient": np.column_stack([np.ones(16), x[:, 0], x[:, 0]]),
                  "no_intercept": x.copy(),
                  "scaled_intercept": np.column_stack([np.full(16, 2.0), x]),
                  "zero_columns": np.empty((16, 0))}[form]
        for constant in (False, True):
            for scale in (1e-220, 1.0, 1e120):
                response = scale * (np.full(16, .75) if constant else rng.normal(size=16))
                snapshots = (design.copy(), response.copy(), control.copy())
                a = old._fit_outcome_regression(design, response, control)
                b = MODEL._fit_outcome_regression(design, response, control)
                exact(snapshots, (design, response, control), "helper nonmutation")
                case = {"form": form, "constant": constant, "scale": scale}
                if form == "intercept" and constant:
                    expected_beta = np.r_[response[control][0], np.zeros(design.shape[1] - 1)]
                    np.testing.assert_array_equal(b[0], expected_beta)
                    np.testing.assert_array_equal(b[1], np.full(len(response), response[control][0]))
                    changes.append(case)
                else:
                    exact(a, b, "unchanged least squares")
                    unchanged.append(case)
    # Zero and subnormal constant response are exact analytical cases, not epsilon cases.
    for value in (0.0, np.nextafter(0.0, 1.0), -np.nextafter(0.0, 1.0), -1e-20):
        design = np.column_stack([np.ones(16), x])
        response = np.full(16, value)
        beta, predicted = MODEL._fit_outcome_regression(design, response, control)
        np.testing.assert_array_equal(beta, np.r_[value, np.zeros(3)])
        np.testing.assert_array_equal(predicted, response)
        changes.append({"form": "intercept", "constant": True, "value": float(value)})
    return {"unchanged": unchanged, "analytical_constant_cases": changes}


def fitted_references(old, old_post):
    configurations = []
    for estimator in ("dr", "aipw", "ipw"):
        for clustered in (False, True):
            for bootstrap in (0, 31):
                configurations.append((estimator, clustered, bootstrap, "varying", True, False))
    configurations.extend([("dr", False, 0, "universal", False, False),
                           ("aipw", True, 31, "universal", False, False),
                           ("dr", True, 0, "universal", True, True),
                           ("ipw", False, 31, "universal", True, True)])
    results = []
    for index, (estimator, clustered, b, base, diagnostics, deficient) in enumerate(configurations):
        panel = normal_panel(clustered=clustered, rank_deficient=deficient)
        panel_before = panel.model_dump(mode="python")
        estimates = []
        rngs = []
        for module, post in ((old, old_post), (MODEL, POST)):
            with rng_capture() as streams:
                model = module.CallawaySantAnnaDID(**FIT_OPTIONS, estimator=estimator,
                                                  base_period=base).fit(panel)
                calls = [model.estimate(bootstrap_replications=b, random_state=1414 + call,
                                        diagnostic_data=diagnostics) for call in range(2)]
                estimates.append([result.model_dump(mode="python") for result in calls])
                # Full report arithmetic is unchanged on positive-SE normal cells.
                reports = [post.run_did_post_inference_diagnostics(panel, result, **REPORT_OPTIONS)
                           for result in calls]
                rngs.append(rng_end(streams))
            if module is old:
                baseline_reports = reports
            else:
                exact(baseline_reports, reports, "normal fitted reports")
        exact(estimates[0], estimates[1], "complete fitted object")
        exact(rngs[0], rngs[1], "bootstrap RNG state and next draws")
        exact(panel_before, panel.model_dump(mode="python"), "panel nonmutation")
        results.append({"id": index, "estimator": estimator, "clustered": clustered,
                        "bootstrap_replications": b, "base_period": base,
                        "diagnostic_data": diagnostics, "rank_deficient": deficient,
                        "estimate_calls": 2})
    return results


def arithmetic_cases():
    cases = [("zero_zero", 0., 0., np.nan), ("tiny_zero", 1e-300, 0., np.nan),
             ("negative_tiny_zero", -1e-300, 0., np.nan), ("nonzero_zero", 2., 0., np.nan),
             ("negative_se", 0., -1., np.nan), ("nan_se", 0., np.nan, np.nan),
             ("inf_se", 0., np.inf, np.nan), ("inf_att", np.inf, 1., np.nan),
             ("nan_att", np.nan, 1., np.nan), ("text_att", "bad", 1., np.nan),
             ("signed_zero_se", 0., -0., np.nan),
             ("subnormal_nonzero", np.nextafter(0., 1.), np.nextafter(0., 1.), 1.),
             ("positive_overflow", 1e308, 1e-308, np.inf),
             ("negative_overflow", -1e308, 1e-308, -np.inf)]
    for scale in (1e-280, 1e-200, 1e-20, 1., 1e20, 1e200, 1e280):
        for sign in (-1, 1):
            cases.append(("scale_%g_%s" % (scale, sign), sign * 3. * scale, scale, sign * 3.))
    index = pd.Index([case[0] for case in cases], name="case")
    att = pd.Series([case[1] for case in cases], index=index)
    se = pd.Series([case[2] for case in cases], index=index)
    att_before, se_before = att.copy(), se.copy()
    actual = POST._safe_t_stat(att, se)
    np.testing.assert_allclose(actual, [case[3] for case in cases], rtol=1e-15, atol=0, equal_nan=True)
    pd.testing.assert_index_equal(actual.index, index)
    exact((att_before, se_before), (att, se), "t-stat input nonmutation")
    p_cases = [(0., 0., 1.), (1e-300, 0., np.nan), (-1e-300, 0., np.nan),
               (0., -1., np.nan), (0., np.nan, np.nan), (0., np.inf, np.nan),
               (np.inf, 1., np.nan), (np.nan, 1., np.nan), (0., 1., 1.)]
    for estimate, standard_error, expected in p_cases:
        actual_p = MODEL._normal_p_value(estimate, standard_error)
        assert np.isnan(actual_p) if np.isnan(expected) else actual_p == expected
    return {"studentization_cases": len(cases), "p_value_cases": len(p_cases)}


def report_edge_cases():
    panel = normal_panel()
    fitted = MODEL.CallawaySantAnnaDID(**FIT_OPTIONS, base_period="varying").fit(panel).estimate()
    pre_mask = ~fitted.att_gt["is_post_treatment"]
    assert pre_mask.sum() >= 2
    cases = [("zero_zero", 0., 0., "YELLOW"), ("tiny_zero", 1e-300, 0., "YELLOW"),
             ("negative_se", 0., -1., "YELLOW"), ("nan_se", 0., np.nan, "YELLOW"),
             ("inf_se", 0., np.inf, "YELLOW"), ("nan_att", np.nan, 1., "YELLOW"),
             ("inf_att", np.inf, 1., "YELLOW"), ("overflow", 1e308, 1e-308, "YELLOW"),
             ("large_finite", 11., 1., "YELLOW"), ("threshold", 10., 1., "GREEN"),
             ("ordinary", 1e-200, 1e-200, "GREEN")]
    results = []
    for label, value, standard_error, expected in cases:
        estimate = fitted.model_copy(deep=True)
        estimate.att_gt.loc[pre_mask, ["att", "se"]] = [0., 1.]
        first = estimate.att_gt.index[pre_mask][0]
        estimate.att_gt.loc[first, ["att", "se"]] = [value, standard_error]
        snapshot = estimate.model_dump(mode="python")
        cells = POST.did_post_inference_cell_table(estimate)
        report = POST.run_did_post_inference_diagnostics(panel, estimate, **REPORT_OPTIONS)
        row = report.loc[report["test"] == "fitted_pre_period_placebo"].iloc[0]
        assert row["flag"] == expected, (label, row.to_dict())
        exact(snapshot, estimate.model_dump(mode="python"), "diagnostic nonmutation")
        if label == "overflow":
            assert np.isposinf(cells.loc[first, "t_stat"])
            assert np.isposinf(row["value"])
        results.append({"case": label, "flag": row["flag"]})
    for missing in ("att", "se"):
        estimate = fitted.model_copy(deep=True)
        estimate.att_gt.drop(columns=[missing], inplace=True)
        row = POST.run_did_post_inference_diagnostics(panel, estimate, **REPORT_OPTIONS)
        row = row.loc[row["test"] == "fitted_pre_period_placebo"].iloc[0]
        assert row["flag"] == "YELLOW"
        results.append({"case": "missing_" + missing, "flag": "YELLOW"})
        estimate.att_gt["t_stat"] = 0.0
        estimate.att_gt["abs_t_stat"] = 0.0
        if missing == "se":
            # Revalidate this case through the actual public result contract.
            estimate = type(estimate)(**estimate.model_dump(mode="python"))
        before = estimate.model_dump(mode="python")
        cells = POST.did_post_inference_cell_table(estimate)
        assert cells.t_stat.isna().all() and cells.abs_t_stat.isna().all()
        row = POST.run_did_post_inference_diagnostics(panel, estimate, **REPORT_OPTIONS)
        row = row.loc[row["test"] == "fitted_pre_period_placebo"].iloc[0]
        assert row["flag"] == "YELLOW"
        exact(before, estimate.model_dump(mode="python"), "cached-stat input nonmutation")
        results.append({"case": "cached_stats_missing_" + missing, "flag": "YELLOW"})
    return results


def saturated_reference(old, old_post):
    panel = saturated_panel()
    summaries = {}
    for label, model, post in (("baseline", old, old_post), ("current", MODEL, POST)):
        estimate = model.CallawaySantAnnaDID(**FIT_OPTIONS, base_period="varying").fit(panel).estimate()
        cells = post.did_post_inference_cell_table(estimate)
        pre = cells.loc[~cells.is_post_treatment, ["att", "se", "t_stat"]]
        report = post.run_did_post_inference_diagnostics(panel, estimate, **REPORT_OPTIONS)
        flag = report.loc[report.test == "fitted_pre_period_placebo", "flag"].iloc[0]
        if label == "current":
            assert (pre.att == 0).all() and (pre.se == 0).all()
            assert pre.t_stat.isna().all() and flag == "YELLOW"
        summaries[label] = {"pre_cells": len(pre), "max_abs_att": float(pre.att.abs().max()),
                            "max_se": float(pre.se.max()), "max_abs_t": float(pre.t_stat.abs().max()),
                            "fitted_pre_flag": flag}
    return summaries


def saturated_bootstrap_delta(old):
    results = []
    for label, module in (("baseline", old), ("current", MODEL)):
        for covariates in (["x"], []):
            args = saturated_panel().model_dump(mode="python")
            args["covariates"] = covariates
            panel = PanelDataDID(**args)
            with warnings.catch_warnings(record=True) as captured, rng_capture() as streams:
                warnings.simplefilter("always")
                estimate = module.CallawaySantAnnaDID(**FIT_OPTIONS, base_period="varying").fit(panel).estimate(
                    bootstrap_replications=31, random_state=1414)
                states = rng_end(streams)
            if label == "current":
                assert (estimate.att_gt.se == 0).all()
                assert estimate.att_gt.simultaneous_critical_value.isna().all()
                assert estimate.att_gt.sim_ci_lower.isna().all() and estimate.att_gt.sim_ci_upper.isna().all()
                assert not captured
            if covariates == [] and label == "baseline":
                assert estimate.att_gt.simultaneous_critical_value.isna().all()
            results.append({"version": label, "covariates": covariates,
                            "all_cell_se_zero": bool((estimate.att_gt.se == 0).all()),
                            "cell_bands_nan": bool(estimate.att_gt.sim_ci_lower.isna().all()),
                            "warnings": [str(w.message) for w in captured],
                            "rng_states": states})
    # Only model fitting changes. Bootstrap sampling and stream consumption do not.
    exact(results[0]["rng_states"], results[2]["rng_states"], "saturated bootstrap RNG x")
    exact(results[1]["rng_states"], results[3]["rng_states"], "saturated bootstrap RNG no x")
    for result in results:
        del result["rng_states"]
    return results


def verify_guard_only_delta(previous_hashes):
    model = (ROOT / SOURCE_PATHS[0]).read_text()
    new_guard = '''        if np.all(se == 0.0):
            # No cell can be studentized; the band is undefined. Avoid taking
            # maxima and quantiles of an entirely NaN bootstrap distribution.
            critical_value = float("nan")
        else:
            denom = np.where(se > 0.0, se, np.nan)
            max_abs_t = np.nanmax(np.abs(shifts / denom[None, :]), axis=1)
            critical_value = float(np.nanquantile(max_abs_t, 1.0 - alpha))
'''
    old_branch = '''        denom = np.where(se > 0.0, se, np.nan)
        max_abs_t = np.nanmax(np.abs(shifts / denom[None, :]), axis=1)
        critical_value = float(np.nanquantile(max_abs_t, 1.0 - alpha))
'''
    assert model.count(new_guard) == 1
    reconstructed_model = model.replace(new_guard, old_branch)
    assert sha(reconstructed_model.encode()) == previous_hashes[SOURCE_PATHS[0]]
    post = (ROOT / SOURCE_PATHS[1]).read_text()
    new_missing_guard = '''    else:
        # Cached statistics cannot establish validity without their inputs.
        out["t_stat"] = np.nan
        out["abs_t_stat"] = np.nan
'''
    assert post.count(new_missing_guard) == 1
    reconstructed_post = post.replace(new_missing_guard, "")
    assert sha(reconstructed_post.encode()) == previous_hashes[SOURCE_PATHS[1]]
    return {"normal_runtime_bytes_unchanged": True,
            "only_additional_runtime_branches": ["all simultaneous SE zero", "missing ATT or SE inputs"],
            "original_full_reference_hashes": previous_hashes,
            "final_source_sha256": {path: sha((ROOT / path).read_bytes()) for path in SOURCE_PATHS}}


def delta_main():
    path = ROOT / "audit/block14_review_probe.json"
    result = json.loads(path.read_text())
    assert "delta_verification" not in result, "preserve initial reference provenance; delta is already captured"
    old = frozen_module(SOURCE_PATHS[0], "block14_delta_old_model")
    hashes = {path: sha((ROOT / path).read_bytes()) for path in SOURCE_PATHS}
    proof = verify_guard_only_delta(result["source_sha256"])
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        delta = {"observed_at": datetime.now(timezone.utc).isoformat(), "proof": proof,
                 "arithmetic": arithmetic_cases(), "mixed_report_cases": report_edge_cases(),
                 "saturated_bootstrap": saturated_bootstrap_delta(old)}
    assert hashes == {path: sha((ROOT / path).read_bytes()) for path in SOURCE_PATHS}
    delta["warnings_outside_expected_baseline_bootstrap"] = [str(w.message) for w in captured]
    assert not captured
    result["delta_verification"] = delta
    result["current_source_sha256"] = hashes
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"delta_guards_verified": proof["only_additional_runtime_branches"],
                      "mixed_report_cases": len(delta["mixed_report_cases"]),
                      "saturated_bootstrap_cases": len(delta["saturated_bootstrap"]),
                      "source_sha256": hashes, "warnings": delta["warnings_outside_expected_baseline_bootstrap"],
                      "issues": []}, indent=2))


def link_main(source):
    assert len(source) == 40 and all(c in "0123456789abcdef" for c in source)
    result_path = ROOT / "audit/block14_review_probe.json"
    result = json.loads(result_path.read_text())
    expected = {**result["current_source_sha256"],
                **result["final_test_review"]["test_module_sha256"],
                **result["unchanged_dependency_sha256"]}
    for path, expected_hash in expected.items():
        committed = subprocess.check_output(["git", "show", source + ":" + path], cwd=ROOT)
        assert sha(committed) == expected_hash == sha((ROOT / path).read_bytes()), path
        if path in UNMODIFIED_DEPENDENCIES:
            assert committed == old_bytes(path), path
    result["committed_source_linkage"] = {
        "source_checkpoint": source,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "four_reviewed_source_test_files_match": True,
        "seven_unchanged_dependencies_match": True,
        "committed_file_sha256": expected,
        "initial_reference_provenance_preserved": True,
        "guard_delta_proof_preserved": True,
        "full_runtime_references_repeated": False,
        "issues": [],
    }
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    with (ROOT / "audit/block14_review_probe.log").open("a") as log:
        log.write("Committed source linkage: " + source + "; four reviewed source/test and seven unchanged dependency bytes verified; original timestamps/HEAD/full-reference hashes preserved; no broad rerun.\n")
    print(json.dumps({"source_checkpoint": source, "verified_files": len(expected), "issues": []}))


def main():
    hashes = {path: sha((ROOT / path).read_bytes()) for path in SOURCE_PATHS}
    dependency_hashes = {}
    for path in UNMODIFIED_DEPENDENCIES:
        data = (ROOT / path).read_bytes()
        assert data == old_bytes(path), path + " is not frozen baseline-compatible"
        dependency_hashes[path] = sha(data)
    old = frozen_module(SOURCE_PATHS[0], "block14_old_model")
    old_post = frozen_module(SOURCE_PATHS[1], "block14_old_post")
    assert old.PanelDataDID is MODEL.PanelDataDID
    assert old.CallawaySantAnnaDIDEstimate is MODEL.CallawaySantAnnaDIDEstimate
    assert old_post.CallawaySantAnnaDIDEstimate is POST.CallawaySantAnnaDIDEstimate
    for before, current in [(old.CallawaySantAnnaDID, MODEL.CallawaySantAnnaDID),
                            (old.CallawaySantAnnaDID.fit, MODEL.CallawaySantAnnaDID.fit),
                            (old.CallawaySantAnnaDID.estimate, MODEL.CallawaySantAnnaDID.estimate),
                            (old_post.did_post_inference_cell_table, POST.did_post_inference_cell_table),
                            (old_post.run_did_post_inference_diagnostics, POST.run_did_post_inference_diagnostics)]:
        assert inspect.signature(before) == inspect.signature(current)
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = {"regression": regression_references(old),
                  "fitted_references": fitted_references(old, old_post),
                  "arithmetic": arithmetic_cases(), "mixed_report_cases": report_edge_cases(),
                  "original_saturated_fixture": saturated_reference(old, old_post)}
    assert hashes == {path: sha((ROOT / path).read_bytes()) for path in SOURCE_PATHS}, "source changed during probe"
    result.update({"baseline": BASELINE,
                   "reviewed_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                   "observed_at": datetime.now(timezone.utc).isoformat(),
                   "source_sha256": hashes, "baseline_sha256": {path: sha(old_bytes(path)) for path in SOURCE_PATHS},
                   "unchanged_dependency_sha256": dependency_hashes,
                   "public_signatures_unchanged": True, "nonmutation_verified": True,
                   "warnings": [str(w.message) for w in captured], "issues": []})
    tests = ["tests/scenarios/did/refutation/test_did_post_inference_diagnostics.py",
             "tests/scenarios/did/refutation/test_did_studentization_contract.py"]
    result["test_module_sha256"] = {path: sha((ROOT / path).read_bytes()) for path in tests if (ROOT / path).exists()}
    (ROOT / "audit/block14_review_probe.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"fitted_configurations": len(result["fitted_references"]),
                      "full_estimate_calls": 2 * len(result["fitted_references"]),
                      "exact_unchanged_regression_cases": len(result["regression"]["unchanged"]),
                      "analytical_constant_cases": len(result["regression"]["analytical_constant_cases"]),
                      "arithmetic": result["arithmetic"], "mixed_report_cases": len(result["mixed_report_cases"]),
                      "warnings": result["warnings"], "issues": result["issues"]}, indent=2))


if __name__ == "__main__":
    if "--delta" in sys.argv:
        delta_main()
    elif "--link-source" in sys.argv:
        link_main(sys.argv[sys.argv.index("--link-source") + 1])
    else:
        main()
