# B18 — learner output contracts and IV storage

2026-10-07. Baseline `b7cbec9ead7c589fa6d4570c0e8f188d349c95be`.
Source checkpoint and committed integration/CI evidence are recorded below
after committing the frozen source and tests. Root implemented, reviewed and
verified the block; no subagents were used.

## Result and scope

IRM, MultiTreatmentIRM and IIVM reject malformed prediction geometry and
complex predictions before class selection, clipping, flattening or assignment.
Previously, scalar/one-row outputs could broadcast across a held-out fold,
row vectors could be flattened into apparently valid predictions, and complex
arrays lost their imaginary part during float conversion. This could produce
plausible finite estimates from invalid learner outputs. Other malformed
outputs failed later with NumPy indexing/assignment errors instead of an
explicit contract error.

The shared private helper validates the complete raw probability output,
including discarded columns. Float-convertible real values retain compatibility,
including numeric object arrays and numeric strings. Complex dtypes are rejected
even when imaginary parts are all zero; object arrays containing complex values
are rejected before conversion. Shape/type failures raise ValueError; non-finite
float values raise RuntimeError, preserving the B07 finite-output policy.

Supported learner outputs:

| Output | Accepted shape for n prediction rows |
| --- | --- |
| Regression/hard-label vector | `(n,)` or `(n, 1)` |
| Binary probability | `(n,)`, `(n, 1)` or `(n, 2)` |
| Multiclass propensity | `(n, K)` with matching class columns |
| Assembled IV nuisance | exactly `(n,)` for all six arrays |

Scalars, wrong row counts, `(1,n)` for n>1, multi-output regression matrices,
higher-dimensional arrays and extra binary probability columns are unsupported.
At n=1, `(1,1)` is the valid single-column representation. Helpers handle empty
outputs consistently; public fitting retains existing data/support requirements.
Available nonempty `classes_` must be one-dimensional and match matrix columns;
multiclass treatment labels must also be distinct. Missing binary metadata,
reversed class order, class-zero/class-one single-column mapping and direct
positive-class vectors preserve the existing adapters. The binary hard-label
fallback still uses the available column if real labels cannot convert to float;
it now validates geometry and rejects complex labels first. The stricter class
metadata check is an intentional migration for inconsistent custom classifiers.

IIVM validates each fold's five nuisance vectors before float assignment and
validates assembled raw arrays before clipping propensity. `fit()` validates
all six assembled arrays again before publishing fitted attributes, including
when `_cross_fit_nuisances` is bypassed. This closes infinity/complex/geometry
gaps in the old NaN-only assembly check. Prediction dictionary order is retained.
Failed refits clear fitted/inference state; earlier returned estimates remain
usable. Ownership, immutable snapshots and post-fit mutation policies are
unchanged and remain a separate task.

No score, estimand, normalization, trimming thresholds, identification assumptions,
split algorithm, data contract, DGP or sensitivity code is changed. Finite
out-of-range probability warning/clipping/normalization policies are retained.
This is output validation; finite inputs can still overflow subsequent score/IF
arithmetic, which belongs to the next block. No performance claim is made.

## Reproducible evidence

- [Final public baseline](block18_baseline_result.json): the final 356-case new
  test file on the exact B17 worktree gives **267 failed / 89 passed**, zero
  errors/skips. Failures include both silently accepted outputs and failures
  at the wrong boundary/type; they are not 267 independent bugs. The runner
  verifies baseline imports, pins the final test hash and removes its own
  temporary worktree. [Runner](run_block18_baseline.py),
  [JUnit](block18_baseline.xml), [log](block18_baseline_tests.log).
- [Final focused JUnit](block18_focus.xml): **460 passed**, zero failures,
  errors, skips or warnings, 31.80s: 356 new cases plus the unchanged 104-case
  B07 prediction contract module. Public fits exercise g/m/r, classifier and
  regression paths, both sequential and threaded cross-fitting, hard-label
  fallback and IV fold/assembled bypasses. Valid column/vector cases compare
  nuisance-based score and inference arrays exactly.
  [Log](block18_focus_tests.log). The earlier focused run was 417 passed
  before 43 extra metadata/class-order/empty/singleton cases; its artifacts are
  historical and are not the final test-set evidence.
- [Independent baseline compatibility probe](block18_probe_result.json):
  **20 exact valid fit pairs / 36 exact inference pairs** against actual Git
  blobs of B17 models and utility modules, with old import bindings explicitly
  substituted. Continuous/binary outcomes, three estimator families, jobs1/2,
  diagnostics on/off (where supported), ATE/ATTE/LATE, duplicate indexes.
  Nuisances/folds/point estimates/SE/p/CI/score arrays and source data agree
  exactly. Constructor signatures and unaffected functions are AST-checked.
  Synthetic rows remain in memory; only configs, counts and source hashes
  are stored. Original process HEAD/time remain in the manifest.
  [Probe](probe_block18.py), [log](block18_probe_checks.log).

## Integration and handoff

Pending committed integration and six-job personal-branch CI verification.
Seven existing sensitivity modules remain deferred. Standalone Sphinx,
release gates and extreme finite score/IF arithmetic are outside this block.

Next standalone **B19: extreme finite score/IF arithmetic and normalized custom
ATE near-boundary policy**. First reproduce failures through public fits/estimates,
establish the target/normalization and independently derive a stable calculation
or explicit failure policy. Avoid blanket `nan_to_num` or score clipping.
Then separate duplicate/snapshot/refit and standalone Sphinx gates, followed by
repeated cross-fitting → group cross-fitting → external OOF → DR/R-CATE features.
Sensitivity, SC08 LOO and selected-U ATT remain deferred.

Stop at B18 for context cleanup; B19 starts only on the next user request.
