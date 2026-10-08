# B22: repeated binary IRM cross-fitting

Baseline: `357e16e8d1faf37e221b92b7e1f83ee5fba3c2dc`.

## Contract fixed before implementation

Use the existing public `IRM(n_rep=M)` parameter; binary ATE/ATTE only.
`n_rep=1` retains the original fit, prediction, diagnostics and inference path.
For M>1, every repetition runs the existing single-partition IRM on the same
ordered sample with the same learner templates, weights and overlap clipping.
`drop` is rejected before learner fitting: split-dependent retention changes
the target population. GATE/GATET, CATE and sensitivity aggregation are not
part of this scalar contract. MultiTreatmentIRM/IIVM repetition is deferred.

Identification is unchanged: iid units, consistency, conditional
unconfoundedness and overlap, plus nuisance-rate/regularity assumptions for DML
inference. Repeated splits do not repair identification, clustering, weak
support or approximation flags for normalized/custom-weight inference.
The target remains the configured ATE or ATTE; clipping has its existing
finite-sample/target limitations. Repetitions reuse observations, not iid
replicate datasets.

A local SeedSequence supplies partition seeds. With an integer random_state,
repetition zero uses exactly that seed, subsequent seeds use spawned children;
the sequence is prefix-stable as M grows. None uses fresh local entropy and
records all realized seeds. This path does not consume global NumPy RNG for
partition creation. Supplied learner RNG parameters are not overridden;
reproducible predictions require deterministic or explicitly seeded learners.
Repetitions run sequentially; n_jobs keeps existing fold parallelism.
Distinct seeds do not guarantee distinct partitions in tiny samples.

For scalar theta_m and already sample-scaled standard errors se_m:

    theta = median(theta_m)
    se = sqrt(median(se_m**2 + (theta_m - theta)**2))

