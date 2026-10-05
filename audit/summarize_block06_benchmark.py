"""Validate identical inputs/scores and summarize sequential worker evidence."""
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
before = json.loads((ROOT / "block06_benchmark_before.json").read_text())
after = json.loads((ROOT / "block06_benchmark_after.json").read_text())
assert before["environment"] == after["environment"]
assert before["seed"] == after["seed"] == 731
assert before["native_threads"] == after["native_threads"] == 1
assert "baseline" in before["library_file"]
assert "baseline" not in after["library_file"]
summary = dict(baseline="bf2ea87534e4eaf82266cb61d905b7e876cc2e1d",
               current="d292b3c2f83ec94ef75652a17f3e34436c71902f",
               environment=after["environment"], contracts=[], extraction=[], binary=[], kde=[],
               limitations=["Sequential fresh processes, one native thread, desktop noise, 5 timing repetitions (KDE/fit 3)",
                            "Tracemalloc is peak traced allocations during the operation, not process RSS",
                            "Constructor/extraction/fit are separate; no global library speed rating",
                            "Owned extraction is an audit-only candidate without production snapshot/caching contract"])


def comparison(first, second):
    return dict(before_seconds=first["median_seconds"], after_seconds=second["median_seconds"],
                speedup=first["median_seconds"] / second["median_seconds"],
                before_peak_traced_MiB=first.get("peak_traced_MiB"),
                after_peak_traced_MiB=second.get("peak_traced_MiB"))


for first, second in zip(before["contracts"], after["contracts"], strict=True):
    for key in ["n", "p", "kind", "snapshot"]:
        assert first[key] == second[key], key
    summary["contracts"].append(dict(n=first["n"], p=first["p"], kind=first["kind"],
                                      **comparison(first["timing"], second["timing"])))
for first, second in zip(before["extraction"], after["extraction"], strict=True):
    for key in ["n", "p", "arrays", "binary_outcome"]:
        assert first[key] == second[key], key
    summary["extraction"].append(dict(n=first["n"], p=first["p"],
                                     **comparison(first["current"], second["current"]),
                                     owned_candidate_seconds=second["owned_candidate"]["median_seconds"],
                                     owned_candidate_speedup=second["current"]["median_seconds"] /
                                                             second["owned_candidate"]["median_seconds"]))
for first, second in zip(before["binary"], after["binary"], strict=True):
    for key in ["n", "outcome", "value"]:
        assert first[key] == second[key], key
    summary["binary"].append(dict(n=first["n"], outcome=first["outcome"],
                                  **comparison(first["timing"], second["timing"])))
for first, second in zip(before["kde"], after["kde"], strict=True):
    for key in ["n", "grid", "bandwidth"]:
        assert first[key] == second[key], key
    old, new = np.array(first["density"]), np.array(second["density"])
    np.testing.assert_allclose(new, old, rtol=2e-13, atol=2e-15)
    summary["kde"].append(dict(n=first["n"], grid=first["grid"],
                               max_density_absolute_difference=float(np.max(np.abs(new - old))),
                               **comparison(first["timing"], second["timing"])))
for key in ["n", "p", "n_folds", "n_jobs", "score", "arrays", "value", "se"]:
    assert before["irm"][key] == after["irm"][key], key
summary["irm"] = dict(n=before["irm"]["n"], p=before["irm"]["p"],
                      **comparison(before["irm"]["fit"], after["irm"]["fit"]),
                      value=after["irm"]["value"], se=after["irm"]["se"],
                      folds_predictions_scores_if_exactly_equal=True)
(ROOT / "block06_benchmark_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
