"""Aggregate-only independent Gaussian oracle contract and numerical evidence.

Immutable baseline blobs and a captured candidate snapshot execute under
separate module names. Reference propensity integration uses scalar QUADPACK,
SciPy softmax, and independently chosen transition neighborhoods. No generated
individual records, observation vectors, identifiers, or trajectories are saved.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import inspect
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
BASELINE = "71f6a619b04e0ab8fab388fb95b7d0f3d6631b96"
MULTI = "causalis/dgp/multicausaldata/base.py"
BINARY = "causalis/dgp/causaldata/base.py"
IV = "causalis/dgp/causaldata_instrumental/base.py"
FUNCTIONAL = "causalis/dgp/multicausaldata/functional.py"
for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[name] = "1"
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".venv/matplotlib"))
os.environ.setdefault("MPLBACKEND", "Agg")
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from scipy.integrate import quad
from scipy.special import expit, ndtr, softmax


def blob(path):
    return subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(name, source, label, path):
    module = types.ModuleType(name)
    sys.modules[name] = module
    exec(compile(source.decode("utf-8"), label + ":" + path, "exec"), module.__dict__)
    return module


def warning_summary(caught):
    return dict(Counter(item.category.__name__ + ": " + str(item.message) for item in caught))


def normal_density(u):
    return math.exp(-0.5 * u * u) / math.sqrt(2.0 * math.pi)


def reference_propensity(a, b):
    """Independent scalar adaptive integrals, without generator helpers."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    points = {0.0}
    for i in range(len(a)):
        for j in range(i):
            difference = float(b[i] - b[j])
            if difference == 0.0:
                continue
            crossing = float((a[j] - a[i]) / difference)
            width = 1.0 / abs(difference)
            candidates = [crossing]
            for offset in (0.5, 2.0, 8.0, 32.0, 64.0):
                candidates.extend((crossing - offset * width, crossing + offset * width))
            points.update(point for point in candidates if -12.0 < point < 12.0)
    probabilities, estimates = [], []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for arm in range(len(a)):
            value, error = quad(
                lambda u: float(softmax(a + b * u)[arm]) * normal_density(u),
                -12.0, 12.0, points=sorted(points),
                epsabs=2e-13, epsrel=2e-13, limit=4096,
            )
            probabilities.append(value)
            estimates.append(error)
    return np.asarray(probabilities), {
        "backend": "scipy.integrate.quad scalar per arm / scipy.special.softmax",
        "epsabs": 2e-13, "epsrel": 2e-13, "interval": [-12.0, 12.0],
        "points_count": len(points), "estimated_abs_errors": estimates,
        "warnings": warning_summary(caught),
        "mass_error": float(abs(sum(probabilities) - 1.0)),
    }


def reference_outcome(link, strength, family):
    """Independent adaptive natural-scale integral on the Gaussian law."""
    points = {0.0}
    if strength != 0.0:
        if family == "binary":
            center, width = -link / strength, 1.0 / abs(strength)
            for offset in (0.0, 0.5, 2.0, 8.0, 32.0, 64.0):
                points.update((center - offset * width, center + offset * width))
        else:
            points.update(((-20.0 - link) / strength, (20.0 - link) / strength))
    points = sorted(point for point in points if -12.0 < point < 12.0)
    def function(u):
        location = link + strength * u
        mean = float(expit(location)) if family == "binary" else math.exp(min(20.0, max(-20.0, location)))
        return mean * normal_density(u)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value, error = quad(function, -12.0, 12.0, points=points,
                            epsabs=2e-13, epsrel=2e-13, limit=4096)
    return value, {"estimated_abs_error": error, "warnings": warning_summary(caught)}


def gh_propensity(a, b, order):
    nodes, weights = np.polynomial.hermite.hermgauss(order)
    return sum(float(weight / math.sqrt(math.pi)) * softmax(np.asarray(a) + np.asarray(b) * math.sqrt(2.0) * node)
               for node, weight in zip(nodes, weights))


