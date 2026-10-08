# B30 — known policy costs and empirical capacity

9 October 2026, macOS, repository-local Python3.12.14. Branch
`codex/correctness-roadmap`; baseline `15f316dc086e658b7cb5567448025f32b7e2f23a`;
source `d4b8f62a281c37e98b44941f12314de073cad721`.
Implementation committed and pushed under the user's persistent explicit
«Разрешаю пуш в нашу ветку». Final audit checkpoint is recorded by `git log -1`.
**Completed:** local focus/correctness/strict docs, all six CI artifacts and
root `--require-ci` verified. Final audit commit/push follows source freeze.

## Scope and statistical contract

Higher outcomes are better. For fixed policy pi(Z), known nonnegative
incremental treatment cost C(X), and potential outcomes Y(1), Y(0), the target is

```
V_C(pi) = E[pi(Z) * (Y(1) - C(X)) + (1 - pi(Z)) * Y(0)]
```

Value comparisons are relative to treating nobody/everybody, not absolute
expected outcomes. Cost has the same units as outcome: monetary cost with a
nonmonetary outcome needs a prespecified conversion. Do not subtract costs
already included in outcome. Cost is known at decision time and measured before
treatment, not estimated by this module or derived from realized outcomes.
Negative incremental costs, learned cost models, uncertain treatment-dependent
resource usage, monetary budgets and randomized/fractional leaves are outside
this contract. Both scalar and heterogeneous observed known costs are supported.

Identification requires consistency/no interference, unconfoundedness given
IRM confounders and overlap. Normal approximation requires iid score limits,
suitable nuisance estimation and negligible remainder. Cross-fitting alone does
not establish these. Clipping can bias signals. Costs do not repair
confounding, misspecified nuisances, inadequate overlap or clipping bias.
No new general rate, finite-sample coverage or optimal regret theorem is claimed.

Independent evaluation conditions on the fixed learned policy, its cost
definition and its partition. It excludes retraining variability. Split before
learning/tuning either nuisance or policy models. Disjoint IDs detect overlap,
not hidden leakage or relabelling. Selection on evaluation results requires a
fresh test sample. Rule intervals are pointwise, not simultaneous or individual
effect intervals. Training reward/means are descriptive.

