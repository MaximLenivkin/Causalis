# B28 — weak-IV LATE: orthogonal AR tests and full Fieller sets

Status: completed; final source/local/docs/CI/root gates passed. Final audit checkpoint via git log -1.
Baseline `ab789bff3d03f6d2b20023c7d259adcdd8cc7019` (completed B27).
Initial source `856b05ca78a7127bdd342eb79cd9fda961aa6873`;
set-geometry correction `8aad3a07b96d174151bd7ef39bcaba05f7d98bfe`;
final source `b9110f0d24d3cc8a107883720d2e475f4317f085`.
Branch `codex/correctness-roadmap`, personal fork `MaximLenivkin/Causalis`.

## Design, target and assumptions

The existing IIVM estimates the ratio of orthogonal reduced-form and first-stage
means, then forms a Wald interval using division by the first stage. It rejects
an empirical denominator smaller than 1e-8. A strength warning does not repair
that interval's behavior under weak identification.

The new scalar procedure tests the moment E[phi_y - theta*phi_d] = 0 directly.
For a nonzero population first stage and valid binary-IV design, the ratio is
LATE among compliers. Required causal assumptions: consistency, conditional
instrument exogeneity, exclusion, monotonicity, and overlap. At zero population
complier share a unique causal LATE need not exist; the moment remains testable.
The method cannot establish identification or instrument validity from data.

Statistical assumptions: iid units, a valid null-score CLT, adequate moments,
positive limiting score variance and nuisance remainder negligible on the
sqrt(n) scale. Uniform weak-IV claims additionally require these conditions
uniformly over the sequence, including candidate-score nuisance convergence.
Arbitrary learners and cross-fitting alone do not establish those conditions.
Active clipping, nuisance misspecification, invalid IV and adaptive selection
can invalidate inference. There is no finite-sample coverage certificate.

