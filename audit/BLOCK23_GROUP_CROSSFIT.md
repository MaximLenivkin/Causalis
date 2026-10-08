# B23 — one-way group cross-fitting for binary IRM

Baseline: `1409e95cf0cfb0cb1f9ab8541eefc25b3cbe1342`. Status: completed (local and six-job CI gates verified).

## Contract fixed before implementation

Public API: `IRM(..., cluster_groups=labels)`, for binary ATE/ATTE only.
`None` keeps the existing iid single/repeated paths. A vector is positional;
a pandas Series must have exactly the fitted DataFrame index, in the same order
(including repeated index labels). No implicit sorting, joining or reindexing.
Labels must be a one-dimensional, nonmissing vector of hashable scalar labels.
Fit snapshots first-occurrence integer codes; estimation never reads mutable
caller labels. Labels do not become confounders and need not be user ids.
The existing `estimate(groups=...)` means GATE subgroups, not clusters.

Independent sampling units are clusters. Dependence within a cluster is allowed;
between-cluster independence, many clusters, no dominating cluster, adequate
cluster-level nuisance rates, consistency/no interference, unconfoundedness and
overlap are still assumptions. Group splitting does not establish identification.
The target remains the row-weighted ATE or treated-row ATTE (a ratio of cluster
totals); it is not an equal-cluster average. Informative cluster size matters.

At least `n_folds` distinct clusters and two clusters are needed. Split unique
first-occurrence codes with shuffled KFold and a recorded local uint32 seed;
each cluster is held out exactly once, all its rows stay together. Folds balance
cluster counts, not row counts or treatment proportions. Each training complement
must contain both treatment arms; validate every fold before fitting its learners.
No random retry, row-level fallback, or claim of stratification. `random_state=None`
uses local entropy and records a replayable seed without consuming global RNG.
Seeded repetitions reuse B22's prefix-stable seeds and unchanged learner templates.

Score, point effect and per-row IF remain the original IRM equations. For n rows,
G clusters and row IF `phi_i`, use
`U_g = sum_{i in g}(phi_i - mean(phi))` and
`SE^2 = G/(G-1) * sum_g(U_g^2)/n^2` (one-way CR1, scalar moment).
All singletons reduce to the original iid ddof=1 variance. The same covariance
rule applies to baseline IF and the full relative-effect delta IF, including
ATTE's empirical treated-share derivative. Normal Wald inference remains;
the correction is not a few-cluster guarantee. Repeated estimates aggregate
these sample-scaled cluster SEs with B22 median-variance policy, no repetition
divisor. No single aggregate IF is fabricated.

Cluster fitting requires `overlap_policy='clip'`; row dropping could change
cluster composition/target. Private fixed folds are rejected. Cluster GATE/GATET,
CATE scoring and sensitivity operations reject explicitly rather than use
uncertified iid paths. Orthogonal signal remains available for a single clustered
partition as a row signal, with no downstream iid inference guarantee.
Multiway clustering, cluster bootstrap, small-G t/CR2/wild-bootstrap inference,
multi-treatment/IV grouping, equal-cluster estimands and sensitivity are deferred.
Existing custom-weight/Hajek approximate IF flags remain approximate with CR1.

Source metadata will identify one-way CR1, G and realized split seed. Raw labels
will not be copied into results. Required integer membership is retained even
without diagnostics; ordinary nuisance diagnostics describe one partition only.
Failed refits preserve the previous complete model through the existing staging
protocol; successful refits clear scalar inference and stale cluster state.

## Method references

