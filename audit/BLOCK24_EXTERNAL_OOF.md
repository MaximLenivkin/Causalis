# B24 — binary IRM external OOF predictions

Baseline: `3668eec10a5cc794dd16be26d8ade6c284277bf4`. Contract fixed before
implementation. Status: complete; final source/local/CI gates verified; final audit checkpoint via gitlog-1.

## Contract

`IRM.fit(external_predictions=predictions, oof_manifest=manifest)` consumes
all three nuisance predictions `g0`, `g1`, `m`; partial substitution rejects.
One partition uses vectors `(n,)`; repetitions use matrices `(n, n_rep)`.
Series/DataFrame inputs must have the exact input index in order (duplicates
allowed); arrays are positional. Real finite float-convertible values only;
propensity and binary-outcome predictions must lie in [0, 1] before the
existing propensity clipping policy. External fits require `clip`.

`IRM.make_oof_manifest(predictions, *, folds, training_indices, split_seeds)`
builds and validates a detached version-1 manifest against current data and
configuration without fitting learners. Fold shapes follow prediction shapes;
integer IDs cover 0..K-1. `training_indices` is repetition -> fold -> positional
indices, recording the shared outer training sample. Each must be exactly the
held-out fold's complement, contain both treatment arms, and exclude every
held-out cluster if cluster_groups is supplied. Outcome nuisance learners use
the corresponding treatment subset of this outer training sample.

Manifest binds ordered row index, numeric X/Y/D contents, ordered role names,
prediction digests, cluster membership (or None), partitions and recorded
uint32 split seeds. Seeds describe supplied partitions; no partitions are
regenerated and random_state does not override them. External fit draws no RNG
and invokes no learner fit/predict/configuration methods. Full manifest checks
for all repetitions precede any fit publication. Successful fits own arrays
and manifest; failed refits retain the previous complete fit.

All preprocessing, feature selection, tuning and nuisance training must use
only the recorded outer training sample, with no held-out outcomes, treatments
or dependent clusters. The manifest records the caller's declaration; hashes
and index checks cannot prove how external code was executed or detect a
fraudulent declaration. It is not a cryptographic attestation, time-series
validation policy or identification guarantee.

Only ATE/ATTE inference is certified. Existing row-weighted scores, iid/CR1 SE,
relative effects, custom-weight approximation warnings and B22 median-variance
aggregation remain unchanged. Inherited minimum K rows per treatment arm is
retained. Repetitions use supplied seeds and partitions, with no M divisor.
External GATE/GATET/CATE/sensitivity and direct exported adapters reject before
work; multi-treatment/IV remain separate. Diagnostics retain normal per-row
predictions/folds if requested, but no fictional feature importance. Results
record external provenance and manifest version, no raw train indices/labels.

The alternative of bare arrays without a manifest is rejected because it
cannot establish even declared sample/partition alignment. A typed bundle
would add a new persistent data contract; the small versioned mapping supports
portable manifests and keeps validation in one helper module.

