# B14 independent DiD studentization regression tests

Date: 2026-10-07, Europe/Moscow. Frozen baseline: `dbded76ecf8a207aad2094903b8f015fed8ae5d6`. Verified source/test checkpoint: `4bdcff7d6388d1d72d5be4a546e8abb2a67a767c`.

The new `tests/scenarios/did/refutation/test_did_studentization_contract.py` contains **51 cases**. The existing `test_did_post_inference_diagnostics.py` retains its **five API tests**, with a genuinely nondegenerate synthetic panel fixture and additional positive finite pre-cell SE assertions. The test author owns these two test files and its audit artifacts; root owns implementation, Git mutations, integration and CI. Final source, tests and runner are frozen.

## Mathematical contract and public coverage

For finite ATT and strictly positive finite SE, the public cell statistic is the signed ratio ATT/SE. Changing outcome units must preserve that ratio. Floating overflow of a ratio with valid finite inputs remains signed infinity and requires caution. Zero SE cannot define a studentized statistic, including exact 0/0; invalid or missing ATT/SE also yield NaN. The fitted-pre-period report may be GREEN only if every pre-cell statistic is finite and satisfies the configured threshold. A finite cell cannot hide another undefined or overflowing cell.

The tests specify that contract through public `CallawaySantAnnaDIDEstimate`, `did_post_inference_cell_table`, `run_did_post_inference_diagnostics`, `PanelDataDID` and `CallawaySantAnnaDID`. They do not call private numerical helpers, reconstruct production influence equations, or monkeypatch estimation. Hand-specified estimate objects provide an independent arithmetic reference; fitted two-period panels test the real model and bootstrap boundaries.

Coverage includes:

- Signed ratios for positive SE and ten sign/scale combinations from `1e-120` to `1e120`, with true small effects and a fixed diagnostic threshold. No absolute effect tolerance is allowed to erase legitimate scale-dependent values.
- Exact-zero SE with zero, tiny nonzero and ordinary signed ATT; nonfinite ATT, nonfinite/negative SE, mixed valid/invalid pre cells, signed overflowing ratios, absent pre cells, and cached fake zero statistics when actual ATT or SE is missing. The report schema and available maximum value are checked, including infinity; undefined cells require a meaningful caution reason.
- A finite all-small-statistics control that remains GREEN.
- Full-rank four-control/four-treated panels with exact constant outcome changes, for both public `dr` and `aipw` estimator aliases. The unique intercept-containing OLS fit to a constant response is independently known: fitted outcome changes are exactly constant, residuals vanish, ATT and SE are exactly zero. The model's exact point-null p-value convention is 1, while its studentized statistic remains undefined.
- Real treated departures at zero SE, including signed binary-exact `2**-80` effects. ATT remains the actual effect; zero-SE nonzero-effect p-values and studentized statistics are undefined.
- Nearly constant control responses with a genuine tiny affine slope, both with zero background and with a larger background; the slope must remain observable. Rank-deficient controls retain their rank warning. These tests also verify that fitting does not mutate the input panel.
- All-zero-score bootstrap with and without covariates: cell and event SE remain zero, simultaneous bands and their critical value are NaN, and no RuntimeWarning is emitted.

The fitted reference panels use explicit monthly calendar periods, one treated cohort, one post-treatment period and never-treated controls. Their purpose is arithmetic and public inference behavior, not validation of identification assumptions, coverage, causal calibration or power for a real study.

## Nondegenerate existing API fixture

The original six-unit panel had only two controls for a two-parameter outcome regression and clusters aligned with entire cohorts. Adding noise alone would not fix that saturated design and its zero clustered variance. The revised fixture replicates the six unit types six times: **36 units, 12 controls, six clusters spanning all cohorts**. Seeded independent unit-period noise supplies genuine residual variation. It retains the original cohort dates, treatment effects, model settings, report thresholds, GREEN assertion, message checks and plotting checks.

The API test now explicitly requires nonempty pre cells with positive finite SE, so a degenerate panel cannot silently become a GREEN reference. The same revised fixture passes all five API tests on both frozen baseline and focused source. The original saturated fixture is preserved separately by the contract owner; this runner does not claim to execute that frozen-fixture probe.

