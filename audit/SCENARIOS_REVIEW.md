# Ревью RCT, CUPED, IV, DID и Synthetic Control

Снимок: `ffe2c356c115f335b74b2f10117e19fe15585d46`, дата проверки 2026-10-05 (Europe/Moscow). Исходники не изменялись. Прочитаны `AGENTS.md` и `audit/PLAN.md`. Интерпретатор — repo-local `.venv/Scripts/python.exe`; Python 3.12.14, NumPy 2.5.3, pandas 3.0.6, statsmodels 0.15.0. Общий pytest запускает главный агент; здесь запускались только собственные фокусные воспроизведения.

**Главный вывод:** в DID есть подтверждённые ошибки inference и выбора pre-period control group. В RCT неверно реализован заявленный default Newcombe CI. CUPED в обычной конфигурации использует разумную Lin/HC2 спецификацию, но есть ошибки имён столбцов и численной диагностики. В ASCM не обнаружена подтверждённая ошибка базовой формулы ridge augmentation; есть дефект воспроизводимости refutation при нестандартных настройках. IIVM score соответствует обычному ортогональному ratio score для LATE; обнаружено несоответствие диагностического API документации, а weak-IV inference остаётся ограничением.

## Воспроизведение

```powershell
$env:MPLCONFIGDIR='D:\codex\Causalis\audit\mplcache'
.\.venv\Scripts\python.exe audit\repro_scenarios.py *> audit\repro_scenarios.log
```

Скрипт самодостаточен относительно установленного проекта; не меняет исходники и не запускает pytest. Каждый probe изолирован и печатает JSON. Лог `repro_scenarios.log` содержит числовые результаты. Reference DR inference — самостоятельный Python перевод влияния нормировок и nuisance estimation из официального DRDID, с `logit_ridge=0`; это не запуск R-пакета и не независимое Monte Carlo доказательство coverage.

## Приоритетные находки

| ID | Уровень | Находка | Статус |
|---|---|---|---|
| SC-01 | P1 | DID IPW SE зависит от произвольного общего временного тренда | Подтверждено воспроизведением |
| SC-02 | P1 | DID pre-period controls содержат собственную treated cohort; IF перезаписывается | Подтверждено воспроизведением и official did |
| SC-03 | P1 | DID MLE/OLS DR inference не учитывает nuisance estimation и control normalization | Подтверждено кодом, reference formula и числовым probe |
| SC-04 | P1 | DID population aggregations не учитывают оценивание весов cohort shares | Подтверждено воспроизведением и official did; важна целевая популяция |
| SC-05 | P1 | RCT `newcombe` default вычисляет другой интервал | Подтверждено сравнением со statsmodels |
| SC-11 | P1 | Clustered DID bootstrap принимает один cluster и выдаёт практически нулевой SE | Подтверждено воспроизведением |
| SC-06 | P2 | CUPED допустимые имена treatment перезаписывают дизайн или ломают fit | Подтверждено воспроизведением |
| SC-07 | P2 | CUPED leverage через `pinv(X'X)` теряет направления при смене масштаба | Подтверждено воспроизведением |
| SC-08 | P2 | SCM refutation не наследует параметры исходного estimate | Подтверждено воспроизведением |
| SC-09 | P2 | IV diagnostics не принимают IIVM, хотя docstring обещает | Подтверждено воспроизведением |
| SC-10 | P2 | RCT неверный enum молча меняет метод CI/p-value | Подтверждено воспроизведением |
| SC-12 | P2 | CUPED batch cache optimization не работает со statsmodels 0.15.0 | Подтверждено установленным исходником statsmodels и suite failure главного агента |

Число пунктов отражает обнаруженные дефекты; для общего top-10 их нужно сопоставить с другими модулями проекта. Уровни соответствуют общей шкале проекта. P1 означает неверный результат в поддерживаемом сценарии, P2 — ограниченный сценарий/API/интерпретация или нарушение заявленной оптимизации.

### SC-01. Неверный IF нормированного IPW DID

**Код:** `causalis/scenarios/did/model.py:563`, `:564`, `:574`, downstream `:317`, `:356`.

