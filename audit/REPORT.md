# Полное ревью Causalis

**Дата:** 5 октября 2026. **Проект:** [GitHub](https://github.com/causalis-causalcraft/Causalis), [документация](https://causalis.causalcraft.com/). **Локальная копия:** `D:\codex\Causalis`. **Commit:** `ffe2c356c115f335b74b2f10117e19fe15585d46`, установленная версия `1.0.8.dev1`.

## Главный результат

Causalis имеет содержательное современное ядро: orthogonal scores и held-out cross-fitting, multi-treatment, GATE/GATET, sensitivity analysis, staggered DiD, augmented synthetic control и отдельную оценку политики. Базовый binary IRM ATE в сопоставленном сценарии совпал с DoubleML по predictions, оценке и стандартной ошибке до machine precision.

Но найден ряд ошибок, из-за которых **соответствующим inference/sensitivity результатам сейчас нельзя доверять без исправления**. Особенно важны multi ATTE influence function, multi sensitivity benchmarks, lifecycle после refit, несколько DiD IF/aggregation paths и default Newcombe CI. Диагностики иногда показывают PASS там, где обнаружено полное separation, или p=1 по алгебраическому тождеству. Документация местами необоснованно превращает «проверка не выявила проблему» в «предпосылка идентификации истинна».

После объединения связанного balance дефекта каталог содержит **31 находку кода/инференса/контрактов/инфраструктуры: 11 P1 и 20 P2**. Здесь один пункт может охватывать несколько связанных paths. Ошибка Newcombe фигурирует также в документационном списке, но это один дефект, а не два независимых. Массовый P0 дефект всего ядра не установлен. Отдельно приведены топ-10 документационных проблем и дополнительные неточности в приложении.

Предположение о повсеместной медлительности из-за pandas не подтвердилось: matched IRM fit здесь **0.147 с у Causalis против 0.364 с у DoubleML**. Тем не менее data preparation имеет измеримые издержки; прототипы ускорили отдельные этапы примерно в 1.7–5.9 раза. Эти числа не означают такое же ускорение всего pipeline.

## Артефакты и навигация

| Документ | Содержание |
|---|---|
| [DML_REVIEW.md](D:/codex/Causalis/audit/DML_REVIEW.md) | Полные derivations, конкретные строки, условия и воспроизведения Unconfoundedness/Multi/GATE/Uplift |
| [SCENARIOS_REVIEW.md](D:/codex/Causalis/audit/SCENARIOS_REVIEW.md) | RCT/CUPED/IV/DiD/SCM, 12 находок, reference formulas и ограничения |
| [CONTRACTS_SHARED_DGP.md](D:/codex/Causalis/audit/CONTRACTS_SHARED_DGP.md) | Data contracts, shared diagnostics, генераторы, зависимости и release workflow |
| [DOCS_RESEARCH.md](D:/codex/Causalis/audit/DOCS_RESEARCH.md) | Сайт, docstrings, 40 notebooks, 10 основных + 9 дополнительных неточностей, первичные статьи |
| [PERFORMANCE.md](D:/codex/Causalis/audit/PERFORMANCE.md) | Методика/результаты benchmark, профиль pandas/arrays, топ-10 оптимизаций |
| [COVERAGE.md](D:/codex/Causalis/audit/COVERAGE.md) | Карта всех модулей, глубина проверок и явно непроверенные области |
| [PROGRESS.md](D:/codex/Causalis/audit/PROGRESS.md), [PLAN.md](D:/codex/Causalis/audit/PLAN.md) | Этапы, журнал и шкала доказательств |

Библиотечные исходники оставлены в исходном состоянии для воспроизводимости; audit scripts, reports и outputs находятся в `audit/`. Исправления и публикация изменений не выполнялись.

## Как проводилась проверка

Проверены все группы модулей, инвентаризированы **130 Python modules без generated `_version.py`, 48 194 строки, 123 test files, 40 notebooks / 1 062 cells**. С `_version.py` source/API inventory содержит 131 модуль. Все source modules проходят AST parse. Основной агент проверял contracts/shared/DGP/performance; три сабагента параллельно проверяли DML, остальные сценарии и документацию/литературу. Детали покрытия и меньшей глубины plotting/helpers указаны в приложениях.

Среда: repo-local `.venv`, Python 3.12.14, pandas 3.0.6, sklearn 1.9.1, statsmodels 0.15.0, Pydantic 2.13.5. Полный список — [environment.json](D:/codex/Causalis/audit/environment.json). Указанный в `AGENTS.md` macOS interpreter недоступен на Windows; выбран локальный interpreter в объявленном диапазоне Python >=3.10,<3.15.

**Baseline:** 968 pytest cases: первоначально **964 passed, 3 failed, 1 error**, 317.21 с. Из четырёх непрошедших три были связаны с Windows sandbox — process named pipes и tmp_path. Повтор этих четырёх без указанных ограничений дал **3 passed, 1 failed**. Таким образом, результаты совместно подтверждают прохождение 967 случаев и **один воспроизводимый реальный failure**, но это не один «чистый полный прогон 967 passed». Логи: [полный](D:/codex/Causalis/audit/pytest_full.log), [JUnit](D:/codex/Causalis/audit/pytest_full.xml), [повтор](D:/codex/Causalis/audit/pytest_recheck.log).

Оставшийся failure: `tests/statistics/test_cuped_rct.py::test_shared_design_and_input_unchanged`. Statsmodels0.15 пересчитывает OLS decomposition несмотря на переданный cache. Числовая корректность CUPED этим failure не опровергнута; нарушено заявленное reuse/performance поведение (SC-12).

Дополнительные adversarial/oracle probes нашли ошибки, не выявленные baseline suite. Наличие большого числа passing tests не гарантирует корректность IF: один текущий multi ATTE тест прямо закрепляет ошибочный score derivative. Пробы основаны на независимых ratio derivatives, invariance свойствах и reference formulas, а не только на повторении реализации.

**Документация:** исходный generated API содержит 126 module HTML; изолированная свежая сборка успешно создала 131. Оригинальные HTML не перезаписывались. Файл `tests/docs/test_generate_api_reference.py` содержит helpers без `test_*`, поэтому baseline pytest сборку docs фактически не проверяет. Из 27 подозрительных AST import flags после динамической проверки ошибочных экспортов оказалось **0**. Логи сборки: [docs_build.log](D:/codex/Causalis/audit/docs_build.log), [summary](D:/codex/Causalis/audit/docs_build_summary.log).

Статусы: **R** — выполненное воспроизведение/числовой counterexample; **S** — подтверждение исходником/metadata/первичным источником. P1 — серьёзный неверный результат в поддерживаемом сценарии; P2 — ограниченный path, API/контракт/интерпретация или потеря заявленной оптимизации; P3 — небольшая неточность. P0 — массовый дефект обычного использования. Приоритет — экспертный порядок исправления, не измеренная частота ущерба.

## Топ-10 ошибок кода и методологии

Все десять имеют уровень **P1**. Рейтинг учитывает приоритет пользователя к DML, риск ошибочного causal inference и простоту обнаружения проблемы пользователем.

| № / ID | Проблема и конкретное последствие | Доказательство | Исправление / критерий приёмки |
|---|---|---|---|
| 1 / **DML-01** | Multi ATTE оценивается как ratio, но IF пропускает случайный знаменатель treatment share. CI/SE неверны | R: noiseless 3-arm ATT=[2,4], правильные SE=[0,0], библиотека=[0.163572,0.327144]. [score](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/model.py:754) | Ratio IF и Jacobian на каждый contrast; обновить score diagnostics и тест, сейчас закрепляющий `psi_a=-1` |
| 2 / **DML-03** | Refit сохраняет старые CATE learners и scalar/sensitivity state | R: эффект изменён с2 на7, после refit CATE остаётся2, fresh model=7; sensitivity использует старую theta. [fit](D:/codex/Causalis/causalis/scenarios/uplift/model.py:86) | Invalidate весь dependent state до нового fit; after-refit result равен fresh fit; error path не оставляет смешанный state |
| 3 / **DML-10** | Multi sensitivity benchmark считает объяснимость long-model residuals, а не gain от confounder | R: удаление сильного X меняет эффекты на −7.785/−3.932, но strengths≈10⁻⁹–10⁻⁷. [benchmark](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/refutation/unconfoundedness/sensitivity.py:1101) | Same-fold long/short outcome и Riesz variance gains; независимый oracle benchmark сильного/нулевого confounder |
| 4 / **DML-07** | Отрицательная `nu2` превращается в нулевой confounding bound через `sqrt(max(...,0))` | R: nu2=−4798.49, выбранные strengths=.5/.5 дают bound0 и ordinary CI. [bound](D:/codex/Causalis/causalis/scenarios/unconfoundedness/refutation/unconfoundedness/sensitivity.py:601) | Проверить finite/positive sensitivity elements; диагностировать и отклонять invalid bound, не выдавать отсутствие confounding |
| 5 / **SC-02** | В pre-period DID target cohort попадает в собственный control pool; duplicated units и overwrite IF | R: true pre-contrast−2 становится−1, 30 duplicate units. [control selection](D:/codex/Causalis/causalis/scenarios/did/model.py:217) | Исключать g и соблюдать eligibility относительно target/base/anticipation; unique/disjoint cell units |
| 6 / **SC-01** | Нормированный DID IPW имеет неверный IF; SE зависит от общего временного уровня | R: добавить всем1000×t: ATT остаётся1.680559, SE0.377856→258.243832, p0.0000087→0.9948. [score](D:/codex/Causalis/causalis/scenarios/did/model.py:553) | Полный IF нормированного IPW; invariance к общему тренду и сопоставление с reference |
| 7 / **SC-03** | DID DR с MLE logit/OLS использует raw score как полный IF; пропущен nuisance-estimation contribution при одном корректном nuisance | R/S: library SE0.044382 vs translated official DRDID full IF0.038876. [nuisance fit](D:/codex/Causalis/causalis/scenarios/did/model.py:261) | Полный MLE/OLS IF либо improved IPT+WLS, либо корректный cross-fit strategy; проверить соответствующие DR inference условия |
| 8 / **SC-04** | DID population aggregation игнорирует estimation uncertainty cohort-share weights | R: heterogeneous deterministic cells ATT5.2, SE≈0 vs population IF SE0.495742. [aggregation](D:/codex/Causalis/causalis/scenarios/did/model.py:803) | Weight IF и cell covariance; либо явный conditional fixed-composition target с соответствующей документацией |
| 9 / **SC-05** | Default `newcombe` CI вычисляет subtraction Wilson endpoints вместо заявленного hybrid score | R:7/34 vs1/34 actual CI[−.045660,.362773], reference[.018921,.340369]. [formula](D:/codex/Causalis/causalis/scenarios/classic_rct/inference/conversion_ztest.py:158) | Hybrid square-distance formula; boundary/rare-event cases и reference checks |
| 10 / **SC-11** | Один cluster отклоняется analytic DID, но принимается bootstrap с почти нулевым SE | R: ATT2.09751, bootstrap aggregate SE2.52×10⁻¹⁶. [bootstrap](D:/codex/Causalis/causalis/scenarios/did/model.py:334) | Общая cluster-count validation до обоих paths; few-cluster warnings |

Технически четыре показательных проверки имеют простой смысл:

- Multi ATTE: при `A_i=d_k(Y−g0)−d0(m_k/m0)(Y−g0)` и `p_k=E[d_k]` правильная population IF — `(A_i−theta_k d_ki)/p_k`. Код вычитает константу theta вместо `theta*d_k/p_k`. Point estimate может совпадать, а SE — нет.
- Newcombe hybrid: при `d=p1−p0` lower=`d−sqrt((p1−L1)^2+(U0−p0)^2)`, upper=`d+sqrt((U1−p1)^2+(p0−L0)^2)`. Разность marginal endpoints — другая процедура.
- DID должен устранять общий временной сдвиг; изменение SE в сотни раз при неизменном ATT — direct invariance counterexample, не просто разница finite-sample conventions.
- DR consistency при одном корректном nuisance не означает автоматически DR asymptotic normality для любой fitted score. Поэтому SC-03 требует согласовать estimator и IF; в этом аудите выполнена проверка формулы, но не большой coverage Monte Carlo.

Подробности, scripts и reference links находятся в [DML_REVIEW](D:/codex/Causalis/audit/DML_REVIEW.md) и [SCENARIOS_REVIEW](D:/codex/Causalis/audit/SCENARIOS_REVIEW.md).

## Остальные подтверждённые находки

| Приоритет / ID | Область и условие | Последствие / рекомендация |
|---|---|---|
| **P1 ROOT-01** | Multi DGP, nonlinear outcome link + latent U | Oracle вычислен при U=0 вместо integration: gamma g0=1 vs E[Y0]=1.64872, CATE1.71828 vs2.83297. Исправить oracle до использования DGP для bias/RMSE benchmarking |
| P2 DML-02 | Binary relative ATT | Baseline denominator IF неверна: noiseless20% effect имеет SE1.8334 п.п. вместо0. Учесть treated share ratio; absolute binary ATT score корректен |
| P2 DML-11 | ATT sensitivity | `m_alpha` nuisance derivative не ортогональна: derivative62.5 vs canonical≈0. Согласовать полный functional/normalization |
| P2 DML-05 + ROOT-04 | Shared/DML balance, variance0 и разные means | Shared SMD=0; DML infinite SMD исключён и даёт PASS. Signed Inf/severe flag нельзя отбрасывать как missing |
| P2 DML-06 | Equal ATE folds, OOS moment diagnostic | Fold residual means−200/−66.7/66.7/200, aggregate t0,p1 по конструкции. Убрать misleading test или независимо обосновать validation statistic |
| P2 DML-08 | RVa | Reported threshold.445374 не обращает собственный varying-bias CI: lower.158181>H0=0. Numerical inversion либо явная approximate label |
| P2 DML-04 | Drop + custom weights | После120→60 retained observations weights остаются length120; estimate ValueError. Применить единую retained mask |
| P2 DML-09 | GATE, большие mean signals | SSE через sum(phi²)−sum(phi)²/n: phi≈10⁸±1, SE0 vs.1. Centered variance/стабильное накопление |
| P2 SC-06 | CUPED treatment имена `intercept`, `x__centered` | IndexError либо тихая overwrite дизайна и иная ATE3.0067 vs2.0211. Внутренние позиционные роли/безопасное namespacing |
| P2 SC-07 | CUPED leverage и масштаб X | `pinv(X'X)` теряет направления: trace hat2.9965 при rank4. QR/SVD либо `X @ pinv(X)`; это касается и covariance path |
| P2 SC-08 | ASCM placebo/LOO | Новые refutation модели не наследуют original regularization/config; сравниваются разные методы. Хранить и передавать config |
| P2 SC-09 | IV diagnostics API | Docstring принимает IIVM model, resolver его отвергает после fit/estimate. Извлекать `model.result_.diagnostic_data` или исправить контракт |
| P2 SC-10 | RCT `ci_method`/`se_for_test` typo | Неизвестное значение молча выбирает Wald/unpooled. Explicit allowed-set validation |
| P2 SC-12 | CUPED batch, statsmodels0.15 | Decomposition cache намеренно перезаписывается `.fit()`; baseline test падает. Public batched QR/SVD и dependency CI |
| P2 ROOT-02 | CausalData/IVCausalData/PanelSCM, Inf | Контракт принимает данные, estimate Infinity/CI NaN. Единая column-wise finite validation |
| P2 ROOT-03 | CausalData complex outcome | Контракт принимает complex, fingerprint теряет imaginary часть, t-test падает. Reject complex; Multi/DID admission отдельно отмечена как static risk |
| P2 ROOT-05 | Legacy RCT генераторы, default IDs | UUID обрезан до20bits; при20k строк получено212 duplicates, causal contract падает. Full UUID либо уникальные seeded IDs |
| P2 ROOT-06 | Outlier return_rows, duplicate pandas index | Summary1outlier, returned2rows, включая non-outlier. Positional mask/iloc |
| P2 ROOT-07 | Assignment splitter, NaN weights | Проверки пропускают NaN, всем присваивается None. Finite numeric validation перед cumsum |
| P2 ROOT-08 | Dependency metadata — S | Pydantic без lower bound при v2-only imports. Declared minimum≥2 с проверкой используемых minor APIs; v1 env отдельно не запускалась |
| P2 ROOT-09 | Release workflow — S | Job «Test and build» не исполняет pytest; failing suite не блокирует этот publish path. Test job как обязательная dependency release |

Детальные exact source references и границы каждого вывода сохранены в тематических приложениях. Для ROOT-05 конкретное число UUID collisions меняется при повторе, математическая причина воспроизводима. ROOT-08/09 подтверждены metadata/workflow, не отдельным downgrade/publish experiment.

## Топ-10 проблем документации

Рейтинг документов отдельный: severity оценивает риск неверного применения метода. Полные тексты, строки notebooks/docstrings и источники — [DOCS_RESEARCH.md](D:/codex/Causalis/audit/DOCS_RESEARCH.md).

| № / ID / уровень | Фактическая проблема | Правильная формулировка или действие |
|---|---|---|
| 1 D01 / P1 | SRM/SMD/KS представлены как проверка истинности randomization/unconfoundedness | Они проверяют counts и observed balance; hidden confounding не исключается. Randomization подтверждается дизайном/assignment logs |
| 2 D02 / P1 | IV: exclusion назван reduced form, monotonicity/no defiers не объяснены | Разделить exclusion и reduced form; перечислить consistency, conditional exogeneity, instrument overlap, monotonicity, relevance; estimand LATE compliers |
| 3 D03 / P1 | Сайт обещает «обеспечить positivity» clipping/trimming | Clipping стабилизирует estimated denominator; structural support не восстанавливается. Drop меняет population/estimand |
| 4 D04 / P2 | CATE predictor назван DML IRM/calibrated individual predictions | Реализован lazy T-learner g1−g0; separate CATE strategy, independent validation, отсутствие индивидуальной CI гарантии |
| 5 D05 / P2 | Неверная Newcombe формула в source docstring и статье | Исправить код SC-05 и описание вместе; square distances, не subtraction endpoints |
| 6 D06 / P2 | CUPED сайт описывает старый denominator/nocov relative CI; HTML обещает finite-sample unbiasedness | Current source использует adjusted baseline и joint delta covariance; согласовать сайт с commit, asymptotic consistency ≠ exact finite unbiasedness |
| 7 D07 / P2 | Generated API: пять public modules отсутствуют, один удалённый остался, policy API не опубликован | Build от release commit, API manifest/drift gate и version marker; свежая локальная сборка успешна |
| 8 D08 / P2 | Retention effect0.1026 назван0.1026п.п. | Правильно10.26п.п.; CI9.48–11.05п.п. Различать probability fraction, percentage points и relative percent |
| 9 D09 / P2 | SCM notebook placebo p-value numerator без+1 при denominator J+1 | `(1+exceedances)/(J+1)` в данном rank scheme; объяснить exchangeability/assignment и pre-fit filtering. Основной estimator не обвиняется без отдельного evidence |
| 10 D10 / P2 | 401(k) participation case категорически причинный при признанном спорном covariate timing | Separate eligibility/participation/IV designs, порядок измерений и assumptions; same-year само по себе не доказывает treatment effect на каждый X |

Дополнительные неточности: prose не совпадает с сохранёнными notebook estimates (IRM9.9026 vs12.1542), defaults расходятся с constructor, DID example knobs не поддерживаются, release docs обещают невыполняемые tests, Gaussian copula correlation названа observed Pearson correlation, sensitivity `R²` labels требуют уточнения Riesz/odds parameterization, diagnostic PASS переобещает causal reliability. Эти пункты имеют P2/P3 по точным условиям и не пропущены из подробного документа.

Ни отсутствие import error по AST-флагам, ни временная ошибка web extractor на DID странице не записаны как дефект. Сайт не имеет установленного сопоставления commit↔version; findings сайта относятся к прочитанному опубликованному snapshot.

## Насколько методы современны

Не требуется заменять корректный метод только потому, что его статья старше последних preprints. Orthogonal DML, Callaway–Sant'Anna DiD и augmented SCM остаются актуальными подходами. Главное отставание здесь — надёжность inference, проверяемость предпосылок и reproducibility, затем repeated/group cross-fitting и более сильные CATE strategies.

| Направление | Оценка текущего положения | Следующий полезный шаг |
|---|---|---|
| Binary IRM ATE/absolute ATT | Canonical scores, held-out CF корректны в проверенных путях; matched ATE reference совпадает | Исправить ancillary inference/diagnostics, добавить repeated CF и dependent-data strategy |
| Multi IRM | Полезные multiarm contrasts; ATE/ATTE нельзя объединять одним IF | Исправить ATT/sensitivity, joint covariance и simultaneous arm inference |
| GATE/GATET | Orthogonal subgroup signals, formal contrasts уже есть | Stable variance, prespecified/honest discovery, inference families |
| Uplift/policy | T-learner допустим как baseline; DR policy signals и disjoint evaluation уже есть | DR/R-learner и costs/capacity/multiarm constraints |
| IIVM | Orthogonal LATE — актуальный метод при IV assumptions | Weak identification robust inference, complete assumption docs |
| RCT/CUPED | Welch/robust regression adjustment — актуальная основа | Newcombe fix, scale/names/cache robustness, cluster/ratio metrics |
| DiD | CS staggered design, cluster IF и simultaneous multiplier bands уже реализованы | Исправить IF/aggregation; HonestDiD sensitivity |
| SCM | Augmented SCM, pointwise conformal и average ATT inference уже существуют | Config-consistent refutations, donor contamination и alternative SDID strategy |

Литература сверена с доступными первичными источниками до сентября2026. В частности: [DML practical guide v2, 12 февраля2026](https://arxiv.org/abs/2504.08324v2), [Long Story Short v6, 21 сентября2026](https://arxiv.org/abs/2112.13398v6), [calibrated DML v3, 20 августа2026](https://arxiv.org/abs/2411.02771v3), [autoDML M-estimands v3, 20 марта2026](https://arxiv.org/abs/2501.11868v3). Это подтверждённые версии источников; наличие свежей версии не устанавливает само по себе ошибку старой реализации. Дефекты sensitivity выше установлены из её собственного functional/контрпримеров. Для полного version-to-implementation proof всех новых статей нужна отдельная углублённая работа.

## Топ-10 методологических расширений

Размер S/M/L — оценка объёма, не календарный срок. Перечень ранжирован для текущего Unconfoundedness/DML ядра. Отсутствие функции не считается багом.

| № | Подход | Польза / критерий качества | Размер | Первичный источник |
|---:|---|---|---|---|
| 1 | Repeated cross-fitting | Устойчивость к split; агрегация estimate/variance с учётом split variability. Сейчас IRM/Multi/IIVM отвергают n_rep≠1 | M | [DML](https://arxiv.org/abs/1608.00060), [official resampling](https://docs.doubleml.org/stable/guide/resampling.html) |
| 2 | Cluster/group-aware DML | Households/users/stores: group-separated folds **и** cluster IF; SE alone недостаточно | L | [Multiway cluster DML](https://arxiv.org/abs/1909.03489) |
| 3 | DR/R-learner CATE | Orthogonal conditional-effect strategies; oracle PEHE, held-out calibration/R-loss, сравнение с T-learner | M–L | [Kennedy](https://arxiv.org/abs/2004.14497), [Nie–Wager](https://arxiv.org/abs/1712.04912) |
| 4 | Explicit ATO/generalized overlap estimands | Отдельный target вместо притворного восстановления full ATE clipping; learned-weight EIF и support | M–L | [Overlap weighting](https://arxiv.org/abs/1609.07494), [multi-treatment](https://projecteuclid.org/journals/annals-of-applied-statistics/volume-13/issue-4/Propensity-score-weighting-for-causal-inference-with-multiple-treatments/10.1214/19-AOAS1282) |
| 5 | Weak-IV identification-robust LATE | Orthogonalized AR inversion, coverage от weak до strong IV, unbounded/disconnected CI sets | L | [Ma, авторская версия](https://arxiv.org/abs/2302.09756v5), [journal DOI2026](https://doi.org/10.1016/j.jeconom.2026.106302) |
| 6 | HonestDiD sensitivity | Bounds при заданных magnitude/smoothness deviations от parallel trends; event-study covariance | L | [Rambachan–Roth](https://jonathandroth.github.io/assets/files/HonestParallelTrends_Main.pdf) |
| 7 | Cost/capacity/multiarm policy learning | Frozen policy independent value inference, benefit−cost, capacity constraints; честно документировать greedy solution | L | [Athey–Wager](https://arxiv.org/abs/1702.02896) |
| 8 | Honest causal forest / GRF backend | Более сильный optional CATE strategy; honest splitting, сравнение T/DR, uncertainty в пределах теории | L | [GRF paper](https://arxiv.org/abs/1610.01271), [official implementation](https://grf-labs.github.io/grf/) |
| 9 | Continuous treatment: PLR или dose-response | Доза не равна multiarm; явные structural/rate assumptions, density diagnostics и curve inference | L | [Kennedy et al.](https://arxiv.org/abs/1507.00747), [Colangelo–Lee](https://arxiv.org/abs/2004.03036) |
| 10 | Calibrated DML inference strategy | Специальная nuisance calibration + theorem-compatible inference; misspecification coverage benchmarks | L, research | [van der Laan–Luedtke–Carone v3](https://arxiv.org/abs/2411.02771v3) |

Обязательное условие внедрения новых estimators: stated estimand/assumptions, independent formula checks, bias/RMSE/coverage simulations при правильных и неправильных nuisances. AutoDML, proximal/sequential effects и synthetic DiD — дальнейший горизонт, не быстрая замена исправлений текущих IF.

## Топ-10 функций и улучшений API

| № | Функция | Конкретная польза / проверка |
|---:|---|---|
| 1 | AnalysisManifest + reproducible report export | Version/commit/schema/seed/folds/models/target population/units/assumptions/warnings; восстановление результата без сырых данных |
| 2 | Public external OOF predictions и sample-splitting contract | Повторное использование learners и интеграция с DoubleML/EconML; row IDs, train/test disjointness, arm/probability alignment и provenance |
| 3 | Fold-local sklearn Pipeline + owned array snapshot | Preprocessing/tuning без leakage, одна conversion, typed categorical/sparse schema при расширении |
| 4 | Evaluate nuisance learners по arm/fold | Held-out RMSE/logloss/Brier/calibration и failure diagnostics вместо одних importance charts |
| 5 | Same-split learner comparison/stacking | Сравнение runtime/loss/estimate dispersion при общих folds; selection по validation, не по минимальному p-value |
| 6 | Typed assumption/diagnostic statuses | Разделить design evidence, empirical check, unidentified assumption и warning; sensitivity scenario export |
| 7 | Independent CATE/policy validation | R-score/DR tests/calibration/RATE/AUUC с заданной reference policy; held-out uncertainty, oracle metrics в synthetic cases |
| 8 | Общая inference family для outcomes/arms/GATE | Holm/Bonferroni/FDR либо covariance-based maxT с обоснованной family. Existing Multi significance correction/GATE contrasts сохранить |
| 9 | Attrition/missing-outcome workflow | Selection report, measurement timing, explicit MAR/selection assumptions; rejection NaN не решает treatment-dependent missingness |
| 10 | Executable versioned docs artifact | API manifest, runnable snippets, smoke notebooks, autogenerated numeric prose/units, drift gate перед release |

Held-out policy evaluation, GATE contrasts, DID simultaneous bands и SCM conformal уже существуют. Их не следует включать в roadmap как совершенно отсутствующие возможности.

## Скорость и pandas: что делать сначала

Измерения и топ-10 безопасных оптимизаций полностью приведены в [PERFORMANCE.md](D:/codex/Causalis/audit/PERFORMANCE.md). Первые четыре действия:

1. Перенести exact-fallback duplicate-column screening: prototype CausalData constructor 1.66–3.45× быстрее на100k–1m rows.
2. Убрать `unique/sort` continuous Y для binary check: extraction prototype 3.15–5.85× быстрее, arrays/flags совпадают.
3. Считать KDE порциями: при1m observations **в одной группе** full n×800 `diff`+`kern` требует минимум12.8GB плюс temporaries.
4. Восстановить CUPED batch QR/SVD reuse публичным механизмом вместо копирования private cache fields statsmodels.

Дальше — единый readonly array snapshot, column-wise validation, DID panel preprocessing reuse, ASCM factorization reuse, memory-aware jobs/thread budget, external OOF cache. DataFrame остаётся удобным public входом и выходом; вычислительное ядро может использовать NumPy. `copy=False` не гарантирует no-copy по [pandas docs](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_numpy.html); нужен явный ownership/mutation contract.

Проверять эффективность при неизменных rows/order/retained mask/folds/seeds/nuisance predictions/score/inference. Сокращение folds, отказ от held-out preprocessing, смена clipping или float precision — отдельные statistical tradeoffs, не бесплатное ускорение.

## Порядок следующих работ

| Этап | Что входит | Критерий завершения |
|---|---|---|
| A. Быстрые исправления | Refit invalidation, Newcombe, sensitivity invalid-state guard, balance Inf, one-cluster guard, finite/complex/enum/NaN checks, IDs/index/names, Pydantic minimum, pytest release gate, наиболее опасные docs claims | Independent regression probes проходят; existing suite; regenerated versioned API; annotations estimand/units согласованы |
| B. Inference repair | Multi ATT/relative ATT/sensitivity benchmark и orthogonality; DID IF/control/aggregation; RVa inversion; stable GATE/CUPED covariance; config-consistent ASCM | Derivations + official reference cases + invariance/oracle probes; затем simulation size/coverage. Ошибочные baseline tests переписаны |
| C. Performance | Screening/binary/KDE, one array snapshot, CUPED batch factorization; остальные rank10 по профилю | Same predictions/IF/results в tolerance; runtime/peak-memory benchmark поддержанных versions, no snapshot/mutation regression |
| D. Расширения | Repeated/group CF, DR/R CATE, manifest/OOF interface, weak-IV и HonestDiD; затем прочие методы | Explicit design/estimand, validation data и coverage evidence, runnable docs |

S/M/L в приложениях — сравнительный объём. Точный календарный срок без согласования реализации/поддерживаемых зависимостей не обещается. Первый release после ремонта следует позиционировать как correctness/inference release, с явным описанием изменившихся CI и sensitivity results.

## Команды и сохранённые доказательства

Из `D:\codex\Causalis`:

```powershell
$env:MPLBACKEND = 'Agg'
$env:MPLCONFIGDIR = 'D:\codex\Causalis\audit\mplconfig'
.\.venv\Scripts\python.exe -m audit.repro_dml_core
.\.venv\Scripts\python.exe audit\repro_scenarios.py
.\.venv\Scripts\python.exe audit\repro_contracts_shared.py
.\.venv\Scripts\python.exe audit\repro_dgp.py
.\.venv\Scripts\python.exe audit\docs_newcombe_check.py
```

Скрипты уже выполнены, outputs сохранены: [DML](D:/codex/Causalis/audit/repro_dml_core.log), [scenarios](D:/codex/Causalis/audit/repro_scenarios.log), [contracts/shared](D:/codex/Causalis/audit/repro_contracts_shared.log), [DGP](D:/codex/Causalis/audit/repro_dgp.log). Они демонстрируют текущие дефекты, не являются уже исправленными regression tests.

Для baseline использована команда `python -m pytest -q --durations=25 --junitxml=audit\pytest_full.xml` с redirect в log. Sandbox process/tmp permissions следует отделять от failures библиотеки. Сборка docs выполнена audit wrapper в изолированной копии; [verify_docs_build.py](D:/codex/Causalis/audit/verify_docs_build.py) сохраняет оригинальный generated API.

## Пределы вывода

Это широкий обзор всех модульных областей с глубокими проверками основных численных paths, а не формальная верификация каждой строки. Все40 notebooks не переисполнялись, каждый plot не проходил visual QA, все combinations learners/versions не тестировались. Нет большой Monte Carlo coverage study всех estimators, production-scale parallel benchmarking, полной проверки безопасности/зависимостей либо исчерпывающего систематического обзора всей литературы. Новейшие источники частично изучались на уровне abstract/strategy; отсутствие метода не записывается как ошибка.

Условия каждой находки важны: default binary ATE не следует объявлять неправильным из-за multi ATT дефекта; translated reference IF comparison не следует выдавать за запуск оригинального R package или доказанную coverage частоту. Положительные результаты и ложные первоначальные подозрения также сохранены. Это делает следующий этап исправлений конкретным и проверяемым.