An initial new two-period fixture used numeric time values, which `PanelDataDID` does not accept as calendar time. It was corrected to explicit monthly periods before final baseline/focused evidence. Intermediate construction failures are excluded from all reported counts. Final baseline has no construction errors and reaches the intended public assertions.

## Verification and provenance

The identical final test files on exact baseline have **28 failed, 28 passed, 0 errors/skips**, pytest summary **5.17 seconds**, exit 1. Four warnings come from overflowing division in the old public studentization implementation. All five revised API tests pass baseline. The failing parameterizations are:

| Public contract | Failing cases |
| --- | ---: |
| Zero-SE studentization | 5 |
| Invalid nonfinite ATT | 2 |
| Mixed valid/undefined pre cells | 9 |
| Overflow retained by the pre-period report | 2 |
| Cached statistics with missing ATT/SE | 2 |
| Full-rank exact constant control changes | 2 |
| Nonzero treated departure with zero-SE inference | 4 |
| All-zero-score bootstrap without RuntimeWarning | 2 |

These are parameterized cases, not a count of distinct bugs. Positive-SE scaling, near-constant responses, rank warnings, finite GREEN references and the revised API fixture pass baseline.

Focused verification has **56 passed, 0 failures/errors/skips/warnings**, pytest summary **5.96 seconds**, exit 0. Both runs have identical SHA256 for both test files and identical ordered collection: 51 new cases and five existing cases. Raw JUnit counts and exact case IDs were independently checked when assembling the combined manifest.

`block14_did_test_runner.py` reconstructs both changed modules, `causalis/scenarios/did/model.py` and `causalis/scenarios/did/refutation/post_inference.py`, from exact baseline Git objects before first import. All other tracked package paths must be unchanged. Five dependencies are additionally checked by loaded-byte hashes: both public data contracts, the DiD and refutation namespace modules, and post-inference plots. Real model/estimate class identities, public report/cell-table aliases and the plot influence-table binding are verified. Temporary baseline source snapshots are deleted automatically.

Evidence:

- `block14_did_test_result.json`: combined raw-JUnit/collection verification, counts, scope, baseline failure families and checkpoint linkage.
- `block14_did_baseline_test_result.json` and `block14_did_focused_test_result.json`: original run provenance, source/dependency/test SHA256, package versions and exact case IDs.
- `block14_did_baseline_tests.log` and `block14_did_focused_tests.log`: raw pytest output.
- `block14_did_test_temp/baseline.xml` and `block14_did_test_temp/current.xml`: raw JUnit in the ignored audit test-temp directory.

Reproduce:

```bash
.venv/bin/python audit/block14_did_test_runner.py --mode baseline
.venv/bin/python audit/block14_did_test_runner.py --mode focused
```

Baseline intentionally exits 1; focused exits 0. The runner sets native thread counts to one, Agg, local `.venv/matplotlib`, `SKIP_DOCS_BUILD=true`, an empty `PYTEST_ADDOPTS` and isolated pytest temp paths. Actual environment: Python 3.12.14, macOS 26.6.2 arm64, NumPy 2.5.3, pandas 3.0.6, SciPy 1.18.1 and Pydantic 2.13.5.

## Committed-byte linkage and limits

Focused verification ran on the completed working-tree implementation while HEAD still referenced baseline `dbded76`. Exact Git objects at `4bdcff7d6388d1d72d5be4a546e8abb2a67a767c` match both changed library files, both final test files and all five unchanged dependencies. Committed hashes, current working-tree bytes and recorded focused hashes match; dependency hashes also match baseline. The combined manifest retains the original pre-commit process HEAD and timestamps. No repeat run was needed to establish that byte linkage.

This evidence covers 56 focused public contract/API cases. Root records neighboring tests, broader integration, cross-version CI and the original saturated fixture separately. Full sensitivity analysis, scientific coverage calibration, standalone documentation builds, release validation and benchmarks were not run by the test author.