Оценка ATT использует отдельно нормированные treated и control weights. Однако `raw_scores = (wt-wc)*ΔY - wt*ATT` для `estimator='ipw'` не является IF этой разности нормированных средних. Даже без covariates корректное leading influence равно `wt*(ΔY-μt)-wc*(ΔY-μc)`. Пропущена control mean centering/нормировка; это не небольшой конечновыборочный множитель.

**Условие:** `estimator='ipw'`, валидная balanced panel, обычный общий тренд. Наличие covariates не требуется.

**Probe `did_ipw_translation`:** добавление `1000*t` всем unit outcome оставило ATT первой post-cell `1.6805588086`, но SE изменился `0.37785552 → 258.24383199`, p-value `8.68e-6 → 0.99480769`. Для второй post-cell SE `0.40543 → 516.38337`. Общий тренд должен сокращаться в DID и не менять uncertainty разности изменений.

**Исправление:** вывести IF именно фактически вычисляемого normalized estimator, добавить propensity-estimation contribution, затем regression invariance test на общий тренд. Multiplier bootstrap текущих неверных scores проблему не устраняет.

### SC-02. Собственная когорта становится своим контролем в pre-period

**Код:** `causalis/scenarios/did/model.py:217`, `:224`, `:539`, `:604`; тот же выбор в `causalis/data_contracts/panel_data_did.py:801`, `:860` и `causalis/scenarios/did/refutation/diagnostics.py:109`, `:378`.

Для target до first treatment функция включает все `first_treatment > target+anticipation`. Включается сама оцениваемая когорта g. Затем `sample_units = treated_units + control_units` дублирует одни и те же unit, а присваивание `full_scores[unit_pos[unit]]=...` перезаписывает treated вклад control вкладом. Для universal base также возможны controls, уже treated к более позднему base time.

**Условие:** `include_pre_periods=True` и `control_group='not_yet_or_never'` (default) либо `not_yet_treated`. `never_treated` защищён от этой конкретной ошибки.

**Probe `did_pre_controls`:** 30 treated и 30 never controls, treated pre slope 2, target Feb и base Mar. Правильный pre difference `-2`; получено `-1`, поскольку 30 treated одновременно включены в 60 controls. Diagnostic payload содержит 30 duplicate unit rows в этой cell.

