# Causalis: список исправлений документации для автора

Дополнения по реализованным B01–B07 обновлены 6 октября 2026 (Europe/Moscow). Исходный аудит ниже относится к своему snapshot; migration sections указывают отдельные immutable implementation commits.

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

## Дополнение после B04: DiD / P1

Implementation: [comparison rule](https://github.com/MaximLenivkin/Causalis/blob/57dbba1e2ecc0c1cab413b1da7f40cfdd8b22131/causalis/data_contracts/_did_comparison_units.py), [cell and aggregation IF](https://github.com/MaximLenivkin/Causalis/blob/57dbba1e2ecc0c1cab413b1da7f40cfdd8b22131/causalis/scenarios/did/model.py), [cluster guard/covariance](https://github.com/MaximLenivkin/Causalis/blob/87228e267aed3dc71dadd4bbe19b969a95463591/causalis/scenarios/did/model.py). Эти изменения пока находятся в personal fork; сайт должен публиковать новое поведение вместе с включающим их release.

### Comparison populations and base periods

> A comparison unit is excluded if it belongs to the evaluated cohort. Later-treated controls must remain untreated, including the anticipation window, at both the base and target dates. This rule also applies to pre-treatment comparisons, whose universal base may be later than the target. Support, estimation, raw DiD and design diagnostics use the same comparison rule and require observed outcomes at both dates.

> A varying base uses the previous period for pre-treatment comparisons. Post-treatment cells use the cohort's universal base. PanelDataDID.comparison_units remains a post-treatment convenience API and accepts optional base_time and anticipation; use att_gt_cells to inspect pre-treatment support.

Приёмка: собственная cohort отсутствует среди controls; unit rows уникальны внутри cell, counts/support/refutation согласованы при universal/varying, anticipation и incomplete panel. Изменение controls может изменить pre-effect, support и число skipped cells; необходимо re-fit. Earliest universal placebo пока не добавлен: enumeration сохраняет прежнюю границу analysis-index1.

### Normalized IPW and traditional DR uncertainty

> Cell influence functions include both normalized-mean denominators and the estimation of logistic propensity coefficients. DR, and its aipw alias, also include the estimation of control OLS coefficients. This is the traditional MLE/OLS procedure. A common outcome trend cancels from normalized IPW uncertainty as well as from its point estimate.

> Fixed ridge regularization and active propensity clipping can change the estimator's probability limit. The corrected sandwich measures uncertainty for the implemented functional; it does not remove this bias or verify conditional parallel trends. Regular inference requires stable clipping regions, design rank and support. The improved IPT/WLS estimator is a separate method.

Reference: [official traditional DRDID](https://github.com/pedrohcgs/DRDID/blob/85807cfbddbd64cc6f3f8ba37f52d07c6c3acc65/R/drdid_panel.R), [Sant'Anna–Zhao](https://arxiv.org/abs/1812.01723). Causalis сохраняет собственную clipping/ridge policy; точное численное совпадение с R-пакетом при всех настройках не обещается.

Migration: re-fit/re-estimate DiD для новых SE/CI/p-values. На неизменной post comparison sample cell ATT не меняется. Не утверждать, что новые intervals всегда шире или coverage всегда выше: estimated-nuisance simulations в двух DGP дали93.5%/95.67% при nominal95%, и первый сохраняет finite-sample gap.

### Estimated population weights and missing periods

> Simple, calendar and event aggregations include uncertainty from estimating their treated complete-pair shares, along with the joint uncertainty of cell effects. Even deterministic but different cohort effects can produce a nonzero population aggregate standard error because the cohort mixture is estimated.

> On balanced panels, complete-pair shares coincide with the corresponding cohort shares. On incomplete panels, the unchanged weighting policy averages effects from observed two-period treated subpopulations. It does not automatically recover full-cohort effects under informative missingness. Cohort tables use fixed equal weights across included post-treatment cells.

Reference: [official did estimated-weight contribution](https://github.com/bcallaway11/did/blob/74b88eb07f1faa644df1271055a0f77848f6550c/R/compute.aggte.R). Complete-pair generalization и independent derivatives описаны в [methodology notes](https://github.com/MaximLenivkin/Causalis/blob/57dbba1e2ecc0c1cab413b1da7f40cfdd8b22131/audit/B04_METHOD_REVIEW.md). Приёмка: heterogeneous deterministic cohorts дают positive simple/calendar/event SE, shared controls сохраняют covariance; нельзя складывать cell SE как independent errors.

### Clustered bootstrap and actual defaults

> Both analytical and multiplier-bootstrap inference require at least two independent clusters. bootstrap_replications must be zero or at least two. Cluster multiplier draws share the analytical method's centered covariance and finite-cluster correction; a fixed seed remains reproducible, but bootstrap outputs can differ from earlier versions. Two clusters satisfy the computational guard and do not guarantee reliable coverage.

Актуальные constructor defaults: propensity_clip=1e-6, logit_ridge=1e-8, max_condition_number=1e8. min_treated_per_cell/min_control_per_cell/min_control_ess/max_propensity_clip_share/max_condition_number — diagnostic thresholds; превышение само по себе не является автоматическим skip. Source docstrings исправлены в linked implementation; generated API пересобрать от release commit. Дополнительные примеры generators из прежнего checklist всё ещё требуют исправления автором документации.

## Дополнение после B05: CUPED / IV / SCM — P2

Изменения ниже находятся в personal fork; обновить сайт/generated API вместе с release, включающим эти commits. Они не изменяют identifying assumptions и не доказывают causal validity diagnostics.

### CUPED names, numerical covariance and outcome batching

Sources: [design and model](https://github.com/MaximLenivkin/Causalis/blob/3c000b10eed1b5366f46cc038870500791b75579/causalis/scenarios/cuped/model.py), [owned SVD / public result adapter](https://github.com/MaximLenivkin/Causalis/blob/3c000b10eed1b5366f46cc038870500791b75579/causalis/scenarios/cuped/_ols.py), [regression checks](https://github.com/MaximLenivkin/Causalis/blob/3c000b10eed1b5366f46cc038870500791b75579/causalis/scenarios/cuped/refutation/regression_checks.py).

> CUPED accepts valid treatment and covariate names even when they resemble internal regression labels. Internal labels are allocated without collisions; coefficient and diagnostic roles follow the design's explicit order. Global centering, Lin interactions and stratified bootstrap recentering are unchanged. Input DataFrames are not modified.

> For each arm-versus-control comparison, CUPED factors the adjusted design once and solves all selected outcomes together. The naive design is also shared. Leverage, HC2/HC3 covariance, raw-control relative covariance and winsorized-outcome checks use the same design factorization. Results and residual-based covariance remain specific to each outcome. Inference remains per comparison without a multiple-testing correction.

Приёмка: treatment=`intercept`/`x__centered` и covariates с `:`/`__centered` воспроизводят estimate/CI/diagnostics после safe rename. Rescaling сохраняет результаты в numerical tolerance; near-collinear accepted designs используют stable HC2/3 projection. Старые private display labels при collision могут измениться; потребителям нельзя определять treatment по prefix/suffix вместо semantic roles.

> The implementation preserves the selected HC0/HC1/HC2/HC3/nonrobust covariance, use_t and relative-denominator policies. Near-zero ratio denominators, leverage near one, very small residual degrees of freedom and extreme conditioning still require care. Covariate variance and numerical rank thresholds remain sensitive to scale; this change does not guarantee invariance for every possible rescaling.

References: [public OLSResults API](https://www.statsmodels.org/dev/generated/statsmodels.regression.linear_model.OLSResults.html), [HC2](https://www.statsmodels.org/dev/generated/statsmodels.regression.linear_model.OLSResults.HC2_se.html), [HC3](https://www.statsmodels.org/dev/generated/statsmodels.regression.linear_model.OLSResults.HC3_se.html). Local statsmodels0.15.0 проверен; dependency matrix ещё не выполнена. [Local fit benchmark](https://github.com/MaximLenivkin/Causalis/blob/3c000b10eed1b5366f46cc038870500791b75579/audit/block05_benchmark_summary.json) показал1.73–2.90× на12000rows/4X/1,8,32Y,HC2/checks=True; это узкое наблюдение, не универсальное ускорение всей библиотеки. Construction/memory не измерены.

### IV diagnostics model/result API and refitting

Sources: [IV resolver](https://github.com/MaximLenivkin/Causalis/blob/5e0379507bac4b6ec9f561e7978e8835194c2247/causalis/scenarios/iv/refutation/diagnostics.py), [IIVM fit lifecycle](https://github.com/MaximLenivkin/Causalis/blob/5e0379507bac4b6ec9f561e7978e8835194c2247/causalis/scenarios/iv/model.py).

> instrument_overlap, first_stage, reduced_form, and instrument_overlap_plot accept an IIVM model after a successful fit().estimate(), its IVCausalEstimate, or an IVDiagnosticData payload. Calling fit() alone does not create post-inference diagnostic data. Each new fit attempt clears the model's previous fitted and inference state; a failed refit leaves the model unfitted, and a successful refit requires a new estimate(). Previously returned estimates remain usable independently of the model. Lazy diagnostics called with a model use the latest estimate's saved options and LATE value.

Приёмка: model/estimate tables и plot совпадают; wrong payload type/fit-only даёт понятную ошибку. Bare payload без cached custom first-stage settings не хранит model_options и использует прежний default threshold; для custom configuration передавать estimate/model. IV nuisance/score/inference formulas и heuristic strength thresholds не менялись.

### ASCM configuration for placebo refits

Sources: [PanelEstimate metadata](https://github.com/MaximLenivkin/Causalis/blob/1b2477755c9b89bd2f69f260fd094002bdc26fe2/causalis/data_contracts/panel_estimate.py), [ASCM snapshots](https://github.com/MaximLenivkin/Causalis/blob/1b2477755c9b89bd2f69f260fd094002bdc26fe2/causalis/scenarios/synthetic_control/model.py), [placebo refutations](https://github.com/MaximLenivkin/Causalis/blob/1b2477755c9b89bd2f69f260fd094002bdc26fe2/causalis/scenarios/synthetic_control/refutation/placebo.py).

> ASCM results record all constructor-compatible fitting settings and the effective inference settings in PanelEstimate.model_options. Placebo-in-space and placebo-in-time refits inherit these settings. Pass model_kwargs to override selected settings; every unspecified setting retains its value from the original estimate. The returned table records the resolved settings and explicit overrides in DataFrame.attrs["model_options"] and DataFrame.attrs["model_kwargs_overrides"].

> Older or manually constructed results may not contain a complete ASCM configuration. Re-estimate with ASCM, or supply all missing constructor options explicitly. Placebo refutations raise ValueError when the configuration is incomplete, because the original estimator cannot be reconstructed from its effect path alone.

Приёмка: actual treated placebo row при omitted kwargs воспроизводит original effect path; partial override сохраняет прочие13constructor settings; pointwise/average inference options отражены в snapshot. Mutating public fitting attributes после fit не меняет cached fitting configuration для auxiliary inference; re-fit нужен для нового estimator. Leave-one-donor-out sensitivity в B05 не мигрировала и остаётся отдельной deferred областью; её default configuration нельзя считать исправленной этим placebo patch.

## Дополнение после B06: dependencies / CI / performance — P2

Изменения ниже относятся к personal fork и должны публиковаться вместе с включающим их release. Performance numbers ниже — локальные узкие измерения, а не новый общий рейтинг библиотеки.

### Installation and actual validation scope

Sources: [package requirement](https://github.com/MaximLenivkin/Causalis/blob/f31b7438f4c4f5a796bf99cb04e204dd5051618c/pyproject.toml), [full release gate](https://github.com/MaximLenivkin/Causalis/blob/f31b7438f4c4f5a796bf99cb04e204dd5051618c/.github/workflows/release.yml), [scoped development matrix](https://github.com/MaximLenivkin/Causalis/blob/1be6b67bfa64a36e77688b47aeb95a2bbf67a25b/.github/workflows/ci.yml), [explicit test runner](https://github.com/MaximLenivkin/Causalis/blob/f31b7438f4c4f5a796bf99cb04e204dd5051618c/scripts/run_tests.py).

> Causalis requires Pydantic 2 or later. Pydantic 1 is incompatible with the data-contract validation APIs and is rejected by package metadata. The declared Python range remains 3.10–3.14. Development CI is configured to test latest compatible dependencies on each supported Python minor and a representative older stack; inspect the recorded job results and installed versions before claiming validated compatibility.

> During the upstream sensitivity-analysis rewrite, development CI explicitly defers seven named sensitivity test modules. Its passing result represents that selected scope. Release CI selects the complete repository test suite, and a failed or empty test run prevents publication. A newly discovered sensitivity test module requires an explicit development-scope review; it is never silently skipped.

Pydantic2 API reference: [migration](https://docs.pydantic.dev/2.0/migration/), [AliasChoices](https://docs.pydantic.dev/2.0/usage/fields/). Representative older stack is a CI fixture, not public lower bounds for every dependency. Full selection retains existing test-level skip policies. Pytest coverage does not establish a Sphinx site build: current docs test file has no collected test functions. B06 local run uses Windows/Python3.12.14. The historical B05 statement “dependency matrix ещё не выполнена” is superseded by the actual B06 results below.

> On 6 October 2026 (Europe/Moscow), all six Linux CI configurations completed successfully on source 09e00de5a9d3dc915c6d59627f8b0ebc875dd4e9: latest compatible dependencies for Python 3.10–3.14, plus a representative older stack on Python 3.10. Every job passed 1582 tests with no failures, errors or skips, within the explicitly selected development scope. This validates those installed stacks; it does not validate sensitivity analysis, every dependency combination or every operating system.

Evidence: [completed CI run and per-job artifacts](https://github.com/MaximLenivkin/Causalis/actions/runs/37373828518). Local Windows integration also passed the same 1582 tests; seven named sensitivity modules remained deferred.

### Data preparation without statistical changes

Sources: [screening](https://github.com/MaximLenivkin/Causalis/blob/5977bb872b79a84e58e3c3c8aa1d0ed8045d1b52/causalis/data_contracts/causaldata.py), [exact equality](https://github.com/MaximLenivkin/Causalis/blob/5977bb872b79a84e58e3c3c8aa1d0ed8045d1b52/causalis/data_contracts/_duplicate_columns.py), [binary IRM/IV check](https://github.com/MaximLenivkin/Causalis/blob/74c0ff0a2081671d179662510c16f5fe53283019/causalis/scenarios/unconfoundedness/_utils.py), [multi check](https://github.com/MaximLenivkin/Causalis/blob/74c0ff0a2081671d179662510c16f5fe53283019/causalis/scenarios/multi_unconfoundedness/_utils.py).

> Data contracts screen candidate duplicate columns on at most 64 positions, then compare matching full fingerprints and exact values. A hash match alone never establishes equality. Numeric binary detection uses exact 0/1 comparisons without sorting continuous outcomes. Binary-treatment IRM and IV require both categories; multi-treatment IRM retains its existing policy that a constant zero or one outcome is binary. Rows, labels, learner selection, nuisance predictions and inference are unchanged.

Приёмка: same first duplicate error, mixednumeric/nullable/bool, signedzero, largeinteger collisions и unsampled differences; unchanged input frames/repeated indices. Numeric/object optional ID fingerprint categories остаются разными: performance patch не расширяет прежнюю duplicate policy. Public pandas copy/ownership semantics сохраняются. Owned array extraction остаётся audit-only candidate и не должна описываться как реализованная новая snapshot API.

### Exact Gaussian KDE with bounded scratch arrays

Source: [KDE](https://github.com/MaximLenivkin/Causalis/blob/d292b3c2f83ec94ef75652a17f3e34436c71902f/causalis/shared/outcome_plots.py), [numerical and memory checks](https://github.com/MaximLenivkin/Causalis/blob/d292b3c2f83ec94ef75652a17f3e34436c71902f/tests/statistics/test_outcome_kde_memory.py).

> Outcome KDE evaluates every Gaussian kernel in blocks, using at most 8 MiB for its explicit kernel and partial-sum work arrays. The bandwidth, plotting grid and density/count normalization are unchanged. Input conversions, variance calculation, filtering, output arrays and native buffers use additional memory; total process memory is not limited to 8 MiB. Ordinary densities may differ from earlier versions by float64 summation roundoff.

Приёмка: same absolute-bandwidth SciPy и dense reference,16byte–8MiB privatebudgets,empty/single/constant/permutation,full observation×grid pair count. Existing public plot parameters не изменены. В local sequential benchmark при30k×800 tracedpeak549.32→8.13MiB,maxdensitydifference5.88e-15. Constructors Causal/IV/Multi1.22–2.24×,IRMextraction1.37–4.14×,matchedcheapIRMfit1.24×. Warmup+5repeats (KDE/fit3),native1,Windows3.12.14; fit excludesconstruction/estimate. Do not claim that all models or platforms speed up by these ratios, or that tracemalloc is processRSS. Full benchmark artifacts accompany the B06 report.

### IV fitting on NumPy 1.x

Sources: [joint labels](https://github.com/MaximLenivkin/Causalis/blob/09e00de5a9d3dc915c6d59627f8b0ebc875dd4e9/causalis/scenarios/iv/model.py), [independent fold reference](https://github.com/MaximLenivkin/Causalis/blob/09e00de5a9d3dc915c6d59627f8b0ebc875dd4e9/tests/inference/test_iivm_numpy_compat.py).

> IIVM constructs joint instrument/treatment stratification labels with a string operation supported by NumPy 1.x and 2.x. Earlier releases could fail before nuisance fitting on NumPy 1.26 because Unicode arrays did not support the addition operator. Joint labels, class order, instrument-only fallback and seeded sample splits retain their previous meaning; the LATE score and inference formulas are unchanged.

Reference: [NumPy 1.26 char.add](https://numpy.org/doc/1.26/reference/generated/numpy.char.add.html). Реальный clean legacy CI обнаружил 53 failures с одной причиной при успешном installation; этот failure нельзя скрывать за последующим canceled status workflow. Новая matrix и integration проверяются на09e00de с1582cases, а первоначальный1569pass локально относится к modernNumPy и более раннему checkpoint. Точные финальные результаты — в B06 implementation report.

## B07: earliest DiD cell, finite nuisance predictions and factual DGP corrections

Изменения реализованы в personal fork; выпуск сайта должен соответствовать выбранному code commit. Sensitivity остаётся вне этого handoff.

### P2 — universal DiD includes the earliest defined pre-treatment contrast

Sources: [support enumeration](https://github.com/MaximLenivkin/Causalis/blob/43f0b3e170f28138fb0155ee99d3680d373b5d52/causalis/data_contracts/panel_data_did.py), [estimator parameters](https://github.com/MaximLenivkin/Causalis/blob/43f0b3e170f28138fb0155ee99d3680d373b5d52/causalis/scenarios/did/model.py), [diagnostic API](https://github.com/MaximLenivkin/Causalis/blob/43f0b3e170f28138fb0155ee99d3680d373b5d52/causalis/scenarios/did/refutation/diagnostics.py), [date-pair and inference regressions](https://github.com/MaximLenivkin/Causalis/blob/43f0b3e170f28138fb0155ee99d3680d373b5d52/tests/scenarios/did/test_did_earliest_pre_period.py).

> With include_pre_periods=True, a universal base compares each earlier observed period with the fixed base g - anticipation - 1, including the first analysis period. A varying base compares adjacent observed periods and therefore starts at the second analysis period. Causalis omits the universal normalizing base and targets in the anticipation window. Comparisons still require eligible controls and observed outcome pairs. With only two pre-treatment periods, the earliest universal contrast is the sole non-normalized placebo contrast.

> Refit existing estimates to obtain the additional supported cells. Cell IDs and negative event-time ranges can change. Existing post-treatment point estimates, influence scores and ordinary analytic intervals are unchanged, but joint pre-tests or simultaneous bands over the expanded cell family can change. These pre-treatment contrasts are placebo diagnostics and do not establish parallel trends.

Приёмка: M/2M, anticipation0/1, balanced/unbalanced, missing pairs, all three control policies и unchanged post inference. Все пять DiD diagnostic parameter lists теперь включают уже поддерживаемый `not_yet_treated`. Нормализованная zero row не добавлена; контрольная политика не расширяется этим fix. Primary reference: [official did::att_gt](https://bcallaway11.github.io/did/reference/att_gt.html). Полная численная идентичность с R-пакетом не заявляется.

### P2 — invalid nuisance predictions must fail before probability repair

Sources: [binary and shared IV adapter](https://github.com/MaximLenivkin/Causalis/blob/a2109a6ecd3c8422fbd4e8a7fd8d5d59334e8159/causalis/scenarios/unconfoundedness/_utils.py), [binary storage](https://github.com/MaximLenivkin/Causalis/blob/a2109a6ecd3c8422fbd4e8a7fd8d5d59334e8159/causalis/scenarios/unconfoundedness/model.py), [multiclass adapter](https://github.com/MaximLenivkin/Causalis/blob/a2109a6ecd3c8422fbd4e8a7fd8d5d59334e8159/causalis/scenarios/multi_unconfoundedness/_utils.py), [multi outcome and storage](https://github.com/MaximLenivkin/Causalis/blob/a2109a6ecd3c8422fbd4e8a7fd8d5d59334e8159/causalis/scenarios/multi_unconfoundedness/model.py), [public-fit and finite-reference regressions](https://github.com/MaximLenivkin/Causalis/blob/a2109a6ecd3c8422fbd4e8a7fd8d5d59334e8159/tests/inference/test_nuisance_prediction_contract.py).

> Learners must return finite numeric nuisance predictions. NaN and positive or negative infinity raise RuntimeError before probability-column selection, hard-label fallback mapping, clipping or normalization can hide them. Binary and multi-treatment IRM also validate assembled predictions before storing them. IIVM obtains the raw-output checks through its shared binary adapter. An invalid unused probability column is rejected as part of the complete learner output.

> The existing warning, clipping and normalization policy for finite out-of-range predictions is preserved. Successful finite fits retain their folds, nuisance predictions, scores and inference. These checks do not guarantee that arithmetic on arbitrarily large finite values cannot overflow. Shape, complex-output and generic refit-state policies are separate follow-ups.

Приёмка: serial/threaded public fits, continuous/binary outcomes, instrument/treatment nuisances, NaN/±inf, single-class metadata fallback, complete raw matrices и independent finite sklearn adapters. IV storage lifecycle не переработан; нельзя описывать этот change как новую полную IV cache policy. Generic sensitivity state остаётся deferred.

### P2 — target rates and copula correlations have distinct reference meanings

Sources: [generator calibration documentation](https://github.com/MaximLenivkin/Causalis/blob/d3b67096dd847792b3b6f79b2a2d43749cab30b0/causalis/dgp/multicausaldata/base.py), [gamma/binary scenario documentation](https://github.com/MaximLenivkin/Causalis/blob/d3b67096dd847792b3b6f79b2a2d43749cab30b0/causalis/scenarios/multi_unconfoundedness/dgp.py).

> target_d_rate calibrates the mean assignment probabilities at U=0 over the generated covariate sample. It does not integrate over latent treatment noise or guarantee exact population-X rates. When latent noise changes relative arm scores, the discrepancy in actual marginal arm rates can persist as sample size grows. Realized treatment shares also fluctuate by sampling. Existing m_<arm> columns remain probabilities at U=0; m_obs_<arm> remains conditional on the realized latent values.

> The Gaussian copula uses a Toeplitz correlation matrix for its latent normal variables Z, with Corr(Z_i,Z_j)=0.3^|i-j|. Marginal transformations, discrete thresholds and clipping can change the Pearson correlations of the observed X variables.

Это factual doc-only correction: generated observations, RNG, existing column values, calibration algorithm и public API не менялись. Example no-X target [.2,.3,.5] с latent strengths [0,2,2] даёт Gaussian-marginal rates [.299729,.262602,.437670], хотя current U=0 probabilities совпадают с target. Supplied U не задаёт автоматически новую reference law. Gaussian-marginal propensity и selection-weighted latent ATT — отдельное запланированное расширение; не описывать их как реализованные B07 функции.

B07 validation: [completed CI run and per-job artifacts](https://github.com/MaximLenivkin/Causalis/actions/runs/37385736343), exact source a2109a6ecd3c8422fbd4e8a7fd8d5d59334e8159. Все шесть Linux stacks (Python3.10–3.14 latest-compatible и3.10representativelegacy) прошли1729casesкаждый, без failures/errors/skips. 147newcases входят в этот count;7sensitivitymodules явно deferred. Это selected correctness scope, не full sensitivity/release или standalone Sphinx validation.

## B08 · Multi-treatment DGP contracts and assignment law

Implementation checkpoint: **9fb8041300410b560da80a45cabac4b541d1629d**, 6October2026. Sources: [generator](https://github.com/MaximLenivkin/Causalis/blob/9fb8041300410b560da80a45cabac4b541d1629d/causalis/dgp/multicausaldata/base.py), [functional wrapper](https://github.com/MaximLenivkin/Causalis/blob/9fb8041300410b560da80a45cabac4b541d1629d/causalis/dgp/multicausaldata/functional.py). Regressions: [numeric contracts](https://github.com/MaximLenivkin/Causalis/blob/9fb8041300410b560da80a45cabac4b541d1629d/tests/data/test_multicausal_generator_contracts.py), [assignment policy](https://github.com/MaximLenivkin/Causalis/blob/9fb8041300410b560da80a45cabac4b541d1629d/tests/data/test_multicausal_assignment_policy.py).

**P2: make assignment-law claims conditional on policy.** The historical sampler retries complete draws until every arm occurs, then forces missing arms into the sample if necessary. Its propensities are nominal model probabilities, not generally actual row-assignment probabilities after conditioning/repair. For n=K=2 and constant probabilities [.9,.1], ensure_all produces one observation per arm, changing actual row probabilities to [.5,.5]. Do not describe this as independent assignment from the supplied probabilities.

Ready-to-use text:

> assignment_policy="ensure_all" is the compatibility default. It retries up to ten complete assignment draws and repairs missing arms while preserving at least one observation in every existing arm. It requires n >= n_treatments. The m and m_obs columns describe the nominal softmax assignment model; they generally do not equal the row probabilities after coverage conditioning or forced insertion. assignment_policy="iid" instead draws once independently per row, permits absent arms, and accepts positive n smaller than n_treatments. In iid mode, m_obs is the conditional assignment probability at the realized U; m remains the softmax probability at U=0.

> Raw DataFrames may contain missing arms under iid. MultiCausalData and downstream estimators retain their separate validation requirements; multiple absent arms can produce duplicate all-zero treatment columns rejected by the data contract. Switching assignment policy can change D, observed Y and RNG progression. The compatibility fix changes formerly invalid repairs that erased an existing singleton arm; first-success draws and already-safe repairs retain their previous labels and RNG sequence.

**P2: document finite numeric boundaries and accepted callback shapes.**

> Numeric configuration, sampled covariates, latent values and callback outputs must be real and finite. Custom X has shape (n, k). Baseline callbacks g_y and g_d accept scalars, one-element vectors or vectors of length n; tau callbacks return n elements. Scalar U broadcasts across observations, while shapes (n,), (n, 1) and (1, n) are normalized to a vector. Non-finite inputs or calculated scores, links, outcomes and oracle columns raise ValueError before invalid values can be concealed by bounded links. The clipped exponential Gaussian oracle also rejects latent strengths whose squared value is not representable; finite output alone is not a certificate of numerical accuracy for arbitrary extreme parameters.

> target_d_rate targets the mean assignment-model probabilities at U=0 over generated X. It does not guarantee realized arm frequencies, population-X rates or latent-marginal rates. Finite positive target weights are normalized; when their sum overflows, scaling by their maximum avoids a zero normalized target. Ordinary finite-sum calibration is preserved.

Marginal Gaussian propensity and selected-treatment ATT are still separate planned APIs. No statistical estimator formula or sensitivity implementation changes in this block. Custom column-name collisions remain a confirmed follow-up; do not claim complete schema validation or hardening of every DGP module. Final integration and CI evidence is recorded in the B08 project report.

B08 CI: [completed run and per-job artifacts](https://github.com/MaximLenivkin/Causalis/actions/runs/37420288433), exact source9fb8041300410b560da80a45cabac4b541d1629d. Each of six representative Linux stacks passed1916cases without failures/errors/skips;187newcases are included. Seven named sensitivity modules remain deferred; this is selected correctness evidence, not full sensitivity, release or standalone Sphinx validation.

## B09 · Multi-treatment output column names

Implementation checkpoint: **1e2b544f7f91a57ad3e049572915a4b3891b084a**. Sources: [generator](https://github.com/MaximLenivkin/Causalis/blob/1e2b544f7f91a57ad3e049572915a4b3891b084a/causalis/dgp/multicausaldata/base.py), [functional wrapper](https://github.com/MaximLenivkin/Causalis/blob/1e2b544f7f91a57ad3e049572915a4b3891b084a/causalis/dgp/multicausaldata/functional.py), [schema regressions](https://github.com/MaximLenivkin/Causalis/blob/1e2b544f7f91a57ad3e049572915a4b3891b084a/tests/data/test_multicausal_namespace_contract.py).

**P2: reject output-name collisions instead of silently replacing columns.** The B08 namespace follow-up is now implemented for the central multi-treatment generator and its wrapper. For example, `d_names=['y', 'arm']` previously replaced the observed outcome with a treatment indicator, and a confounder named `g_d_0` was replaced by an enabled oracle. Even unique arm names `['a', 'obs_a']` produce a duplicate oracle name `m_obs_a`.

Ready-to-use text:

> The generated output schema must have unique, nonempty string column names across the outcome y, treatment arms, actual expanded confounders, and enabled oracle columns. A collision raises ValueError identifying the column and both conflicting roles. Names retain their exact spelling; the generator does not add suffixes, strip whitespace or rename the requested schema. Categorical levels are checked after expansion, including distinct levels that render to the same column name.

> Only columns actually emitted are reserved. With include_oracle=False, oracle-like names remain available. No cate column is emitted for the control arm, so its hypothetical name is also available when it does not collide with another actual column. A custom X sampler retains its existing one-column-per-spec naming behavior rather than expanding categorical specs.

> Treatment and enabled-oracle names are checked at construction and before each generation. The complete schema is checked after successful covariate sampling and before latent draws, structural callbacks, treatment assignment or outcome generation. Mutating public generator fields between calls does not bypass these checks. Existing covariate sampling errors can still occur before the complete schema check.

Migration: choose a unique name explicitly for each requested column when a formerly colliding configuration now raises ValueError. Valid configurations retain their column order, sampled values and RNG progression; 64 configurations with two consecutive generations each were compared exactly with the preceding source. This change adds no marginal propensity or selected-treatment ATT API and does not alter causal estimator formulas.

The shared categorical Gaussian-copula sampler has a separately confirmed pre-existing coordinate-selection defect; B09 does not establish its sampling accuracy or fix that algorithm. Sensitivity remains deferred. Actual local integration and compatibility results are recorded separately in the B09 block report.

B09 CI: [completed run and per-job artifacts](https://github.com/MaximLenivkin/Causalis/actions/runs/37530152376), exact source `1e2b544f7f91a57ad3e049572915a4b3891b084a`. Every one of the six Linux configurations passed **2039 tests**, with no failures, errors or skips. Python 3.10–3.14 latest-compatible and the representative 3.10 legacy stack were verified from downloaded environment, selection and JUnit artifacts. Seven sensitivity modules remain deferred; full sensitivity, release and standalone Sphinx validation are not claimed. Local macOS integration recorded **2038 passed and one DiD diagnostic assertion failure**; its provenance and follow-up are retained in the block report rather than reported as a clean local suite.

## B10 · Categorical Gaussian-copula coordinates

Implementation checkpoint: **95a8b7599fb129fb2c5973f50e9b4a8018732f6c**. Sources: [shared sampler](https://github.com/MaximLenivkin/Causalis/blob/95a8b7599fb129fb2c5973f50e9b4a8018732f6c/causalis/dgp/base.py), [independent regression references](https://github.com/MaximLenivkin/Causalis/blob/95a8b7599fb129fb2c5973f50e9b4a8018732f6c/tests/data/test_copula_categorical_coordinates.py), [existing public CUPED caller](https://github.com/MaximLenivkin/Causalis/blob/95a8b7599fb129fb2c5973f50e9b4a8018732f6c/causalis/dgp/causaldata/functional.py).

**P2: each categorical marginal uses its own latent Gaussian coordinate.** A categorical spec in first position previously raised UnboundLocalError; subsequent categorical specs used the uniforms of the preceding numeric marginal, giving incorrect dependence. With identity latent correlation, a balanced category followed the sign of its preceding normal exactly. Explicit-copula binary, multi-treatment and inherited IV paths receive the shared fix; existing make_cuped_tweedie also uses the affected sampler.

Ready-to-use text:

> Each confounder spec uses the Gaussian uniform from its own latent coordinate. Categorical probabilities are normalized and applied as cumulative intervals, then expanded into indicators excluding the first category. At a cumulative threshold, the next nonzero interval is selected. The existing one-level category representation remains a zero column named <name>__onlylevel.

> Categorical uniforms are not clipped to the numeric inverse-CDF bounds, preserving legitimate probability intervals smaller than 1e-12. If the Gaussian CDF saturates at its upper boundary, the fallback selects the final category with positive probability; a trailing zero-probability category cannot be selected solely by that boundary. The numeric marginal transforms retain their existing clipping, latent correlation repair and jitter.

> The correlation matrix describes latent Gaussian dependence. Discretization changes observed Pearson correlations; for a balanced binary category defined by the sign of a standard normal, Corr(Z0, category)=rho*sqrt(2/pi), rather than rho.

Migration: corrected categorical X values can change D, Y and oracle columns for the same seed. The shared helper consumes the same Gaussian random draw and adds no draws. Full downstream RNG equality is not promised for categorical datasets because dependent sampling branches may change. Numeric-only arrays and full binary/multi/IV frames, dtypes, schema and next RNG draws were compared exactly with the preceding source. This block does not add malformed categorical-spec validation or new marginal propensity APIs.

B10 CI: [completed run and downloaded per-job evidence](https://github.com/MaximLenivkin/Causalis/actions/runs/37532909989), exact source95a8b7599fb129fb2c5973f50e9b4a8018732f6c. All six representative Linux configurations passed **2072 tests each**, without failures/errors/skips; 33 new cases are included. Local macOS integration recorded **2071 passed and one confirmed pre-existing DiD near-zero diagnostic assertion failure**, with unchanged fixture/called-source and the same B09 cell values. Seven sensitivity modules remain deferred; full sensitivity, standalone Sphinx and release validation are not claimed.

B10 does not establish complete output-name validation for binary or IV generators. A separately confirmed confounder named d can overwrite their raw treatment column; B09's namespace guard covers the multi-treatment generator. Complete binary/IV actual-schema validation remains a separate planned correction.


## B11 · Binary and IV output column names

Implementation checkpoint: **cdc2c9590246c5b049d2184ba3479324217b2b00**. Sources: [binary generator](https://github.com/MaximLenivkin/Causalis/blob/cdc2c9590246c5b049d2184ba3479324217b2b00/causalis/dgp/causaldata/base.py), [IV generator](https://github.com/MaximLenivkin/Causalis/blob/cdc2c9590246c5b049d2184ba3479324217b2b00/causalis/dgp/causaldata_instrumental/base.py), [schema regressions](https://github.com/MaximLenivkin/Causalis/blob/cdc2c9590246c5b049d2184ba3479324217b2b00/tests/data/test_binary_iv_namespace_contract.py).

**P2: reject collisions across the actual core-generator output schema.** A confounder named `d` previously replaced the binary treatment with arbitrary numeric values in both generator families. Duplicate expanded confounders, outcome names and enabled oracle names could also silently replace columns. An IV instrument named `m` was replaced by its instrument-propensity oracle when oracles were enabled.

Ready-to-use text:

> CausalDatasetGenerator and InstrumentalGenerator require unique, nonempty string names across every emitted core column, actual expanded confounder and enabled oracle. ValueError identifies the conflicting column and both roles. The generator preserves exact names, including whitespace, and requires the actual confounder-name count to match the sampled width. Existing categorical expansion and custom-sampler naming rules remain in effect.

> Each family reserves only its own enabled oracle columns. IV emits m, r_obs, r_z0, r_z1, g_z0, g_z1, iv_first_stage, iv_reduced_form, late_x, late, tau_link, g_d0, g_d1 and cate. Binary emits m, m_obs, tau_link, g0, g1 and cate. With oracles disabled, their names remain available. IV also permits binary-only names such as m_obs and g0 with IV oracles enabled.

> Fixed output names are checked at construction and before every generation. The complete actual namespace is checked after covariate sampling and before latent draws, structural callbacks, calibration and assignment. A final check before DataFrame assembly catches callbacks that change the instrument name or enable colliding oracle columns during the same call. A late rejection can occur after callbacks and random draws; failed generation does not roll back their effects.

Migration: explicitly choose unique names for formerly colliding configurations. Valid schemas retain values, column order, dtypes and RNG progression, including previously accepted zero-confounder custom containers. Public signatures, assignment and oracle arithmetic remain unchanged. The IV alias and wrappers inherit core conflicts through generate.

Wrapper-added pre-period and ancillary columns, column ordering and data-contract feature projection retain separate policies. Confirmed remaining cases include custom pre_name='y', ancillary/confounder age overwrite, IV ordering that duplicates instrument names user_id or a disabled oracle name, and automatic conversion that excludes disabled-oracle-named confounders. Complete wrapper namespace validation is a separate planned correction. Sensitivity, marginal-propensity API, selected-treatment ATT and numerical-zero DiD diagnostics remain separate work.

B11 baseline/focused evidence: the same163newcases produced103failures/60passes on exact4d6b814 and163passes after the correction. Final local integration and CI results are recorded in the B11 block report.


B11 CI: [completed run and per-job artifacts](https://github.com/MaximLenivkin/Causalis/actions/runs/37589241406), exact source `cdc2c9590246c5b049d2184ba3479324217b2b00`. Each of the six representative Linux configurations passed2235cases without failures/errors/skips. The Mac run passed2234cases with the same confirmed pre-existing numerical-zero DiD assertion failure; the local suite is not clean. Seven named sensitivity modules remain deferred; standalone Sphinx and release were not validated.
