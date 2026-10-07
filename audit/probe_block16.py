"""Reproduce Gaussian outcome errors and verify frozen-baseline compatibility.

Only aggregate errors/counts and source/environment metadata are written.
Baseline library modules execute from exact Git blobs under separate names.
"""

import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import types
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "e8459e1"
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".venv/matplotlib"))
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from scipy.integrate import quad
from scipy.special import expit
from causalis.dgp.causaldata.base import CausalDatasetGenerator
from causalis.dgp.causaldata_instrumental.base import InstrumentalGenerator
from causalis.dgp._gaussian_outcome import _gaussian_outcome_mean


def load(name, data):
    module = types.ModuleType(name)
    sys.modules[name] = module
    exec(compile(data, name, "exec"), module.__dict__)
    return module


def blob(path):
    return subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT)


def main():
    binary_path = "causalis/dgp/causaldata/base.py"
    iv_path = "causalis/dgp/causaldata_instrumental/base.py"
    old_binary = load("_b16_old_binary", blob(binary_path)).CausalDatasetGenerator
    iv_bytes = blob(iv_path).replace(
        b"from causalis.dgp.causaldata.base import CausalDatasetGenerator",
        b"from _b16_old_binary import CausalDatasetGenerator")
    old_iv = load("_b16_old_iv", iv_bytes).InstrumentalGenerator
    assert old_iv.__bases__ == (old_binary,)
    spec = importlib.util.spec_from_file_location("_b16_test_references",
        ROOT / "tests/data/test_binary_iv_marginal_outcomes.py")
    refs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(refs)
    compatibility = []
    for current, baseline in ((CausalDatasetGenerator, old_binary), (InstrumentalGenerator, old_iv)):
        assert str(inspect.signature(current)) == str(inspect.signature(baseline))
        for family in ("continuous", "binary", "poisson", "gamma"):
            for strength in (0.0, 0.5, 10.0):
                for include in (False, True):
                    counters = [0, 0]
                    def callback(index):
                        def function(x):
                            counters[index] += 1
                            return 0.01 * x[:, 0]**2
                        return function
                    kwargs = dict(k=2, beta_y=np.array([0.2, -0.1]),
                        beta_d=np.array([0.3, 0.4]), alpha_y=-0.4, theta=0.7,
                        u_strength_y=strength, u_strength_d=0.3,
                        outcome_type=family, target_d_rate=0.4, include_oracle=include,
                        tau=lambda x: 0.7 + 0.1 * x[:, 0], seed=812)
                    old, new = baseline(g_y=callback(0), **kwargs), current(g_y=callback(1), **kwargs)
                    corrected = strength != 0 and family != "continuous" and include
                    excluded = (["g_d0", "g_d1", "cate"] if current is InstrumentalGenerator
                                else ["g0", "g1", "cate"]) if corrected else []
                    for generation in range(2):
                        left, right = old.generate(31), new.generate(31)
                        pd.testing.assert_frame_equal(left.drop(columns=excluded), right.drop(columns=excluded),
                                                      check_exact=True)
                        assert left.dtypes.equals(right.dtypes)
                        assert list(left.columns) == list(right.columns)
                        assert old.rng.bit_generator.state == new.rng.bit_generator.state
                        assert old.alpha_d == new.alpha_d
                        assert old._generated_confounder_names == new._generated_confounder_names
                        assert old._generated_column_roles == new._generated_column_roles
                        np.testing.assert_array_equal(old.rng.random(10), new.rng.random(10))
                    compatibility.append(dict(generator=current.__name__, family=family, strength=strength,
                        include_oracle=include, frame_rng_pairs=2, outcome_callback_calls=counters,
                        corrected_columns=excluded))
    references = []
    for family in ("binary", "gamma"):
        for strength in (0.1, 0.9, 1.0, 2.0, 8.0, 8.01, 10.0, 50.0, 100.0, 1e6):
            for link in (-25.0, -20.0, -5.0, 0.0, 0.2, 19.5, 25.0):
                expected = refs.reference(link, strength, family)
                actual = float(_gaussian_outcome_mean(link, strength, family))
                absolute = abs(actual - expected)
                relative = absolute / expected if expected else 0.0
                assert absolute <= 2e-11 if family == "binary" else relative < 3e-10, (family, strength, link, actual, expected)
                references.append(dict(family=family, strength=strength, link=link,
                                       abs_error=absolute, rel_error=relative))
    residual = []
    # Shared-U targets remain joint integrals, never products of marginals.
    density = lambda u: np.exp(-0.5*u*u)/np.sqrt(2*np.pi)
    iv = InstrumentalGenerator(k=0, alpha_y=-5, theta=1.0,
        outcome_type="binary", u_strength_y=50.0, u_strength_d=2.0, seed=91)
    x, tau = np.empty((1, 0)), np.ones(1)
    for z in (0.0, 1.0):
        value = float(iv._g_by_z(x, z, tau)[0])
        expected = quad(lambda u: ((1-expit(2*u+iv.first_stage*z))*expit(-5+50*u)
            + expit(2*u+iv.first_stage*z)*expit(-4+50*u))*density(u),
            -12, 12, points=[0,0.08,0.1], epsabs=1e-12, epsrel=1e-12)[0]
        residual.append(dict(target="IV joint g_by_z", z=z, current=value,
                             reference=expected, abs_error=abs(value-expected)))
    for target, actual in (("binary treatment m GH21", old_binary(k=0, alpha_d=-5,
        u_strength_d=50, seed=3).generate(2)["m"].iloc[0]),
        ("Tweedie shared-U GH21", CausalDatasetGenerator(k=0, alpha_zi=-5,
         u_strength_zi=50, alpha_y=0, theta=0, u_strength_y=0,
         outcome_type="tweedie", seed=3).generate(2)["g0"].iloc[0])):
        expected = refs.reference(-5, 50, "binary")
        residual.append(dict(target=target,current=float(actual),reference=expected,
                             abs_error=abs(actual-expected)))
    paths = [binary_path, iv_path, "causalis/dgp/_gaussian_outcome.py",
             "causalis/dgp/base.py", "causalis/dgp/multicausaldata/base.py",
             "tests/data/test_binary_iv_marginal_outcomes.py",
             "tests/data/test_gaussian_outcome_accuracy_policy.py"]
    for path in paths[3:5]:
        assert (ROOT/path).read_bytes() == blob(path)
    result = dict(baseline=subprocess.check_output(["git", "rev-parse", BASELINE],cwd=ROOT,text=True).strip(),
        observed_at=datetime.now(timezone.utc).isoformat(), python=sys.version,
        process_head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        exact_frame_rng_pairs=sum(c["frame_rng_pairs"] for c in compatibility), compatibility=compatibility,
        independent_references=references, remaining_out_of_scope=residual,
        limitations=["Stateful/random outcome callbacks change nonlinear IV call counts; no equivalence claim.",
                     "Binary errors are estimated absolute errors, not rare-tail relative certificates.",
                     "Sensitivity, standalone Sphinx, CI and release not verified by this probe."], issues=[])
    (ROOT/"audit/block16_probe_result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(dict(exact_frame_rng_pairs=result["exact_frame_rng_pairs"],
        reference_cases=len(references), max_binary_abs_error=max(c["abs_error"] for c in references if c["family"]=="binary"),
        max_gamma_rel_error=max(c["rel_error"] for c in references if c["family"]=="gamma"),
        residual=residual),indent=2))


if __name__ == "__main__":
    main()