Официальный [`did/compute.att_gt.R`](https://raw.githubusercontent.com/bcallaway11/did/master/R/compute.att_gt.R) выбирает not-yet controls с исключением текущей когорты и threshold по более позднему из target/base. Нужно единое правило для support, estimator и refutation; иначе после локального исправления модели диагностика останется несогласованной.

### SC-03. DR score используется вместо полного IF MLE/OLS estimator

**Код:** `causalis/scenarios/did/model.py:261` (logit MLE), `:307` (control OLS), `:574` (raw score), `:594` (embedding).

Модель оценивает propensity обычным MLE и outcome обычным OLS. Для такого традиционного DR estimator inference при misspecification одного nuisance требует first-order contributions от оценивания обоих nuisance и от нормировок. Код не вычисляет их; одинаковая raw formula используется для DR, AIPW и IPW. Orthogonality при двух корректных моделях не делает score полным IF при одном корректном nuisance.

**Probe `did_dr_mle_influence`:** n=1000, logit propensity корректен, линейный outcome misspecified (`exp(.7*x)`). Library cell SE `0.04438196748`; SE полного MLE/OLS IF `0.03887567351`; weighted control residual mean `0.08749728`. Max difference между individual scores и reference IF `2.79495`. Это доказательство несовпадения формулы, а не оценка частоты покрытия.

В официальном [`DRDID/drdid_panel.R`](https://raw.githubusercontent.com/pedrohcgs/DRDID/master/R/drdid_panel.R) явно присутствуют normalization, OLS influence и logit influence contributions. Возможные решения: реализовать полный традиционный IF либо IPT propensity + weighted least squares improved DR, либо cross-fitting с корректно заявленными условиями. [Improved DRDID](https://psantanna.com/DRDID/reference/drdid_imp_panel.html) отдельно обосновывает double robustness inference.

### SC-04. Population aggregate SE не учитывает оценивание cohort shares

**Код:** `causalis/scenarios/did/model.py:803`, `:824`, `:838`, `:847`, `:853`.

Simple/calendar/event aggregation использует эмпирические `n_treated` и вычисляет influence только как weighted sum cell IF. Пропущен contribution от random sample cohort proportions. Для conditional estimand с фиксированными cohort counts можно заявить другой inferential target, но текущий API назван Callaway–Sant'Anna population aggregation и такого ограничения не сообщает.

**Probe `did_aggregate_weight_influence`:** 30 units в когорте g1 (tau=2, три post cells), 30 в g2 (tau=10, две post cells), 30 controls. Внутри cell outcomes детерминированы. ATT=5.2; library aggregate SE `8.1e-18`, population weight IF SE `0.4957418683`. Нулевая внутри cell неопределённость не устраняет неопределённость population cohort mixture.

Официальный [`did/compute.aggte.R`](https://raw.githubusercontent.com/bcallaway11/did/master/R/compute.aggte.R) добавляет `wif` для simple, dynamic и calendar aggregates. Исправление нужно согласовать с estimand, missing-data policy и cluster inference.

### SC-05. Default Newcombe interval вычислен неверно

**Код:** `causalis/scenarios/classic_rct/inference/conversion_ztest.py:158`–`:161`.

Вычитаются endpoints двух Wilson intervals: `(l1-u0,u1-l0)`. Newcombe hybrid score использует корень суммы квадратов односторонних расстояний от p1/p0 до Wilson endpoints. Это существенно другой интервал, обычно шире заявленного.

**Probe `newcombe`:** 7/34 successes treated, 1/34 control. Library default CI `[-0.04566046,0.36277297]`; [официальный statsmodels](https://www.statsmodels.org/dev/_modules/statsmodels/stats/proportion.html) `newcomb` CI `[0.01892144,0.34036869]`. Library p-value=.0239258 при default CI, включающем 0. Тесты разных методов в принципе могут расходиться с CI, поэтому доказательство ошибки здесь — формула/reference comparison, а не само расхождение p и CI.

**Исправление:** реализовать hybrid distances или использовать `confint_proportions_2indep(...,method='newcomb')`; обновить tests, которые сейчас могут закреплять неверную формулу.

### SC-06. Collision внутренних имён CUPED с валидными входными именами

**Код:** `causalis/scenarios/cuped/model.py:405`, `:410`, `:442`, `:536`.

Design строится словарём с ключами `intercept`, treatment_name, generated `x__centered`, `treatment:x`, а treatment coefficient берётся как `params[1]`. Входные data contracts не резервируют эти имена. При совпадении ключа Python dictionary перезаписывает колонку без ошибки.

**Probe `cuped_name_collision`:** treatment='intercept' с covariates=[] вызывает IndexError на корректном CausalData. Treatment='x__centered' и covariate='x' удаляет D из adjusted design: ATE=3.006655, тогда как harmless rename treatment→'d' даёт 2.021069 на тех же данных. Меняется математическая модель лишь из-за имени столбца.

**Исправление:** уникальные внутренние design names независимо от user columns и явная сохранённая позиция D; validation generated-column collisions как быстрый промежуточный patch.

### SC-07. Leverage диагностика нестабильна к масштабу X

**Код:** `causalis/scenarios/cuped/refutation/regression_checks.py:126`; то же использование `pinv(z.T@z)` в `causalis/scenarios/cuped/model.py:968`, `:998` влияет на delta CI с raw-control denominator.

Normal equations квадратично увеличивают condition number. SVD threshold `pinv(X'X)` может выбросить направления, которые SVD/QR исходного X ещё сохраняет. В результате Cook's distance, studentized residuals и HC2/HC3 stability diagnostics вычисляются для другой projection matrix.

**Probe `cuped_leverage_scaling`:** full-rank design rank4. После умножения covariate на 3e7 condition исходного design ~7.94e7 (ниже default warn threshold1e8). Trace leverage должен быть4 и reference trace~4, но библиотека получает2.9965158. При scale1 trace4. Max individual h error .00730446.

**Исправление:** использовать `diag(X @ pinv(X))`, economy QR или уже доступный statsmodels `pinv_wexog`; не пересчитывать normal-equation pseudoinverse. Нужны scale invariance checks для диагностики и raw-control relative inference.

### SC-08. Refutation ASCM меняет конфигурацию модели

**Код:** `causalis/scenarios/synthetic_control/refutation/placebo.py:144`, `:182`; `sensitivity.py:133`.

При `model_kwargs=None` каждый refit создаёт default ASCM независимо от исходной модели. Placebo-in-space даже заново оценивает actual treated row другим estimator. Leave-one-donor-out delta смешивает изменение donor pool, regularization и способа вычисления average ATT.

**Probe `scm_refutation_settings`:** исходный lambda_aug=1e6, average t-test отключён. Original mean gap1.331466; actual-treated row placebo без kwargs1.371201, с matching kwargs1.331466. Drop donor2 LOO default delta .472748, с matching kwargs≈-1.01e-5. Значительная часть «sensitivity» вызвана сменой конфигурации.

**Исправление:** сохранять полный serializable fitting/inference configuration в estimate, наследовать его default refutation, явно сообщать intentional overrides. До этого документация должна требовать передачу matching kwargs. Failures LOO сейчас также проглатываются без reason (`sensitivity.py:146`): добавить status/reason columns.

### SC-09. Документированный IIVM diagnostics API не работает

**Код:** `causalis/scenarios/iv/refutation/diagnostics.py:134`; обещание типов в `:420`, `:473`, `:518`, `:562`.

Resolver принимает IVDiagnosticData или объект с `.diagnostic_data`. У IIVM нет этого атрибута; модель хранит `.result_` и `.diagnostics_` другой структуры.

**Probe `iv_fit_diagnostics`:** после `.fit().estimate()` first_stage(estimate) возвращает таблицу7×5, first_stage(model) выдаёт ValueError “Missing result.diagnostic_data”. Это также касается instrument_overlap, reduced_form и plot.

**Исправление:** resolver может извлекать `model.result_.diagnostic_data`, проверяя факт estimate; либо изменить docstrings и type contract на исключительно estimate/payload.

### SC-10. Неверные enum значения молча выбирают другой z-test

**Код:** `causalis/scenarios/classic_rct/inference/conversion_ztest.py:135`, `:167`.

Нет runtime проверки `ci_method` и `se_for_test`. Любой опечатанный se_for_test приводит к unpooled p-value; любой неизвестный ci_method к Wald-unpooled CI. Literal annotations runtime не защищают.

**Probe `newcombe`:** `ci_method='typo',se_for_test='typo'` успешно возвращает p=.0188701 и CI `[.0291694,.3237718]`. Пользователь не узнаёт, что запрошенный метод не применён.

**Исправление:** explicit allowed-set validation; это быстрый low-risk patch.

### SC-11. Clustered DID bootstrap обходит требование двух clusters

**Код:** `causalis/scenarios/did/model.py:334`, `:374`; analytic check только в `:328`.

`_variance_from_scores` отклоняет один cluster, но при bootstrap ветка этой функции не вызывается. Единственный cluster получает общий multiplier, а сумма корректно центрированных scores≈0; inference становится почти вырожденным.

**Probe `did_single_cluster_bootstrap`:** analytic путь корректно отклоняет панель с единственным cluster: `ValueError: Clustered inference requires at least two clusters.` Но199-replication bootstrap на тех же данных успешно выдаёт ATT2.09751 и aggregate SE2.52e-16; cell SE1.52e-16 и3.86e-16. Требование минимум двух clusters следует проверять до обеих ветвей; для малого числа clusters желательно отдельное finite-cluster предупреждение. Статус — подтверждено воспроизведением.

### SC-12. Повторное использование CUPED design cache не работает на statsmodels0.15

**Код:** `causalis/scenarios/cuped/model.py:436`, `:445`, `:481`–`:493`; тест `tests/statistics/test_cuped_rct.py:80`.

`_reuse_design_decomposition` устанавливает `pinv_wexog`, `normalized_cov_params`, `rank`, `wexog_singular_values` в следующую OLS модель перед `.fit()`. Все эти имена существуют, но установленный statsmodels0.15.0 теперь явно пересчитывает их при каждом `.fit()` независимо от существующего cache. Это видно в `.venv/Lib/site-packages/statsmodels/regression/linear_model.py:377`–`:390`: recomputation — намеренная semantics новой реализации, а не переименование полей.

**Подтверждение:** главный агент воспроизвёл failure `assert first_ols.pinv_wexog is second_ols.pinv_wexog` в общем suite и повторной проверке. Этот subagent прочитал установленную реализацию и проверил наличие всех четырёх cache attributes. Числовое соответствие batch и отдельных fits покрывается существующими тестами; найденный дефект касается promised reuse/performance и compatibility test. Новый fit probe не запускался во время изолированного benchmark главного агента.

**Исправление:** выполнять batched least squares самостоятельно с одной QR/SVD факторизацией и outcome-specific robust covariance или использовать публичный поддержанный механизм reuse. Не расширять копирование внутренних полей statsmodels: текущий `.fit()` намеренно их перезаписывает. Поддерживаемые версии зависимостей должны проверяться в CI; простое снятие identity assertion скрывает потерю ускорения.

## Документация и методологические оговорки

1. **P2:** `did/model.py:909` говорит, что cells skipped при превышении clipping threshold, но `:591` лишь добавляет warning flag. Минимумы n/ESS и condition threshold тоже не являются hard support constraints. Нужно явно разделить warn/raise/skip policy.
2. **P2:** `did/model.py:889` описывает varying base `t-1` для всех t, тогда как post cells используют universal base (что соответствует CS). Docstring должен ограничить varying rule pre-periodами.
3. **P2:** `did/dgp.py:306` обещает “0 = parallel” для parallel_trend_violation, но DGP имеет multiplicative levels, differential initial log_size (`:186`) и общие факторы во времени. Параллельность лог-трендов не равна аддитивным parallel trends outcome levels. Это подтверждённая необоснованность общего обещания; полная conditional PT для конкретных covariates не доказана в этом аудите. Нужен отдельно гарантированный additive-PT benchmark и Monte Carlo проверки под нулём.
4. **P2:** `did/refutation/diagnostic_plots.py:42` агрегирует raw cell SE как будто cells независимы. Shared controls и overlapping periods делают covariance ненулевой. Для honest plotted uncertainty нужно unit-level IF covariance, либо показывать raw point estimates без inferential error bars.
5. **P2:** `did/refutation/post_inference.py:1003` green overall reliability сообщает “I can rely on the results”. Такие thresholded diagnostics не подтверждают parallel trends, causal identification, корректность influence formula или coverage. Указать, что это heuristic readiness/fragility checks.
6. **P3:** DID model doc defaults propensity_clip1e-4, ridge1e-4, condition1e5; фактически1e-6,1e-8,1e8 (`did/model.py:23`–`:27`, `:974`–`:985`). DGP doc n_treated20/n_control60 (`did/dgp.py:289`) против200/600. CUPED Tweedie doc n10000 (`cuped/dgp.py:123`) против20000 (`:82`).
7. **P3:** многочисленные DID diagnostic examples передают `n_units,n_periods`, которых нет среди поддержанных generator knobs; сейчас **advanced_params** их принимает и generator явно отклоняет unknown parameters (`did/dgp.py:374`). Примеры в diagnostics.py:257,349,518,668,893; diagnostic_plots.py:105,254; post_inference.py:206,287,559. В post_inference.py:210 обещана колонка 'group', фактически 'cohort'.
8. **P3:** `iv/__init__.py:7` расшифровывает IIVM как Iterated Instrumental Variable Model; class называется Instrumental Interactive Regression Model. Исправить терминологию.
9. **P3:** SCM Poisson doc default treatment start2003-02 (`synthetic_control/dgp.py:259`) скопирован с36-month Gamma default; actual n_pre180 implies2015-02 по описанным offset semantics. Это требует runtime confirmation генератора, статическая арифметика и doc defaults явно несогласованы.
10. **P2 методология:** permutation Welch test (`classic_rct/inference/welch_permutation_t_test.py:110`) должен различать finite-sample exactness при exchangeability/sharp null и асимптотическую weak-null validity studentization при unequal distributions; фраза “valid correction” для +1 сама по себе не оправдывает exchangeability. Для ASCM conformal указать условия permutation scheme, serial dependence и grid truncation. Текущий код разумно хранит disjoint confidence sets и warns grid boundaries, но grid approximation не является точной непрерывной инверсией.

## Современность и десять направлений развития

Это scoped assessment этих пяти сценариев, не утверждение об исчерпывающем обзоре всех статей до2026. Сначала исправления inference; добавление новых estimator поверх неверных IF увеличит технический долг.

| Приоритет | Направление | Что добавить и почему |
|---|---|---|
| 1 | Improved DR DID | IPT + weighted outcome regression, full influence payload, независимо проверить с official DRDID. [Sant'Anna–Zhao implementation](https://psantanna.com/DRDID/reference/drdid.html) |
| 2 | Weak-IV robust confidence sets | Orthogonal Anderson–Rubin/test inversion, разрешить unbounded/disconnected sets; absolute first-stage threshold и F≥10 не заменяют robust inference. [Ma, updated2025](https://arxiv.org/abs/2302.09756), [DoubleML robust IV API](https://docs.doubleml.org/dev/examples/py_double_ml_robust_iv.html) |
| 3 | DID sensitivity к parallel trends | Honest-DiD-style deviation bounds и sensitivity curves, а не green status по nonsignificant pretest. [Rambachan–Roth paper](https://www.aeaweb.org/conference/2022/preliminary/paper/B4ADD9Qd) |
| 4 | Population/conditional aggregation targets | Явный target, estimated-weight IF, event-window selection и balanced composition, reference parity с [official did](https://raw.githubusercontent.com/bcallaway11/did/master/R/compute.aggte.R) |
| 5 | Cluster RCT/CUPED inference | cluster-robust SE, randomization unit в data contract, few-cluster methods и design-consistent permutation assignment; текущий CUPED doc честно сообщает отсутствие |
| 6 | Nonlinear RCT adjustment | Cross-fitted prognostic ML/CUPAC/AIPW with known randomization probability, наравне с полезным низковариантным Lin default; variance reduction без post-treatment covariates |
| 7 | Robust relative-effect inference | Fieller/log-risk-ratio/inversion при near-zero control mean; сейчас delta CI остаётся нестабильным ещё до machine-epsilon guard |
| 8 | ASCM tuning | Pre-treatment blocked CV lambda_aug с scale-aware parameterization и selection diagnostics. Ridge augmentation как семейство соответствует [Ben-Michael–Feller–Rothstein](https://arxiv.org/abs/1811.04170) |
| 9 | ASCM validated inference protocols | Coverage regression against latest [CWZ t-test v9,2025](https://arxiv.org/abs/1812.10820), autocorrelated/nonstationary DGPs, block choices and degeneracy reporting; здесь формула self-normalization выглядит совместимой, это не найденный баг |
| 10 | Design-aware RCT analysis | Stratification, unequal known propensity, multiple outcomes/arms multiplicity, sequential monitoring/e-values as explicit inference modes rather than optional kwargs |

## Производительность: конкретные места

1. **DID support и diagnostics repeatedly scan/copy long panel.** `PanelDataDID.att_gt_cells` внутри cohort×time фильтрует whole DataFrame; diagnostics helper `_delta_y` ещё раз `df_analysis()` и pivot per cell. Prepare indexed unit×time NumPy outcomes/covariates once; cache first-treatment index and eligibility masks. Preserve missingness semantics и row alignment.
2. **DID main prepared outcome pivot уже есть**, но `_design_at_base` делает boolean filter по long df per cell; хранить covariate blocks per time. В official did latest [compute.att_gt.R](https://raw.githubusercontent.com/bcallaway11/did/master/R/compute.att_gt.R) такая precomputation тоже используется — полезная практическая reference, а не сравнение абсолютных benchmark times.
3. **Unit positions rebuilt every DID cell** (`did/model.py:601`); создать once mapping/vector integer positions. Изменение также облегчает duplicate-treated/control detection.
4. **CUPED repeated design decomposition:** batch-outcome cache перестал экономить SVD на statsmodels0.15 (SC-12). Дополнительно `design_matrix_checks` делает rank и condition декомпозиции до fit и снова в default checks. Нужна одна поддержанная факторизация на design с reuse для всех outcomes и diagnostics. Предварительная validation не должна исчезать ради скорости.
5. **CUPED diagnostics recompute normal-equation inverses** for h/raw denominator; use cached pinv/QR simultaneously improves correctness (SC-07) and speed.
6. **CUPED bootstrap** creates DataFrames, centers, and refits statsmodels1000 times; preallocate numeric matrices and solve least squares; percentile/bootstrap ratio draws still need full recentering per sample. Keeping recentering is statistically necessary for chosen target.
7. **ASCM pointwise conformal** performs grid_size×n_post repeated simplex SLSQP and linear solves. Cache base Gram/rhs and update a single candidate-outcome rhs; warm-start simplex optimization and reuse augmented constrained-system factorization. Preserve exact same optimization tolerances and accepted sets.
8. **ASCM circular shifts** allocate n×n arrays and loops despite pointwise n_post=1: p reduces to rank of final |residual| among all |residuals|; implement vectorized comparison where mathematically identical.
9. **ASCM reference fits** repeatedly validate/copy full panel, including all oracle columns; retain only required typed arrays, share immutable core with explicit donor selections. Source data must remain protected from mutation.
10. **IV predict/training arrays** already extract NumPy once; current n_jobs thread-based folds reduces dataframe overhead. Main runtime may be nuisance CatBoost rather than pandas; profile with cheap learners before generalizing “pandas slower”. Defaults are correctly configured thread_count1 for fold-level parallelism.

Эти пункты — candidates, не измеренные ускорения. Главный агент выполняет общий performance benchmark. Нужны equality checks по point estimate, score, SE/CI, ordering, missingness и sensitivity before timing comparisons.

## Что просмотрено и что осталось непроверенным

Все39 Python files этих scenario directories просмотрены статически: classic_rct(7), cuped(7), iv(6), did(8), synthetic_control(11), включая `__init__`, dgp, models, inference и refutation helpers. Некоторые core DGP/data-contract функции вне этих directories использовались для трассировки; общий их аудит выполняет главный агент.

| Область | Coverage |
|---|---|
| Classic RCT | model, ttest, conversion_ztest, permutation, DGP, exports; Newcombe/enum numeric probe |
| CUPED | single/batch RctCausalData path, shared design decomposition, relative delta/bootstrap, covariance policy, all regression flags/config/forest plot, both DGPs; names and leverage probes |
| IV | learners, fit, support, cross-fit, normalized score, diagnostics/balance, DGP, exports; cheap-learner fit and diagnostic resolver probe |
| DID | support/preparation, propensity/OR, influence, cluster/bootstrap, all four aggregate families, all pre/post diagnostics and plots, Gamma DGP; invariants/reference influence/aggregation probes |
| SCM | simplex/projected-gradient, ridge constraint, fit state, all conformal/average inference paths, placebo/time/LOO, feasibility/diagnostic plots, both DGP wrappers; config inheritance probe |

Не выполнены: исчерпывающий Monte Carlo coverage, сравнение всех R package outputs, adversarial tests всех параметров и pandas dtypes, визуальный QA всех matplotlib figures, полный benchmark всех grid/donor sizes. Числовой probe на нескольких сценариях подтверждает конкретные дефекты, но не доказывает отсутствие иных. Lin adjustment и IIVM score не объявляются ошибочными только из-за того, что существуют более новые исследования.
