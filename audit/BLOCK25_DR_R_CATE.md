# B25 — DR/R CATE

## Contract fixed before implementation

Baseline `ebf940f76ec81317a2a59ff6a52880473a23f581`, personal branch
`codex/correctness-roadmap`. This block adds effect prediction; held-out
validation is the following block. Existing IRM scalar inference, lazy
T-learner, sensitivity and external/cluster/repetition guards are preserved.

Target: tau(x) = E[Y(1)-Y(0) | X=x] for binary treatment, iid observations,
consistency, conditional exchangeability and overlap. With a restricted final
regression class this is an approximation/projection, not exact recovery.
Binary outcomes use the risk-difference scale. No individual counterfactual,
automatic calibration, standard errors, confidence intervals, rate/coverage
or superiority claims.

Public API: `DRLearner(ml_tau=None).fit(fitted_irm).predict(X)` and
`RLearner(ml_tau=None).fit(fitted_irm).predict(X)`, exported from
`causalis.scenarios.uplift`; default LinearRegression. The source is an internal,
single-partition, unweighted, iid IRM with clipping and nonempty confounders.
ATE/ATTE and normalize_ipw settings do not change this conditional target.
External OOF, repeated, grouped, overlap-drop and custom-weight fits reject
before final learner methods. These extensions need their own target and
validation contracts. No nuisance retraining and no split RNG draw.

DR uses unnormalized AIPW pseudo-outcomes from OOF g0,g1,e. R uses
q_hat = (1-e_hat)*g0_hat + e_hat*g1_hat, residual Y-q_hat and D-e_hat,
fitting their ratio with sample_weight=(D-e_hat)^2. This derived q avoids a
fourth nuisance learner, but inherits error in all three pilots. R's regression
adapter must support and honor sample_weight and squared loss; regularization
and weight normalization follow the supplied estimator. No fallback to an
unweighted fit. Require 0<e_hat<1 and finite real arrays/targets/weights before
fit; no extra clipping, target normalization, or silent row removal.

Honesty: each pseudo-outcome uses nuisances trained without its IRM fold.
The final model pools those targets and trains on all rows. Prediction on
training rows is in-sample for the final stage; ordinary CV of precomputed
targets can leak through nuisance training. Independent validation or nested
outer refits of the entire pipeline are required for evaluation/tuning. This
implementation does not claim Kennedy's independent-sample theorem or a
specialized honest forest/local-polynomial construction. The caller must keep
preprocessing/tuning within the corresponding nuisance training folds; IRM
cannot certify hidden preprocessing done outside its learners.

Fit validates the current sample/index/roles against the IRM snapshot, even
without diagnostics; detaches arrays, clones the final learner and publishes
only after success. Failed refit retains the previous fitted predictor; later
IRM/data/config mutations do not change it. Scoring DataFrames require unique
columns and all fitted feature names, reorder to fitted schema and ignore
extras; ndarrays are positional (1D means one row). Real finite float-convertible
features only; complex/object-complex rejects before casting. Empty batches
return an empty vector. Prediction outputs require one real finite value per
row, optionally a single column; binary CATE predictions are not forcibly
bounded to [-1,1]. Supplied estimator objects and public fitted attributes
remain mutable; no concurrency/crash/hostile-callback guarantees.

Alternative considered: extend IRM.predict_cate(method=..., ml_tau=...). That
would mix scalar configuration and lazy mutable caches with fitted effect
models. Separate composable estimators keep the final regression lifecycle and
feature schema local, reuse existing OOF fits, and leave the T-learner intact.
Cost: fit expects an IRM, not sklearn's ordinary X/y contract; generic
cross_val_score/Pipeline cannot evaluate the whole causal pipeline directly.

Primary references checked on 8 October 2026:
[Kennedy, DR learner, Algorithm 1](https://arxiv.org/html/2004.14497v5#S4),
[Nie–Wager, R loss and weighted regression](https://arxiv.org/html/1712.04912v4).
Pooled OOF regression is our explicit implementation choice; no numerical/API
equivalence to a third-party library is claimed.

## Verification plan

Independent finite-support conditional moment checks for DR robustness and R
population loss; direct residual-design least-squares oracle rather than only
mirroring transformed-target formulas; fold-exclusion spies; new-data synthetic
oracle recovery; input/numerical/schema and refit lifecycle checks. Then adjacent
IRM/uplift regressions, committed correctness with the seven existing sensitivity
exclusions, strict standalone Sphinx, six CI configurations with raw artifacts.
Only synthetic observations; clean exact owned temporary paths after use.

## Results

Implemented in `causalis/scenarios/uplift/learners.py`, exported by the uplift
package, with README usage and corrected scenario table. Existing library
algorithms/workflows/test selection unchanged; the only edited existing
library file is the uplift export list. Four non-audit paths in total.

[Focused result](block25_focus_result.json): **584 passed**, zero failures,
errors or skips, **64 warnings**, **30.47 s**; **124 new cases**. Working-tree
source hashes recorded against baseline HEAD, before the source commit.
[Focus log](block25_focus_tests.log), [runner](run_block25_focus.py).
Conditional finite-support potential-outcome contrasts independently verify
DR robustness when either nuisance is correct, including binary risk
contrasts, and a both-wrong negative control. R is checked against a direct
residual-design least-squares solve, with binary/continuous outcomes and both
diagnostic settings. Constant models recover different ordinary/overlap-weighted
projections. Noiseless predictions recover the known effect on new covariates;
this is an algebraic recovery check, not a performance or coverage benchmark.
Fold spies prove held-out outcome predictions exclude their training rows and
that the effect fit does not retrain nuisances or use the lazy T cache. Default
final fits leave global RNG state unchanged. Source scalar estimates and cached
T-learner predictions are exactly preserved in two lifecycle checks.

Other regressions cover ATE/ATTE and normalized/unnormalized scalar settings,
cloned estimators/owned arrays, frozen schema after source refit, failure retention,
real finite scoring and outputs, binary predictions beyond [-1,1], empty batches,
unsupported contexts (including actual external manifest fits), fit-time settings,
modified source/index/roles, mandatory R weights and numerical overflow/underflow.
Initial unrecorded development run: 14 failed /95 passed, caused by test fixture
API mistakes (score belongs to estimate; CausalData fields differ from properties).
An added empty-feature fixture first failed because IRM already forbids empty X;
then the guard order was made explicit after source mutation. These intermediate
focus logs were overwritten by the final recorded run and are not final evidence.

Final review added eight complex-source-mutation regressions: all **8 failed**
before the raw-value correction (116 deselected,4 warnings,21.67s). Real-valued
casts in IRM could discard zero-imaginary complex dtype, or raise an unhelpful
TypeError for object-complex values. New learner validation now rejects both
before that cast, without editing IRM's old path.
[Pre-correction result](block25_complex_baseline_result.json) records source/test
hashes and [log](block25_complex_baseline_tests.log); all eight now pass in the
final focused run. Baseline here means this block's pre-correction working tree,
not the B24 commit (which has no new learner API).

Committed correctness, standalone docs, CI and final root verification pending.