def json_safe(value):
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def main():
    started = datetime.now(timezone.utc).isoformat()
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == BASELINE
    baseline_bytes = {path: blob(path) for path in (MULTI, BINARY, IV, FUNCTIONAL)}
    candidate_bytes = {path: (ROOT / path).read_bytes() for path in (MULTI, FUNCTIONAL)}
    baseline_binary = load("_block15_baseline_binary", baseline_bytes[BINARY], "baseline", BINARY)
    iv_source = baseline_bytes[IV].decode("utf-8").replace(
        "from causalis.dgp.causaldata.base import CausalDatasetGenerator",
        "from _block15_baseline_binary import CausalDatasetGenerator",
    ).encode("utf-8")
    baseline_iv = load("_block15_baseline_iv", iv_source, "baseline", IV)
    baseline_multi = load("_block15_baseline_multi", baseline_bytes[MULTI], "baseline", MULTI)
    candidate_multi = load("_block15_candidate_multi", candidate_bytes[MULTI], "candidate_snapshot", MULTI)
    assert baseline_iv.InstrumentalGenerator.__bases__ == (baseline_binary.CausalDatasetGenerator,)
    assert "include_marginal_propensity" not in inspect.signature(baseline_multi.MultiCausalDatasetGenerator).parameters
    assert list(inspect.signature(candidate_multi.MultiCausalDatasetGenerator).parameters)[-1] == "include_marginal_propensity"
    assert candidate_multi._gaussian_copula is baseline_multi._gaussian_copula
    assert candidate_multi._sigmoid is baseline_multi._sigmoid

    called_paths = set()
    called_snapshot_paths = {"baseline": set(), "candidate_snapshot": set()}
    def profile(frame, event, _arg):
        if event != "call":
            return
        filename = frame.f_code.co_filename
        for label in called_snapshot_paths:
            if filename.startswith(label + ":causalis/"):
                called_snapshot_paths[label].add(filename[len(label) + 1:])
                return
        prefix = str(ROOT) + os.sep
        if filename.startswith(prefix):
            path = filename[len(prefix):]
            if path.startswith("causalis/"):
                called_paths.add(path)
    sys.setprofile(profile)
    integration_events = []
    real_quad_vec = candidate_multi.quad_vec
    def captured_quad_vec(*args, **kwargs):
        probability, error, info = real_quad_vec(*args, **kwargs)
        integration_events.append({
            "estimated_abs_error": float(error), "success": bool(info.success),
            "status": int(info.status), "evaluations": int(info.neval),
            "intervals_count": len(info.intervals), "points_count": len(kwargs.get("points", ())),
        })
        return probability, error, info
    candidate_multi.quad_vec = captured_quad_vec
    cls = candidate_multi.MultiCausalDatasetGenerator

    reference_cases = []
    for arms in (2, 3, 5):
        intercept = np.linspace(-0.8, 0.9, arms)
        pattern = np.linspace(-1.0, 1.0, arms)
        for slope in (0.0, 0.1, 1.0, 2.0, 5.0, 10.0, 50.0, 1000.0):
            reference_cases.append((f"K{arms}_s{slope:g}", intercept, pattern * slope))
    reference_cases.extend((
        ("B07_equal_intercepts", [0.0, 0.0, 0.0], [0.0, 1.0, 1.0]),
        ("narrow_middle_1000", [0.0, 5.0, 0.0], [-1000.0, 0.0, 1000.0]),
        ("narrow_middle_1e6", [0.0, 5.0, 0.0], [-1e6, 0.0, 1e6]),
        ("narrow_middle_shifted", [0.0, 7.0, -200.0], [-1e4, 0.0, 1e4]),
        ("near_tail_crossing", [0.0, -11800.0], [0.0, 1000.0]),
        ("equal_nonzero_slopes", [-2.0, 0.3, 1.0], [50.0, 50.0, 50.0]),
        ("shared_slope_part", [-1.2, 0.4, 1.1, -0.2, 0.6], [5.0, 5.0, -3.0, 1.0, 1.0]),
    ))
    propensity_records = []
    for case, intercept, slope in reference_cases:
        intercept, slope = np.asarray(intercept), np.asarray(slope)
        reference, diagnostics = reference_propensity(intercept, slope)
        count_before = len(integration_events)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            actual = cls._gaussian_marginal_propensity(intercept[None, :], slope, softmax(intercept)[None, :])[0]
        difference = float(np.max(np.abs(actual - reference)))
        assert difference < 1e-10, (case, difference)
        assert diagnostics["warnings"] == {}, (case, diagnostics)
        assert warning_summary(caught) == {}, (case, caught)
        assert np.all((actual >= 0.0) & (actual <= 1.0))
        assert abs(actual.sum() - 1.0) < 1e-14
        propensity_records.append({
            "case": case, "arms": len(intercept), "structural_intercepts": intercept,
            "structural_slopes": slope, "reference_probabilities": reference,
            "candidate_probabilities": actual, "max_abs_error": difference,
            "reference_diagnostics": diagnostics,
            "candidate_quadrature": integration_events[count_before:],
            "candidate_warnings": warning_summary(caught),
        })

    invariance_records = []
    a, b = np.array([-1.2, 0.4, 1.1, -0.2, 0.6]), np.array([5.0, 5.0, -3.0, 1.0, 1.0])
    nominal = cls._gaussian_marginal_propensity(a[None, :], b, softmax(a)[None, :])[0]
    permutation = np.array([3, 1, 4, 0, 2])
    for case, test_a, test_b, expected in (
        ("latent_sign", a, -b, nominal),
        ("intercept_common_shift", a + 100.0, b, nominal),
        ("slope_common_shift", a, b + 100.0, nominal),
        ("arm_permutation", a[permutation], b[permutation], nominal[permutation]),
    ):
        actual = cls._gaussian_marginal_propensity(test_a[None, :], test_b, softmax(test_a)[None, :])[0]
        error = float(np.max(np.abs(actual - expected)))
        assert error < 1e-12, (case, error)
        invariance_records.append({"case": case, "max_abs_error": error})

    gh_failures = []
    for case, a, b in (
        ("steep_shifted_binary", [0.0, 1.0], [0.0, 1000.0]),
        ("narrow_middle", [0.0, 5.0, 0.0], [-1000.0, 0.0, 1000.0]),
    ):
        reference, diagnostics = reference_propensity(a, b)
        approximations = {str(order): gh_propensity(a, b, order) for order in (21, 32, 64, 81, 128)}
        gh_failures.append({"case": case, "reference": reference, "reference_diagnostics": diagnostics,
                            "GH_probabilities": approximations,
                            "GH_max_abs_errors": {order: float(np.max(np.abs(value - reference))) for order, value in approximations.items()},
                            "GH32_vs_GH64_max_abs_difference": float(np.max(np.abs(approximations["32"] - approximations["64"])))})
    assert gh_failures[0]["GH32_vs_GH64_max_abs_difference"] < 1e-14
    assert gh_failures[0]["GH_max_abs_errors"]["32"] > 1e-4

    generation_records = []
    for policy in ("iid", "ensure_all"):
        for supplied in (False, True):
            for calibrated in (False, True):
                config = dict(n_treatments=3, k=0, seed=731, d_names=["control", "A", "B"],
                              alpha_d=[0.0, 0.0, 0.0], u_strength_d=[0.0, 2.0, 2.0],
                              outcome_type="gamma", theta=[0.0, 0.7, -0.4], u_strength_y=1.0,
                              assignment_policy=policy)
                if calibrated:
                    config["target_d_rate"] = [0.2, 0.3, 0.5]
                old, new = baseline_multi.MultiCausalDatasetGenerator(**config), cls(**config, include_marginal_propensity=True)
                latent = np.full(64, 7.0) if supplied else None
                before = len(integration_events)
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    old_df, new_df = old.generate(64, U=latent), new.generate(64, U=latent)
                pd.testing.assert_frame_equal(old_df, new_df[old_df.columns], check_exact=True)
                assert old.rng.bit_generator.state == new.rng.bit_generator.state
                assert np.array_equal(old.rng.random(10), new.rng.random(10))
                actual_a = np.array([math.log(float(new_df["m_" + arm].iloc[0])) for arm in config["d_names"]])
                q, diagnostics = reference_propensity(actual_a, config["u_strength_d"])
                actual_q = np.array([float(new_df["m_marginal_" + arm].mean()) for arm in config["d_names"]])
                assert np.max(np.abs(actual_q - q)) < 1e-10
                generation_records.append({
                    "assignment_policy": policy, "supplied_U": "constant 7 / non-Gaussian reference illustration" if supplied else "drawn independent standard normal",
                    "target_d_rate": config.get("target_d_rate"), "sample_size": 64,
                    "existing_frame_exact_equal": True, "all_rng_state_exact_equal": True, "next10_exact_equal": True,
                    "baseline_columns": list(old_df.columns), "new_columns": list(new_df.columns.difference(old_df.columns, sort=False)),
                    "m_means": [float(new_df["m_" + arm].mean()) for arm in config["d_names"]],
                    "m_obs_means": [float(new_df["m_obs_" + arm].mean()) for arm in config["d_names"]],
                    "m_marginal_means": actual_q, "reference_q": q,
                    "max_m_marginal_abs_error": float(np.max(np.abs(actual_q - q))),
                    "reference_diagnostics": diagnostics, "candidate_quadrature": integration_events[before:],
                    "warnings": warning_summary(caught),
                })

    outcome_records = []
    outcome_cases = [("binary", 0.7, s) for s in (0.0, 1.0, 2.0, 2.01, 5.0, 10.0, 50.0, 1000.0)]
    outcome_cases += [("binary", a, 50.0) for a in (-5.0, 0.0, 5.0)]
    outcome_cases += [("gamma", a, s) for a in (0.0, 19.0, -19.0, 25.0, -25.0) for s in (1.0, 3.0, 10.0, 50.0)]
    for family, link, strength in outcome_cases:
        reference, diagnostics = reference_outcome(link, strength, family)
        record = {"family": family, "structural_link": link, "latent_strength": strength,
                  "reference": reference, "reference_diagnostics": diagnostics, "implementations": {}}
        for label, module in (("multi_baseline", baseline_multi), ("multi_candidate", candidate_multi)):
            generator = module.MultiCausalDatasetGenerator(k=0, u_strength_y=strength)
            actual = float(generator._marginal_natural_scale_from_link(np.array([[link]]), family)[0, 0])
            record["implementations"][label] = {"value": actual, "abs_error": abs(actual - reference),
                                                 "relative_error": abs(actual - reference) / max(abs(reference), np.finfo(float).tiny)}
        assert record["implementations"]["multi_baseline"] == record["implementations"]["multi_candidate"]
        binary = baseline_binary.CausalDatasetGenerator(k=0, alpha_y=link, theta=0.0, u_strength_y=strength,
                                                       outcome_type=family, seed=731)
        binary_df = binary.generate(8, U=np.zeros(8))
        binary_actual = float(binary_df["g0"].mean())
        iv = baseline_iv.InstrumentalGenerator(k=0, alpha_y=link, theta=0.0, u_strength_y=strength,
                                             outcome_type=family, seed=731)
        iv_actual = float(iv._potential_outcome_means(np.zeros((8, 0)), np.zeros(8))[0].mean())
        for label, actual in (("binary_baseline_public_generate_GH21", binary_actual), ("IV_baseline_potential_outcome_helper_GH31", iv_actual)):
            record["implementations"][label] = {"value": actual, "abs_error": abs(actual - reference),
                                                 "relative_error": abs(actual - reference) / max(abs(reference), np.finfo(float).tiny)}
        outcome_records.append(record)

    sys.setprofile(None)
    dependencies = []
    for path in sorted(called_paths):
        current = (ROOT / path).read_bytes()
        original = blob(path)
        assert current == original, path
        dependencies.append({"path": path, "sha256": digest(current), "unchanged_from_baseline": True})
    result = {
        "baseline_sha": BASELINE,
        "process_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_label": "immutable baseline plus precommit candidate snapshots / aggregate-only independent references",
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "pandas")},
                        "native_threads": 1},
        "source_sha256": {"baseline": {path: digest(data) for path, data in baseline_bytes.items()},
                          "candidate_snapshot": {path: digest(data) for path, data in candidate_bytes.items()}},
        "frozen_IV_class_bound_to_frozen_binary": True,
        "candidate_shared_helpers_bound_to_unchanged_actual_modules": True,
        "actual_called_snapshot_sources": {
            label: [{"path": path,
                     "original_source_sha256": digest(baseline_bytes[path] if label == "baseline" else candidate_bytes[path]),
                     "executed_source_sha256": digest(iv_source if label == "baseline" and path == IV else (baseline_bytes[path] if label == "baseline" else candidate_bytes[path])),
                     "import_rebinding_only": label == "baseline" and path == IV}
                    for path in sorted(paths)]
            for label, paths in called_snapshot_paths.items()
        },
        "snapshots_modules": {
            "baseline_binary_class": baseline_binary.CausalDatasetGenerator.__module__,
            "baseline_multi_class": baseline_multi.MultiCausalDatasetGenerator.__module__,
            "candidate_multi_class": candidate_multi.MultiCausalDatasetGenerator.__module__,
            "baseline_IV_class": baseline_iv.InstrumentalGenerator.__module__,
        },
        "actual_called_package_dependencies": dependencies,
        "tail_bounds": {"Gaussian_probability_mass_outside_12": float(2.0 * ndtr(-12.0)),
                        "clipped_exp_natural_mean_omitted_tail_bound": float(2.0 * ndtr(-12.0) * math.exp(20.0))},
        "propensity_reference_cases": propensity_records,
        "invariance_cases": invariance_records,
        "fixed_GH_false_convergence_cases": gh_failures,
        "public_generation_cases": generation_records,
        "existing_outcome_numerical_cases": outcome_records,
        "counts": {"propensity_reference_cases": len(propensity_records), "invariance_cases": len(invariance_records),
                   "GH_false_convergence_cases": len(gh_failures), "public_generation_cases": len(generation_records),
                   "outcome_cases": len(outcome_records), "actual_quad_vec_calls": len(integration_events),
                   "actual_called_unchanged_package_paths": len(dependencies)},
        "max_propensity_abs_error": max(item["max_abs_error"] for item in propensity_records),
        "issues": [],
    }
    output = ROOT / "audit/block15_contract_result.json"
    output.write_text(json.dumps(json_safe(result), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output.relative_to(ROOT)), "counts": result["counts"],
                      "max_propensity_abs_error": result["max_propensity_abs_error"], "issues": result["issues"]}))


if __name__ == "__main__":
    main()
