# B20 — duplicate values and fitted data snapshots

Baseline: `98d5478a36b5fbb051c863db4599cbc0bc9a8bbf`.
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
skips; existing warning policies are recorded in the log.

Exact compatibility probe: **20 fit pairs / 36 inference pairs**, comparing
ordinary finite folds/nuisances, score/IF, effect/SE/CI/p, diagnostic arrays and
public signatures. Includes three families, n_jobs1/2, normalization0/1 and
binary/multi diagnostic storage0/1. Source frames are unchanged. **132 existing
functions have unchanged executable ASTs**, excluding docstrings and explicitly
listed changed methods. These checks do not certify every dependency/input or
extreme arithmetic magnitude, nor supply a performance/memory improvement.
Returned payload copies add memory proportional to the payload.

Committed integration and six-stack CI evidence will be linked here after
completion; sensitivity and standalone Sphinx are separate gates.

## Evidence

- [Public regressions](../tests/inference/test_data_snapshot_contracts.py)
- [Revised historical duplicate policy test](../tests/data/test_duplicate_screening.py)
- [Fit/payload publication helper](../causalis/scenarios/_fit_state.py)
- [Baseline runner](run_block20_baseline.py), [manifest](block20_baseline_result.json), [JUnit](block20_baseline.xml), [log](block20_baseline_tests.log)
- [Focus JUnit](block20_focus.xml), [log](block20_focus_tests.log)
- [Compatibility/AST probe](probe_block20.py), [manifest](block20_probe_result.json), [log](block20_probe_checks.log)

Next B21: dedicated standalone Sphinx build and documentation compatibility
gate. Repeated cross-fitting, group-aware cross-fitting, external OOF and
DR/R-CATE follow correctness. Sensitivity, SC08 LOO and selected-U ATT remain
deferred. Stop at B20; B21 needs the next user request.
