# B29 — HonestDiD-style trend restrictions and conservative projection

Baseline `d88299887f96bd032fe3533349b2e2eb28ecf4ef`; implementation
`d54269201e8ab6c9fd44e01a506d868d1b61f472`; final source
`2c63f8d73c5d6f3ca15c4ca17ab0c1beb296f720` changes only the numerical
adapter test's tolerance. Branch
`codex/correctness-roadmap`, personal fork MaximLenivkin/Causalis.
Source changes: README, DiD exports, one new module, one new test module.
Existing CSA estimation, covariance, aggregation and diagnostics are unchanged.

## Statistical contract established before implementation

For ordered event coefficients beta, normalize the omitted common reference
at event time -1 to zero. Write beta = tau + delta, where tau_pre = 0
(no anticipation) and delta is the counterfactual untreated treated-control
trend gap relative to the same reference. Target theta = l' tau_post for a
fixed, explicitly supplied post contrast; the default selects time 0.
No heterogeneous-cohort event aggregation is silently interpreted as one gap.
The population and comparison set must remain common across coefficients.

Two population restriction sets follow Rambachan and Roth:

- **smoothness**: every consecutive second difference of delta, across pre,
  reference and post periods, has absolute value at most M. M=0 permits an
  arbitrary linear gap. M has outcome units per event-step squared.
- **relative_magnitude**: each absolute post first difference is at most
  Mbar times the largest absolute pre first difference, including the final
  pre-to-reference difference. Mbar is dimensionless. Mbar=0 imposes zero
  post violation, while leaving pre violations unrestricted.

