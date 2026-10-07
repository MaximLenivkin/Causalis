# B20 — duplicate values and fitted data snapshots

Baseline: `98d5478a36b5fbb051c863db4599cbc0bc9a8bbf`.
Source: `28acf6b4fea588ee682251a35a5f23a8757f4415` (source/tests frozen after this checkpoint).
Scope: four row-data contracts' shared duplicate screening and primary
binary/multi/IV estimation snapshots. Synthetic data exists only in memory;
artifacts retain code, counts, configurations, hashes and test evidence.
No sensitivity module or algorithm is edited.

## Reproduced defects and chosen policy

Numeric object user IDs equal to a selected outcome were admitted because
numeric and object fingerprints used different categories. This explicitly
changes the historical B06 separate-category policy: selected columns with
exact Python-equal values are duplicates irrespective of numeric/object dtype.
Integer, float, mixed real scalar, Decimal, Fraction and zero-imaginary complex
IDs are covered. Float/complex-to-real conversion is screening only; it does
not coerce stored IDs or determine equality. Numeric-looking strings and
rounded large integers still require the unchanged exact object comparison.
Samples and hash collisions never establish equality. Numeric analysis roles
retain their existing real/finite validation; this adds no complex outcome API.
Fallback object fingerprints use Python scalar hashes to respect equality
across heterogeneous numeric types. Arbitrary custom objects with unusual
conversion/equality/hash behavior are not a newly certified input domain.

Previously returned diagnostic arrays could alias fitted y/d/X, nuisances,
folds and primary inference arrays. Editing a returned estimate could therefore
change a later estimate, including the primary effect itself. Each returned
primary diagnostic payload now owns independent copies of its public fields,
including nested caches. Payloads remain writable. The private `_model` link
retains its existing live-model meaning; this is not a complete model archive
for sensitivity or future model-dependent refutation calls.

Fit-time sample arrays were already copied, but result labels read mutable
contracts. Successful fits now retain outcome/treatment/confounder/instrument
names and use these names in scalar estimates, multi contrast labels, IV
feature labels and confidence-interval labels. Older fitted objects without
the schema cache retain their existing fallback. Data contracts and public
model attributes remain mutable; fit-time snapshots are not a new immutable
public API. Model configuration/model_options and lazy CATE/group definitions
are outside this schema guarantee.

Binary/multi fitting could publish a new sample before learner failure or
late overlap validation while retaining old nuisances. Fits now run on a
shallow staging estimator and publish its state only after complete success.
Failed refits preserve the previous fit and data reference, including early
configuration and late overlap failure. Changes a caller already made to
model parameters remain changes. Supplied learner objects and callback effects
are shared external state and are not rolled back; default learner thread
configuration may mutate such objects. A successful replacement fit clears
primary scalar inference and requires a new estimate() call. IV retains the
already established different policy: a failed refit leaves it unfitted.
Generic sensitivity scalar-state invalidation remains deferred; retaining or
clearing a primary inference cache is not sensitivity correctness validation.

## Verification

Final identical new-test file on isolated exact baseline: **107 cases,
86 failed / 21 passed / zero errors or skips**. Failures reproduce missing
rejections, array aliasing, incorrect labels, mixed failed-refit samples and
stale primary inference. Final focus: **2106 passed**, zero failures/errors/
skips; **15 existing policy warnings / 31.36s** are recorded in the log.

Exact compatibility probe: **20 fit pairs / 36 inference pairs**, comparing
ordinary finite folds/nuisances, score/IF, effect/SE/CI/p, diagnostic arrays and
public signatures. Includes three families, n_jobs1/2, normalization0/1 and
binary/multi diagnostic storage0/1. Source frames are unchanged. **132 existing
functions have unchanged executable ASTs**, excluding docstrings and explicitly
listed changed methods. These checks do not certify every dependency/input or
extreme arithmetic magnitude, nor supply a performance/memory improvement.
Returned payload copies add memory proportional to the payload. An additional
8public numeric/object large-integer cases share exactly the same rounded
float64 fingerprint but are accepted because exact values differ; inputs are
unchanged. These are supplementary checks, not additional pytest counts.

Committed correctness integration: **3359 passed**, zero failures/errors/skips,
**91 warnings / 115.72s**, exit0. Seven named sensitivity exclusions are
unchanged. Source/tests are frozen at the checkpoint above. This is a scoped
correctness run, not full sensitivity, standalone Sphinx or release validation.
[CI37665898544](https://github.com/MaximLenivkin/Causalis/actions/runs/37665898544) completed/success on exact `28acf6b4fea588ee682251a35a5f23a8757f4415`.
All six downloaded JUnit artifacts contain **3359 passed**, zero failures/
errors/skips each. Complete case sets, all2106focus cases, exact source,
actual normalized pytest argv and all seven sensitivity exclusions match the
local committed integration. Snapshot UTC2026-10-07T18:23:05.139669+00:00.
Actual Python versions:3.10.21latest/3.10.22legacy,3.11.16,3.12.15,3.13.16,
3.14.7. Full dependency/source/selection/hash evidence is in the CI manifest.
Root verification checks8changedsource/testpaths,8committedhashes,
132unchanged executablefunctions, originalbaseline/probe provenance and
alllocal/CIcaseIDs/artifacthashes; issues[]. Handoff127immutablelinksverified.
Only audit artifacts change after the source checkpoint. Owned worktrees and
pytest temporary files were removed; aggregate evidence is retained. Personal
source/final audit pushes use the existing branch; no PR/release/upstream merge.

## Evidence

- [Public regressions](../tests/inference/test_data_snapshot_contracts.py)
- [Revised historical duplicate policy test](../tests/data/test_duplicate_screening.py)
- [Fit/payload publication helper](../causalis/scenarios/_fit_state.py)
- [Baseline runner](run_block20_baseline.py), [manifest](block20_baseline_result.json), [JUnit](block20_baseline.xml), [log](block20_baseline_tests.log)
- [Focus JUnit](block20_focus.xml), [log](block20_focus_tests.log)
- [Rounded fingerprint collision evidence](block20_collision_result.json)
- [Compatibility/AST probe](probe_block20.py), [manifest](block20_probe_result.json), [log](block20_probe_checks.log)

- [Integration runner](run_block20_integration.py), [selection](block20_integration_selection.json), [result](block20_integration_result.json), [log](block20_integration_tests.log)
- [CI observer](observe_block20_ci.py), [artifact verifier](summarize_block20_ci.py), [manifest](block20_ci_result.json), [log](block20_ci_checks.log)
- [Root verifier](verify_block20.py), [result](block20_validation_result.json)

Next B21: dedicated standalone Sphinx build and documentation compatibility
gate. Repeated cross-fitting, group-aware cross-fitting, external OOF and
DR/R-CATE follow correctness. Sensitivity, SC08 LOO and selected-U ATT remain
deferred. Stop at B20; B21 needs the next user request.
