# B09 independent namespace regression tests

Date: 2026-10-06. Frozen pre-B09 source: `74145665127f8fa5a0bf038d769697ab880854b8`.

The new public-API regression module is `tests/data/test_multicausal_namespace_contract.py`. It contains **123 cases**. No generator implementation, existing test module, or estimation formula was edited by this test author. The test module is frozen after the focused verification below.

## Contract covered

- Reject outcome/treatment/confounder overlaps, duplicate treatment names, and duplicate actual confounder names. The exception identifies the conflicting column.
- Check every enabled propensity, realized-U propensity, treatment-link, potential-outcome, and noncontrol contrast name. Distinct arms `control` and `obs_control` must reject their shared `m_obs_control` oracle name.
- Check the actual categorical expansion, including single-level names, duplicate categories, category labels that stringify to the same suffix, and overlaps between expanded and ordinary confounders. Both ordinary and copula paths are exercised.
- Reserve only emitted oracle columns. Disabled oracle names remain available; `cate_control` remains available because the control contrast is omitted. A custom X sampler retains its actual unexpanded confounder names.
- Reject actual nonstring/empty treatment and custom-sampler confounder names. Preserve ordered tuple and NumPy string-array arm names, Unicode, embedded spaces, and unique whitespace names without trimming.
- Apply the contract through both functional return modes and generator reuse after mutable schema changes. Reject invalid schemas before structural g_y/g_d/tau callbacks execute.
- Run 16 seeded schema-renaming checks across ordinary, categorical, copula, and custom X sampling; both oracle settings and assignment policies are covered. Within each source version, valid renaming preserves numerical values, column order, and the next ten RNG draws. These checks alone do not establish equality between two different source versions; separate old/new reference probes belong to the independent review.

Tests use the public generator and functional wrapper, without calling namespace helpers. They require errors identifying the column rather than a specific full helper message.

## Verification

The final frozen-source baseline has **87 failed, 36 passed, 0 errors/skips** (pytest summary 0.99 seconds). These are failing parameterizations of the missing contract, not a count of independent bugs. The patched generator has **123 passed, 0 failures/errors/skips**, without warnings (pytest summary 3.65 seconds).

The first 101-case baseline contained one incorrect test assertion: MultiCausalData presents its canonical outcome/confounder/treatment column order, while the raw generator presents outcome/treatment/confounder order. That fixture assertion was corrected before final verification. Historical evidence is retained separately: initial 69 failed/32 passed; corrected 101-case baseline 68 failed/33 passed and patched 101-case run all passed. These runs must not be added to final counts.

Evidence:

- `block09_namespace_tests_selection.json`: exact final collection, identical between baseline and patch.
- `block09_namespace_tests_result.json`: counts, JUnit locations, source/test hashes, environment, and historical labels.
- `block09_namespace_baseline_tests.log` and `block09_namespace_current_tests.log`: final focused raw outputs.
- `block09_namespace_baseline_reproduction.json` and `.log`: successful reproduction of the expected baseline failures by the standalone runner.
- `block09_namespace_initial_baseline_tests.log` and `block09_namespace_initial101_*_tests.log`: historical runs described above.

The original baseline used ignored git-show snapshots in `.venv/block09-namespace-baseline`. A reproducible runner avoids dependence on that snapshot:

```bash
.venv/bin/python audit/block09_namespace_baseline.py
```

The runner reconstructs both target source files directly from the frozen Git object, loads them under their original module names before pytest collection, and verifies that other tracked `causalis` paths remain unchanged from the baseline. It writes a separate `block09_namespace_baseline_reproduction` log/JSON and preserves JUnit in `.venv`. Exit code 1 is expected because this run demonstrates the pre-fix failures. Its temporary source snapshot is deleted after use.

Focused patched verification:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
MPLBACKEND=Agg MPLCONFIGDIR=.venv/matplotlib SKIP_DOCS_BUILD=true \
.venv/bin/python -m pytest -q -p no:cacheprovider \
  --basetemp=.venv/block09-namespace-current-temp \
  --junitxml=.venv/block09-namespace-current-junit.xml \
  tests/data/test_multicausal_namespace_contract.py
```

The focused verification used Python 3.12.14 on macOS arm64. The root block report owns broader integration, commits, CI, and final source provenance. This test-author task did not run the full suite or validate sensitivity analysis.

## Separate residual defect

The unchanged shared `_gaussian_copula` sampler reads its local `u` before assignment when its first specification is categorical. Copula namespace cases intentionally start with an ordinary continuous coordinate so this unrelated sampling defect does not obscure namespace validation. No fix or general copula correctness claim is included in this test task.