Primary sources read before choosing the estimator:
[Rambachan–Roth paper](https://jonathandroth.github.io/assets/files/HonestParallelTrends_Main.pdf),
[authors' smoothness implementation](https://github.com/asheshrambachan/HonestDiD/blob/master/R/deltasd.R),
[authors' relative-magnitude implementation](https://github.com/asheshrambachan/HonestDiD/blob/master/R/deltarm.R),
[authors' fixed-length implementation](https://github.com/asheshrambachan/HonestDiD/blob/master/R/flci.R).
Restriction definitions agree with these sources, after translating their
normalized reference to event time -1. No original conditional/hybrid/FLCI
algorithm or R numerical parity is claimed. No client observations were used.

**Inference method: bonferroni-projection.** For p reported coefficients, let
q = normal.isf(alpha/(2p)), and construct the rectangle
beta_j in [beta_hat_j - q se_j, beta_hat_j + q se_j]. Project the rectangle
and the selected population restriction onto l' tau_post. This is a
conservative HonestDiD-style interval, not the original R package's optimized
interval. Off-diagonal covariance is validated but does not narrow the box.
Singular covariance is allowed if all marginal variances are positive.
Covariance means covariance of the estimates, not observation-scale IFs.

Validity argument: with asymptotic probability at least 1-alpha, every true
coefficient belongs to this rectangle, by marginal Gaussian limits and the
union bound. If the true delta also satisfies the restriction and tau_pre=0,
the true theta is feasible in the projection and therefore belongs to its
interval. This proof does not replace a valid underlying DiD design, normal
limits or consistent variances. Bounds, contrasts and analysis axes must be
prespecified. Fixed-dimension asymptotic coverage is the claim; no finite-sample,
few-cluster or arbitrary growing-dimension guarantee is made. Clipping bias,
misspecified nuisance models, selection and invalid comparison populations are
not repaired. Generic arrays do not certify the causal interpretation.

For relative magnitudes the projection hull has an exact closed form. The
maximum possible pre slope over the rectangle is attained at a pair of
adjacent corners (with reference fixed to zero). For signed post weights,
post-gap variation is Mbar times this maximum times the sum of absolute
reverse cumulative weights. Add the post rectangle's support radius. This
accounts for uncertain pre-trends; it is not a plug-in estimate of their max.

For smoothness, insert the zero reference and impose all second-difference
inequalities. Two unrestricted-sign LPs minimize/maximize l' delta_post,
with pre coordinates bounded by their confidence intervals. Post beta remains
free in its rectangle, giving the additional signed-contrast support radius.
This permits signed weights, multi-period targets and restrictions on pre
curvature. Infeasibility yields an explicit empty confidence set: a confidence
rectangle incompatible with the model, not a significant treatment effect.
No scalar p-value, ordinary-interval fallback or fabricated point estimate is
returned. Solver errors and failed endpoint checks raise RuntimeError.

Numerical limits: common physical and contrast scaling precedes LP arithmetic.
HiGHS primal/dual feasibility tolerances are 1e-9; returned primal feasibility,
dual stationarity, dual signs and objective gap are checked at 1e-8 scale.
Endpoints have ordinary float64 numerical tolerance, not formally certified
real-arithmetic enclosures. Nonzero normalized smoothness bounds or marginal
radii below 1e-8 are unsupported and fail explicitly. Overflow, lost nonzero
normalization and endpoint underflow also fail. Exact M=0 remains supported.
Covariance symmetry/PSD uses relative 1e-10 validation tolerance, without
repairing covariance or using its off-diagonal values. No extra dependency.

## Interface and alternatives

Applied codebase-design skill from
`/Users/m.lenivkin/.agents/skills/codebase-design/SKILL.md`;
sequentially considered two designs, without subagents.

1. Add robust-bound kwargs/output to CSA estimate/event aggregation. This
   couples one cohort's trend restrictions to heterogeneous event aggregation,
   varying pre bases and existing scalar inference/result contracts.
2. Chosen: standalone owned HonestDiD with explicit coefficient/covariance/time
   contract and a pure, narrow existing-result adapter. It centralizes rectangle
   projection, restrictions, solver checks and failure semantics. Existing
   callers and model state do not change; the adapter enforces supported data
   interpretation before constructing the generic object.

```python
from causalis.scenarios.did import HonestDiD

owned = HonestDiD(coefficients, estimator_covariance, [-3, -2, 0, 1])
result = owned.infer(restriction="smoothness", bound=.2,
                     post_weights=[.5, .5], alpha=.05)
result.confidence_set       # ((lower, upper),) or ()
result.set_type             # bounded / empty
result.contains(0.)         # closed endpoint membership
result.summary()            # fresh aggregate-only DataFrame
snapshot = HonestDiD.from_did(csa_result)
snapshot.infer(restriction="relative_magnitude", bound=1.)
```

Inputs are copied; immutable result fields are scalars and tuples. No raw unit
records, influences, identifiers or optimization iterates are returned.
Constructor requires consecutive integer pre times ending -2 and consecutive
post times starting 0, omitting -1. At least one pre/post coefficient is needed.
Positive marginal variances, real finite arrays, PSD covariance, finite scalar
parameters and finite nonzero correctly shaped post weights are validated.
Time spacing is one step; no interpolation or irregular-spacing assumption.
Weights need not be nonnegative or sum to one. Initialization stores O(p)
owned values/SEs after O(p^2) covariance storage and an O(p^3) eigensolve; smoothness
uses O(p^2) constraint storage and two LP solves. Relative projection is O(p).

`from_did` accepts only actual CallawaySantAnnaDIDEstimate results with:

- universal base, zero anticipation, pre coefficients, never-treated controls;
- one cohort, iid inference, equally spaced calendar periods, common reference
  immediately before treatment and unique cells/IF columns/unit IDs;
- diagnostic_data=True and identical complete treated/control memberships in
  every selected cell, with both groups present.

It aligns columns to sorted event cells and owns a snapshot. Source IFs are
centered and use CSA's existing iid covariance convention sum(IF^2)/n^2
(ddof=0/n), not InferenceFamily's ddof=1/n. Small empirical centering differences
are numerical; adapter tests match actual CSA SEs. No fitting, estimating,
prediction callbacks, source cache mutation or RNG consumption. Later source
edits do not alter inference; prior manual edits to public result arrays cannot
be certified. Clustered, varying-base, staggered-cohort, incomplete/changing
population and missing/corrupt diagnostic inputs are rejected. Generic input
cannot be used to bypass these assumptions with the same coverage claim.

## Reproducible verification

Final 190 new cases include:

- 72 analytic one-pre projections, two restrictions, three bounds, four signed
  contrasts and three outcome scales 1e-80/1/1e80;
- 27 independent two-pre smoothness vertex enumerations without an LP solver;
- 9 relative-magnitude corner/slope enumerations and explicit distinction
  between M=0 linear extrapolation and zero post violation;
- nested bounds; outcome/sign/contrast transformations; covariance/input/result
  ownership; singular valid covariance; raw/object complex and finite guards;
- actual CSA result/SE alignment with fit/estimate callback bombs and unchanged
  NumPy global RNG, later result mutations and stable copied inference;
- real unbalanced/staggered fits rejected, 15 corrupted/unsupported-result
  cases, missing/shifted calendar metadata, solver failures and independent
  primal/dual certificate corruption, tiny-bound/overflow/scalar-tail guards;
- 250 correlated Gaussian draws for each restriction, seed915, with nonzero
  valid population violations, coverage gate >=.94. These are finite numerical
  smoke checks, not a proof of estimated-nuisance or finite-sample coverage.

Development history is retained rather than overwritten:
[initial](block29_development_tests.log): 176passed/1failed, a fixture attempted
assigning .5 into an integer pandas column before API invocation. Fixed the
fixture to use float. [intermediate](block29_development_final_tests.log):
177passed. [expanded](block29_development_complete_tests.log):186passed/1failed,
a fixture attempted constructing a gapped PanelDataDID, which the existing
contract already rejects. Replaced it with an explicitly mutated result to
exercise the adapter's own calendar check. Neither failure indicated an
analytic-projection discrepancy. [Precommit](block29_precommit_tests.log):
190passed/5.66s. Actual source implementation was committed only after this pass.
Raw JUnits remain in ignored, separately named current-run runtime directories.

Initial committed local gates on d542692 (before portability correction):
[focused manifest](block29_initial_focus_result.json): 420passed, 190new, 3warnings,
31.71s. [Correctness manifest](block29_initial_integration_result.json):4282passed,
157warnings,153.57s,0failures/errors/skips. [Selection](block29_initial_integration_selection.json)
retains exactly the same seven deferred DML sensitivity modules. All 4092
B28 case IDs remain present; precisely 190 new IDs belong to test_honest_did.
[Standalone strict Sphinx](block29_initial_docs_result.json):exit0/24.670s,
warnings-as-errors, no publishing. [Handoff check](handoff_validation.json):
167 immutable source links,issues[]. [Owned cleanup](block29_initial_cleanup_result.json)
removed exactly audit/block29_integration_test_temp/pytest-temp before runtime-folder renaming; focused
basetemp was not created. All JUnits and metadata remain available; no prefix
cleanup or client-data export. [Local root verification](block29_initial_local_validation_result.json)
exit0/issues[],151 existing source/workflow Python/YAML paths and186existing
Python test paths unchanged, plus the full four-path source diff guard.
[Initial CI37844628093](https://github.com/MaximLenivkin/Causalis/actions/runs/37844628093)
failed on all six Linux stacks, each4281passed/1failed with the same new adapter
oracle test. All six source/selection/case sets/JUnits/docs artifacts are verified
and retained in [initial CI manifest](block29_initial_ci_result.json).
Every strict Sphinx job passed. The failed test asserted bitwise dataclass
endpoint equality for algebraically equivalent scaled/unscaled covariance
products. The Python3.12 log records upper endpoints2.3120474494654175 and
2.312047449465418: one ULP, about4.44e-16, within float64 rounding.
[Actual initial failed logs](block29_initial_ci_failed_tests.log) and
[completed Python3.12 job log](block29_initial_py312_ci_failed_tests.log) are
preserved as failure excerpts. [Log manifest](block29_initial_log_result.json)
records hashes of excerpts and the complete originals retained under the ignored
initial CI runtime tree. CLI refused whole-run logs until completion; the completed-job
API provided the first evidence. No approval/authentication rejection occurred.

Portability fix commit2c63f8d uses assert_allclose rtol=atol=2e-12 for this
independent endpoint oracle and retains set geometry, CSA SE, ownership,
callback and RNG checks. No scientific formula, library path, old test or
case ID changed. [Focused portability test](block29_adapter_portability_tests.log)
1passed/4.32s. The full local/doc/CI gates are rerun on the new exact source;
initial evidence was renamed separately and never overwritten.
Final committed local gates on2c63f8d:
[focus](block29_focus_result.json)420passed/3warnings/36.66s,190new;
[correctness](block29_integration_result.json)4282passed/157warnings/166.63s,
0failures/errors/skips. [Selection](block29_integration_selection.json) retains
all seven old exclusions and all4092B28case IDs. [Strict standalone Sphinx](block29_docs_result.json)
exit0/25.165s, no publishing. [Final cleanup](block29_cleanup_result.json)
removed exactly the new current-run integration basetemp; focus basetemp again
was not created. [Final local root](block29_local_validation_result.json) checks
initial/final gates, all six historical failure artifacts and unchanged library
across the test portability correction. The first final-source root invocation stopped on the report's self-link to
its own not-yet-written local validation output. [Trace](block29_initial_root_link_checks.log)
is preserved; verifier now permits only its own expected output during input
checks and validates all links again after writing it. This was an audit
ordering issue, not a feature/test/Sphinx failure. [Final CI37845415092](https://github.com/MaximLenivkin/Causalis/actions/runs/37845415092)
completed/success on exact2c63f8d. [Final CI manifest](block29_ci_result.json)
verifies six4282passed JUnits,0failures/errors/skips, all six strictSphinx exit0,
full/focus case sets, source/environment, normalizedpytestargv/seven exclusions,
and five artifact hashes per job. SnapshotUTC2026-10-08T21:21:05.915966+00:00.
Actual Python versions: 3.10/latest: 3.10.22, 3.10/legacy: 3.10.22, 3.13/latest: 3.13.16, 3.11/latest: 3.11.17, 3.12/latest: 3.12.15, 3.14/latest: 3.14.8.
[Final root verification](block29_validation_result.json) --require-ci checks
all final gates and the preserved first six failures. Two actual CI runs;
the second follows a real portability-test source change, not an arbitrary
rerun. Six representative Linux stacks, not all dependency/platform combinations.
Source/tests frozen after2c63f8d. Both observers finished; no background CI jobs
remain. Ordinary pushesd882998..d542692 andd542692..2c63f8d succeeded under
existing authorization. Final audit-only checkpoint is gitlog-1; its push does
not retrigger the matrix. Clean tree and live local/remote identity are checked
at completion. No automatic approval review rejection occurred.

## Scope and boundary

B29 is the next separately authorized feature in FIX_PLAN; it does not resume
or modify the deferred upstream DML sensitivity rewrite. The existing seven
named exclusions remain explicit and unchanged. Original optimized HonestDiD
inference, cluster/staggered/varying-base adapters, sign/monotonicity variants,
combined restrictions and breakdown-value selection are outside this API.
No dependency refresh, login, client query/download, PR, release, notebooks,
website publishing, upstream merge or external messages. Existing explicit
«Разрешаю пуш в нашу ветку» authorizes ordinary pushes to the personal branch.
Stop after B29 completion; B30 policy costs/capacity requires the next user
request after context cleanup.
