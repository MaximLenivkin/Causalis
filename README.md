# Causalis
[![PyPI version](https://img.shields.io/pypi/v/causalis.svg)](https://pypi.org/project/causalis/)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/causalis?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/causalis)
![Python](https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12%20|%203.13%20|%203.14-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Code quality](https://img.shields.io/badge/code%20quality-A-brightgreen)
[![Docs](https://img.shields.io/badge/docs-causalis.causalcraft.com-blue)](https://causalis.causalcraft.com/)

<a href="https://causalis.causalcraft.com/"><img src="https://raw.githubusercontent.com/causalis-causalcraft/Causalis/main/notebooks/new_logo_big.svg" alt="Causalis logo" width="80" style="float: left; margin-right: 10px;" /></a>

Robust causal inference for experiments and observational studies in Python, organized around **scenarios** (e.g., Classic RCT, CUPED, Unconfoundedness) with a consistent `fit() → estimate()` workflow.

- 📚 Documentation & notebooks: https://causalis.causalcraft.com/
- 🔎 API reference: https://causalis.causalcraft.com/api-reference

## Why Causalis?
Causalis focuses on:
- Scenario-first workflows (you pick the study design; Causalis provides best-practice defaults).
- Extensive robustness tests that reveal issues in the study design or model specification
- Pydantic data contracts 
- An advanced DGP (Data Generating Process) with heterogeneous treatment effects, latent variables, and correlated confounders
- A website with notebooks based on real-world cases

## Installation
### Recommended
```bash
pip install causalis
```

### Building the API reference

Install the documentation extra with `.venv/bin/python -m pip install -e ".[docs]"`.
Run `.venv/bin/python scripts/generate_api_reference.py --check` to build in a
temporary directory without replacing the checked-in HTML. Sphinx warnings fail
the build. CI records the standalone result through `scripts/run_docs_check.py`.

To regenerate `notebooks/api/html`, run the generator without arguments. Use
`--output-dir build/api-reference` for a separate local output; the generator
replaces the entire destination directory after a successful build. Docstrings
retain the existing MyST rendering. This build does not run notebook examples
or validate statistical claims, sensitivity methods, or the documentation website.

# Quickstart: Classic RCT (difference in means + inference)

```python
from causalis.dgp import generate_classic_rct_26
from causalis.scenarios.classic_rct import DiffInMeans, check_srm

# Synthetic RCT data as a validated CausalData object
data = generate_classic_rct_26(seed=42, return_causal_data=True)

# Optional: Sample Ratio Mismatch check
srm = check_srm(data, target_allocation={0: 0.5, 1: 0.5}, alpha=1e-3)
print("SRM detected?", srm.is_srm, "p=", srm.p_value, "chi2=", srm.chi2)

# Estimate treatment effect with t-test inference (or bootstrap / conversion_ztest)
result = DiffInMeans().fit(data).estimate(method="ttest", alpha=0.05)
result.summary()
```
# Quickstart: Observational study (Unconfoundedness / DML IRM)
```python
from causalis.scenarios.unconfoundedness.dgp import generate_obs_hte_26
from causalis.scenarios.unconfoundedness import IRM
from causalis.data_contracts import CausalData

causaldata = generate_obs_hte_26(return_causal_data=True, include_oracle=False)

from causalis.scenarios.unconfoundedness import IRM

model = IRM().fit(causaldata)
result = model.estimate(score='ATTE')
result.summary()
```

### Repeated cross-fitting for binary IRM

```python
from sklearn.linear_model import LinearRegression, LogisticRegression

model = IRM(causaldata, ml_g=LinearRegression(),
            ml_m=LogisticRegression(max_iter=1000),
            n_folds=4, n_rep=5, random_state=42).fit()
result = model.estimate(score="ATTE")
result.summary()
result.repetition_seeds
result.repetition_estimates[0].diagnostic_data
```

For `n_rep > 1`, binary ATE/ATTE use the median of single-partition effects and
`sqrt(median(se_m**2 + (effect_m - median_effect)**2))`. The same observations
are reused, so the standard error is not divided by the number of repetitions.
This is the scalar median-variance rule; current Python DoubleML uses a
different interval aggregation ([resampling documentation](https://docs.doubleml.org/stable/guide/resampling.html)).
The iid, unconfoundedness, overlap and nuisance regularity assumptions remain.
Normalized IPW/custom-weight approximation warnings remain as well.

The returned `RepeatedCausalEstimate` contains each partition's estimate and
diagnostics; its primary `diagnostic_data` is `None`. With diagnostics enabled,
`model.folds_repetitions_` has shape `(n_observations, n_rep)`. With diagnostics
disabled, that attribute is `None`; seeds and scalar per-repeat results remain.
The first integer split seed matches `random_state`; later seeds are generated
locally and recorded. Learner seed parameters are preserved, so deterministic
or explicitly seeded learners are needed for reproducible predictions.
Repetitions run sequentially; `n_jobs` controls fitting within each partition.
Storage and fitting cost grow with the number of repetitions.

Relative percentage effects are aggregated separately, and are undefined if
any partition has undefined relative inference. Repeated fits require
`overlap_policy="clip"` to keep a common sample. GATE/GATET, CATE prediction and
sensitivity aggregation are unavailable for repeated fits. Multi-treatment and
IV repetition are not implemented by this API. `n_rep=1` keeps the existing
single-partition behavior; repetition counts must be positive integers.

## RCT data with multiple outcomes and treatment arms

```python
from causalis.data_contracts import RctCausalData

data = RctCausalData.from_df(
    df,
    treatment="treated",
    outcomes=["revenue", "purchases", "retention"],
    confounders=["age", "prior_spend"],
    user_id="customer_id",  # optional
)
Y = data.Y  # DataFrame, including when only one outcome is specified
X = data.X
revenue_data = data.for_outcome("revenue")  # CausalData for existing estimators
```

For multiple arms, supply one-hot columns including the control arm:

```python
data = RctCausalData.from_df(
    df,
    treatment_names=["variant_a", "control", "variant_b"],
    control_treatment="control",
    outcomes=["revenue", "purchases", "retention"],
    confounders=["age", "prior_spend"],
)
D = data.D  # treatment matrix, with control first
revenue_data = data.for_outcome("revenue")  # MultiCausalData for multiple arms
```

Every row must belong to exactly one arm, and every arm must be represented.
A single binary column uses 0 as control; omit `control_treatment` in that case.

This contract stores one independent copy of the selected columns and validates
shared treatment/confounders once. It checks missing values column by column and
screens duplicate columns with fingerprints before exact comparisons. Outcomes
and confounders must be finite, real numeric or boolean, and non-constant;
each treatment column must contain both 0 and 1. Identical columns are rejected.
`Y`, `D`, `X`, and `get_df()` return copies; `for_outcome()` copies and validates a
single-outcome subset using the destination contract's constraints, including
`MultiCausalData`'s limit of 15 arms. Existing estimators consume that
`CausalData` or `MultiCausalData` subset. Validation checks data structure;
it does not establish that treatment assignment was randomized.

To measure construction time and retained data size on your machine, run
`.venv/bin/python benchmarks/rct_causal_data.py --rows 1000000 --outcomes 32 --arms 3`.

### CUPED with RCT data

Generate a reproducible experiment using the internal DGP outcome families and
covariate samplers:

```python
from causalis.dgp import generate_rct_causal_data

data = generate_rct_causal_data(
    n=20_000,
    n_treatments=3,
    d_names=["control", "variant_a", "variant_b"],
    confounder_specs=[{"name": "prior_spend", "dist": "normal"}],
    outcome_specs=[
        {"name": "revenue", "alpha_y": 20, "beta_y": [3], "theta": [1, 2]},
        {"name": "purchases", "alpha_y": 10, "beta_y": [2], "theta": [0.5, 1]},
    ],
    seed=42,
)
```

Each outcome supports `continuous`, `binary`, `poisson`, or `gamma`. `theta`
sets arm effects on the family's link scale; the example uses continuous
outcomes, so revenue effects are exactly 1 and 2. For a binary treatment column,
set `n_treatments=2, treatment_encoding="binary"`. Use
`return_causal_data=False, include_oracle=True` for a DataFrame containing
allocation probabilities, potential-outcome means, and natural-scale effects.
Random assignment is shared across outcomes; rare missing arms raise an error
instead of changing sampled assignments.

```python
from causalis.scenarios.cuped import CUPEDModel

model = CUPEDModel().fit(data, covariates=["prior_spend"])
estimates = model.estimate()  # estimates[outcome][active_arm]
estimates.summary(outcome="revenue")  # formatted comparisons, side by side
revenue_a = estimates["revenue"]["variant_a"]

# Fit just one comparison when needed:
revenue_model = CUPEDModel().fit(
    data, covariates=["prior_spend"], outcome="revenue", treatment="variant_a",
)
revenue_a = revenue_model.estimate()  # CausalEstimate
```

CUPED compares each active arm only against the declared control and centers
covariates over those two arms. It shares the design matrix and decomposition
across outcomes within each comparison. Pass `covariates=[]` for unadjusted
estimates. One fitted comparison returns a `CausalEstimate`; multiple comparisons
return `RctEstimates`, preserving nested outcome/arm dictionary access.
`estimates.summary(outcome="revenue")` displays all arms for an outcome using
the same field and confidence-interval formatting as `CausalEstimate.summary()`.
Omit `outcome` to show every outcome, or add `treatment` to select an arm.
The same selectors work in `estimate()` and
`summary_dict()`. Batch `assumptions_table()` adds outcome and treatment columns.
Confidence intervals and p-values are per comparison, without multiplicity
adjustment. Existing `CausalData` inputs retain their single-estimate behavior.

CUPED keeps `treatment_mean` and `control_mean` as raw observed group means.
The additional `adjusted_control_mean` (regression intercept) and
`adjusted_treatment_mean` (intercept plus treatment coefficient) are evaluated
at the comparison sample's mean covariates. Their difference equals the adjusted
ATE; the difference of raw means may not. Both pairs appear in the summary.
The default relative effect is `100 * ATE / adjusted_control_mean`.
Choose `relative_denominator="raw_control"` explicitly to divide by the observed
control mean instead; the summary reports which denominator was selected.
CUPED preserves consistency and asymptotic unbiasedness under randomization
and standard regularity conditions; finite-sample bias need not be zero.

The comparison benchmark is
`.venv/bin/python benchmarks/cuped_rct.py --rows 100000 --outcomes 8`.
It disables optional regression checks with `run_checks=False`; ordinary fits
keep their configured checks.

### Plan an experiment: sample size and MDE

Use a past `RctCausalData` to estimate future sample size or sensitivity from
**historical control rows only**. Both calculators require one explicit `outcome`.
Omitted covariates, `None`, and `[]` use classic unadjusted planning, even when
the data declares confounders. Pass an explicit list to enable CUPED. With the
`data` from the example above:

```python
from causalis.shared.rct_design import calculate_mde, calculate_sample_size

allocation = {"control": 0.5, "variant_a": 0.25, "variant_b": 0.25}

# Classic planning: separate experiments for relative MDEs [0.5, 1, 5, 10, 20]%.
sizes = calculate_sample_size(data, outcome="revenue", allocation=allocation)

# Custom relative targets: 1 means 1%, not 100%.
custom = calculate_sample_size(
    data, outcome="revenue", scenario="user", mde_type="relative",
    mde=[1, 3, 5], allocation=allocation,
)

# CUPED sample-size planning with absolute effects in revenue units.
adjusted_sizes = calculate_sample_size(
    data, outcome="revenue", covariates=["prior_spend"],
    scenario="user", mde_type="absolute", mde=[0.5, 1, 2],
    allocation=allocation, include_details=True,
)

# Classic sensitivity for an exact total audience of 30,000 participants.
sensitivity = calculate_mde(
    data, outcome="revenue", sample_size=30_000, allocation=allocation,
)

# CUPED sensitivity for the same audience and allocation.
adjusted_sensitivity = calculate_mde(
    data, outcome="revenue", sample_size=30_000, covariates=["prior_spend"],
    allocation=allocation, include_details=True,
)

# Format for presentation without rounding the underlying numeric results.
print(sizes.to_string(index=False, formatters={
    "mde_relative": "{:.1f}%".format,
    "mde_absolute": "{:.3f}".format,
    "n_control": "{:,.0f}".format,
    "n_treatment": "{:,.0f}".format,
    "n_total": "{:,.0f}".format,
}))
```

`calculate_sample_size` takes MDE targets and returns required sample sizes.
`scenario="default"` uses the preset percentages and rejects custom `mde` or
`mde_type`. `scenario="user"` requires both a type and a nonempty sequence of
finite positive targets; input order and duplicates are preserved.
`calculate_mde` takes one positive integer `sample_size` across all future groups
and returns absolute and relative MDE for each active arm.

Both return unrounded numeric DataFrames with compact columns `outcome`,
`control`, `treatment`, `mde_relative`, `mde_absolute`, `n_control`, `n_treatment`,
and `n_total`. The MDE columns describe **requested targets** in sample-size
results and **calculated sensitivity** in MDE results. Relative values are
percentages of the raw historical control mean: with baseline 10, a relative
input of 1 corresponds to an absolute difference of 0.1. Relative target planning
requires a positive mean. Absolute target planning and MDE calculation remain
available for nonpositive means, with relative output set to NaN.

`include_details=True` appends `baseline_mean`, `variance_raw`, `variance_used`,
`variance_reduction_pct`, `n_reference`, `alpha`, and `power`. Sample-size results
also include `achieved_power` after rounding. Classic planning uses raw sample
variance (`ddof=1`) without fitting a regression; `variance_used` equals
`variance_raw` and variance reduction is zero. CUPED uses only explicitly selected
pre-treatment confounders and residual variance `SSE / (n_reference - design_rank)`.
Historical variance is estimated once for all targets.

All declared groups participate in each future experiment. Allocation defaults
to equal shares; custom shares must be positive and sum to one. For a binary
treatment column `d`, use keys `"d=0"` and `"d=1"`. For each sample-size target,
take the largest continuous requirement across active arms and round every group
up. MDE calculations preserve the supplied total using largest remainders, with
ties resolved in contract order, control first. Every group needs at least one
participant. `n_total` counts shared control once; do not sum it across rows.

Planning uses deterministic, two-sided normal power and assumes independently
randomized units with the same historical-control variance in every future arm.
Binary outcomes also use this fixed-variance approximation. `alpha` and `power`
are per comparison, without multiple-testing correction or a joint detection
guarantee. Control-constant covariates are dropped with a warning; singular CUPED
fits, insufficient residual degrees of freedom, and zero or non-finite variance
raise errors. Estimated variance reduction can be negative and is not clipped.

**Breaking API change:** the old `calculate_cuped_mde` and
`calculate_cuped_sample_size` names and CUPED design module are removed. Use the
shared calculators above; there are no aliases or deprecation wrappers. The old
shared summary-statistics `calculate_mde` API (`baseline_rate`, `variance`,
`ratio`, and `data_type`) is also removed. Both new APIs require `RctCausalData`
and a single `outcome`; the previous multi-outcome mapping interface is removed.

## Binary sensitivity protocol for observational DML/IRM

Pre-specify a practically meaningful effect boundary and one or more
domain-justified groups of observed **pre-treatment** confounders. The primary
decision uses element-based long/short gain statistics for the benchmark
group. Its `r2_y`, `r2_d`, and `rho` are calibrated jointly from the outcome
variance, Riesz-representer variance, and actual effect shift. The 2× strength
and forced `rho=1` scenarios are reported as secondary stress tests.

```python
from causalis.scenarios.unconfoundedness.refutation import run_sensitivity_protocol

# Example only: replace with a domain-justified, pre-specified group.
primary_group = list(causaldata.confounders[:2])

protocol = run_sensitivity_protocol(
    model,
    causaldata,
    benchmark_groups={"primary_domain_benchmark": primary_group},
    decision_threshold=0.0,  # replace with the minimum practical effect
    direction="auto",  # default: infer direction relative to the threshold
    preconditions_passed=True,  # causal set, overlap, nuisance quality, stability
)

print(protocol["status"])
print(protocol["summary"])
protocol["primary"]
protocol["stress"]
protocol["adversarial"]
```

`PASS` means every primary benchmark's bias-aware confidence interval remains
strictly beyond `decision_threshold` in the requested direction. `RV` and
`RVa` are reported as robustness diagnostics, not compared with universal
cutoffs. An empty benchmark set, failed external preconditions, unavailable
sensitivity elements, or strengths outside the finite sensitivity domain
produce `FAIL`.

By default, `direction="auto"` selects positive when the original estimate is
at or above `decision_threshold`, and negative otherwise. It uses this same
direction for every scenario and returns it in `protocol["direction"]`, with
an inference warning in `protocol["warnings"]`. For a negative estimate at a
zero threshold, every primary CI must have `ci_upper < 0`; touching or crossing
zero still fails. Thresholds retain their supplied sign, and an estimate equal
to the threshold does not pass. Use explicit `direction="positive"` or
`direction="negative"` for a pre-specified directional claim; these choices are
never overridden. Significance before sensitivity analysis alone does not
guarantee a pass.

Benchmark boundary handling matches DoubleML: raw `cf_y` and `cf_d` are
clipped to `[0, 1]`. If either long/short gain is not strictly positive,
primary and stress use `rho=sign(theta_short-theta_long)`; the adversarial
scenario still forces `rho=1`. `protocol["benchmarks"]` retains raw gains,
clipping/fallback flags, long/short elements, and warnings for auditability.
In particular, a negative `cf_d_raw` becomes a numerical `cf_d=0` boundary
benchmark rather than a missing scenario.

## One-way clustered binary IRM

```python
# Labels correspond to the same rows and order as data.df.
model = IRM(data, ml_g=ml_g, ml_m=ml_m, cluster_groups=cluster_labels,
            n_folds=4, n_rep=3, random_state=3141).fit()
ate = model.estimate(score="ATE")
atte = model.estimate(score="ATTE")
```

`cluster_groups` is a one-dimensional vector of nonmissing scalar labels. A
pandas Series must have exactly the input DataFrame index in order. Fit snapshots
integer membership; later label/configuration changes require refitting. Labels
are not automatically added to confounders. This argument is separate from the
subgroups passed to `estimate(groups=...)` for GATE.

Whole clusters are held out together using shuffled KFold over first-occurrence
cluster codes, balancing cluster counts. Row counts and treatment proportions
may differ across folds. Each training complement must contain both arms; an
unsupported split raises before that partition's learners fit. There is no
row-level fallback or random retry. `cluster_split_seed_` records the realized
seed for a single partition, including when `random_state=None`; repetitions
use the recorded B22 repetition seeds. Learner RNG settings remain unchanged.

ATE and ATTE keep the original observation-weighted targets. Absolute, baseline
and relative delta-method SEs use one-way CR1: with n rows and G clusters,
`SE² = G/(G−1) × sum_g[sum_{i in g}(IF_i − mean(IF))]²/n²`.
All singleton clusters reduce to the iid ddof=1 variance. Normal Wald inference
requires many independent clusters, no dominating cluster, suitable nuisance
rates, unconfoundedness, overlap and no interference. The correction does not
guarantee coverage with few clusters or fix identification. Custom-weight and
normalized-IPW approximation flags still apply. Repeated partitions aggregate
the cluster SEs by the same median-variance policy; they have no single IF.

Cluster fitting requires clipping, at least `n_folds` clusters and at least two
clusters. Results identify `inference="one_way_cluster_cr1"`, `n_clusters` and
`cluster_target="row_weighted"`. Membership remains necessary in lightweight
mode. Cluster GATE/GATET, CATE scoring and sensitivity reject explicitly;
multiway clustering, cluster bootstrap, few-cluster inference and grouping for
multi-treatment/IV models are separate follow-ups.

## External OOF predictions for binary IRM

```python
# Predictions and fold_ids were produced by your external cross-fitting code.
# All arrays refer to the original data.df rows, in exactly the same order.
import numpy as np

predictions = {"g0": g0_oof, "g1": g1_oof, "m": propensity_oof}
model = IRM(data, n_folds=4)
training_indices = [[np.flatnonzero(fold_ids != fold).tolist()
                     for fold in range(4)]]
manifest = model.make_oof_manifest(
    predictions, folds=fold_ids, training_indices=training_indices,
    split_seeds=[3141],
)
result = model.fit(external_predictions=predictions,
                   oof_manifest=manifest).estimate(score="ATE")
```

Supply all three nuisances; partial replacement is unavailable. With `n_rep=1`,
predictions and folds must be vectors `(n,)`. With repetitions, they must have
shape `(n, n_rep)`; training indices are nested as repetition, fold, row
positions, and `split_seeds` contains one recorded uint32 seed per repetition.
Each outer training sample must equal its held-out fold's complement and
contain both treatment arms. Folds must cover `0..n_folds-1`. When
`cluster_groups` is supplied, each cluster must belong to one held-out fold.
The inherited support guard also requires at least `n_folds` rows per arm.

The version-1 manifest binds ordered numeric data, row index, variable roles,
cluster membership and prediction hashes. Pandas predictions require exactly
the input index in order, including duplicates; arrays are positional. Inputs
are copied. Values must be real and finite; propensities and binary-outcome
predictions must lie in `[0, 1]` before propensity clipping. External fits
require `overlap_policy="clip"` and reject private fixed folds.

All preprocessing, tuning and nuisance fitting must use only the recorded outer
training samples; outcome learners use the corresponding treatment subsets.
Validation checks the caller's declarations and alignment, and cannot prove
the history of an external program. Rebuilding a manifest around leaked or
misordered predictions does not make them valid OOF predictions. Time-series
splitting, independent external training samples and arbitrary train subsets
need separate contracts.

Fit invokes no nuisance learner methods and draws no split RNG. Supplied folds
are used directly; `random_state` does not override recorded manifest seeds.
ATE/ATTE use the existing scores, iid or one-way cluster SE and relative-effect
policy. Repetitions use median-variance aggregation without dividing by their
count. Identification, nuisance-rate and independent-unit/cluster assumptions
still apply. Results record `nuisance_source="external_oof"` and manifest
version; full training indices remain private. External GATE/GATET, CATE
prediction and sensitivity inference reject, including direct adapters.

## DR and R conditional-effect learners

The existing `irm.predict_cate(X_new)` uses a lazy T-learner. Separate DR and R
learners regress cross-fitted signals to predict the conditional average effect
`E[Y(1) - Y(0) | X=x]`:

```python
from causalis.scenarios.uplift import DRLearner, RLearner

# irm is already fitted. X_new contains independently collected covariates
# in the same feature schema; do not reuse training rows for validation.
dr = DRLearner().fit(irm)  # default final regressor: LinearRegression
r = RLearner().fit(irm)
dr_predictions = dr.predict(X_new)
r_predictions = r.predict(X_new)
```

Both require an internal, single-partition, iid, unweighted binary IRM fit with
`overlap_policy="clip"`, nonempty confounders and fitted propensities strictly
inside `(0, 1)`. External OOF, cluster, repeated, drop and custom-weight fits
reject. The source sample/index/roles must still match its fit snapshot, even
without diagnostics. Final regressors are cloned and fitted separately; failed
refits retain the previous predictor. Later source IRM changes do not affect a
fitted predictor. DataFrames reorder required features and may include extras;
duplicate columns, missing features, complex and non-finite values reject.

DR uses unnormalized AIPW pseudo-outcomes; IRM's scalar ATE/ATTE choice and
`normalize_ipw` do not change these targets. R fits the squared residual loss
using `q=(1-e)*g0+e*g1` as its OOF marginal outcome pilot, transformed targets
`(Y-q)/(D-e)` and weights `(D-e)^2`. An optional `ml_tau` must be a cloneable
regressor; for R it must support and honor `sample_weight` with squared loss.
Regularization follows that estimator. A restricted final model approximates
CATE; the population R-loss projection weights covariates by `e(x)*(1-e(x))`.

Identification requires consistency, unconfoundedness and overlap. OOF
nuisances exclude each row's fold; the final effect model trains on all rows.
Its training predictions are in-sample. Tuning and evaluation require independent
data or outer refits of the entire pipeline, including preprocessing and
nuisances. Ordinary CV on already computed pseudo-outcomes can leak information.
These predictors provide no automatic calibration, individual counterfactuals
or CATE confidence intervals. Binary-outcome predictions use the risk-difference
scale and are not forcibly bounded to `[-1, 1]`. Use the held-out validator below;
no generic rate or coverage guarantee is claimed. Method references:
[Kennedy's DR learner](https://arxiv.org/abs/2004.14497) and
[Nie–Wager's R learner](https://arxiv.org/abs/1712.04912).

## Held-out nuisance and CATE validation

Reserve an independent validation sample before training, preprocessing and
hyperparameter selection. Both `CausalData` objects must declare the same stable,
unique `user_id` role; DataFrame row indices are not identities. For an already
fitted training IRM:

```python
from causalis.scenarios.uplift import HeldOutCATEValidation, RLearner

validation = HeldOutCATEValidation(learner=RLearner()).fit(irm)
metrics = validation.evaluate(validation_data)
print(metrics.propensity_brier, metrics.r_loss, metrics.dr_gain_vs_zero)
```

The validator clones and fits its effect learner using the training IRM's OOF
signals. It separately refits copies of the **current** `irm.ml_g`/`irm.ml_m`
templates on the full training sample (outcome models by arm). These evaluation
pilots are distinct from IRM's discarded fold models. Templates, source IRM and
lazy T-learner cache are unchanged; failed refits preserve the last complete
validator. Evaluation performs predictions and aggregate calculations only.
Stable identities must be disjoint, features and outcome/treatment/identity
roles must match, both binary treatment arms must appear, and observations and
predictions must be real and finite. The source restrictions are the same as
DR/R learners: internal, single-partition, iid, unweighted, clip overlap.

`CATEValidationResult` is an immutable aggregate record. Outcome MSE by arm is
factual predictive error, on each arm's observed covariate distribution. Brier
and log loss assess raw propensity predictions; the result also records their
range and how many were clipped at IRM's **fit-time** overlap threshold for the
causal signals. Raw probabilities outside `[0, 1]` reject. Log loss separately
bounds probabilities at machine epsilon; it does not use the overlap-clipped
probabilities. DR loss is the mean squared error against held-out AIPW signals.
It includes pseudo-outcome noise and is **not observed CATE MSE**.
`dr_gain_vs_zero` is the zero-effect loss minus candidate loss, computed directly
as `mean(2*signal*tau - tau**2)`; larger is better. R loss is
`mean((Y-q-(D-e)*tau)**2)`, with derived `q=(1-e)*g0+e*g1`; smaller is better.
Only compare candidates on the same sample with the same evaluation pilots.

With oracle pilots, DR loss differences equal unweighted CATE risk differences,
and R loss differences measure CATE risk weighted by `e(x)*(1-e(x))`.
Estimated pilots, active propensity clipping and confounding can bias these
criteria. Disjoint IDs do not prove independence or detect relabelled records
or hidden preprocessing leakage. These diagnostics provide no test of
unconfoundedness, calibration guarantee, causal intervals or model superiority
claim. No individual outcomes, scores or residuals are returned.

If validation metrics select or tune a model, use a new independent test for
final assessment. For nested outer validation, start with each outer training
sample: refit preprocessing and all nuisances there, construct a fresh IRM and
validator, then evaluate the outer validation sample with training-fitted
transformations. Do not slice or cross-validate pseudo-outcomes computed once
on the complete sample. This API handles independent validation; it does not
orchestrate nested splitting or preprocessing.

# Pick your scenario

| Scenario                                                                                   | Estimator                                                 | Assumptions                                                                                                                     |
|--------------------------------------------------------------------------------------------|-----------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| [Classic RCT](https://causalis.causalcraft.com/articles/classic_rct)                       | Difference in means (ttest, ztest, welch_permutation_t_test)             | Random assignment, no sample ratio mismatch, SUTVA                                                                              |
| [CUPED](https://causalis.causalcraft.com/articles/cuped)                                   | CUPED-adjusted difference in means with Lin specification | Random assignment, no sample ratio mismatch, SUTVA, valid pre-period metrics                                                    |
| [Unconfoundedness](https://causalis.causalcraft.com/articles/unconfoundedness)             | DML IRM                                                   | Unconfoundedness, Overlap, SUTVA, No leakage, Score stability                                                                   |
| [GATE](https://causalis.causalcraft.com/articles/gate)                                     | DML IRM (GATE and GATET)                                  | Same assumptions as unconfoundedness, plus meaningful pre-specified or validated subgroup definitions.                          |
| [Multi Unconfoundedness](https://causalis.causalcraft.com/articles/multi_unconfoundedness) | Multi DML IRM                                             | Unconfoundedness, Multi class Overlap, SUTVA, No leakage, Score stability                                                       |
| [Synthetic Control](https://causalis.causalcraft.com/articles/synthetic_control)           | ASCM                                                      | No interference / spillovers, No anticipation, The treated unit’s untreated outcome path is well approximated by the donor pool |
| [Difference in Difference](https://causalis.causalcraft.com/articles/did)                  | CallawaySantAnnaDID                                       | Parallel trends, no anticipation, stable group composition, no spillovers between treated and control groups.                   |
| [IV](https://causalis.causalcraft.com/articles/iv)                                         | DML IV                                                    | First-stage strength, Reduced form, Instrument balance by Z, Instrument propensity / predictability                             |
| [Uplift / CATE scoring](https://causalis.causalcraft.com/articles/uplift)                  | T-learner, DRLearner, RLearner                              | Consistency, unconfoundedness, overlap; validate generalization on independent data.                                            |

[Introduction to Causal Inference](https://causalis.causalcraft.com/articles/introduction-to-causal-inference): guide

See scenario notebooks: https://causalis.causalcraft.com/explore-scenarios

# [Contributing guidelines](https://github.com/causalis-causalcraft/Causalis?tab=contributing-ov-file)

# Maintainers

[Ioann Martynov](https://www.linkedin.com/in/ioannmartynov/)

# References

https://github.com/DoubleML/doubleml-for-py

## Inference for prespecified effect families

```python
from causalis.inference import InferenceFamily

# Both fitted IRMs describe the same ordered stable user IDs and treatment.
# Each may have a different outcome, feature set and cross-fitting partition.
family = InferenceFamily.from_irm({"revenue": revenue_irm, "retention": retention_irm}, score="ATE")
family.infer(alpha=.05, method="bonferroni").summary()
family.infer(alpha=.05, method="max-t", n_boot=1999, random_state=42).summary()

# Prespecified contrasts in commensurate units form their own declared family.
contrast = family.contrast([[1., -1.]], names=["difference"])
contrast.infer().summary()
```

The target is a fixed vector of population scalar effects. `from_irm` supports
absolute ATE or ATTE from internal, single-partition, iid, unweighted binary IRM
fits with overlap clipping and `normalize_ipw=False`. It validates unchanged
fit-time data and unique, nonmissing stable user IDs in the same order, plus the
same treatment role and values. Different outcomes, confounders and folds are
allowed. It computes effects and influences without fitting, predicting,
updating source inference caches or drawing random numbers. The family owns
its snapshot; later changes to source models do not change family inference.
External OOF, clustered, repeated, trimmed and weighted fits are rejected.
These limits apply to the adapter; passing such rows to the generic interface
does not establish a valid iid influence representation.

For other regular iid estimators, use
`InferenceFamily(values, influence, names)`, with values shape `(p,)` and raw
observation-scale influences shape `(n, p)` on the **same ordered units**.
Do not divide the influences by sample size. Empirically centered influences
give covariance `IF.T @ IF / (n*(n-1))`. Each column needs positive variance;
singular dependence across nondegenerate columns is supported. `covariance`
returns a detached aggregate matrix. `contrast(L, names)` transforms both
effects and influences, preserving dependence. Contrasts must have meaningful
units and be declared before inspecting results.

Bonferroni uses normal marginal p-values, adjusted p-values `min(1, p*p_value)`
and critical value `norm.isf(alpha/(2*p))`. Max-t shares Gaussian multipliers
across columns, studentizes each perturbation using the same iid variance, and
uses the maximum absolute statistic. It processes draws in batches of at most
256; it perturbs scores rather than refitting the causal pipeline. Its local
Generator preserves global/source RNG state. Choose enough draws for the
desired tail accuracy: at least 99, with `alpha >= 1/(n_boot+1)`; integer seeds
must be uint32. Cross-version exact RNG reproducibility is not promised.
Finite-draw adjusted p-values are `(1+exceedances)/(n_boot+1)`, including ties;
the band critical value uses ordered draw `ceil((1-alpha)*(n_boot+1))`.
These are Monte Carlo approximations, not exact randomization p-values.

Results contain only aggregates, simultaneous two-sided absolute confidence
bands, marginal and family-adjusted p-values, and explicit method/draw metadata.
`null` may be a scalar or one value per effect; it changes tests but not bands
centered on estimates. Rejection uses adjusted p-value `<= alpha`; finite-draw
ties can differ from open-band endpoint comparisons. `summary()` returns a
fresh table. Bonferroni uses no bootstrap draws and records `n_boot=0`.

Family error control and coverage are **asymptotic**, conditional on a valid
joint influence representation, moments and nondegenerate variances. Causal
interpretation additionally needs consistency, conditional exchangeability,
overlap and appropriate nuisance convergence. Estimated nuisances, active
clipping or confounding can bias the effects; multiplicity correction cannot
remove that bias. Stable IDs cannot verify independence, hidden preprocessing
leakage or selection history. A family selected after inspecting outcomes,
validation scores or effect estimates requires separate selection inference or
an independent sample. This API supplies no pointwise CATE intervals,
finite-sample coverage certificate, arbitrary growing-family theorem,
Romano-Wolf stepdown, weak-IV or cluster inference.

## Weak-instrument inference for binary-IV LATE

```python
from causalis.scenarios.iv import IIVM, WeakIVInference

iv = IIVM(normalize_ipw=False).fit(iv_data)
robust = iv.estimate_weak_iv(alpha=0.05, null=0.0)
print(robust.confidence_set)  # a tuple of closed interval components
print(robust.set_type, robust.p_value)
robust.contains(1.0)
robust.summary()  # aggregate results only

# Snapshot once to test additional candidates without touching the fitted model.
snapshot = WeakIVInference.from_iivm(iv)
snapshot.infer(null=2.0)
```

The method tests the orthogonal moment `mean(phi_y - theta*phi_d) = 0`
without dividing by the estimated first stage. The squared studentized moment
uses empirically centered covariance of the signal means, with `ddof=1`, and
an asymptotic chi-square(1) cutoff. It inverts the complete quadratic inequality
over the real line. A result can be a bounded interval, two rays, one half-line,
a singleton, the entire real line, or empty. Infinite endpoints mean unbounded
components. Keep the entire tuple: taking its minimum and maximum would fill
an excluded gap. Boundaries are included; `is_significant` uses a strict
statistic-above-cutoff comparison. No finite search grid or effect bounds are
imposed, and no first-stage strength pretest selects the inference method.

The original `estimate()` still returns the existing Wald estimate and
interval; `estimate_weak_iv()` neither changes its caches/diagnostics nor
requires it to succeed. Only single-partition, unnormalized `truncate` IIVM
fits are supported. The adapter uses the successful fit's copied observations
and nuisance arrays; later live-data edits do not change them. A snapshot owns
its signals and survives later model edits. Public fitted-array mutation is
not certified. Generic `WeakIVInference(phi_y, phi_d)` accepts aligned iid
observation-scale signals of shape `(n,)`, with `n >= 2`; it does not establish
their validity or provide a cluster/weighted/repeated-split workaround.

Causal LATE needs consistency, conditional IV exogeneity, exclusion,
monotonicity, overlap, and a nonzero population complier share. At exactly zero
population first stage a unique complier LATE may not exist; the procedure
still tests the moment. Its weak-IV robustness is asymptotic and conditional
on a valid null-score CLT, positive limiting score variance, adequate moments,
and negligible nuisance-estimation remainder. Uniform validity across weak-IV
sequences requires these conditions uniformly. Arbitrary learners or ordinary
cross-fitting do not certify them. Clipping, nuisance misspecification, invalid
instruments or adaptive selection can invalidate inference. This is a scalar
orthogonal AR-style test with Fieller inversion, not a finite-sample AR/F test,
CLR procedure, sensitivity analysis or identification diagnostic.

Singular joint signal covariance is allowed. A requested null with zero
empirical score variance is rejected; other such candidates retain the
algebraic inequality in the returned set without a coverage claim at degenerate
points. Complex/nonfinite/misaligned inputs are rejected. Float64 determines
near-boundary geometry; no tolerance silently removes a quadratic term.
Unrepresentable finite roots, statistics or underflowed coefficients raise.
Common rescaling of the signals can improve arithmetic but does not change
statistical assumptions or cure an extreme difference between their scales.

## Search terms / supported methods

Causalis covers methods often searched as:

- causal inference Python
- causal machine learning Python
- treatment effect estimation
- A/B testing Python
- randomized controlled trial analysis
- CUPED Python
- Double Machine Learning Python
- DML / IRM
- CATE estimation
- uplift modeling
- propensity score diagnostics
- synthetic control Python
- difference-in-differences Python
