# B08: central multi-treatment DGP contract review

Reviewed 2026-10-06. Scope: `MultiCausalDatasetGenerator` input and callback
contracts; sensitivity analysis untouched. This file records pre-fix evidence,
not a claim that every generator module has been hardened.

## Confirmed findings

All examples below call `MultiCausalDatasetGenerator(k=1, seed=42, **kwargs)`
and `.generate(12)` using the repository Python 3.12 virtual environment.

1. **P2: non-finite link inputs can be concealed by bounded outcome links.**
   `alpha_y=np.inf, outcome_type='binary'` returns an entirely finite DataFrame
   with saturated outcome probabilities. `g_y=lambda X: np.full(len(X), np.inf),
   outcome_type='gamma'` also returns a finite frame: exponential clipping
   converts an invalid callback output into a bounded mean. Validation belongs
   before sigmoid/exp clipping; finite large links may legitimately saturate.
2. **P2: invalid distribution parameters can escape as invalid generated data.**
   `gamma_shape=np.inf, outcome_type='gamma'` returns NaN outcomes; existing
   `shape <= 0` validation misses infinity. Finite nonnegative continuous noise
   and finite positive gamma shape should be checked explicitly.
3. **P2: custom confounder samples have no public shape/finite boundary.**
   `x_sampler=lambda n,k,s: np.full((n,k), np.inf)` returns infinite covariates
   when the covariates are not used in scores. Wrong-dimensional values fail
   later through incidental indexing/broadcasting rather than a sampler error.
4. **P2: supplied latent values lack an observation-count and finite contract.**
   `U=np.array(0.)` broadcasts across all rows; `(n,1)` works if outcome latent
   strength is zero but adds an `(n,n)` outcome matrix if it is nonzero. Explicit
   flattening of accepted singleton-axis vectors, followed by size/finite
   validation, removes this inconsistent path. Scalar latent broadcast is not
   documented as a public feature; B08 preserves existing scalar broadcast
   explicitly and normalizes singleton-axis vectors to shape (n,).
5. **P2: extreme finite calculations need explicit arithmetic boundaries.**
   `u_strength_y=1e155, outcome_type='gamma'` raises a raw `OverflowError` in
   `strength**2` during marginal-oracle calculation. Finite inputs alone do not
   guarantee finite intermediates. Validate computed treatment scores,
   structural links, sampled outcomes, and oracle output, with a contextual
   error instead of returning corrupt data. This does not establish an exact
   oracle for all representable strengths.

## Compatibility constraints

- Existing finite `g_y`/`g_d` scalar outputs broadcast intentionally and should
  remain supported. `g_y=lambda X: 2.0` currently succeeds.
- Existing `tau` callback flattens any output having exactly n elements;
  retain singleton row/column forms and n-element outputs unless separately
  changing the documented contract.
- Preserve k=0, sigma_y=0, normalized K/K-1 coefficient forms, ordinary finite
  link clipping, and current finite output/RNG sequence.
- Validate callback values before any transformation that hides infinity.
- Check arithmetic independently of `include_oracle`; invalid observed data
  must fail even when optional oracle columns are disabled.
- Scope finite guards to the central generator first. Shared binary generator,
  confounder distribution specification details, and custom naming collisions
  remain separate audits unless a shared change is demonstrably necessary.

## Suggested bounded implementation

Add reusable contextual real-numeric/finite checks at existing normalization
and generate boundaries, explicit positive integer n/K and nonnegative integer
k validation, and context-specific shape checks. Reject invalid distribution
parameters before sampling. Validate X, supplied U, callback outputs, scores,
structural links, sampled outcomes, and optional oracle output. Preserve
accepted scalar baseline/treatment callbacks and n-element heterogeneous
effect outputs. Add independent regressions for invalid cases above and
seeded baseline identity for ordinary finite configurations.

## Implemented bounded changes and verification

`base.py` now rejects non-finite or complex numeric parameters before float
conversion, validates integer n/K/k and custom X shape, checks callback values
before bounded links, normalizes accepted latent shapes, and checks calculated
scores, links, observed outcomes and optional oracle outputs. Scalars and
one-element baseline callbacks, n-element heterogeneous callbacks, and scalar U
remain supported. Gamma oracle strength whose square overflows raises a
contextual ValueError; this is not arbitrary-strength oracle support. Other
non-finite oracle results also fail explicitly. Finite score subtraction may
still produce a negative-infinity exponential argument when correctly yielding
zero probability; guards target the untransformed score, not that legitimate
softmax underflow.

Finite positive target weights whose sum overflows are rescaled by their maximum
before normalization. Ordinary finite-sum calibration arithmetic is unchanged.
Complex alpha_d/u_strength_d/theta/beta_d are checked before legacy float casts
can discard imaginary components. No `nan_to_num` or latent-law replacement is
introduced. The sampling policy changes are documented separately in the B08
assignment review.

- Original 21-case regressions against exact B07 source: **17 failed, 4 passed,
  3 warnings, 3.77 s** (`block08_contract_before_tests.log`). The initially
  observed direct run was 10.74 s; the preserved reproducible isolated-source
  run is the evidence reported here.
- Expanded final 112-case regressions against exact B07 source: **100 failed,
  12 passed, 36 warnings, 7.00 s**
  (`block08_contract_expanded_before_tests.log`). Many parameterizations test
  the same missing boundary; these are not 100 distinct library defects.
- Initial patch with original 21 cases plus 30 existing neighbors: **51 passed,
  38.14 s** (`block08_contract_after_tests.log`). This predates final expansion
  and compatibility corrections.
- Independent seeded old/current comparison: **16 configurations verified**
  (all four outcome families, oracle on/off, custom callbacks on/off), exact
  full DataFrame values/schema and next ten RNG draws, seed731/n120. See
  `verify_block08_finite_reference.py` and
  `block08_finite_reference_result.json`. Default assignment policy is compared;
  new iid mode intentionally follows a different draw law and is tested separately.

`probe_block08_contract_baseline.py` dynamically loads the exact B07 source
`b33922f1c0db8885ae9e8e071c45fc46de5205b6` in an isolated module and runs the new
public regressions, without replacing checkout files. Its current invocation
runs the expanded final test file; the original and expanded logs above are
different checkpoints of that test file.

Final focused verification: **149 passed, 1 warning, 46.14 s**
(`block08_contract_final_tests.log`): all 112 new contract cases plus 37
existing latent-oracle, generator-semantics, multiclass DML, gamma26 and binary26
neighbors. The warning is the deliberately overflowing finite matmul regression;
its ensuing contextual ValueError is asserted. A first attempted final test
command referenced a nonexistent path, collected zero tests and was immediately
corrected; it provides no validation evidence.
