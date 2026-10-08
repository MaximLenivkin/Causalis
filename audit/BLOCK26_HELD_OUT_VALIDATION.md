# B26 — held-out nuisance and CATE validation

8 October 2026, branch `codex/correctness-roadmap`.
Baseline `48761037fcbceae8d3aaaf2cc5595d481e63eca6` (completed B25).
Implementation and final gates: pending below while this block is in progress.

## Target, design and interface

The target is tau(x)=E[Y(1)-Y(0)|X=x] under consistency, conditional
exchangeability, overlap and iid observations. The validation sample must be
independent of training, preprocessing and tuning. Observed data do not expose
individual treatment effects or CATE MSE. Nuisance predictive diagnostics and
surrogate CATE criteria are descriptive; this block adds no CATE intervals,
calibration test, causal identification test, rates or superiority theorem.

Sequential alternatives, using the codebase-design skill:

1. A stateless function accepting prediction arrays: small and flexible, but
   every caller must manage fit lineage, sample disjointness, feature alignment
   and numerical/prediction contracts. It cannot tell training predictions from
   independent predictions.
2. An owned validator fitted from an internal IRM: concentrate training-only
   nuisance refits, cloned DR/R learning, identities/schema, ownership and metric
   calculation behind `fit(irm).evaluate(data)`. It supports the independent
   sample path with no change to existing IRM algorithms. Chosen.
3. A nested-CV pipeline orchestrator: handles outer splits and preprocessing but
   requires a larger factory/transformer/tuning protocol. Deferred; documented
   manual whole-pipeline outer refits and tested that actual training calls
   exclude every outer validation row. No honest-CV certification for arbitrary
   callbacks or preprocessing.

```python
from causalis.scenarios.uplift import HeldOutCATEValidation, RLearner
validator = HeldOutCATEValidation(learner=RLearner()).fit(irm)
metrics = validator.evaluate(validation_data)
```

The template is DRLearner by default or an explicit DRLearner/RLearner. The
validator clones and fits the CATE learner on the source's OOF signals. IRM
retains predictions but discards nuisance fold models; the validator separately
refits clones of the **current** ml_g/ml_m templates using only full training
observations (arm-specific outcome models). These evaluation pilots are not
those discarded fold models and are not guaranteed to reproduce their accuracy.
Current templates are an explicit caller choice; no historical template identity
or hidden preprocessing lineage can be certified. Binary constant-outcome arms
reuse the existing constant model adapter. Shared scoring/prediction/IRM guards
are reused; no generic dependency layer is added.

Supported sources match B25: already fitted internal single-partition iid
unweighted binary IRM, clip overlap, nonempty features and interior OOF
propensities. Actual fit context/sample/roles are checked; repeated, cluster,
external, drop, custom-weight and changed-sample sources reject. Both source and
validation declare stable unique nonmissing user_id values; validation IDs must
be disjoint. Reused RangeIndex positions are permitted. Caller identities can
be relabelled and cannot prove independence. Role and feature sets must match;
feature order is frozen from training. Validation requires both treatment arms,
finite real observations and one finite real prediction per row. For binary
training outcomes, validation 0/1 constants are accepted and other values reject.
No learner methods are called before applicable source/sample guards. Evaluation
calls predict only, never fit. All model fit/predict inputs are owned copies;
source IRM, templates and lazy T cache are not changed. Failed refits retain the
previous complete validator. Later source mutations/refits do not change it.
Public model attributes and malicious shared callbacks remain mutable; no
thread-safety or crash-durability guarantee is claimed.

## Metrics and interpretation

`CATEValidationResult` is a frozen dataclass containing aggregate counts,
arm-specific factual outcome MSEs, raw propensity Brier/log loss/range and
clipping count, mean CATE/DR signal, DR loss, zero-effect DR gain and R loss.
No row outcomes, scores, features or residuals are returned.

