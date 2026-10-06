# B08 independent methodological review

Review date: 2026-10-06 (Europe/Moscow). Baseline: `b33922f1c0db8885ae9e8e071c45fc46de5205b6`. This is a bounded review of the multi-treatment generator contracts and assignment policy. Sensitivity analysis is deferred. No source edits were made by this reviewer.

## Extreme Gaussian exponential oracle

The existing clipped exponential Gaussian oracle evaluates `strength**2`. A finite `u_strength_y=1e200`, link zero, gamma outcome raises `OverflowError` before returning a mean. The mathematical mean is bounded between exp(-20) and exp(20), so the exception is numerical rather than mathematical nonexistence. The proposed explicit representability check and finite-output validation are appropriate fail-fast behavior for this block; they do not establish arbitrary-precision oracle accuracy.

Independent reference: for mean link `a` and strength `s>0`, compute lower and upper tails analytically and the middle term as the bounded integral

`exp(-20)*Phi((-20-a)/s) + exp(20)*Phi((a-20)/s) + integral[-20,20] exp(w)*phi((w-a)/s)/s dw`.

Using SciPy adaptive quadrature (absolute tolerance 1e-6, relative tolerance 1e-12), the existing helper at `s=1e8,a=0` gives 242582559.36219272 versus reference 242582560.92984235 (relative difference -6.4623e-9). At strengths 10 through 1000 and links -100,0,100 the relative differences were at most 1.5e-13. At 1e6 the observed differences reached 8.7e-11. These exploratory probes identify cancellation sensitivity; they are not a comprehensive certified error bound. Stable bounded integration for extreme strengths remains a separate numerical improvement, not a reason to silently clip invalid computed means.

## Assignment law

Retries conditioned on all arms appearing and forced arm insertion modify the joint assignment law. Softmax probabilities remain nominal probabilities of the original independent assignment model, not actual marginal probabilities under the repair algorithm. Keeping the legacy policy explicit and adding an opt-in single-draw iid policy is a compatible interface decision. Neither policy creates the Gaussian-marginal propensity oracle; `m` remains the U=0 reference and `m_obs` remains conditional on realized U.

Repair must sample positions only from arms with surplus observations, preserving existing singleton arms. A repaired sample with n>=K can then contain every arm. Under iid, absent arms are expected and should remain absent in raw DataFrames. Conversion to MultiCausalData can still fail its independent validation, especially duplicate all-zero absent-arm columns; documentation must make this distinction explicit.

## Confirmed residual name collisions (P2; outside B08)

Baseline public-API probes, seed 1, n=30:

- `n_treatments=2,k=0,d_names=['y','arm']`: treatment assignment overwrites outcome `y`; its values become only 0/1.
- `confounder_specs=[{'name':'d_0','dist':'normal'}]`: confounder insertion overwrites the `d_0` treatment column with continuous values.
- `confounder_specs=[{'name':'g_d_0','dist':'normal'}]`: default oracle insertion overwrites the confounder with the control oracle (zeros in this simple configuration).

These are actual data-corruption cases for custom schemas, not general failures of default names. Follow-up should validate the complete generated namespace before assignment: outcome, arm names, expanded categorical confounder names, and enabled oracle names. Adding suffixes silently would change the user's requested schema and require a deliberate policy. This block documents the issue without broadening its source changes.

## Review boundary

Finite checks must run before links or probability normalization can conceal invalid raw values. Finite inputs alone do not guarantee every floating-point intermediate is finite, and output validation does not prove statistical identification or numerical accuracy. Existing supplied-U Gaussian reference semantics and the B07 latent-confounding caveats remain applicable. No new marginal propensity or selected-ATT guarantee is introduced.

## Implementation review

Read-only review of the shared working-tree implementation found the following sound boundaries:

- Finite and real checks precede alpha/theta/latent-strength/beta normalization, callback addition, clipped outcome links, and oracle insertion. An early draft cast complex coefficients before checking them; this was reported and corrected in the normalizers.
- The clipped exponential oracle rejects strengths whose square cannot be represented, with a contextual ValueError rather than the baseline OverflowError. Finite-output checks also reject invalid computed or sampled outcomes.
- Calibration scales finite positive target weights by their maximum only when the ordinary sum overflows. This preserves the existing arithmetic on ordinary configurations.
- Scalar and shape-(1,) g_y/g_d callback broadcasting remains supported, along with scalar/vector/column U and the existing flattened tau callback behavior.
- The new dataclass policy is appended after the existing seed parameter, preserving previous positional arguments. The functional wrapper also appends and forwards the policy.
- Fallback repair retains the original proposed index draw; it replaces an index only if overwriting it would erase a singleton arm. Counts are updated after each insertion. For n>=K, sufficient surplus observations remain to fill all missing arms.
- The iid branch consumes exactly one uniform draw per row, uses the conditional softmax probabilities, and permits small samples. Its last cumulative-probability entry is set to one to avoid rounding gaps.

The new assignment tests use an independent searchsorted reference, compare subsequent RNG state, check 60 rare/zero-support coverage configurations, and compare ordinary first-success public outcomes with independently consumed X/U/assignment/noise draws. These substantiate the law and compatibility decisions rather than asserting only the implementation's own output.

Source changes inspected here are confined to the generator and functional wrapper. No estimation score, influence-function, DiD, IV, or sensitivity formula change is part of this implementation. Integration counts and final source provenance belong to the root block report; this reviewer does not claim to have rerun that integration.