Wald intervals and two-sided normal p-values use this theta/se.
For exactly zero aggregate SE, p=1 for theta=0 and p=0 otherwise; the
nonzero-effect statistic is signed infinity. Single-partition zero-SE policy
is unchanged. No division by
M or sqrt(M). This is an explicit scalar median-variance policy, informed by
Chernozhukov et al. Definition 3.3 and the documented DoubleML R rule; it is
NOT a claim of parity with the current Python DoubleML interval aggregation.
References: [DML paper](https://arxiv.org/abs/1608.00060),
[DoubleML resampling](https://docs.doubleml.org/stable/guide/resampling.html).
Fixed M asymptotics do not establish finite-sample coverage for arbitrary
learners or a growing-M regime. No new covariance or simultaneous inference.

Relative percentage effects are separately aggregated by the same rule using
single-repeat delta-method SE. If any repetition has undefined relative
inference, aggregate relative inference is NaN; repetitions are not omitted.
Aggregate relative effect need not equal aggregate absolute effect divided by
an aggregate baseline. Absolute inference requires every repetition finite;
invalid/overflowed inputs fail, no nanmedian, winsorization or imputation.

A RepeatedCausalEstimate extends CausalEstimate and carries detached per-repeat
results and realized seeds. Its primary diagnostic_data is None: a median
estimate has no single nuisance/IF payload. Per-repeat diagnostics remain on
per-repeat results. Parent stores private fitted repetitions and explicit
folds_repetitions_ (n,M) when diagnostics are enabled; no fake single-repeat
nuisance attributes. The scalar public coef/se/pvalues/summary/confint expose
aggregate inference. Failed refit retains the previous complete fit; successful
refit clears primary inference and repetition results. Fit-time repetition
count/config governs estimate even if public constructor params later mutate.
Library sensitivity algorithms and seven existing CI exclusions stay unchanged.

## Verification and completion

Implemented with six non-audit source/test/doc paths. Existing scalar
score/relative inference methods are reused by fitted single-partition children;
no nuisance prediction averaging and no fabricated median influence function.
Strict integer counts replace prior lossy n_rep coercion (booleans, floats,
strings and nonpositive counts now reject). Two sensitivity entry guards reject
new repeated fits; sensitivity algorithms and existing single-fit behavior are
unchanged.

- New cases: 67. Focused with existing neighbors: 221 passed, 29 existing/policy
  warnings, 22.51 seconds; no failures/errors/skips. Independent scalar sorting,
  actual per-partition score/IF and relative references, public oracle no-SE-
  shrinkage, leakage-rejecting learners, seeded/None RNG, prefix/fold/job parity,
  labels/arrays ownership and failed later-partition refit checks.
- Baseline public n_rep=2 fails with NotImplementedError; current succeeds.
  Exact n_rep=1 comparison: 16 fitted prediction/sample/diagnostic pairs,
  24 full returned-estimate pairs, eight unchanged weighted-ATTE rejections.
  Owned source copies and synthetic payloads removed; hashes/counts retained.
  Initial comparison probe stopped on the expected weighted-ATTE rejection;
  final probe records that rejection explicitly on both sides.
- Synthetic iid check: 200 samples of 600 rows, three repetitions/three folds,
  constant effect0.7, specified linear outcomes/logistic treatment and LR
  learners. ATE mean0.70122, ATTE0.70220; both coverage0.965 (193/200).
  MeanSE/empiricalSD1.0061/1.0266. Approximate MCSE0.015 near nominal coverage;
  no universal coverage claim. Only aggregate evidence saved.

Source commit: `ede6deda2eb82c518ed3d7f5b48780d39cdfe5f0`,
`feat(irm): support repeated scalar cross-fitting`.

Standalone strict Sphinx succeeds on the committed source (warnings are
errors, no HTML publication): exit0, 17.307 seconds. Committed correctness
integration: **3434 passed**, zero failures/errors/skips, 116 warnings,
115.66 seconds (runner115.870). All 67 new cases and 221 focused cases are
included by complete JUnit case IDs. Seven sensitivity exclusions unchanged.
Local environment Python3.12.14; versions and argv in selection manifest.
Remote push in the ordinary personal branch was rejected by automatic
approval review: it found no explicit trusted authorization to send code to
this repository/branch. Push and the six-job CI matrix have NOT run. Request
explicit user confirmation for that concrete push after local checks finish;
do not bypass the rejection or treat the historical handoff as renewed approval.
No release, upstream merge or PR.

Evidence:

- [Focused results](block22_focus_result.json), [log](block22_focus_tests.log).
- [Exact compatibility probe](block22_probe_result.json), [runner](probe_block22.py).
- [Sampling aggregates](block22_sampling_result.json), [runner](sample_block22.py).
- [Committed correctness](block22_integration_result.json), [selection](block22_integration_selection.json), [log](block22_integration_tests.log).
- [Committed Sphinx result](block22_docs_result.json), [log](block22_standalone_checks.log).
- [Root validation](block22_validation_result.json), [verifier](verify_block22.py).

Root verifier confirms six changed non-audit paths and committed hashes,
43 unchanged IRM method ASTs, and unchanged sensitivity bodies after
removing exactly the two new entry guards. Compatibility/focus/local/docs
manifests and all case sets verified, issues[]. Portable handoff136 immutable
URLs verified against local git objects; four new URLs await remote push.
The exact owned integration pytest-temp was removed after successful use;
JUnit, aggregate evidence and raw code/test logs remain. Probe-owned source
copies and synthetic per-row payload files were removed by TemporaryDirectory.
Pytest's default focused temp directories are not claimed removed here.

Completion requires confirming the personal push, running/verifying its exact-
source CI, and updating this report/handoff. Only audit files change after the
source commit. The next feature block should establish group-aware binary IRM
contracts; multi-treatment/IV repetition remain explicitly separate follow-ups.
Sensitivity, SC08 LOO, selected-U ATT and NumPy/RST migration remain deferred.
Do not begin the next block until B22 is finished and the user asks.
