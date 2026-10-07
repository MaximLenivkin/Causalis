# B17 — Gaussian propensity and compound shared-U means

B16 baseline `aaeadd8`. B17 fixes binary treatment `m`, IV `r_z0/r_z1`,
IV joint `g_z0/g_z1`, and two-part Tweedie `g0/g1/cate`. Source checkpoint and
committed integration/CI results are recorded after the source commit below.

## Target and identification

Reference law is independent `U ~ N(0,1)`, including when `generate(U=...)`
supplies different realized values. Binary `m = E[sigmoid(a_d(X)+s_d U)]`;
IV `r_z` adds the calibrated intercept and `first_stage*z` before integration.
Observed assignment propensity, generated `D/Y/Z`, score bounding, sharpness,
calibration and instrument `m` retain their original meanings.

IV nonlinear `g_z` integrates
`(1-p_d(U))*h(a_y(X)+s_y U) + p_d(U)*h(a_y(X)+tau(X)+s_y U)`.
Tweedie integrates `sigmoid(a_zi(X)+d*tau_zi(X)+s_zi U)` times
`exp(clip(a_y(X)+d*tau(X)+s_y U,-20,20))` over the **same U**.
These are joint means; a product of separately marginalized factors generally
has a different value. For continuous IV outcomes the exact identity is
`g_z = a_y(X) + tau(X)*r_z`, because `E[U]=0` and `tau(X)` is independent of U.
The unconfounded IRM identification guard is unchanged. This block does not
add identification for latent-confounded ATT, arbitrary supplied-U laws or
selection-conditioned outcome means.

## Numerical policy

`m/r` and cases with only one latent link use the B16 Gaussian helper unchanged.
The new private [_gaussian_joint.py](../causalis/dgp/_gaussian_joint.py)
uses `quad_vec` on `[-12,12]` for two active latent links. It supplies logistic
transition neighborhoods, exponential clipping boundaries, zero and the tilted
Gaussian mode as breakpoints. Near-identical knots coalesce at 32 floating-point
epsilons. Each component is normalized by a candidate log-integrand peak.
Backend max-norm estimated absolute error must be finite, <=1e-11, and the
backend must report convergence. In natural units that estimate is multiplied
by the row's exponential scale. This is **not** a rigorous error certificate,
nor a universal relative bound for rare probabilities or very narrow overlaps.

Omitted Gaussian mass is <3.6e-33: natural absolute tail bounds are <3.6e-33
for binary products and <1.75e-24 for clipped exponential products. This does
not establish relative precision when those tails dominate a rare target.
At most 32 distinct rows are integrated together; `limit=4096`, 1MiB backend
cache. Working storage is O(n) plus bounded per-batch integration state.
Real finite inputs, convergence and natural response ranges are checked.
Unresolvable logistic/clipping transitions, unsupported float geometry or
backend failure raise `ValueError`; no fixed-GH or product-of-marginals fallback.
Finite extreme strengths need not be supported: compound transitions below
floating-point resolution are rejected; tests cover both signs through 1e6.
Single-link B16 extreme support remains unchanged. No RNG draws occur here.
Backend parameter meanings and estimated errors follow the official
[SciPy quad_vec documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.quad_vec.html).

## Compatibility and migration

Public signatures and output schema/dtypes are preserved. `num_quad` in
`oracle_nuisance` remains accepted and must convert to a positive integer;
it no longer selects the integration order for any nonlinear oracle. Propensity
callables and generated `m` now use the same adaptive method. Tweedie remains
unsupported in `oracle_nuisance`; this block adds no such public API.

`r_z/g_z` corrections propagate to `iv_first_stage`, `iv_reduced_form`,
`late_x` and `late`, with their existing denominator policy unchanged.
Even continuous `g_z` can change by roundoff when replacing the old GH summation
with its exact Gaussian identity. Zero-strength paths retain old arithmetic.
Callbacks must define deterministic functions of X. IV `_r_by_z` now evaluates
one treatment score instead of31 per z; active `_g_by_z` evaluates one treatment
score and two outcome locations instead of31 and62 respectively. Stateful or
random callbacks can therefore change call counts, values and future RNG;
there is no blanket equivalence claim for them. Binary/Tweedie callback counts
are preserved in the measured comparisons. Failed generation does not roll
back RNG or callback side effects, including internal binary oracle computation
when `include_oracle=False`.

## Verification

All verification is root-run; no subagents or corporate data tools used.
Only synthetic observations are held in memory; saved probes contain configs,
aggregate errors/counts and hashes, without generated individual rows.

- Final public module:57cases; exact frozen B16 classes:45failed/12passed,
  no errors/skips. Failures represent numerical/callable disagreements, not
  45 independent bugs. [Baseline runner](run_block17_baseline.py) rebinds exact
  Git-blob classes and their actual parent class; baseline test hash is recorded.
- Focused two modules:90passed, no errors/skips/warnings,22.38s.
  [Public tests](../tests/data/test_gaussian_propensity_joint_means.py) use scalar
  adaptive Gaussian references with independently constructed knots;
  [policy tests](../tests/data/test_gaussian_joint_accuracy_policy.py) cover
  invalid inputs, failure estimates, unresolvable geometry, sign dependence,
  storage batches, duplicate/order restoration and legacy num_quad validation.
- Neighbors:1449passed,2existing warnings,32.49s. This preceded the final scalar
  reference tolerance refinement; library bytes were final. Committed broad
  integration below checks the final test bytes.
- [Probe](probe_block17.py):90configs x2generations=180 exact frame/schema/dtype,
  calibration/metadata/full RNG state/next10 pairs, excluding corrected oracle
  columns and their named IV derivatives. Deterministic nonlinear callbacks,
  heterogeneous tau, score bounding/sharpness, calibration and oracle on/off.
  Derived IV fields are separately checked against their unchanged algebra.
  52 independent joint scalar references: max binary abs1.67e-16, max gamma
  rel9.82e-11 (narrow opposite-slope overlap at strengths1e6). This is measured
  evidence on these configs, not a uniform relative certificate.
- B16 stress repairs: binary m/Tweedie abs error .0935195 removed to floating
  precision; IV joint z0/z1 errors .0734161/.0747962 removed to floating precision.
  [Probe manifest](block17_probe_result.json) records actual values, hashes,
  original process HEAD/time and unchanged methods/dependencies.

Source changes: new private helper plus binary and IV base files. B16 Gaussian
helper, shared DGP base, multi generator, observed sampling methods, calibration,
IV potential means and sensitivity sources remain byte/AST unchanged as
applicable. Source/tests are frozen before committed integration.

## Remaining scope and handoff

No new multi oracle API, Tweedie nuisance API, latent-selected ATT, sensitivity,
Sphinx/release gate or performance guarantee is claimed. Adaptive compound
integration can be slower than fixed GH; no benchmark was performed.

Next independent B18: learner output shape/real/complex and IV storage contracts,
then extreme finite score/IF, normalized custom ATE, duplicate/snapshot/refit
and standalone Sphinx backlog. Repeated/group cross-fitting, external OOF and
DR/R-CATE remain subsequent feature blocks. Sensitivity and SC08 LOO deferred.
Stop at B17; B18 starts with a new user request after context cleanup.