Primary reference: [Athey–Wager, Policy Learning with Observational
Data](https://arxiv.org/abs/1702.02896), consulted for the constrained
policy-learning formulation. This implementation's greedy partition plus
whole-leaf allocator is our limited algorithm, not their globally optimized
policy class or regret theorem. [Treatment Allocation under Uncertain
Costs](https://arxiv.org/abs/2103.11066) concerns a different uncertain-cost
problem; that cost estimation/priority-score procedure is not implemented here.

## Design alternatives and chosen API

Two alternatives were considered sequentially with `codebase-design`:

1. Extend the existing `UpliftPolicyTree` constructor with two defaults, freeze
   their successful-fit interpretation, reuse splitting/assignment and report
   evaluation on net signals. Existing callers remain unchanged. Numeric/raw
   context validation is strict for the new mode; source IRMs remain untouched.
2. Add a separate cost-policy class with composition or inheritance. Composition
   would require a second signal/partition API or duplicating the splitter;
   inheritance would couple overridden learning/evaluation to private tree
   state. It adds caller types and migration burden without a different policy
   representation. A batch-rationing policy also needs a separate inference
   contract because recipients depend on other batch rows.

Alternative1 was selected. The optional question about capacity semantics was
presented early; no answer arrived, so the stated training-sample interpretation
was used after providing time to reply. No required approval was pending.
Hard batch limits remain outside this block.

```python
from causalis.scenarios.uplift import UpliftPolicyTree

policy = UpliftPolicyTree(
    treatment_cost=0.5,  # or a known cost-confounder column name
    max_treatment_fraction=0.25,
).fit(train_irm, policy_features=["age", "score"])
evaluation = policy.evaluate(independent_eval_irm)
summary = evaluation.summary()
rules = evaluation.rules_summary()
```

Scalar costs are finite real nonnegative values, excluding bool/complex.
A column name must be a fitted confounder; raw numeric/nonnegative/finite/real
values are validated. It need not enter the policy predicates, but then
assignment cannot adapt to that cost individually. Assign requires policy
features and IDs only; cost is needed during training/evaluation.
Capacity is a finite real fraction in [0,1], excluding bool/complex/string.
Both nondefault-mode IRMs must be internal, single-partition, iid, unweighted,
clipped fits. Repeated, external-OOF and grouped/clustered fits reject explicitly.
Matching roles, immutable fit snapshots and unique disjoint IDs are checked.
Canonical unnormalized DR signals are independent of scalar ATE/ATTE and
normalize_ipw settings. Raw source data/nuisance shape/complex/finite guards
precede casts for the new mode. All old default behavior/columns are retained.

Successful fit owns the tree, rules, copied IDs, diagnostics and frozen scalar
or cost-column name. Later estimator parameter edits do not alter decisions or
evaluation. Failed refits retain the entire previous policy. Reports return
copies. No fit/estimate/predict callbacks, RNG consumption or source-model
mutation is needed during evaluation; no new dependency was added.

## Learning and capacity semantics

Let H_i = Gamma_i - C_i. Greedy growth uses leaf reward
`max(0, sum_leaf H_i)` and the old size/per-arm/depth constraints and tie
conventions. For nondefault settings the objective is scaled by a common
positive value to avoid unnecessary sum overflow. Nonfinite arithmetic and
lost nonzero normalized signals fail explicitly; no replacement scores are used.

After partition growth, each leaf l has training count n_l and total net
reward R_l. Binary knapsack solves

```
maximize sum_l a_l R_l
subject to sum_l a_l n_l <= floor(n_train * max_treatment_fraction)
           a_l in {0,1}
```

It optimizes over the **fixed learned leaves**, not all possible constrained
trees. Negative/zero-reward leaves stay off. Equal reward states retain earlier
choices; final reward ties prefer fewer recipients. Each state owns an immutable
selection bitset, avoiding mutable backtracking reuse. The cap is computed with
ordinary float64 multiplication/floor; close optimization ties retain float64
precision, not certified real-arithmetic optimality. The allocator uses at most
capacity+1 count states; O(leaves*capacity) iterations, excluding bitset cost.
No performance benchmark or general speedup is claimed.

Leaves are indivisible. Positive capacity need not be exhausted. A positive
constant root larger than the cap treats nobody. A greedy tree can miss a
useful constrained partition; an explicit counterexample is retained in tests.
No zero-gain split is forced just to make capacity spendable.

**Training-sample feasibility is the only capacity guarantee.** Frozen
pointwise `assign` does not rank, ration or truncate within a new batch.
A changed client composition can yield a treatment fraction above the training
limit, even one. There is no population-feasibility or deployment-budget claim.

## Independent net evaluation

For fixed actions a_i, comparisons use paired signals
`a_i H_i`, `(a_i-1) H_i`, `H_i`. Values are their full-sample means and standard
errors are centered sample standard deviation with ddof1 divided by sqrt(n).
Normal intervals use the requested alpha. Cost variation and covariance with
Gamma are included **inside** the signal, not subtracted after computing a
gross-value standard error.

In nondefault mode summary adds `gross_value` and signed `incremental_cost`;
`value = gross_value - incremental_cost` up to arithmetic rounding.
Rule `value`/HC3 intervals describe mean H irrespective of action, with
`gross_value`/`mean_cost` decomposition. Unsupported/empty rules keep explicit
statuses and unavailable effect intervals; their clients remain in the overall
evaluation. There is no synthetic individual-effect export or observed
individual-benefit claim. Training capacity never truncates evaluation clients.

## Verification and development history

All fixtures are synthetic; no corporate client records/IDs/attributes or
individual metric values were requested/downloaded. No SQL or corporate tools
were used. Existing source/tests outside the three-path diff are unchanged:
README, policy module, new cost/capacity test module.
The root verification counts152existing library/scripts/workflow Python/YAML
paths and all187existing Python test paths unchanged.

New cases:92. They cover24 exhaustive binary-choice knapsack oracles;
independent net split reward enumeration; whole-leaf counts/net priorities;
constant/zero-net actions; unused capacity and greedy constrained-optimum
counterexample; paired net value/variance/normal limits and HC3; variable-cost
sampling noise; pointwise batch reorder/empty behavior; clone/configuration and
failed-refit ownership; invalid costs/capacity/raw columns/nuisance arrays;
unsupported context metadata; rescaling1e-80/1/1e80; callback/RNG isolation;
default compatibility; overflow failure; empty/unsupported rule statuses.

Development records are preserved in [history manifest](block30_development_result.json):

- Initial legacy51passed.
- Initial new module72passed/5failed: four expectations incorrectly assumed
  all profitable subgroups would be split; one tiny-scale fixture lost its
  signal by adding1e-80 to unscaled outcomes. Corrected synthetic fixtures.
- Intermediate77passed/1known complex-cast warning; later strict raw checks
  eliminate that cast in the new mode.
- Expanded142passed/1failed: an unsupported-arm fixture used globally constant
  treatment, rejected by existing CausalData before policy evaluation.
- Expanded142passed/1failed: the revised empty-leaf fixture populated both
  actual greedy leaves. Corrected the fixture to a monotonic-effect partition.
- Final precommit143passed/0warnings/6.07s. Existing51cases are all retained.

The first root evidence invocation checked environment/exclusion fields in the
test-result JSON instead of the runner's selection JSON and raised KeyError.
The audit-only schema check was corrected; its initial log is preserved in
[initial root schema log](block30_initial_root_schema_checks.log). No source,
test result or evidence payload was changed to address that audit error.

Final committed local evidence:

- [Focused](block30_focus_result.json):380passed,7warnings,8.58s;92new.
- [Correctness](block30_integration_result.json):4374passed,157warnings,140.53s;
  zero failures/errors/skips, all4282B29case IDs retained.
- [Selection](block30_integration_selection.json): exactly the same seven
  named deferred DML sensitivity exclusions; this is not a full release gate.
- [Strict Sphinx](block30_docs_result.json):exit0,17.232s; no published HTML.
- [Handoff](handoff_validation.json):171immutable implementation links,issues[].
- [Root verifier](verify_block30.py): source scope/hashes, raw JUnits/case IDs,
  environments, docs hashes, development history, exact cleanup and CI artifacts.

CI run [37848086801](https://github.com/MaximLenivkin/Causalis/actions/runs/37848086801)
completed/success on exact source d4b8f62. All six downloaded artifacts have
4374passed, zero failures/errors/skips and strict docs exit0. Actual Python
versions:3.10.22 latest/legacy,3.11.17,3.12.15,3.13.16,3.14.8.
SnapshotUTC2026-10-08T21:42:52.761024+00:00. Full case sets/focus inclusion,
source/env/normalized args/seven exclusions and five artifact hashes per job
verified in the [CI manifest](block30_ci_result.json). One actual CI run,
no reruns, no failed CI/source-test gates. Linux representative stacks do not
cover all platforms/dependency combinations. Source/tests are frozen.

[Local root result](block30_local_validation_result.json) and
[final root result](block30_validation_result.json) have issues[];
the latter requires and validates all six exact-source CI jobs.

Only the exact owned focused/integration basetemps are removed after tests;
raw JUnits, logs, code and environment evidence remain under ignored runtime
trees. [Cleanup manifest](block30_cleanup_result.json) records actual paths.
No broad-prefix deletion or cleanup of earlier blocks is permitted.

Stop after B30 and let the user clear context. The original ordered feature
list ends with policy costs/capacity. No B31 is assigned automatically: next
session should review the remaining backlog/scope first. Hard deployment
capacity, uncertain costs, sensitivity upstream rewrite/SC08LOO/selected-U ATT,
multi-IV repetitions/grouping, few/multiway clusters and NumPy/RST debt remain
separate. No subagents, login/setup, dependency refresh, PR, upstream/main/
forcepush, release, notebooks, website or external messages were used.
