# B12 independent wrapper namespace regression tests

Date: 2026-10-07, Europe/Moscow. Frozen baseline: `eb6dfe23f0a97991b6e3d6109febc1b0170e128d`. Verified source/test checkpoint: `0b30db33fd2593dc25ea1b823a91795c789e0191`.

The new `tests/data/test_wrapper_namespace_contract.py` contains **162 cases**. The test author changed only this new test module and its audit artifacts. Library implementation, existing tests, Git mutations, broader integration and CI belong to root. The final test module is frozen after focused verification.

## Contract and independent coverage

Augmentation may add only distinct, nonempty literal string names. Existing columns and requested new columns cannot be overwritten or projected twice. Actual emitted roles govern column ordering and automatic feature selection. A numeric field called `user_id` is a confounder or instrument when no ancillary identifier was added. Disabled oracle-looking names remain ordinary features. Unused pre-period options do not change values, schema, order or automatic projection.

The tests exercise:

- RCT pre-name collisions with outcome, treatment, an enabled oracle, an actual confounder and prospective ancillary fields. Unused pre names are checked against fixed columns, oracle columns, confounders and actual ancillary fields, including automatic conversion. Disabled-oracle and inactive identifier names remain available for an actual pre covariate.
- Every shared ancillary field (`user_id`, `age`, `cnt_trans`, `platform_Android`, `platform_iOS`, `invited_friend`) as a conflicting existing column, actual wrapper confounder, or IV instrument. Direct-helper rejections preserve the original frame and the next ten RNG draws.
- Shared pre helper collisions, invalid requested types, duplicate input columns, and a builder callback that creates the prospective pre column. Early rejection must prevent builder invocation and RNG consumption. A callback-created field must retain the callback's values when augmentation rejects it. Nonempty NumPy strings and whitespace are preserved literally.
- All six binary and fourteen IV oracle names as actual disabled-oracle confounders, through both direct `to_*` and public wrappers. Exact sampled feature values must survive conversion. Two direct-conversion cases use actual sampled names different from the declared specification, checking the returned public feature matrix rather than private metadata.
- Numeric `user_id` confounders, IV instruments named `user_id`, `m` or `age`, enabled-oracle default exclusion, and explicit selection of varying generated oracle fields. Multi-treatment conversion is an unchanged-family control.
- Exact renamed-frame comparisons for disabled-oracle-looking confounders participating in RCT pre/ancillary signals and observational/IV ancillary signals. Valid shared-helper comparisons include the next ten RNG draws. These compare names within each selected source version; historical old/new compatibility is verified independently by review.
- Binary and Tweedie CUPED helpers: actual pre fields named `user_id` or a disabled oracle remain features; enabled oracles, sampled fields and fixed core fields cannot be overwritten; enabled pre names must be nonempty strings; unused names are ignored. Tweedie's prospective `_latent_A` oracle is reserved only when it will actually be emitted; the disabled name remains available for an actual pre field.
- Ancillary conversion identifies only the identifier actually added and retains numeric ancillary covariates.

These tests use synthetic data only. They do not introduce general X-shape, finite-value, callback-numeric, statistical calibration or estimand guarantees. The test module never asserts private generated-role snapshot fields or the implementation of a namespace-validation helper.

## Verification and provenance

The final exact same-module baseline has **136 failed, 26 passed, 0 errors/skips**, pytest summary **6.53 seconds**, exit 1. Failing parameterizations are not a count of distinct bugs. The unchanged-family and valid shared-helper/RNG controls pass on baseline. Review found a test-fixture defect in two actual-sampler cases: the slotted generator instance cannot accept a method assignment. The fixture now patches the class with automatic restoration; the final baseline was rerun, and both cases fail at the intended missing-feature assertion.

The focused implementation has **162 passed, 0 failures/errors/skips/warnings**, pytest summary **4.74 seconds**, exit 0. Both runs used the exact same final test-file SHA256 and identical ordered case collection. The focused runner checked all six working-tree source hashes; no implementation file changed during the run. Focused verification ran before root's source commit, while HEAD still referenced the baseline audit checkpoint. The original process metadata is retained.

All six implementation modules were reconstructed from frozen Git objects before their first package import:

1. `causalis/dgp/base.py`
2. `causalis/dgp/causaldata/preperiod.py`
3. `causalis/dgp/causaldata/base.py`
4. `causalis/dgp/causaldata/functional.py`
5. `causalis/dgp/causaldata_instrumental/base.py`
6. `causalis/dgp/causaldata_instrumental/functional.py`

The runner verifies loaded source bytes, exact IV inheritance, functional wrappers' bindings to the selected classes, and shared ancillary/pre helper aliases. Other tracked package paths must be unchanged from baseline. Source snapshots are deleted automatically; raw JUnit remains under the ignored audit test-temp directory. This evidence is independent of concurrent implementation edits.

Evidence:

- `block12_wrapper_baseline_test_result.json`: original counts, timing, source/test SHA256 and exact collected case IDs.
- `block12_wrapper_baseline_tests.log`: raw baseline pytest output.
- `block12_wrapper_test_temp/baseline.xml`: raw baseline JUnit.
- `block12_wrapper_focused_test_result.json` and `block12_wrapper_focused_tests.log`: original focused provenance and raw pytest output.
- `block12_wrapper_test_temp/current.xml`: raw focused JUnit.
- `block12_wrapper_test_result.json`: combined status and evidence linkage.

Reproduce:

```bash
.venv/bin/python audit/block12_wrapper_test_runner.py --mode baseline
.venv/bin/python audit/block12_wrapper_test_runner.py --mode focused
```

The baseline command intentionally exits 1; the focused command exits 0 on the verified implementation. The runner sets native thread counts to one, Agg, `.venv/matplotlib`, `SKIP_DOCS_BUILD=true`, and an empty `PYTEST_ADDOPTS`; pytest temp paths are isolated by mode.

## Committed-byte linkage

All six library files and the final test module were compared byte-for-byte with Git objects at `0b30db33fd2593dc25ea1b823a91795c789e0191`. Their committed hashes, current working-tree bytes and recorded focused-run hashes match exactly. The combined manifest records this source/test checkpoint while retaining the original pre-commit process metadata. No repeat test run was needed. This evidence does not claim a post-commit process start or any broader integration/CI result.
