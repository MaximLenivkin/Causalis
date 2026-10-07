# B14 implementation: exact constant OLS and complete pre-period checks

Baseline: `dbded76ecf8a207aad2094903b8f015fed8ae5d6`. Source checkpoint is recorded in the final block report.

The estimand remains the existing normalized traditional MLE/OLS cell ATT and complete-pair aggregates. Treatment/control selection, propensity optimization, nuisance influence derivatives, clustering, bootstrap draws and aggregation formulas are unchanged.

`causalis/scenarios/did/model.py` preserves the unique analytic OLS solution `(c, 0, ...)` when the control response is exactly constant, the entire design has a unit first-column intercept and the actual `lstsq` solver reports full column rank. It uses exact equality, not a numerical tolerance. Nonconstant, deficient-rank, non-unit-intercept and zero-column fits retain the original solver outputs. This prevents rounding residuals in a mathematically exact fit; it is not a general correction of cancellation in arbitrary outcome differences or near-degenerate fits.

The normal p-value helper rejects nonfinite inputs and negative SE. At zero SE it keeps the legacy p=1 convention only for an exactly zero effect; a real nonzero effect, however small, receives NaN. Positive finite-SE arithmetic remains unchanged. The exact-zero convention does not certify valid studentization or nondegenerate inference.

`causalis/scenarios/did/refutation/post_inference.py` computes ATT/SE only for finite ATT and positive finite SE. Zero/negative/unavailable SE produces NaN; an overflowing finite-input ratio remains signed infinity. A local NumPy error context handles representational over/underflow during division without altering the caller's error settings or replacing outputs.

The fitted pre-period check requires every eligible cell to have a finite standardized statistic. Undefined and infinite statistics can no longer disappear from a mixture of cells and produce GREEN. Missing ATT or SE invalidates cached statistics in the public cell table. The report preserves its columns, threshold and scalar maximum-value shape; the maximum may now expose infinity. A separate message explains undefined/nonfinite cells. Ordinary finite statistics retain their previous threshold behavior.

The original six-unit public API fixture has two controls for two regressors and cohort-only clusters. Its mathematical pre-effect and variance are zero. It remains in frozen-baseline contract evidence, where corrected zero ATT/SE must produce an undefined statistic and YELLOW caution. The public API success fixture now supplies additional controls, clusters spanning cohorts and deterministic seeded outcome noise; GREEN assertions and report/model thresholds are retained, with an additional positive finite pre-SE assertion.

Fully zero-SE multiplier-bootstrap tables keep undefined simultaneous critical values and bands (NaN), without taking maxima and quantiles of an all-NaN distribution. The nondegenerate bootstrap path and draws are unchanged; this does not supply a joint test for a degenerate design.

Public signatures, data contracts and pre-fit raw diagnostics are unchanged. The seven sensitivity exclusions, statistical thresholds and test assertions are not weakened. Sensitivity, general simultaneous-band validity, general nonconstant numerical conditioning, marginal Gaussian oracles, standalone Sphinx and release validation are outside B14.

Verification is recorded in [tests](B14_DID_TESTS.md), [contract/reference](B14_DID_CONTRACT.md), [independent review](B14_DID_REVIEW.md) and the [block report](BLOCK14_DID_NUMERICAL_ZERO.md).
