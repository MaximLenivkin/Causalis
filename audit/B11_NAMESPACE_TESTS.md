# B11 independent binary/IV namespace regression tests

Date: 2026-10-07, Europe/Moscow. Frozen baseline: `4d6b8143db7a93c1a7eba371fcd144878d80c896`. Verified source/test checkpoint: `cdc2c9590246c5b049d2184ba3479324217b2b00`.

The new `tests/data/test_binary_iv_namespace_contract.py` contains **163 cases**. The test author edited only this new test module and its audit artifacts. No existing test module, library path, or Git state was changed by this task. The test module is frozen after the verification below.

## Public contract and coverage

The binary generator emits fixed `y` and `d`, plus six enabled oracle columns: `m`, `m_obs`, `tau_link`, `g0`, `g1`, and `cate`. IV emits `y`, `d`, its current configured instrument, and fourteen enabled oracle columns: `m`, `r_obs`, `r_z0`, `r_z1`, `g_z0`, `g_z1`, `iv_first_stage`, `iv_reduced_form`, `late_x`, `late`, `tau_link`, `g_d0`, `g_d1`, and `cate`.

Tests require the actual emitted namespace to be distinct. Collisions raise ValueError identifying the column and the conflicting roles, without requiring a particular ordering of those roles or a full implementation-specific message. They exercise:

- Confounder overwrite of outcome, treatment, and instrument; every enabled family oracle as a confounder name; every IV oracle as an instrument name.
- Expanded categorical/oracle and categorical/custom-instrument overlaps, single-level expansion, normal/expanded-confounder overlaps under ordinary and copula sampling, and category labels that stringify to the same column.
- Literal nonempty string names for actual columns, including NumPy strings and whitespace without trimming. Existing ordinary fallback names and stringified categorical names remain valid. Custom X names are checked as actually returned, without hypothetical categorical expansion.
- Actual name count against the returned covariate width, in both directions. No general finite-value, dtype, row-count, or two-dimensional-X contract is introduced by these tests.
- Every disabled oracle name as a valid raw confounder, preserving its values and exact requested column. A disabled-oracle-looking IV instrument is also allowed. Names emitted only by the other family are not reserved.
- Reuse after changed confounder specifications, instrument names, or oracle settings. Invalid configured IV names reject before custom sampling; invalid sampled namespaces reject before latent/assignment RNG draws and before structural callbacks.
- Three callback-mutation regressions: binary g_y or IV g_z enables oracles over an existing `m` confounder; IV g_z changes its instrument to `y`. These must raise before DataFrame construction can corrupt the output, even though the schema was valid before the callback.
- Four valid schema-renaming comparisons: binary/IV and both oracle settings preserve numerical values, exact column order, and the next ten RNG draws when only valid user confounder names change. These compare renaming within each source version; separate old/new compatibility checks belong to root/review verification.
- Public RCT and IV wrappers, both raw and data-contract return modes, inherit the core rejection. Optional ancillary/preperiod augmentation is disabled in these tests.

Fourteen compatibility cases preserve historical zero-confounder custom containers: binary list rows and flat arrays for empty and positive n, with both oracle settings; IV flat arrays with both oracle settings, and IV list rows without oracles. IV Python-list X with oracles has a separate pre-existing AttributeError and is not promoted to a new valid-input guarantee. Empty IV tests set `target_z_rate=None`, avoiding calibration warnings. These checks prevent namespace validation from introducing an unrelated X-conversion requirement.

## Verification and provenance

The final same-module baseline has **103 failed, 60 passed, 0 errors/skips**, pytest summary 5.81 seconds. The focused patch has **163 passed, 0 failures/errors/skips/warnings**, pytest summary 4.14 seconds. Failing parameterizations are not a count of distinct bugs. No fixture corrections or mixed intermediate collections were needed.

Both source modules were reconstructed from the frozen Git objects before their first package import. The baseline runner verifies loaded bytes, the IV class's exact binary parent identity, and the real RCT/IV functional wrappers' bindings to those same selected classes. All other tracked package paths must remain unchanged from the baseline. This makes the baseline independent of concurrent root edits.

Focused verification ran on the working-tree patch before its commit. Subsequently, both source files and the new test module were checked byte-for-byte against `cdc2c9590246c5b049d2184ba3479324217b2b00`; their recorded SHA256 hashes all match. No post-commit repeat run was necessary, and the manifest does not claim that the focused process started at the later commit.

Evidence:

- `block11_namespace_test_result.json`: combined counts, identical exact collection, recorded source/test hashes, committed-byte linkage, and scope boundaries.
- `block11_namespace_baseline_test_result.json` and `block11_namespace_focused_test_result.json`: original run provenance and timing.
- `block11_namespace_baseline_tests.log` and `block11_namespace_focused_tests.log`: raw pytest outputs.
- `block11_namespace_test_temp/baseline.xml` and `block11_namespace_test_temp/current.xml`: raw JUnit under the ignored audit test-temp directory.

Reproduce the same baseline and current focused run:

```bash
.venv/bin/python audit/block11_namespace_test_runner.py --mode baseline
.venv/bin/python audit/block11_namespace_test_runner.py --mode focused
```

The baseline command intentionally demonstrates missing contracts and exits 1; the focused command exits 0. The runner sets native thread counts to one, Agg, `.venv/matplotlib`, and `SKIP_DOCS_BUILD=true`; uses isolated pytest temp paths; and deletes temporary source snapshots. For future reproduction it also clears `PYTEST_ADDOPTS`; that runner-only adjustment did not rewrite the original run manifests or require a new test run.

Root owns broader integration, CI, commits, and final block conclusions. This test-author task did not run the full suite or modify DiD, sensitivity, ancillary augmentation, or preperiod behavior.

## Separate wrapper follow-ups

Core raw namespace guarantees do not settle wrapper column-order/conversion policies. The existing IV wrapper treats oracle-looking names as oracle columns regardless of `include_oracle`; an allowed disabled-oracle instrument such as `m` can appear in both core and oracle order lists. Default data-contract confounder selection also excludes oracle-looking confounders even when oracles are disabled. Ancillary and preperiod augmentation have their own emitted namespaces. These concerns were reported to root and kept outside the two-library-path B11 scope; tests do not silently broaden their guarantee to those policies.
