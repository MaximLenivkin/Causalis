# B23 — one-way group cross-fitting for binary IRM

Baseline: `1409e95cf0cfb0cb1f9ab8541eefc25b3cbe1342`. Status: in progress.

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
is B22's policy. Source/tests will freeze after the implementation commit.