Method references: [DML paper](https://arxiv.org/abs/1608.00060),
[DoubleML resampling](https://docs.doubleml.org/stable/guide/resampling.html).
No numerical/API equivalence with DoubleML is claimed.

## Final implementation and focused evidence

Final source `7e947f44e3d5a0ca9dbbe0b68bf7f070fc6150fd`; initial feature commit
`2652d9faeb027da871cd2cc4d1cea5f518485fcd`. Seven non-audit paths change.
One helper validates/snapshots all external nuisances and normalizes a portable
version-1 manifest. IRM stages a complete fit through its existing decorator;
all parent partitions validate before repeated children fit from detached
arrays/manifests. No source/tests change after7e947f4; later edits audit-only.

**491 focused passed**, **127 new cases**, zero failures/errors/skips,
**58 warnings**, **32.15s**, all synthetic. Independent sklearn OOF nuisance
training and hand-written score/IF, iid/CR1/baseline/relative oracles; exact
internal/external replay for R1/R2/R3/R4 and ATE/ATTE; no-learner-call Bombs;
RNG preservation; all-partition validation; invalid schema/shapes/complex/
nonfinite/range inputs; sample/role/prediction changes; exact pandas ordering
with duplicate indices; leaked/duplicate/subset train indices; split clusters;
one-arm complements; owned arrays/manifest; failed refit; undefined relative
policy; weight approximation flags; unsupported entrypoints/direct adapters;
external/internal lifecycle and final set_params normalization are checked.
[Focus](block24_focus_result.json), [log](block24_focus_tests.log),
[runner](run_block24_focus.py).

B23 compatibility: **64 exact internal fit configuration pairs**, **96 exact
full estimate pairs**, **32 same weighted-ATTE rejections** across binary/
continuous, iid/cluster, R1/R3, normalize/store/weights settings. Nuisances,
folds, frozen targets and all result fields except time compared. Matched
_version.py; owned copied source trees and synthetic payloads removed.
[Probe](block24_probe_result.json), [runner](probe_block24.py).
Both final focus/probe ran on initial HEAD2652d9f plus recorded working-tree
hashes of the final implementation, before7e947f4 was committed.

50 pre-existing IRMmethodASTs unchanged; five change: fit, estimate, predict_cate
and two sensitivity entrypoints. The sensitivity bodies and complete GATE/
uplift modules match B23 after only new entry guards are removed. Repetition
algorithms unchanged except omission of first partition oof_split_seed from
aggregate metadata. No multi/IV, sensitivity modules/tests, workflow/dependency
changes. No new MC/performance/coverage claim; same-fit parity and independent
variance oracles validate this prediction-consumption feature.

## Initial gates and final review correction

Initial source2652d9f: local3646passed/145warnings/146.00s, strictSphinxexit0/
17.685s; CI37771095421 all6artifacts3646passed plus strictdocs. These successful
runs are superseded by the final correction below, with initial metadata/logs
and raw JUnits/docs retained separately.
[Initial local](block24_initial_integration_result.json),
[initial docs](block24_initial_docs_result.json), [initial CI](block24_initial_ci_result.json),
[initial root](block24_initial_validation_result.json).

Final review found external fit validated but discarded normalized overlap
configuration after public set_params. Uppercase CLIP could miscount clipping
or reject cluster fits; float-convertible thresholds could remain strings.
Fix7e947f4 returns the normalized pair and publishes it in staged fit, matching
ordinary fitting. Manifest construction validates without rewriting caller
configuration. Two new iid/cluster cases bring the final counts to127/491/3648.

Initial111-case test iteration19failed/92passed: overly strict relative p-value
tolerance for existing1-cdf cancellation, one-arm fixture missingfold2, missing
sensitivity arguments, wrong warning class. Test fixes preserved all inference
equations; then111passed, followed by125new/489focuspassed. Expanded command
first named a nonexistent parallel-test file and collected no tests; corrected.
Final set_params cases first failed before fit because sklearn legitimately
inspected nested Bomb params (2failed/489passed). Corrected fixture uses ordinary
estimators for set_params and Bombs for manifest/fit, then491passed.

## Limits

Manifest checks declarations, not actual external training history; false
caller claims remain undetectable. Transport is JSON-compatible; current
numeric/index hashes are implementation-specific, with no cross-version/
platform fingerprint stability guarantee. The existing random_state field in
single results records configuration, not the supplied external split seed.
Only full shared outer complements, all nuisances and clipping are supported.
Independent external training samples, partial prediction replacement,
arbitrary train subsets, time-series splits and multi/IV need separate
contracts. The inherited minKrows-per-arm guard remains conservative for some
otherwise feasible partitions. Identification, adequate nuisance rates and
independent rows/clusters with many nondominating clusters are still required.
The seven named sensitivity exclusions are unchanged; no full release gate.

No subagents, login/setup/install, upstream/PR/release/messages/notebooks or
website publication. User's explicit ordinary push permission persists for
personal branch codex/correctness-roadmap. Initial and corrected implementation
pushes succeeded. Final audit commit/live equality/clean state are checked at
completion. Stop at B24 for context cleanup; next B25 DR/R-CATE contracts first.
Sensitivity/SC08LOO/selected-UATT/multi-IV repetition/grouping/multiway/fewcluster
and NumPyRST debt remain deferred. Do not automatically start B25.

## Final committed local gate

On exact final7e947f4: **3648 passed**, zero failures/errors/skips,
**145 warnings**, **132.65s** (runner133.800s). Seven exclusions unchanged,
selected_full_suite=false, sensitivity_validated=false. [Selection](block24_integration_selection.json),
[result](block24_integration_result.json), [log](block24_integration_tests.log),
[runner](run_block24_integration.py). Strict standalone Sphinx **exit0**, **23.040s**,
warnings as errors, no HTML publication. [Result](block24_docs_result.json),
[log](block24_standalone_checks.log).

Owned copies/payloads and the exact two recorded pytest-temp dirs removed;
code-testJUnits/logs/metadata retained. Initial default pytest temp locations
were not manually cleaned. [Cleanup](block24_cleanup_result.json). Synthetic
fixtures only. Handoff146immutablelinks verified. [Handoff](DOCUMENTATION_HANDOFF.md),
[checks](block24_handoff_checks.log). FinalCI37772289364 completed/success on exact7e947f4.

## Final CI and root verification

[CI37772289364](https://github.com/MaximLenivkin/Causalis/actions/runs/37772289364)
completed/success on **exact final source `7e947f44e3d5a0ca9dbbe0b68bf7f070fc6150fd`**. All six downloaded
artifacts contain **3648 passed** each, zero failures/errors/skips, plus strict
standalone Sphinx **exit0**. Actual Python/stack versions: 3.10.22 latest, 3.10.21 legacy, 3.11.16 latest, 3.12.15 latest, 3.13.15 latest, 3.14.8 latest.
SnapshotUTC: 2026-10-08T11:51:49.085206+00:00.
Full local/CI case-ID sets match; focus491/new127 are included. Scope,
normalized pytest argv (only basetemp/JUnit paths differ), seven exclusions,
source/Python/dependencies and all five hashes/job (selection/result/JUnit,
docs result/log) verified. Six representative Linux stacks, not all dependency
combinations. Sensitivity/full release/RST/notebooks/hosted website not certified.
[CI evidence](block24_ci_result.json), [log](block24_ci_checks.log),
[observer](observe_block24_ci.py), [artifact verifier](summarize_block24_ci.py).

Root-only [verifier](verify_block24.py) --source7e947f4 --require-ci verifies
seven source hashes,50unchangedIRMmethodASTs, guard-only sensitivity/adapter
changes, repetition algorithms, final probe/focus/local/docs/cleanup and all
raw CI case sets/hashes. Initial3646-case local/CI evidence remains separately
verified, including raw initial artifact hashes. Handoff146immutablelinks and
all report local links checked. [Result](block24_validation_result.json),
[log](block24_validation_checks.log),issues[]. No source/tests changes after7e947f4;
final evidence is audit-only, so it needs no CI rerun. Final ordinary audit push,
live local/remote equality and clean tree are checked at completion. Checkpoint
via gitlog-1. Stop here for context cleanup/new user request before B25.