Let e be raw propensity clipped at the IRM's fit-time overlap threshold and
phi=g1-g0 + D*(Y-g1)/e - (1-D)*(Y-g0)/(1-e).
DR loss is mean((phi-tauhat)^2); gain is mean(2*phi*tauhat-tauhat^2).
The latter computes zero-effect loss minus candidate loss directly without
subtracting two squared losses that share the signal-squared term.
R loss is mean((Y-q-(D-e)*tauhat)^2), q=(1-e)*g0+e*g1.
The marginal pilot is derived, not separately fitted.
Raw propensity predictions outside [0,1] reject rather than silently repair.
Brier/log loss use raw probabilities; log arguments alone bound at float machine
epsilon. Overlap clipping is reported and only affects causal signals. At
threshold zero, boundary propensities reject; overflowing arithmetic rejects.
There is no arbitrary additional causal clipping or row dropping.

Arm MSEs apply to X|D=arm, not both counterfactual surfaces across all X.
With correct e or both correct outcome pilots, *unclipped* phi has conditional
mean tau; independent fixed-candidate DR loss differences then equal differences
of unweighted CATE risks. Its absolute value includes pseudo-outcome noise.
With oracle e/q, R excess loss weights errors by e(X)*(1-e(X)). Estimation
errors, active clipping and confounding can bias criteria. Only compare the
same validation sample with the same actual evaluation pilots; independently
refitted random pilots are not automatically comparable. These identities are
our algebraic interpretation, not a theorem certification for this API.

Primary method sources: [Kennedy DR learner](https://arxiv.org/abs/2004.14497),
[Nie–Wager R loss](https://arxiv.org/abs/1712.04912). They motivate the signals;
this independent-validation API does not claim numerical/API equivalence to
another implementation or all assumptions of their rate results.

Validation-driven model selection consumes this sample. Final assessment needs
a new independent test, or nested outer refits of preprocessing/IRM/CATE and
training-fitted transformations on the held-out part. Ordinary CV of signals
computed once on all rows can leak. The API does not orchestrate nested CV.

## Development and verification

Synthetic fixtures only; no client records, identifiers or attributes were
queried or downloaded. All local rows in tests are generated synthetic data.
No auth/environment install/fork reset, subagents, upstream/main/force push,
PR/release, notebooks/website or external messages.

Initial 89 new cases: 6 failed /83 passed /23.47s. Four failures used an
unrealistically tight 1e-24 tolerance around a floating-point R loss of 1; two
fixtures attempted fractional assignment into an integer pandas3 outcome
column. Fixtures corrected, with explicit float casting and 1e-12 tolerance.
No runtime-source correction was needed for these fixture failures.
The first focus-runner launch failed before pytest because automatic adaptation
produced a nonexistent test filename; the audit runner filename was corrected.
Development stdout is retained as `block26_development_tests.log`; final focus
and integration evidence below are separate.

First adjacent focus: 1 failed /684 passed /64 warnings /31.43s. The
scalar-preservation test referenced nonexistent CausalEstimate `ate`/`std_error`
fields; corrected to actual public value and absolute CI fields. Raw log:
[initial focus](block26_initial_focus_tests.log). A subsequent focus with 102 new
cases passed686/64warnings/32.48s; final enhancements added explicit propensity
fit spies and a training-only StandardScaler to the outer-refit example, then
reran the focus against final source bytes.

Final focused checks: **686 passed**,102newcases,0failures/errors/skips,
64warnings,32.48s. [Runner](run_block26_focus.py),
[result](block26_focus_result.json), [raw log](block26_focus_tests.log).
Oracle moments/noise/risk differences, factual sklearn metric comparisons,
binary/constant outcome pilots, explicit external/repeated/cluster/drop/weight
rejections, raw complex/nonfinite/shape/probability/overflow guards,
identities/roles/feature order, source snapshots, prediction ownership,
failed-refit retention/replacement, clone semantics, global RNG and old scalar/T
preservation are covered. Outer refits test three outer folds: 9 outcome/effect
fit calls and4propensityfit calls per fold, none using held-out features. The
outer StandardScaler fits only that outer training part. No Monte Carlo,
performance or empirical inference claim.

Final committed integration, docs, CI, root verification and owned cleanup: pending.

## Boundary

Next B27: inference families, beginning with estimand/assumptions and supported
fit/evaluation contexts. Sensitivity rewrite/full release, SC08 LOO, selected-U
ATT, multi/IV repetition/grouping, few/multiway clusters and NumPy/RST doc debt
remain separate. Stop after completed B26 for context cleanup; do not start B27
until the user's next request.
