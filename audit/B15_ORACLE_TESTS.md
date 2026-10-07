# B15 independent Gaussian-marginal propensity tests

Date: 2026-10-07, Europe/Moscow. Frozen baseline: `71f6a619b04e0ab8fab388fb95b7d0f3d6631b96`. Verified source/test checkpoint: `9a57e91942a4b90b0401c0f8e3ebe6f5b4d82cdf`.

The new `tests/data/test_multicausal_marginal_propensity.py` contains **79 public cases**. The test author owns this new test module, its runner and audit evidence. Root owns the two library modules, Git mutations, broader integration and CI. Final tests and runner are frozen after focused verification.

## Reference law and scope

For each observed covariate row, the target is

\[
q_k(x)=\int_{-\infty}^{\infty}
\operatorname{softmax}_k\{a(x)+b u\}\phi(u)\,du,
\qquad U\sim N(0,1),\ U\perp X.
\]

This is the marginal probability of the **nominal** assignment model. It differs from the existing `m_<arm>` at U=0 when latent slopes vary by arm. `m_obs_<arm>` continues to describe the realized supplied/drawn U. Supplied non-Gaussian or X-dependent U does not change the new columns' Gaussian-reference law. Under all-arm resampling/repair, q is not the row probability of the conditioned or repaired sample.

The opt-in field and wrapper keyword `include_marginal_propensity=False` append `m_marginal_<arm>` only when enabled and require `include_oracle=True`. The tests require an additive output, preserve existing propensities/outcome oracles/calibration, and make no selected-latent ATT claim. They check numerical probability behavior, not causal identification, population-X calibration or estimation coverage.

## Independent numerical reference

The test reference integrates each row and arm separately using scalar SciPy `quad` and SciPy `softmax`, without production oracle helpers, vector quadrature, empirical treatment frequencies or fixed Gaussian nodes. Affine score intersections and transition-width boundaries resolve narrow changes between dominant arms. Integration is over [-12,12]; each softmax component is bounded by one, so omitted Gaussian mass is below 4e-33. Every reference rejects IntegrationWarning and requires its absolute error estimate below 5e-11. Production/reference comparisons use unchanged absolute probability tolerance **2e-9**, with finite/bounded probabilities and unit row sums checked independently. These numerical estimates are not a rigorous certificate for arbitrary coefficients.

Coverage includes:

- K=2/3/5, four distinct X rows, arm-specific intercepts/linear coefficients and propensity sharpness. Strengths 0, .1, 1, 2, 5, 10 and 50 are represented, with asymmetric strength-1000 scores providing separated dominant-arm transitions. The steep case explicitly differs from its U=0 probabilities.
- A closed two-arm symmetry reference q=(.5,.5), including signed strengths up to 1000; equal latent slopes must cancel and reproduce existing m exactly. Gaussian sign reversal, common intercept/X-score/latent shifts and arm permutation preserve the appropriate probabilities.
- Nonlinear treatment callbacks in independently computed scores. Calibration remains at sampled-X/U=0: marginal q integrates the calibrated logits, and does not silently retarget m to Gaussian-marginal rates.
- Supplied constant non-Gaussian U and X-dependent U, with changing m_obs and observed outcomes but identical Gaussian q.
- Rare-arm nominal probabilities [1,0,0] under both `iid` and `ensure_all`: all-arm repair can emit an arm whose nominal probability is zero without changing the meaning or values of q.
- Four outcome families and two consecutive generations, comparing all existing column names/order/values/dtypes, callback names/inputs/call counts, complete RNG state and the next ten RNG values. New columns must appear after the complete existing oracle list. Default and explicit disabled settings retain the same schema and RNG; the full historical positional constructor still works.
- Python/NumPy booleans, rejection of nonboolean/coercible option values at construction and every generate, conflicting oracle flags, and rejection before sampler/latent RNG use where the input can be checked early.
- Actual confounder, expanded categorical, treatment and existing-oracle collisions with enabled new names. Disabled new names remain legitimate treatments/features and are preserved by automatic conversion. Late callback flag and treatment-name mutations cannot produce a corrupted output.
- Both real wrapper exports, through `causalis.dgp.multicausaldata` and its `functional` module, for raw/data-contract returns. Automatic features remain exactly the actual confounders; opt-in oracle columns do not become estimator inputs. Direct `to_multicausal_data` also preserves observations/features under latent assignment.
- An unsupported finite Gaussian geometry that still generates normally at realized U=0 without the option, but raises explicitly when integration is requested. One targeted fault injection makes the SciPy backend report failure despite returning a bounded unit-mass candidate; the public generator must raise rather than publish it. Numerical reference tests never patch integration.