Primary references consulted:
[Ma, orthogonalized AR for high-dimensional LATE, Algorithm 2.1](https://arxiv.org/html/2302.09756v5)
and [Mikusheva, inversion of weak-identification robust tests](https://economics.mit.edu/research/publications/robust-confidence-sets-presence-weak-instruments).
The implementation uses a scalar centered score with ddof=1, rather than the
paper's ddof=0 convention; these are asymptotically equivalent, not numerically
identical. It does not implement that paper's specific lasso tuning, prove
uniform learner conditions, reproduce its experiments or implement CLR/QLR.
The quadratic inversion and numerical boundary policy were independently derived
and tested against direct sample moments and known roots.

## Alternatives and selected interface

1. Add a method flag to `IIVM.estimate`, extending `IVCausalEstimate` with a
   disconnected set. This forces every existing consumer of its single
   lower/upper fields to understand new geometry and changes cache semantics.
2. Add a separate owned `WeakIVInference(phi_y, phi_d)` module, a pure fitted
   adapter, an immutable aggregate result, and a convenience IIVM method.
   Selected: geometry and failure handling stay together; existing scalar
   estimation, diagnostics and downstream consumers keep their behavior.

```python
from causalis.scenarios.iv import WeakIVInference
result = fitted_iv.estimate_weak_iv(alpha=.05, null=0.)
result.confidence_set  # tuple of closed interval components
result.set_type
result.contains(1.)
result.summary()
snapshot = WeakIVInference.from_iivm(fitted_iv)
snapshot.infer(null=2.)
```

Generic inputs are two aligned real finite observation-scale vectors (n,), n>=2.
They are copied and jointly scaled; no observation arrays are returned. The
caller supplies valid signals for the same independent units. Generic inputs
are not a workaround for unsupported clustered/weighted/repeated inference.

`from_iivm` supports fitted single-partition IIVM with current normalize_ipw=False
and truncate. IIVM has no cluster/weights/external OOF fit API. The adapter reads
successful-fit copied y/d/z and fitted g0/g1/m/r0/r1; it does not read live data,
fit/predict/estimate, draw randomness, mutate source state or construct diagnostics.
Later live-data edits do not change fit arrays; a snapshot survives later model
mutations. Public fitted-array mutation is not certified. Binary D/Z, real finite
aligned arrays, strict interior m and r probabilities in [0,1] are checked.
Normalized IPW requires a separate score/variance contract and is rejected.
Failed source refits remain unfitted under the existing IIVM lifecycle.

## Test and complete inversion

Let a=mean(phi_y), b=mean(phi_d), and V be the empirically centered sample
covariance of (phi_y, phi_d), divided by n, with ddof=1. For candidate t:

- q(t)=a-t*b;
- v(t)=Vyy-2*t*Vyd+t²*Vdd;
- statistic=q(t)²/v(t), p=2*normal.sf(sqrt(statistic));
- z=normal.isf(alpha/2); reject when statistic>z²;
- confidence set solves (b²-z²Vdd)t²+(-2ab+2z²Vyd)t+(a²-z²Vyy)<=0.

No first-stage division, pretest, finite grid, imposed effect bounds, multipliers
or pipeline refit occurs. Results preserve bounded intervals, two rays,
half-lines, singleton, all-real and empty sets. Infinite endpoints represent
unbounded components; `contains` accepts finite real values and includes
endpoints. Taking the minimum/maximum of a two-ray union would fill its excluded
gap and is invalid. Results contain aggregate means/test/set metadata only;
`summary()` creates a fresh one-row DataFrame.

Joint signal covariance may be singular: a constant nonzero first-stage signal
is supported. Zero empirical score variance at the requested null is an explicit
failure. Other zero-variance candidates retain the algebraic inequality in the
set without a coverage claim at those degenerate points. Wald SE/point estimates
are not manufactured for a zero denominator.

Arithmetic: float64, common signal scaling before squaring, centered covariance,
scaled null contrast, exact power-of-two polynomial scaling and stable root
formula. Exact float64 zeros determine linear/tangent cases; no tolerance erases
a small quadratic term. Near-boundary geometry remains finite-precision output.
Nonfinite scores/statistics, lost nonzero coefficients, false zero discriminants
from underflow, and unrepresentable finite roots fail explicitly. An extreme
difference between signal scales can still require an explicit failure; common
rescaling does not cure that difference or change statistical assumptions.
Work/memory are O(n) for two signals; inversion is O(1).

## Verification and development corrections

[Development log](block28_development_tests.log): initial 102 new cases,
2 failed /100 passed, 23.06s. One runtime error: arbitrary polynomial scaling
moved exact roots 1 and 2, excluding a mathematical endpoint in the two-ray
case. Corrected by binary scaling. One fixture error: assigning .5 into an
integer D array produced zero, so the nonbinary guard was never exercised;
fixture now retains raw floats. Initial raw JUnit is retained separately.
[Development rerun](block28_development_final_tests.log): 107 passed, 21.62s,
before adding the actual fitted zero-first-stage case and final underflow cases.
Counts are overlapping checkpoints, not additive tests.

Initial committed source856b05c: [focus](block28_initial_focus_result.json)
377 passed/16warnings/28.33s,108new; [integration](block28_initial_integration_result.json)
4089 passed/157warnings/136.29s; [strict docs](block28_initial_docs_result.json)
exit0/19.446s. These are preserved historical gates, not final-source evidence.
A subsequent independent [probe](block28_initial_discriminant_probe.json) found
that t*(t+1e-200)<=0 had become a false singleton after squaring the tiny linear
coefficient underflowed. Correction8aad3a0 rejects this arithmetic loss, with positive
and negative coefficient regressions. [Final probe](block28_final_discriminant_probe.json)
confirms explicit failure. No initial source was pushed alone.

Intermediate8aad3a0 passed379focused cases and4091correctness cases,
strictSphinx0/20.227s and all6CI artifacts4091passed each, run37813839790:
[intermediate CI](block28_pre_statistic_ci_result.json),
[intermediate integration](block28_pre_statistic_integration_result.json).
Final review found a nonzero squared statistic rounded to0 for null1e-200,
symmetric phi_y and constant phi_d. Finalb9110f0 explicitly rejects that
underflow, while retaining exact-zero test statistics. One new regression
[guard test](block28_statistic_guard_tests.log)passed before committing.
Because source changed, final local/docs/CI gates are rerun onb9110f0; the
intermediate CI is historical evidence, not the final gate.
First cleanup helper assumed focused basetemps existed and stopped before
any deletion; actual existence was checked and recorded. Initial/final8aad3a0
integration basetemps were exactly deleted, focused basetemps never created:
[intermediate cleanup](block28_pre_statistic_cleanup_result.json).
First root verification consequently failed on a not-yet-copied docs manifest;
[initial verifier log](block28_initial_validation_checks.log)retains this
orchestration failure. Later intermediate root exit0 verified source and raw
artifacts; no source/Sphinx/test failures were caused by that missing copy.

Final local gates onb9110f0:
[focus](block28_focus_result.json)380passed/16warnings/27.76s,111new;
[committed correctness](block28_integration_result.json)4092passed/157warnings/
135.30s,0failures/errors/skips; [selection](block28_integration_selection.json)
retains the seven sensitivity exclusions. All3981B27case IDs are retained.
[Strict standalone Sphinx](block28_docs_result.json)exit0/19.026s, warnings as
errors, no publishing. [Handoff validation](handoff_validation.json)163immutable
source links,issues[]. [Final cleanup](block28_cleanup_result.json)deletes only
current owned integration pytest-temp; focused basetemp was never created.
Raw JUnits/logs/source/environment evidence are retained. All previous owned
integration basetemps were removed separately; probe Matplotlib cache was
automatically deleted at process exit. [Final CI37815247713](https://github.com/MaximLenivkin/Causalis/actions/runs/37815247713)
completed/success on exactb9110f0; [CI manifest](block28_ci_result.json)verifies
all6artifacts4092passed/strictdocs0, full/focuscase sets, source/environment,
normalizedpytestargv/seven exclusions and5hashes/job. ActualPython3.10.22bothstacks,
3.11.17,3.12.15,3.13.16,3.14.8; snapshotUTC2026-10-08T17:21:31.077414+00:00.
Two actual CI runs; the second was necessary after a source/statistic guard
change. Neither run failed. Six representative Linux stacks, not all possible
platform/dependency combinations. [Final root verification](block28_validation_result.json)
--require-ci exit0/issues[], checks raw local/initial/intermediate/finalCI data
and owned cleanup; [local root](block28_local_validation_result.json)also passed.
Source/tests frozen afterb9110f0. Ordinary pushesab789bf..8aad3a0 and8aad3a0..b9110f0
succeeded under existing authorization; final audit commit is audit-only and
does not rerun CI. Final audit push/live local-remote identity and clean tree
checked at completion. No automatic approval review rejection occurred.

The 111 final new cases include independently known quadratic roots/all seven
geometries, direct ddof1 score/covariance/p-value oracles over 36 null/stage/scale
combinations, finite-endpoint equalities, near-zero and exactly zero first
stages, constant strong stage, coordinate transformations, ownership/results/
source/global RNG preservation, shape/raw-complex/nonfinite/scalar/variance/
overflow/underflow guards, actual production fitted adapter with callback bombs,
actual normalized fit rejection and failed-refit lifecycle. A real balanced
binary-IV fit has an exactly zero orthogonal first stage: old Wald refuses,
new score test returns a finite result without division.

Coverage smoke tests: Gaussian iid ratio moments, stage means0/.02/1,
1500 replications per regime,n80,seed810,broad acceptance gate .925..975;
binary monotone exogenous-IV oracle signals with latent U confounding D/Y,
complier share0/.02/.4,600replications per regime,n500,seed714,gate .92..98.
At share0 these check the structural moment, not an identified complier LATE.
Oracle pilots are known: this does not certify arbitrary estimated nuisance
coverage, high-dimensional rates or finite-sample/uniform validity. Actual
estimated-nuisance integration is checked separately against direct signals.

[Intermediate local root verification](block28_pre_statistic_validation_result.json)exit0/issues[]:
155 existing source/scripts/workflow files and 190 existing test files are
unchanged; all 30 existing IIVM methods retain identical ASTs. Five non-audit
paths change: README, IV exports, IIVM method, new weak module and new tests.
Only the new method is added; old IIVM fit/Wald/diagnostic algorithms are preserved.

Synthetic fixtures only. No client records, identifiers or attributes were
queried or downloaded. Sensitivity's seven existing exclusions remain separate
from correctness and are not a full release gate. No release/notebooks/website,
PR/upstream merge, dependency changes, login or external messages were requested.
User's persistent «Разрешаю пуш в нашу ветку» authorizes ordinary personal-branch
pushes. No subagents were used. Stop at completed B28; next block B29 HonestDiD
starts only after context cleanup and a new user request.
