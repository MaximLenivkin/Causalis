# B13 independent scenario namespace regression tests

Date: 2026-10-07, Europe/Moscow. Frozen baseline: `9f0a63c42308ca886d92dc73d8d8d9611d5b2c31`. Verified source/test checkpoint: `4428be0e39bda8a2a47f1a6f184c92873da10976`.

The new `tests/data/test_scenario_namespace_contract.py` contains **91 cases**. The test author changed only this test module and its audit artifacts. Root owns implementation, existing tests, Git mutations, integration and CI. The final test module is frozen after focused verification.

## Contract and public coverage

Classic scenarios perform additional work after the underlying DGP wrapper: the binary scenario renames outcome `y` to `conversion`, and both binary/Gamma scenarios always expose `user_id`, including when ancillary generation is disabled. Enabled pre fields cannot share those actual scenario roles. A Gamma pre field named `conversion` remains valid because its outcome stays `y`. Automatic projection retains actual pre fields named like disabled oracles; unused pre names do not reserve or reclassify columns.

Tests exercise:

- Eight binary `pre_name='conversion'` collisions across raw/data-contract returns, oracle flags and ancillary flags. A successful raw return with duplicate outcome names is not acceptable.
- Eight binary/Gamma `pre_name='user_id'` collisions with ancillary disabled, demonstrating the identifier owned by the scenario rather than the underlying wrapper.
- Twelve disabled-oracle pre features: `m`, `m_obs`, `tau_link`, `g0`, `g1`, and `cate` in both classic families. Exact renamed contract-frame comparisons preserve feature values, dtype, outcome and identifiers.
- Unused `pre_name` values: scenario outcome/ID/oracle names, `None`, list and empty string. With pre generation disabled, these options leave the raw frame's values, schema, order and dtype unchanged.
- Literal valid NumPy-string and prefix names, and Gamma's valid `conversion` pre covariate. These are exact renamed-frame comparisons with conventional pre names.
- Six real public exports: both classic functions through `causalis.dgp`, `causalis.dgp.causaldata`, and lazy `causalis.data_contracts` aliases. These must return the same actual features and frame.
- All valid classic pre/ancillary/oracle flag combinations for both families. The tests verify unique columns, actual feature order, binary outcome/treatment encoding where applicable, the required ID role, oracle availability, and raw-to-contract value/dtype preservation.
- Eight unchanged CUPED controls across binary/Tweedie, pre and oracle flags, preserving actual one/two pre fields and feature matrices. Four unchanged IV controls verify the three late-renamed roles, twelve actual features, ID role, oracle flags, and both deterministic-ID options.

Raw-to-contract references explicitly canonicalize treatment to `int8`, honoring the existing public data-contract normalization. All other dtype comparisons remain strict. An initial fixture incorrectly required raw float treatment and normalized contract treatment to have identical dtype; it was corrected before final baseline/focused evidence. Those intermediate fixture failures are not counted as namespace defects.

Tests call public scenario generators and aliases. They do not monkeypatch core generation or scenario constants, assert private namespace helpers, reconstruct production equations, or repeat B12's internal augmentation tests. All data are synthetic. No new statistical calibration, finite-value, general shape, CUPED secondary-name, UUID-uniqueness, or estimand policy is introduced.

## Verification and provenance

The final same-module baseline has **28 failed, 63 passed, 0 errors/skips**, pytest summary **4.79 seconds**, exit 1. The 28 failing parameterizations cover conversion collisions (8), required scenario-ID collisions (8), and missing disabled-oracle pre features (12); parameter counts are not a count of distinct bugs. Valid classic controls and unchanged CUPED/IV controls pass on baseline.

The focused implementation has **91 passed, 0 failures/errors/skips/warnings**, pytest summary **4.37 seconds**, exit 0. The runs used the same final test-file SHA256 and identical ordered case collection. Source and test bytes were checked against the focused manifest after execution.

The baseline runner reconstructs the single changed scenario module, `causalis/scenarios/classic_rct/dgp.py`, from exact Git objects before its first import. All other tracked package paths must match baseline. It additionally verifies loaded-byte hashes for the six unchanged B12 DGP dependencies and unchanged CUPED/IV scenario modules, real classic helper aliases, required ID-helper identity, all six public classic exports, core class bindings and IV inheritance. Temporary source snapshots are deleted automatically.

Evidence:

- `block13_scenario_test_result.json`: combined collection/hash verification, counts, scope and checkpoint linkage.
- `block13_scenario_baseline_test_result.json` and `block13_scenario_focused_test_result.json`: original run provenance, source/dependency/test SHA256 and exact case IDs.
- `block13_scenario_baseline_tests.log` and `block13_scenario_focused_tests.log`: raw pytest output.
- `block13_scenario_test_temp/baseline.xml` and `block13_scenario_test_temp/current.xml`: raw JUnit in the ignored audit test-temp directory.

Reproduce:

```bash
.venv/bin/python audit/block13_scenario_test_runner.py --mode baseline
.venv/bin/python audit/block13_scenario_test_runner.py --mode focused
```

The baseline command intentionally exits 1; the verified focused command exits 0. The runner sets native thread counts to one, Agg, local `.venv/matplotlib`, `SKIP_DOCS_BUILD=true`, an empty `PYTEST_ADDOPTS`, and isolated pytest temp paths.

## Committed-byte linkage

Focused verification ran on root's completed working-tree implementation while HEAD still referenced the baseline audit checkpoint. The changed library file, final test module and eight unchanged dependency/control modules were compared with exact Git objects at `4428be0e39bda8a2a47f1a6f184c92873da10976`. Committed hashes, current working-tree bytes and recorded focused hashes match exactly. The dependency hashes also match baseline. The combined manifest records that linkage while retaining the original pre-commit process metadata; no repeat run was needed. Broader integration, CI, DiD and sensitivity validation are outside this test-author evidence.
