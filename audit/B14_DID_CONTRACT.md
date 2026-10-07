# B14: exact-zero DiD regression и диагностическая studentization policy

Дата: 2026-10-07, Europe/Moscow. Baseline: `dbded76ecf8a207aad2094903b8f015fed8ae5d6`. На начале проверки branch `codex/correctness-roadmap` имел clean working tree. Применён workflow `diagnosing-bugs`: pinned reproduction, отдельные falsifiable numerical references и реальные estimator/report seams. Reviewer не меняет library/tests/Git, не запускает integration/CI/network; собственные artifacts — этот документ, [probe](block14_contract_probe.py), [result](block14_contract_result.json).

Предыдущий фактический симптом описан в [B09 numerical note](B09_LOCAL_INTEGRATION_NOTE.md). B14 не меняет thresholds или sensitivity exclusions ради green status. Primary NumPy API references: [lstsq rank/minimum-norm contract](https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html), [local errstate context](https://numpy.org/doc/stable/reference/generated/numpy.errstate.html); root проверил эти official references. Математическое доказательство ниже независимо от документации NumPy.

## Estimand, дизайн и exact reference

Речь о fitted Callaway–Sant'Anna ATT(g,t) для eligible treated/comparison units с complete base/target observations. Для pre-period cells estimator оценивает placebo contrast, а не постулирует нулевую строку автоматически. В общем causal design нужные identifying assumptions включают отсутствие anticipation, соответствующий comparison set и conditional parallel trends; один numerical fixture не доказывает их для реальных данных.

Frozen public API fixture имеет шесть synthetic units, шесть monthly periods, два treated cohorts и два never-treated controls. Untreated outcome каждой unit — fixed baseline плюс общий slope1; cohort effects2/3 добавляются только после adoption. Covariate в base period задаёт design с unit intercept и одним numeric X. Каждый control design — full rank2 при двух controls: outcome regression saturated. Внутри treated cohorts оба units имеют один cluster, оба controls также в одном cluster.

Для каждой cell controls имеют **точно одинаковое** ΔY=c. Обозначим control design X_C. При full column rank и unit intercept β*=(c,0,…,0) удовлетворяет X_Cβ*=c·1 без residual. Уникальность следует из full rank: если X_Cβ=c·1, то X_C(β−β*)=0, а kernel содержит только0. Следовательно, этот exact solution не является tolerance или выбором произвольного solution among nonunique fits.

Estimator использует residual r=ΔY−Xβ и normalized weights W_T=D/q, W_C=control odds / empirical mean(control odds), у которых empirical means равны1. ATT = E_n[(W_T−W_C)r]. В fixture pre-period r=0 для всех units → ATT0. В post-period r_C=0, r_T=cohort effect τ, одинаковый у treated units → ATTτ, поскольку E_n[W_T]=1.

Cell IF состоит из centered treated/control residual terms и estimated-nuisance terms. Здесь η_T=τ, η_C=0; W_T(r−η_T) и W_C(r−η_C) нулевые. OLS nuisance term умножается на control residual0. Propensity derivative тоже использует control residual−η_C=0. Поэтому **все cell IF scores и cell variances точно0** как до, так и после treatment. Это не утверждение о variance simple aggregate: estimated cohort-share weights при разных effects2/3 могут добавлять собственный aggregate IF.

Tiny floating residues исходного solver не имеют отношения к материализованному pre-effect. На baseline responsible cell0 имеет ATT `1.1102230246251558e-16`, SE `2.9351198205368013e-31`, |t| `378254753641406.06`. OLS β примерно `(0.9999999999999993, 1.570092458683775e-16)` вместо exact `(1,0)`. Design full rank и condition number около13.6; blanket conditioning warning не объясняет этот defect.

## Согласованный numerical contract

Bounded runtime scope — `causalis/scenarios/did/model.py` и `causalis/scenarios/did/refutation/post_inference.py`; root/test agent владеют implementation и regression/fixture edits.

В `_fit_outcome_regression` сохранить exact β=(c,0,…,0) только если одновременно:

1. Existing `np.linalg.lstsq(..., rcond=None)` **возвращает full column rank**.
2. Первая design column буквально состоит из1 для всего prediction design.
3. Control responses буквально равны одному representable c, без `isclose`, scale threshold или epsilon.

Остальные fits сохраняют обычный solver result. Zero-column private-helper case не индексирует отсутствующую intercept column. Solver-reported rank важен: это тот же numerical rank convention, которым выбран ordinary least-squares solution. Branch сохраняет tiny representable treated departures: constant-control response не означает, что treated responses тоже должны быть constant/zero.

Global response-centering плюс intercept shift нельзя применять как blanket equivalent correction. При rank deficiency minimum-norm solution меняется, а с ним extrapolation на treated X: controls `[1,1],[1,1]`, ΔY1 дают minimum-norm β≈(.5,.5). Для treated designs `[1,2]`/`[1,3]` predictions≈1.5/2. Centered response plus restored intercept даёт β=(1,0), predictions1/1. Поэтому full-rank restriction substantive; rank-deficient source path остаётся unchanged. Branch также не обещает устранить cancellation для arbitrary nonconstant responses, IPW-only estimators или extreme finite design scaling.

## Studentization и reporting policy

Оценка0 при variance0 не задаёт Wald t-statistic: `0/0` undefined. Она не доказывает GREEN standardized pre-period diagnostic. `_safe_t_stat` вычисляет literal ratio только для finite ATT и finite strictly positive SE. Zero, negative, missing/nonfinite SE и nonfinite ATT возвращают NaN. Никакого minimum-SE cutoff: например, `ATT=SE=1e-300` сохраняет t1; `ATT=1e-12, SE=1e-20` сохраняет t1e8. Overflow finite-input ratio остаётся infinite и заметным diagnostic caution.

Report требует finite standardized values **для всех fitted pre cells**, чтобы выдавать GREEN при unchanged magnitude threshold. Previously `_finite_numeric` удалял NaN/inf перед maximum; одна problematic cell рядом с нулевыми valid t могла silently исчезнуть и дать GREEN. Новая policy делает mixed valid/undefined или valid/infinite rows YELLOW. Missing att/se payload не должен сохранять cached t_stat/abs_t_stat и показывать forged GREEN; cell-table statistic для него unavailable.

Вырожденная simultaneous multiplier distribution при all-zero scores/SE не имеет standardized maximum/critical value. Critical value и simultaneous bands остаются NaN, без all-NaN reduction warnings; обычный nondegenerate bootstrap path не изменяется этой узкой веткой.

Existing exact-zero pointwise p-value convention p1 сохранена **только** для literal ATT=SE=0; она не делает t определённым и не переопределяет report caution. Nonzero ATT/SE0, включая tiny legitimate ATT, и invalid ATT/SE дают pNaN. Pointwise inference/CI legacy conventions и broader zero-variance statistical API не объявляются полностью перепроектированными.

## Public fixture policy

Исходный frozen GREEN assertion по-прежнему fails на baseline и corrected source, но по разным корректно различённым причинам: baseline huge roundoff ratio; corrected source accurate zeros и undefined studentization. Это explanatory reproduction, не failing goal test, который требуется сделать зелёным любыми средствами.

Public API success test должен использовать genuinely nondegenerate synthetic design и сохранить assertion GREEN. Просто добавить treated outcome noise к исходным шести units недостаточно: controls2/regressors2 остаются saturated, control IF нулевые, а treated-centered IF sums отменяются внутри единственного cohort cluster. Нужны residual variation, больше controls, чем regressors, и independent within-cohort cluster support.

Независимый prototype в probe содержит12 units,4 never-treated controls,12 independent unit clusters,6 periods и fixed-seed iid mean-zero outcome shocks, independent от cohort/X. Его untreated trend common; effects действуют только после adoption. Этот DGP design задаёт nondegenerate sampling reference, а не требование observed placebo estimates быть точно0. На baseline и corrected source prototype GREEN при неизменных relaxed report thresholds; min pre SE `0.17423052114026663`, max |pre t| `1.3081931319110782`. Это **не** final public test fixture и не реальное causal study: final fixture/tests принадлежат test-agent evidence. Deterministic exact-zero fixture отдельно сохраняет свой regression contract/caution.

## Воспроизводимые фактические проверки

Команда: `.venv/bin/python audit/block14_contract_probe.py`. Native thread settings фиксируются до NumPy import. Baseline/current model/post source snapshots исполняются в отдельных namespaces; оригинальные `causalis.*` modules не подменяются. Frozen original fixture import block явно rebound к соответствующим model class/post functions; class/function identities и module names сохранены в JSON. Fixture source всегда pinned к baseline, даже если test-agent изменяет public success fixture. Три imported data-contract files byte-identical baseline/current.

Runtime profile fit/estimate/cell/report/influence calls подтверждает пять actual package paths: model, post-inference и три data-contract modules. Hashes каждого именно **загруженного** source записаны отдельно для baseline/current. Current evidence до commit обозначен working_tree_snapshot; historical source не переименовывается в committed proof без нового запуска.

Проверенный current snapshot:

- model SHA256 `10f2970af432507212e5355090dc3cfa97bdb3699acd279b5dbf4a0fff5610c1`;
- post-inference SHA256 `a77606edb6787b7c9cac8e539a9393c3101d2adfe68cbd1455430779bc19939e`.

Evidence категории не являются pytest counts и не суммируются с integration:

- Frozen original test callable реально воспроизводит AssertionError/YELLOW на обеих версиях. Baseline значения cell0 совпадают с B09; current все five pre cells имеют ATT=SE=IF0, β=(1,0), tNaN. Для всех fitted cells проверены exact mathematical ATT, zero IF/SE; only aggregated/coefficient metadata сохраняется.
- **11 direct OLS references**: пять exact constant scales/signs (включая `2**-500`/`2**500`), tiny treated departures, representably nearconstant controls, обычный nonconstant fit, rank deficiency, non-unit intercept, zero-column private helper. Non-target paths имеют exact coefficient/prediction equality. Independent rank-deficient centered/minimum-norm counterexample подтверждает substantive отличие.
- **14 statistic/p-value pairs на каждой версии** покрывают zero/negative/nonfinite SE, nonfinite ATT, tiny positive SE/effects и ratio overflow.
- **7 mixed invalid-pre configurations × 2 versions**: baseline каждый ошибочно GREEN после finite filtering, current каждый YELLOW. Overflow value остаётся infinite; cached unavailable values не превращаются в evidence.
- **2 missing-payload/cached-stat cases × 2 versions** проверяют att/se deletion при подложенном cached t0: current statistic unavailable и report caution.
- **All-zero bootstrap reference на каждой версии**: current critical/bandsNaN без reduction warnings, point estimates/SE0 сохраняются. Baseline reduction warnings записаны честно.
- Nondegenerate prototype проверен на обеих версиях с positive finite SE и GREEN; retained outputs aggregate only.

JSON не содержит individual unit records, trajectories, identifiers или IF vectors. Synthetic arrays существуют только в памяти; сохраняются aggregate cell rows, coefficients, source hashes, error/status flags и scalar reference summaries.

## Verification limits

Проверка не является Monte Carlo coverage study, полной sensitivity validation, stochastic propensity accuracy audit или performance benchmark. Diagnostic GREEN на relaxed API fixture не доказывает identification/robustness в arbitrary applications. Full finite numeric arithmetic under overflow/underflow, arbitrary rank switches и all minimum-norm extrapolation choices не решаются этим exact-constant branch.

Final committed source linkage, new pytest case count, changed public fixture, targeted neighbors, local integration и CI проверяет root/reviewer. Parent artifacts должны отделять historic numerical-zero failure от corrected fixture/diagnostic contract; нельзя сохранять blanket exclusion старого DiD node либо выдавать warranted YELLOW exact-degenerate fixture за clean reliability evidence.