The separation of cluster-disjoint training and variance adjustment follows the
motivation in [DoubleML's cluster example](https://docs.doubleml.org/stable/examples/py_double_ml_multiway_cluster.html)
and [Chiang et al.](https://arxiv.org/abs/1909.03489). This scalar row-weighted
one-way implementation is not a claim of numerical parity with their multiway
estimator. CR1 is the intercept-only sandwich convention documented in
[statsmodels](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_cluster.html).
Group splitting uses [KFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.KFold.html)
on unique cluster codes, not StratifiedGroupKFold; this keeps the contract explicit
across supported dependency stacks. Primary sources inspected 8 October 2026.

## Required verification

Synthetic public score/IF/absolute and relative CR1 oracles; independent
statsmodels intercept covariance; group leakage learners; unsupported/invalid
inputs before fitting; group-level treatment support; unequal sizes/singletons;
fit/result ownership and transitions; repeated seed replay/prefix; parallel
equivalence; exact iid compatibility against baseline. Seeded clustered Monte
Carlo records coverage and mean-SE/empirical-SD, including iid-SE comparator,
without a universal coverage claim. Then committed correctness scope with seven
existing sensitivity exclusions, standalone strict Sphinx and all six CI jobs.
No actual client/unit records are acquired; all numerical fixtures are synthetic.

## Focused implementation evidence

87 new cases plus neighboring repeated/single IRM, score/relative IF, alignment,
fit snapshots, GATE/GATET and CATE tests: 364 passed, zero failures/errors/skips,
38 existing/policy warnings. [Focused manifest](block23_focus_result.json) and
[log](block23_focus_tests.log); raw code/test JUnit is retained in ignored runtime
output. Four initial exported-adapter test calls omitted the required groups
argument; corrected to groups=None. One initial scalar variance comparison used
exact equality across different rounding orders; corrected to tight allclose.
These were test mistakes, with no corresponding source formula changes.

[Compatibility probe](block23_probe_result.json): exact 32 iid fit configurations
(n_rep 1/3, binary/continuous outcomes, diagnostics on/off, custom weights,
normalized IPW); exact 48 full returned estimates and 16 identical weighted-ATTE
rejections. Baseline rejects cluster_groups; current public fit/estimate succeeds.
Owned source copies and synthetic comparison payloads were removed. Probe was
performed before committing source; it records actual baseline HEAD and hashes.

[Cluster simulation](block23_sampling_result.json): 400 samples, 80 clusters,
independent sizes 4–12, cluster-randomized treatment, shared normal cluster shock
plus individual noise. LR/logistic nuisance learners and four cluster folds;
R1 is the first of the three fitted partitions. ATE coverage R1/R3 .945/.945;
ATTE .9525/.9425. Mean cluster SE/empirical SD .9701/.9787 and .9778/.9819.
Replacing only variance with iid row IF SE gives coverage .4825/.475 and
.495/.505, respectively. MC SE about .011 at 95%; one favorable DGP only.
No inference on real client records, universal coverage or performance claim.
Source hashes and actual precommit baseline HEAD are recorded.

45 pre-existing IRM method ASTs are unchanged. New variance dispatch changes
three covariance calculations; point moment/IF/relative delta equations remain.
Both sensitivity bodies are identical after removing one new cluster entry
guard each. GATE and uplift adapters each gain only one entry guard; all other
code in those modules is unchanged. No sensitivity algorithm rewrite. Single
partition zero-SE t/p-value behavior remains unchanged; repeated zero-SE policy
is B22's policy. Source/tests are frozen at the implementation commit; subsequent changes are audit-only.

## Committed local gate

Implementation source `b1adeb291870c965825c60712144d23ea4c31ce9` is pushed.
[Correctness manifest](block23_integration_result.json),
[selection](block23_integration_selection.json), [log](block23_integration_tests.log):
3521 passed, zero failures/errors/skips, 125 warnings; pytest 211.90s, runner
212.079s. Local Python 3.12.14/macOS. Seven sensitivity exclusions unchanged;
selected_full_suite=false and sensitivity_validated=false. No full release/tag
gate claim. All 364 focused cases (including all 87 new ones) are present.

[Standalone docs](block23_docs_result.json), [log](block23_standalone_checks.log):
strict Sphinx exit0, warnings are errors, 23.928s on the same source, no HTML
publication. B21's generator/workflow remain unchanged. NumPy/RST migration is
still documentation debt, not certified by build compatibility.

[Cleanup](block23_cleanup_result.json): removed only this run's exact integration
pytest-temp and probe-owned source copies. Code/test JUnits, standalone logs
and environment metadata remain in ignored runtime directories. No real client
records, credentials, notebook execution, external messages, release, upstream
merge or website publication. Root-only work; no subagents or setup/login repeats.

## CI and completion

[CI run 37763490246](https://github.com/MaximLenivkin/Causalis/actions/runs/37763490246)
completed/success on exact implementation source
`b1adeb291870c965825c60712144d23ea4c31ce9`. All six downloaded artifacts have
3521 passed each, zero failures/errors/skips, and strict standalone Sphinx exit0.
Actual Python: 3.10.21 latest, 3.10.22 legacy, 3.11.16, 3.12.15, 3.13.16,
3.14.7. Snapshot UTC 2026-10-08T10:31:35.169995+00:00.
[CI manifest](block23_ci_result.json) and [observation log](block23_ci_checks.log).
Full case sets equal the local committed suite; all focused 364/new87 cases,
normalized pytest arguments, unchanged seven exclusions, source/dependency
metadata and five artifact hashes per job are checked. Six representative
Linux stacks, not every possible dependency combination.

[Root verifier](verify_block23.py), [manifest](block23_validation_result.json),
[log](block23_validation_checks.log) validate seven non-audit paths, 45 unchanged
IRM method ASTs, unchanged sensitivity/adapter bodies minus new entry guards,
compatibility/focus/MC provenance, local/CI source/cases/docs and raw artifacts;
issues[]. [Documentation handoff](DOCUMENTATION_HANDOFF.md) contains 141 locally
verified immutable links; implementation sources are pushed. All code/test
evidence is local aggregate/synthetic evidence, not client data.

Ordinary push to MaximLenivkin/Causalis:codex/correctness-roadmap remains
authorized by the user's explicit «Разрешаю пуш в нашу ветку». Final checkpoint
is git log -1; final ordinary audit push, live HEAD/remote equality and clean
working tree are checked at completion. Audit-only changes do not rerun the
workflow. No PR, upstream/main push, force-push or release.

Stop at B23 for context cleanup. Next B24: binary IRM external OOF predictions
and manifest/alignment/ownership/leakage contracts before implementation.
Repeated multi/IV, multiway grouping, equal-cluster/few-cluster inference,
DR/R-CATE, sensitivity, SC08 LOO, selected-U ATT and NumPy/RST migration remain
separate or deferred. This block does not certify downstream iid diagnostic
inference, joint/subgroup inference, notebook execution or universal coverage.

## Retained conservative support limitation

The original `_validate_treatment_support` method is unchanged: in addition to
G>=n_folds and both arms in each training complement, it requires at least
n_folds input rows in each treatment arm. Therefore a cluster partition with
adequate training support can still fail this inherited row-count gate. B23
retains the existing input eligibility policy; relaxing it for clustered data
is a separate follow-up. [Supplementary support probe](block23_support_result.json)
and [log](block23_support_checks.log) demonstrate two before-fitting rejections
(n_rep1/3) with two treated rows across distinct clusters and valid first-split
training complements. These two supplementary checks are not added to the
87 new/364 focused/3521 full pytest counts. This restriction is explicit in the
documentation handoff; it is not a fallback to iid inference.
