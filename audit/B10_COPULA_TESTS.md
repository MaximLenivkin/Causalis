# B10 independent categorical Gaussian copula tests

Date: 2026-10-07, Europe/Moscow. Frozen baseline: `83b63836dbd0c4793c24dd95ff7dc18c443792ad`. Verified source/test checkpoint: `95a8b7599fb129fb2c5973f50e9b4a8018732f6c`.

The new module `tests/data/test_copula_categorical_coordinates.py` contains **33 cases**. It verifies the shared sampler directly, complete binary- and multi-treatment generation, and the public inherited IV wrapper with both raw DataFrame and causal-data return modes. No existing test module or library file was edited by this test author. The new test module is frozen after the focused verification below.

## Independent reference

The reference draws one matrix of independent standard normals and applies explicit analytic formulas for a one-, two-, or three-coordinate positive-definite equicorrelation Gaussian law. It does not call the production PSD correction, Cholesky routine, or copula helper. It includes the existing diagonal jitter so numeric-only expectations retain their established sampling contract. All tested correlation matrices are already positive definite; this block does not validate arbitrary invalid-matrix repair.

Categorical expectations use explicit disjoint CDF intervals and drop the first level. The helper's categorical search operation is not used by the reference. Gaussian CDF saturation at one remains in the last positive-mass interval, even when raw categories have zero-probability trailing levels. Unique schema names and single-level `__onlylevel` output are asserted explicitly.

The cases cover:

- Categorical first, consecutive categories after a numeric coordinate, and categories separated by numeric coordinates; positive, negative, and identity latent correlations.
- Default, normalized explicit, and unnormalized probabilities; single-level output; exact threshold assignment; lower/upper CDF saturation; leading and trailing zero-probability levels; valid category intervals smaller than the numeric inverse-CDF clipping threshold.
- Numeric-only Gaussian/uniform/Bernoulli output and the next ten RNG draws. Mixed schemas and singleton categories also check the subsequent RNG stream against the independent normal draw reference.
- Full binary/multi generation with the category first or after a normal coordinate. Expanded X, its ordering and dropped first level, linear oracle means, finite outcomes, and multi-treatment one-hot assignment are checked.
- Full inherited IV generation through `generate_iv_data`, category first or after a normal coordinate, and both return modes. Its expanded confounders agree with the same Gaussian-coordinate reference.
- An independent distribution-level check of `Corr(Z0, 1{Z1 >= 0}) = rho * sqrt(2/pi)` for latent rho -0.75, 0, and 0.75. This deliberately distinguishes latent Gaussian correlation from observed mixed-type correlation. Under identity correlation, agreement between category and numeric sign is about one half, rather than the baseline's erroneous equality on every row. Fixed seed and conservative finite-sample tolerances are used.

The RCT multiple-outcome wrapper does not expose a copula option; this test task does not claim coverage of a categorical copula RCT configuration. IV provides a direct public inherited path for the shared sampler.

## Exact baseline and focused verification

The final same-module baseline has **30 failed, 3 passed, 0 errors/skips**, pytest summary 4.29 seconds. The focused patch has **33 passed, 0 failures/errors/skips/warnings**, pytest summary 3.84 seconds. Failing parameterizations are evidence of the missing coordinate/boundary contract, not a count of distinct bugs. No test fixture corrections or mixed intermediate baselines were needed.

Focused verification ran before the source commit. Both the helper and new test module's recorded SHA256 hashes were subsequently checked against the exact committed bytes at `95a8b7599fb129fb2c5973f50e9b4a8018732f6c` and the current files; all match. No repeat run was necessary. The baseline failures comprise 20 unbound-current-coordinate errors during test calls and 10 incorrect generated-value assertions; pytest counts all 30 as failed cases, with zero collection/setup errors.

Root created the library patch before this new test module's baseline execution. The baseline therefore uses a frozen Git-source import hook, rather than the working-tree helper: it reconstructs the entire shared `causalis.dgp.base` module from the baseline Git object and intercepts its first import. Binary, multi, and IV callers bind to that same frozen helper. The runner verifies the loaded module source hash and confirms that all other tracked package paths are unchanged from the baseline. This makes the recorded baseline independent of the concurrent library edit.

Evidence:

- `block10_copula_test_result.json`: baseline/focused counts, source/test hashes, identical collection, failure categories, reference scope, and exact committed-source/test linkage.
- `block10_copula_baseline_test_result.json` and `block10_copula_focused_test_result.json`: run provenance and timing.
- `block10_copula_baseline_tests.log` and `block10_copula_focused_tests.log`: raw focused outputs.
- `block10_copula_test_temp/baseline.xml` and `block10_copula_test_temp/current.xml`: raw JUnit, kept under the ignored audit test-temp directory.

Reproduce the same frozen baseline and current focused run:

```bash
.venv/bin/python audit/block10_copula_test_runner.py --mode baseline
.venv/bin/python audit/block10_copula_test_runner.py --mode focused
```

The baseline command intentionally demonstrates the pre-fix failures and returns exit code 1. The focused command returns exit code 0. The runner sets native thread counts to one, Agg, `.venv/matplotlib`, and `SKIP_DOCS_BUILD=true`; uses the repository's Python 3.12.14 environment; and deletes its temporary source snapshot after verification. The new tests and source hashes match the recorded final collection.

Root owns neighboring tests, broader integration, commits, CI, and final source provenance. This task did not change DiD or sensitivity behavior, rerun the full suite, validate causal identification, or claim observed correlation equals the configured latent correlation.
