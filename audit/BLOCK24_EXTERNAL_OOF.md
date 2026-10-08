# B24 — binary IRM external OOF predictions

Baseline: `3668eec10a5cc794dd16be26d8ade6c284277bf4`. Contract fixed before
implementation. Status: implementation and focused verification complete; committed integration/CI pending.

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

## Implementation and precommit evidence

One validation helper owns prediction shape/range checks and portable version-1
manifest normalization. IRM stages the complete fit through the existing fit
publication decorator. Repeated children consume detached per-partition arrays
and manifests; the full parent manifest is checked first. Existing score,
relative-effect and covariance helper methods are unchanged. External result
metadata records supplied partition seeds; aggregate metadata drops the first
partition's oof_split_seed. The existing random_state configuration field may
remain in single-partition results; it did not generate external folds.

Final focused checks: **489 passed**, **125 new cases**, zero failures/errors/
skips, **58 warnings**, **31.33s**, synthetic fixtures only. The new cases include
independent sklearn nuisance training, hand-written score/IF and iid/CR1/relative
oracles, exact internal/external replay for R1/R2/R3/R4 and both scores, Bomb
learners, RNG preservation, every partition's manifest checks, invalid shapes/
complex/nonfinite/probability inputs, ordered pandas alignment with duplicate
indices, data/roles/prediction digest changes, schema types, leaked/duplicate/
subset training indices, split clusters, one-arm complements, owned inputs,
undefined relative effects, seed provenance, custom weights and refit lifecycle.

Compatibility probe against unmodified B23: **64 exact internal configuration
pairs**, **96 exact estimate pairs**, **32 same weighted-ATTE rejections** across
continuous/binary outcomes, iid/cluster, R1/R3, normalize/store/weights settings.
Payloads include nuisances, folds, frozen targets and full result fields except
time. Matched generated _version.py; owned source copies and synthetic payloads
removed. [Probe](block24_probe_result.json), [focused manifest](block24_focus_result.json),
[focus runner](run_block24_focus.py), [probe runner](probe_block24.py).
These ran on the baseline HEAD plus recorded working-tree source hashes, not on
a later committed SHA.

Initial111-case test iteration: 19failed/92passed; failures were test-oracle
p-value absolute tolerance (existing 1-cdf cancellation), malformed one-arm
fixture missing fold2, omitted sensitivity arguments and incorrect warning
class. Corrected tests, preserving all library inference equations; then
111passed. Final additional schema/ownership/finite-data checks bring new count
to125. First expanded invocation used a nonexistent parallel-test filename and
collected no tests; corrected paths before the recorded successful run.

50 pre-existing IRM method ASTs are unchanged; five change: fit, estimate,
predict_cate and two sensitivity entrypoints. Sensitivity algorithms and whole
GATE/uplift modules match B23 after removing only new entry guards. _repeated.py
changes only removal of single-partition external seed from aggregate metadata.
Seven non-audit paths change; no multi/IV, sensitivity modules/tests, workflow
or dependency changes. No new Monte Carlo coverage/performance claim: this
block consumes predictions and preserves estimators; same-fit exact parity
and independent score/variance oracles provide its numeric evidence.

The minimum-K-rows-per-arm support guard remains conservative for external
folds, just as for B23 cluster folds. Only complete outer complements are
supported; independent external training samples, arbitrary smaller training
sets, partial nuisances, time-series folds and multi/IV bundles need separate
contracts. False caller declarations remain undetectable.
