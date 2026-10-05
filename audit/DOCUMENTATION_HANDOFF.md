# Causalis: список исправлений документации для автора

Подготовлено: 5 октября2026. Проверенный snapshot кода: **`ffe2c356c115f335b74b2f10117e19fe15585d46`**, [репозиторий](https://github.com/causalis-causalcraft/Causalis/tree/ffe2c356c115f335b74b2f10117e19fe15585d46). Сайт: [causalis.causalcraft.com](https://causalis.causalcraft.com/). Сайт и GitHub snapshot могут принадлежать разным версиям; версии опубликованных статей пока явно не сопоставлены.

Файл самостоятельный и переносимый: ниже ссылки на GitHub/сайт/первичные источники, готовые английские формулировки и критерии приёмки. Он предназначен для пересылки автору документации. **Sensitivity analysis исключён по согласованию с пользователем:** команда библиотеки уже переписывает этот модуль; его формулы/parameter labels/benchmarks нужно документировать после согласования новой реализации.

Уровни: P1 — высокий риск неверной причинной интерпретации; P2 — существенная неточность метода/единиц/API; P3 — defaults/names/examples. Это приоритет исправления документации. Статус кода указан отдельно: часть source уже корректна, часть bugs исправляется в независимой рабочей ветке и требует совместного выпуска docs.

## Приоритет 1: предпосылки и причинные выводы

### D01 / P1 — SRM и observed balance не доказывают unconfoundedness

Где: [classic_rct introduction](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/notebooks/scenarios/classic_rct.ipynb#L35), [CUPED conclusion](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/notebooks/scenarios/cuped.ipynb#L747), conclusions classic_rct_average_bill и retention case. Notebook raw links указывают строки JSON; для просмотра текста использовать notebook renderer GitHub.

Проблема: успешные SRM/SMD/KS checks представлены как подтверждение randomization или истинности unconfoundedness. SRM проверяет counts относительно allocation ratio, balance — распределение измеренных X. Ни то ни другое не исключает hidden confounding; non-rejection не доказывает предпосылку.

Предлагаемый текст для RCT:

> The SRM and covariate-balance checks did not identify a problem in the quantities tested. Randomization is justified by the assignment mechanism and its implementation, rather than established by these diagnostics. Unmeasured imbalance and implementation failures may remain undetected.

Для observational IRM:

> Unconfoundedness is an identifying assumption about treatment assignment after conditioning on the selected pre-treatment covariates. Balance diagnostics assess observed covariates and cannot verify the absence of unmeasured confounding.

Приёмка: удалить выводы «assumption is true», «random split proved», «model correctly specified» из одних диагностик. Сохранить явные unresolved assumptions. Current [refutation docstring](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/causalis/scenarios/unconfoundedness/refutation/unconfoundedness/__init__.py#L21) уже содержит более корректное ограничение. Методологический источник: [DML](https://arxiv.org/abs/1608.00060).

### D02 / P1 — IV: exclusion restriction, reduced form и LATE assumptions

Где: [README](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/README.md#L349), [IV notebook](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/notebooks/scenarios/iv.ipynb#L27), [статья IV](https://causalis.causalcraft.com/articles/iv).

Проблема: exclusion назван reduced form; monotonicity/no defiers не объяснена; observed instrument balance переобещает exogeneity. Reduced form — эффект Z на Y; exclusion — отсутствие влияния Z на Y вне D.

Предлагаемый текст:

> For the binary-instrument LATE interpretation, assume consistency and no interference, conditional instrument independence given X, instrument overlap, exclusion, monotonicity D(1) ≥ D(0), and a nonzero complier share. The exclusion restriction rules out an effect of Z on Y through paths other than D. The reduced form describes the effect of Z on Y. The identified effect concerns compliers and need not equal the population ATE.

Отдельно:

> Instrument-balance and first-stage diagnostics can reveal some problems, but do not establish exclusion, monotonicity, or conditional exogeneity. A first-stage F threshold is a heuristic and does not by itself guarantee valid Wald inference.

Приёмка: таблица assumption/design evidence/diagnostic/unverifiable component; consistent IIVM terminology «Instrumental Interactive Regression Model», не Iterated IV. Источники: [Imbens–Angrist](https://www.nber.org/papers/t0118), [Angrist–Imbens–Rubin](https://www.nber.org/papers/t0136).

### D03 / P1 — Clipping не обеспечивает structural positivity

Где: [IRM model article](https://causalis.causalcraft.com/articles/unconfoundedness-model); current [overlap API](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/causalis/scenarios/unconfoundedness/model.py#L79).

Предлагаемый текст:

> Positivity is an assumption about treatment support in the target population. Clipping estimated propensity scores stabilizes numerical denominators; it does not restore missing treatment support and can introduce bias. Dropping observations targets the retained overlap sample, which differs from the original population. State the overlap policy and target population alongside every reported effect.

Приёмка: актуальные имена `overlap_policy`, `overlap_threshold`; если старая статья использует `trimming_threshold`, указать version/migration. Разделить structural assumption, empirical overlap diagnostics и regularization. Не обещать automatic coverage после clipping. Источник: [DML guide v2](https://arxiv.org/abs/2504.08324v2).

## Приоритет 2: методы, единицы и согласованность с кодом

### D08 / P2 — Retention units ошибочны в100раз

Где: [retention conclusion](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/notebooks/cases/retention_on_third.ipynb#L1366).

0.1026 probability risk difference — **10.26 percentage points**, не0.1026п.п.; CI[0.0948,0.1105] — **[9.48,11.05]percentage points**. Relative percent lift — отдельная величина.

Готовая замена:

> The estimated absolute effect is 0.1026 on the probability scale, equivalent to 10.26 percentage points, with a 95% confidence interval of 9.48 to 11.05 percentage points. This is distinct from the relative percentage lift.

Приёмка: централизованная units formatting; привести text/table/plot к одной шкале. Числа относятся к сохранённому snapshot; при re-execution подставить новые estimates. Вывод о causal validity не строить на одних diagnostics.

### D04 / P2 — CATE predictor является T-learner

Где: [README](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/README.md#L350), [predict_cate](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/causalis/scenarios/uplift/model.py#L157), [uplift example](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/notebooks/scenarios/uplift.ipynb#L502).

Готовый текст:

> `predict_cate` uses a T-learner: separate treatment-arm outcome models are fitted on the training data, and predictions are differenced as g1(X) − g0(X). This predictor is distinct from the orthogonal scalar ATE/ATT estimator. A CATE is a conditional average effect; the API does not establish an individual treatment effect or provide individual-effect confidence intervals. Validate generalization and calibration on independent data.

Приёмка: убрать automatic «calibrated individual predictions»/DML CATE label; example «new observations» не брать из training frame для демонстрации validation. DR/R-learner — future feature, не существующее поведение. Источники: [DR learner](https://arxiv.org/abs/2004.14497), [R learner](https://arxiv.org/abs/1712.04912).

### D05 / P2 — Newcombe hybrid formula

Где: [source formula исходного snapshot](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/causalis/scenarios/classic_rct/inference/conversion_ztest.py#L158), [статья RCT model](https://causalis.causalcraft.com/articles/rct-classic-model).

Исходный код и сайт вычитали endpoints Wilson intervals `[L1−U0,U1−L0]`. Для Newcombe hybrid method без continuity correction правильная формула при `d=p1−p0`:

```text
lower = d − sqrt((p1 − L1)^2 + (U0 − p0)^2)
upper = d + sqrt((U1 − p1)^2 + (p0 − L0)^2)
```

Числовая проверка:7/34treated vs1/34control; старый CI[−0.04566046,0.36277297], hybrid reference[0.01892144,0.34036869]. [Reference statsmodels](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.confint_proportions_2indep.html), method=`newcomb`.

**Координация с кодом:** исправлено в личной ветке `codex/correctness-roadmap`, [commitbd8a2be](https://github.com/MaximLenivkin/Causalis/commit/bd8a2be2dc363400a572c6d369cda887fb17aad9) (B01);36conversion tests и31соседнийRCTtestpassed. Commit опубликован в личном fork, но ещё не выпущен upstream: опубликованный старый package не следует описывать как уже исправленный. После release обновить code docstring/site/examples/generated API вместе. Указать, что выбранный CI и pooled/unpooled z-test p-value — разные настройки и не обязательно inversion одной процедуры.

### D06 / P2 — CUPED relative inference article отстаёт от source

Где: [CUPED article](https://causalis.causalcraft.com/articles/cuped-model), [current parameter specification](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/causalis/scenarios/cuped/model.py#L114), [joint delta calculation](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/causalis/scenarios/cuped/model.py#L909).

Source уже использует adjusted-control denominator по умолчанию и covariance в joint delta method; raw-control option тоже учитывает covariance. Сайт описывает старый raw-control/nocov rule. Старый generated HTML обещает отсутствие finite-sample bias; current source правильно говорит о consistency/asymptotic unbiasedness.

Предлагаемый текст:

> Specify the relative-effect numerator and denominator explicitly. The current default uses the adjusted control baseline and a joint delta-method variance that includes their covariance. The raw-control option uses a different denominator and also accounts for covariance. Regression adjustment is consistent under the stated conditions, but is not generally exactly unbiased in finite samples. A baseline close to zero makes ratio-based inference unstable.

Приёмка: source specification — источник истины, не переносить старую nocov формулу назад в код. Источник о regression adjustment: [Lin2013](https://arxiv.org/abs/1208.2301).

### D09 / P2 — SCM placebo p-value formula

Где: [research notebook](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/notebooks/research/scm_diagnostics.ipynb#L322).

Для описанного сравнения treated statistic с J donor-placebos и denominator `J+1` numerator должен учитывать actual treated:

```text
p_rank = (1 + count(R_placebo >= R_treated)) / (J + 1)
```

Приёмка: объяснить minimum attainable p, ties, donor exclusions и pre-fit filtering; inference требует assignment/exchangeability justification. В observational SCM это не automatic exact randomization p. Установлен дефект объяснения notebook; основной estimator не обвиняется без отдельной проверки. Источник: [Abadie–Diamond–Hainmueller](https://www.nber.org/papers/w12831).

### D10 / P2 — 401(k): design/estimand и степень causal claim

Где: [choice of treatment](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/notebooks/cases/401k.ipynb#L144), [conclusion](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/notebooks/cases/401k.ipynb#L1445).

Используется participation `p401`, не eligibility `e401`. Same-year measurement создаёт риск post-treatment adjustment, но не доказывает влияние treatment на каждый X. Вывод категорически causal при признанном спорном дизайне.

Предлагаемый текст:

> This analysis estimates the effect of participation under a stated unconfoundedness design. Eligibility-based and instrumental-variable analyses target different effects and require different assumptions. Same-year measurement creates a risk of adjusting for post-treatment variables; establish the timing and role of each covariate. Treat the estimate as illustrative where these design questions remain unresolved.

Приёмка: separate eligibility/participation/IV questions и assumptions; DML nuisance debiasing не представлять как исправление любого design bias.

## Приоритет 2–3: API, examples и publishing

### D07 / P2 — Пересборка generated API

Исходный checked-in API126moduleHTML vs текущий source131. Отсутствующие public modules:

- `causalis.data_contracts.rct_causal_data`
- `causalis.data_contracts.rct_estimates`
- `causalis.dgp.rct_causal_data`
- `causalis.scenarios.uplift.policy`
- `causalis.shared.rct_design.design`

Удалённый `causalis.shared.rct_design.mde` ещё опубликован. `UpliftPolicyTree` и новый design API должны быть представлены. [Generate script](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/scripts/generate_api_reference.py) надо запускать из выбранного release SHA. Изолированная local build успешно создала131HTML; исходные published files не перезаписывались.

Приёмка: version/package commit marker, public API manifest, stale modules/signatures отсутствуют. [Docs test file](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/tests/docs/test_generate_api_reference.py) содержит helper functions без `test_*`, поэтому его наличие не означает, что pytest запускает docs build. CI test/gate — code infrastructure task; автор docs должен согласовать release SHA с разработчиками.

### Дополнительный checklist

| ID / уровень | Где / что исправить | Критерий приёмки |
|---|---|---|
| D11/P2 | Numerical prose не совпадает с сохранёнными outputs: [IRM](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/notebooks/scenarios/unconfoundedness.ipynb#L974):9.9026vs12.1542; GATE11.7030vs12.1542;401k12461.3189vs12486.5221 | Re-execute pinned notebook и генерировать prose из result; не подменять новым ручным числом |
| D12/P2 | [RCT notebook](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/notebooks/scenarios/classic_rct.ipynb#L595): произвольные n<100k/n<10k правила выбора z/permutation | Условия по counts/moments/null/assignment unit. Studentized permutation не universal exact mean test при heterogeneous distributions; ratio-of-sums требует covariance. [Chung–Romano](https://arxiv.org/abs/1304.5939) |
| D13/P2 | [DID introduction](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/notebooks/scenarios/did.ipynb#L12) скопирован из unconfoundedness | Conditional parallel trends, no anticipation, ATT(g,t), control eligibility/base period; [Callaway–Sant'Anna](https://arxiv.org/abs/1803.09015) |
| D14/P2 | [SCM research](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/notebooks/research/scm_diagnostics.ipynb#L115) называет SCM requirement обычными parallel trends | Donor-weighted counterfactual/factor-model assumptions; не подменять DiD terminology. [Augmented SCM](https://arxiv.org/abs/1811.04170) |
| D15/P2 | [Signed donor weights](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/notebooks/research/scm_diagnostics.ipynb#L507):1/sum(w²) назван literal donor count | Для signed weights показатель может быть<1; label и interpretation уточнить, показывать L1/negative share/maxabs |
| D16/P2 | [CONTRIBUTING release](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/CONTRIBUTING.md#L87) обещает tests, [workflow](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/.github/workflows/release.yml) pytest не запускает | Сейчас честное описание; после code CI fix — проверить required job на release SHA |
| D17/P3 | [Binary IRM docstring](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/causalis/scenarios/unconfoundedness/model.py#L72):n_folds5vsactual4; старый `causalis.refutation` namespace | Binary default4, multi default5; runnable imports текущего namespace |
| D18/P2 | [DML vs PSW notebook](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/notebooks/research/dml_vs_psw.ipynb#L23) обещает universal superiority | Bias/RMSE/coverage/runtime по seeds/DGP; один DGP не доказывает превосходство каждого sample |
| D19/P3 | [SUTVA helper](https://github.com/causalis-causalcraft/Causalis/blob/ffe2c356c115f335b74b2f10117e19fe15585d46/causalis/shared/sutva_validation.py#L11) смешивает SUTVA с temporal/data-quality checks | No interference и consistency/no hidden treatment versions отдельно; helper checklist, не statistical test |

### Дополнительные source docstrings, не связанные с sensitivity

- DID clipping threshold описан как skip, код лишь ставит warning. Описать current warn/raise/skip policy точно, не менять сайт на желаемое поведение до code fix.
- DID varying base `t−1` относится к pre-periods, post cells используют universal base. Defaults propensity clip/ridge/condition и DGP n нужно брать из constructor/specification.
- DID generator examples с `n_units,n_periods` не поддерживаются текущим wrapper; указанная колонка `group` должна быть `cohort`. Проверить примеры в refutation diagnostics/plots/post_inference реальным smoke execution.
- Raw DID cell SE нельзя складывать как независимые при shared controls. Error bars в diagnostics либо используют IF covariance, либо помечены descriptive; «I can rely on the results» заменить перечислением checks/limitations.
- Copula `0.3**distance` — correlation latent Gaussian, не обещание observed Pearson correlation после nonlinear/binary marginals.
- IV diagnostics docstrings обещают model payload, который resolver сейчас отвергает. До code fix показывать estimate/diagnostic payload; после fix проверить оба supported forms.
- SCM/CUPED DGP default dates/sample sizes проверять относительно actual generator signature, не копировать из другой family.

## Порядок работы автора документации

1. Сначала D01–03 и units D08: независимые текущие factual errors, не требуют ожидания новых estimators.
2. D04/D06/D09/D10 и дополнительные methodology claims; отдельно явно указать ограничения.
3. Runnable examples/defaults/namespace/numerical narrative; re-execution сохранять version/seed.
4. Newcombe D05, IV resolver и другие поведенческие изменения публиковать с соответствующими code commits.
5. Rebuild API от release SHA, site version marker, links/snippet checks; затем общая smoke проверка.

Не добавлять обещания отсутствующих возможностей: GATE contrasts, held-out policy evaluation, DID simultaneous multiplier bands и SCM conformal уже есть; DR/R CATE, repeated/group CF и weak-IV robust sets — отдельные future features. Homepage «state-of-the-art/best-in-class/production-ready» подкреплять versioned benchmarks/assumption/support list.

Прочитаны markdown всех40notebooks и ключевые статьи сайта; все40 notebooks не переисполнялись. Из27подозрительных import flags после runtime проверки actual export errors0. Ошибка web extractor отдельной страницы не классифицируется как broken URL. Эти границы не меняют подтверждённых текстовых несогласованностей выше.

## Дополнение после B02: публиковать вместе с исправленным кодом

В личной ветке `MaximLenivkin/Causalis:codex/correctness-roadmap` исправлены семь grouped findings contracts/shared/DGP. Общая проверка: 606 passing tests. Эти изменения **пока не означают upstream release**: сначала включить code commits в выбранный release, затем синхронизировать сайт/API. Ниже готовые английские тексты для описания нового поведения.

### Конечные вещественные данные / P2

Source: [CausalData / inherited IV validation](https://github.com/MaximLenivkin/Causalis/blob/817c24c9b00e8896bb578b3568476c178bc024e4/causalis/data_contracts/causaldata.py), [PanelDataSCM](https://github.com/MaximLenivkin/Causalis/blob/817c24c9b00e8896bb578b3568476c178bc024e4/causalis/data_contracts/panel_data_scm.py). Complex checks также добавлены в MultiCausalData и PanelDataDID.

> Analysis columns must contain finite real numeric values, with boolean values accepted where supported by the contract. Infinity and complex values are rejected with ValueError before estimation. A zero imaginary component does not make a complex dtype supported. Panel outcome and covariate columns retain their documented numeric-string conversion. Invalid values are not automatically replaced or imputed.

Migration: datasets, ранее содержавшие Inf/complex, теперь явно отклоняются. Не обещать finite estimates при любых конечных inputs: numerical degeneracy расчётов — отдельная проверка.

### SMD при полном разделении групп / P2

Source: [shared balance](https://github.com/MaximLenivkin/Causalis/blob/add2f36652a7bb7d814975234255f7993f96f240/causalis/shared/confounders_balance.py), [binary weighted report](https://github.com/MaximLenivkin/Causalis/blob/add2f36652a7bb7d814975234255f7993f96f240/causalis/scenarios/unconfoundedness/refutation/unconfoundedness/unconfoundedness_validation.py). Multi comparison/overall reports используют тот же принцип.

> The shared balance table divides the signed difference in group means by sqrt((s0²+s1²)/2). If both within-group variances are zero, unequal means yield signed infinity and identical means yield zero. Weighted DML diagnostics use absolute SMD. Infinite SMD indicates separation: it counts as a violation, fails the balance summary, and receives a RED flag. Entirely unavailable statistics cannot pass. These checks assess measured covariates and do not establish unconfoundedness.

Убрать label «Cohen's d using pooled std», если подразумевается sample-size-weighted pooled variance: фактический denominator выше. Поддержать отображение Inf; не превращать его в 0/NA при форматировании или сериализации отчёта.

### UUID IDs и строки выбросов / P2

Source: [ID generation](https://github.com/MaximLenivkin/Causalis/blob/a5a6e3a4887c7ac22aa86b36883398a34bbb5d76/causalis/dgp/base.py), [outlier rows](https://github.com/MaximLenivkin/Causalis/blob/a5a6e3a4887c7ac22aa86b36883398a34bbb5d76/causalis/shared/outcome_outliers.py).

> Random user identifiers are full 32-character UUID4 hex strings and are unique within the generated dataset. They use operating-system randomness and are independent of random_state. Set deterministic_ids=True for reproducible identifiers. Do not assume a fixed identifier length across both modes.

> With return_rows=True, outcome_outliers returns exactly the flagged source rows by position and preserves their original index labels, including repeated labels.

Migration: random ID length изменилась с 5 на 32; formulas IQR/z-score и grouping order сохранены.

### Allocation weights / P2

Source: [split validation](https://github.com/MaximLenivkin/Causalis/blob/a5a6e3a4887c7ac22aa86b36883398a34bbb5d76/causalis/shared/rct_design/split.py).

> Variant weights must be finite, nonnegative real numbers, excluding booleans, with a total in (0, 1]. NaN, infinity, strings, complex values, and unsupported numeric types are rejected before assignment. Weights are not normalized. If the total is below one, the remaining coverage is unassigned.

Supported numeric interface — `numbers.Real`; Decimal не зарегистрирован как Real и сейчас отвергается. Hashing и assignments для допустимых float weights не менялись.

### Latent-U outcome oracle / P1

Source: [multi-treatment DGP](https://github.com/MaximLenivkin/Causalis/blob/c27e74406ffacee460ee6deb7c4be7669d1394e1/causalis/dgp/multicausaldata/base.py).

> The g_<arm> columns are natural-scale potential-outcome means under the reference law U ~ N(0,1), independent of X. They integrate out U; cate_<arm> is their difference from control. Exponential links use the same clipping as the observed outcome draws. Binary means use deterministic numerical integration. With latent treatment confounding, these means differ from E[Y | D=arm, X].

> Supplying U overrides realized latent values for observed draws. Outcome oracle columns still use the Gaussian reference law, so they need not describe a supplied vector with a different law or dependence on X. The m_obs_<arm> columns describe assignment at realized U. The existing m_<arm> columns describe assignment at U=0 and generally differ from marginal P(D=arm | X) when latent noise affects treatment.

Приёмка: не использовать `m_<arm>` как marginal propensity в latent-confounded benchmarks. Не интерпретировать среднее Gaussian-marginal CATE по treated как automatically true ATT при selection on U. Пересчитать benchmark targets после code update; при gamma example a=0, u_strength_y=1, theta1=1 baseline ≈1.64872 и marginal CATE ≈2.83297, с пренебрежимо малой clipping correction. Для иных latent laws требуется отдельная oracle specification.

## Реализовано в B03: DML / GATE / Uplift migration

Этот раздел относится к personal correctness branch, а не к исходному audit snapshot и не автоматически к опубликованному PyPI release. Выпускать site/API text вместе с соответствующими code fixes.

### Multi-treatment ATT inference / P1

Source: [multi ATT score / relative baseline](https://github.com/MaximLenivkin/Causalis/blob/e6a92759f3c8844999c53bd065a673e31330d604/causalis/scenarios/multi_unconfoundedness/model.py), [additive psi_a payload field](https://github.com/MaximLenivkin/Causalis/blob/e6a92759f3c8844999c53bd065a673e31330d604/causalis/data_contracts/causal_diagnostic_data.py).

Предлагаемый текст:

> For each active arm k, ATTE is an empirical ratio with the observed share p_k in that arm. The linear score coefficient is psi_a,k = -d_k/p_k, and its influence function is psi_b,k - theta_k*d_k/p_k. Replacing that coefficient by -1 preserves the point estimate but changes its sampling variance. MultiTreatmentIRM now stores psi_a with shape (n, K-1) for ATTE; the ATE coefficient remains a vector of length n.

> Relative ATTE uses the counterfactual control mean among units in arm k. Its delta-method interval combines the ratio influence functions of both the effect and that baseline, including their covariance. Old saved estimates should be recomputed to obtain corrected absolute intervals. The return shapes of effect estimates are unchanged.

Приёмка: source class docstring и score reconstruction согласованы; constant noiseless potential outcomes дают zero absolute SE, а proportional potential outcomes — zero relative SE. Не добавлять multi relative CI как отдельный исходный defect: прежние ошибки numerator/baseline могли сокращаться, обе части обновлены совместно.

### Binary relative ATT baseline / P2

Source: [binary IRM](https://github.com/MaximLenivkin/Causalis/blob/6084b34d799e9af34228136c0a2e9549063638ac/causalis/scenarios/unconfoundedness/model.py).

> The relative ATT is 100 times ATT divided by the counterfactual control mean among treated units. The baseline is an empirical ratio and its influence function subtracts (D/p)*mu_0, where p is the observed treated share. The interval includes the covariance of the effect and baseline influence functions. The low-signal baseline check uses the same corrected baseline standard error.

Приёмка: `Y(0)=10, Y(1)=12` дают relative ATT20% и zero sampling SE для любого достаточного nondegenerate sample; rare-treated share сама по себе не вызывает low-signal warning. Existing approximate weighted/Hájek ATE inference policy не изменена этим исправлением.

### Overlap filtering and custom weights / P2

Source: [raw weight validation / retained normalization](https://github.com/MaximLenivkin/Causalis/blob/6084b34d799e9af34228136c0a2e9549063638ac/causalis/scenarios/unconfoundedness/_score_utils.py), [fit snapshots](https://github.com/MaximLenivkin/Causalis/blob/6084b34d799e9af34228136c0a2e9549063638ac/causalis/scenarios/unconfoundedness/model.py).

> Supply custom ATE weights in the order of the original input rows. fit() validates and copies weights and weights_bar before nuisance training. With overlap_policy='drop', the same retention mask applies to outcomes, predictions, identifiers, and weights. Estimation normalizes both weight vectors by the mean of weights over the retained sample. Changes to caller arrays or model.weights after fitting take effect only after a new fit().

Приёмка: dictionaries, supported row/column shapes, repeated indices, diagnostics и repeated fit сохраняют positional alignment. Drop изменяет estimation population; эта правка не заменяет существующее предупреждение об approximate inference при normalized custom weights.

### Refit and CATE / P1

Source: [successful fit cache invalidation](https://github.com/MaximLenivkin/Causalis/blob/6084b34d799e9af34228136c0a2e9549063638ac/causalis/scenarios/unconfoundedness/model.py).

> A successful IRM refit invalidates its cached CATE outcome models. The next predict_cate call rebuilds them using the current data, feature schema, and outcome learner. The predictions then match a fresh model fitted with the same configuration.

Это independent T-learner cache fix; generic scalar estimate/sensitivity refit lifecycle исключён из текущего блока и не должен описываться как исправленный.

### Fold stability and unavailable OOS inference / P2

Source: [binary diagnostics](https://github.com/MaximLenivkin/Causalis/blob/113c693a0dd721c6e77dfe84bc647d2ffb4c7841/causalis/scenarios/unconfoundedness/refutation/score/score_validation.py), [multi diagnostics / legacy cache migration](https://github.com/MaximLenivkin/Causalis/blob/113c693a0dd721c6e77dfe84bc647d2ffb4c7841/causalis/scenarios/multi_unconfoundedness/refutation/score/score_validation.py).

> The oos_moment_test entry reports descriptive fold stability from cached cross-fitted scores. It is not an independently calibrated validation experiment. Its legacy t-statistics and p-values are NaN, available is False, and the oos_moment flag is NA. fold_diagnostics_available separately indicates whether complete descriptive summaries can be computed.

> Inspect fold_theta_range, fold_theta_gap_max_abs, fold_score_mean_rms, fold_score_mean_max_abs, and the fold table to see differences on the effect or score scale. These measures have no calibrated significance threshold. Equal-fold score averages can cancel exactly even when individual folds differ substantially. Cross-fitting alone does not validate the causal assumptions.

Приёмка: example fold means0/100/200/300 показывает effect range300 и leave-fold gaps; больше не p=1/GREEN. Keep old keys для consumer migration, но обновить examples/summary interpretation; не заменять missing t/p values на0/1 в rendered tables. Multi ATTE legacy cache inconsistency отражается в `meta.psi_cache_status`; old estimates надо переоценить.

### GATE numerical covariance / P2

Source: [centered group variance](https://github.com/MaximLenivkin/Causalis/blob/c9259072a24f5325f944cd37c4f203f33c39a5e7/causalis/scenarios/gate/model.py).

> GATE computes its HC covariance from squared deviations around each group mean. A large common shift of the orthogonal signal does not erase within-group variation. GATET uses the same centered calculation for descriptive signal spread; its ATT covariance continues to use centered ATT moment residuals.

Приёмка: HC0/1/2/3 и public group contrasts сохраняют корректную SE при signals1e8±1. Не обещать universal extreme-value accuracy или measured speedup: алгоритм остаётся O(n+groups), broad benchmark относится к следующему performance блоку.