The general `causalis.dgp` and `causalis.data_contracts` namespaces do not currently export `generate_multitreatment`; the tests use the two actual exports rather than inventing extra aliases.

## Reference-harness correction

The first focused run had 78 passing cases and one failed reference check. Three algebraically equal pairwise crossings were represented as -11.840000000000002, -11.839999999999998 and -11.839999999999996. Their smallest gap was 1.776e-15; QUADPACK reported “Extremely bad integrand behavior” and an error estimate up to .0069. The reference now coalesces partition knots within 32 ULP, while preserving the full integration domain and unmodified integrand. Its warning/error rejection and the probability-comparison tolerance remain unchanged. Scalar probe evidence is `block15_oracle_reference_knot_probe.json`.

This was a reference-partition defect, not a library numerical failure. Both final baseline and focused runs were repeated with the same corrected test bytes; intermediate counts are excluded from final proof.

## Final verification and provenance

The identical final module on exact baseline has **74 failed, 5 passed, 0 errors/skips/warnings**, pytest summary **6.11 seconds**, exit 1. All 74 failures are **planned new-API absence**, not evidence of 74 existing numerical bugs: 67 TypeErrors reject the unknown keyword, and seven AttributeErrors arise because the slotted historical generator lacks the new mutable field. Raw failure messages all identify `include_marginal_propensity`. The five baseline passes cover the historical full positional constructor, disabled-name automatic features and default namespace availability.

Focused verification has **79 passed, 0 failures/errors/skips/warnings**, pytest summary **6.99 seconds**, exit 0. Test SHA256: `3e6ade34ff0d7faadd172eab87ab15a9ccc24b968564c81302ede8a686f8df37`. Both runs have identical ordered collection and test-file bytes. Raw JUnit counts and exact case IDs were independently checked when assembling the combined manifest.

The runner reconstructs both changed modules, `causalis/dgp/multicausaldata/base.py` and `causalis/dgp/multicausaldata/functional.py`, from exact baseline Git objects before their first import. All other tracked package paths must be unchanged. Four dependencies are additionally checked by loaded-byte hashes: shared DGP helpers, the MultiCausalData contract, the multicausal public package namespace and duplicate-column support. Real generator/wrapper/contract identities, both public function exports and shared sigmoid/copula bindings are verified. Temporary baseline source snapshots are deleted automatically.

Evidence:

- `block15_oracle_test_result.json`: combined collection/JUnit/hash verification, scope, planned feature-absence classification and checkpoint linkage.
- `block15_oracle_baseline_test_result.json` and `block15_oracle_focused_test_result.json`: original run metadata, source/dependency/test SHA256, actual package versions and exact case IDs.
- `block15_oracle_baseline_tests.log` and `block15_oracle_focused_tests.log`: raw pytest output.
- `block15_oracle_test_temp/baseline.xml` and `block15_oracle_test_temp/current.xml`: raw JUnit in the ignored audit test-temp directory.

Reproduce:

```bash
.venv/bin/python audit/block15_oracle_test_runner.py --mode baseline
.venv/bin/python audit/block15_oracle_test_runner.py --mode focused
```

Baseline intentionally exits 1; focused exits 0. The runner sets native threads to one, Agg, local `.venv/matplotlib`, `SKIP_DOCS_BUILD=true`, an empty `PYTEST_ADDOPTS` and isolated pytest temp paths. Actual environment: Python 3.12.14, macOS 26.6.2 arm64, NumPy 2.5.3, pandas 3.0.6, SciPy 1.18.1 and Pydantic 2.13.5.

## Checkpoint linkage and limits

Focused verification ran on root's completed working-tree implementation while HEAD still referenced baseline `71f6a619`. Exact Git objects at `9a57e91942a4b90b0401c0f8e3ebe6f5b4d82cdf` match both changed library files, the final test file and all four unchanged dependencies. Committed hashes, current working-tree bytes and recorded focused hashes match; dependency hashes also match baseline. Original process HEAD and timestamps remain unchanged in the run manifests. No repeat run was needed to establish that byte linkage.

This test-author evidence covers 79 focused cases. Root records independent review, broad integration and cross-version CI separately. Sensitivity, selected-U ATT, additional latent laws, a new calibration mode, arbitrary-coefficient accuracy certificates, standalone documentation builds, release checks and performance benchmarks were not validated here.
