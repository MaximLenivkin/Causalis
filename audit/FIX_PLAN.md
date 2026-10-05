# План исправлений и поэтапной разработки

Обновлён: 2026-10-05. Проект: `D:\codex\Causalis`. Рабочая ветка: **`codex/correctness-roadmap`**, создана от `main` на `ffe2c356c115f335b74b2f10117e19fe15585d46`. Исходный аудит — `audit/REPORT.md`; он остаётся историческим snapshot, а не переписывается после каждого исправления.

## Решение о scope

Разработчики upstream уже исправляют sensitivity analysis. **Все sensitivity formulas, benchmarks, bounds, RV/RVa, nuisance derivatives и связанные sensitivity tests/docstrings отложены.** Мы не создаём конкурирующую реализацию и не подгоняем новый код под старые sensitivity outputs.

Отложены целиком DML-07, DML-08, DML-10, DML-11, sensitivity-specific документационные замечания и generic refit/sensitivity scalar state часть DML-03. Возврат: после получения upstream commit, проверка diff/API/score contracts, новый короткий аудит, перенос либо закрытие прежних findings. Сообщение разработчиков о будущей правке не означает, что текущие defects уже исправлены.

Независимая часть DML-03 — **CATE learner cache после refit** — остаётся в плане. Изменения общих scores/IF DML-01/02 допускаются, но sensitivity modules/tests в этих commits не редактируются. Если upstream change затрагивает те же contracts, фиксируем зависимость и переносим конкретный пункт до синхронизации. Sensitivity-targeted Monte Carlo и новые sensitivity функции сейчас не выполняются.

## Сначала correctness, затем скорость и новые методы

| Блок | Приоритет / scope | Findings исходного аудита | Критерий готовности | Размер |
|---|---|---|---|---|
| **B00. Основа проекта** | Ветка, сохранение аудита, план, handoff документации, Git access и файл продолжения | Инфраструктура работы | Локальный commit создан; remote auth ограничения записаны; всё для следующего контекста в файлах | S |
| **B01. RCT inference** | Правильный Newcombe hybrid CI; строгие `ci_method`/`se_for_test` | **SC-05 P1**, SC-10 P2 | Statsmodels reference на rare/boundary/unequal-n, symmetry, invalid options; RCT tests; отдельный commit | S |
| **B02. Contracts / shared / DGP** | Finite/real checks, separation SMD, positional outliers, NaN split weights, UUID uniqueness, nonlinear multi oracle | ROOT-01/02/03/04/05/06/07; DML-05 | Repro → focused tests; строгий row/schema/ID contract; oracle analytic identity; не менять sensitivity implementation | M |
| **B03. DML / GATE / Uplift** | Multi ATTE ratio IF, binary relative ATT IF, drop+weights, OOS diagnostic, stable GATE variance, независимый CATE cache | **DML-01 P1**, DML-02/04/06/09, DML-03 только CATE | Oracle IF/SE, same-split reference, invariance, fresh-fit equivalence; исправить ошибочные existing assertions | M–L |
| **B04. DiD inference** | Pre-controls, normalized IPW IF, nuisance-estimation IF, population cohort-share IF, one-cluster guard | **SC-01/02/03/04/11 P1** | Derivations и official-source reference; unit uniqueness; common-trend invariance; analytic/bootstrap; затем targeted coverage simulation | L |
| **B05. CUPED / IV / SCM** | Collision-safe design, stable leverage/covariance, публичный batched QR/SVD, IV diagnostic resolver, ASCM config inheritance | SC-06/07/08/09/12 | Scale/name invariance, HC/relative covariance, batch-vs-single, original-config refutations; existing suite | M–L |
| **B06. Compatibility / CI / performance** | Pydantic minimum, release pytest gate, tested versions; duplicate screening, linear binary checks, bounded-memory KDE, owned arrays | ROOT-08/09, performance top10 | Чистая install matrix; no false release pass; identical arrays/scores/IF; documented time/memory benchmark | M–L |

B02–B06 — большие тематические блоки, внутри которых можно делать несколько небольших законченных commits. Размер S/M/L — сравнительная сложность, не календарное обещание. P1 задачи B03/B04 имеют более высокий риск, но B01 первым даёт короткий независимый correctness commit; внутри B02 сначала устраняем silent invalid results и wrong oracle.

## Порядок commits внутри больших блоков

- B02: finite/complex validation → balance separation → outlier/split/IDs → multi DGP oracle. Изменение contract не должно автоматически impute/replace invalid values. Проверить explicit migration, если ранее принимавшиеся данные теперь отвергаются.
- B03: multi ATT IF + diagnostics → relative ATT baseline IF → drop mask/weights → CATE cache → stable GATE variance → заменить бессодержательный OOS aggregate test. Общие influence payloads сверять с потенциальными upstream sensitivity changes.
- B04: eligibility/unit alignment → normalized cell IF → nuisance-estimation strategy → aggregation weight IF → cluster validation. Последний простой guard можно сделать отдельным ранним commit. Full MLE/OLS IF и improved IPT/WLS — выбор реализации после review derivation, а не смешение обеих процедур.
- B05: CUPED names → scale-stable leverage → batch least-squares/covariance → IV resolver → ASCM config. Не снимать cache identity assertion без восстановления обещанного ускорения.
- B06: compatibility и release gate перед performance. Screening и linear binary checks отдельно от ownership/caching. При изменении data path сохранять folds, predictions, score, target population и statistical checks.

## Документация: отдельный рабочий поток

`audit/DOCUMENTATION_HANDOFF.md` — переносимый файл для автора сайта, с GitHub snapshot links, приоритетами и готовыми английскими формулировками. Он не содержит локальных D-drive ссылок и sensitivity-specific tasks.

Текущие inaccuracies можно исправлять сразу; описание изменяемого поведения Newcombe/CI/diagnostics должно выпускаться вместе с соответствующим кодом. Generated API пересобирать из нужного release commit, а не редактировать HTML вручную. Изначальные отчёты описывают старый commit и должны сохранять этот marker.

## Правила проверки и границы блока

1. Перед изменением прочитать `AGENTS.md`, этот файл и `audit/NEXT_SESSION.md`; проверить branch/status и не затрагивать чужие изменения.
2. Выбрать **один блок** и небольшой законченный commit. Источник finding → независимое reproduction/property/reference → patch → focused tests.
3. Python — только `.venv\Scripts\python.exe`. Local environment manifest сохранён в audit; источник base suite известен.
4. При Windows sandbox failures process/tmp использовать разрешённый запуск или writable `--basetemp`, не считать их bug библиотеки.
5. После focused проверки запускать необходимые соседние tests. Полный suite — на интеграционных границах B03/B04/B05/B06; при текущем baseline учитывать известный SC-12, пока он не исправлен.
6. Не повторять большой benchmark/весь suite после правки только prose. Для score changes нужны independent IF и coverage evidence; passing mirrored-formula tests недостаточно.
7. Commit включает завершённую code/test/docstrings правку и короткий block log. Отчёт показывает, что закрыто, что осталось, как проверено и известные ограничения.
8. Обновить `NEXT_SESSION.md`, отметить block/commit/test commands/следующее действие. **Остановиться на границе блока**, чтобы пользователь мог очистить контекст. Следующий блок начинается отдельным запросом пользователя.

## Git и синхронизация upstream

Локальный Git и author identity работают, branch создана. Public remote чтение проверено: upstream main всё ещё исходный audit SHA. Сохранённая GitHub авторизация не найдена; создание удалённого fork и push не проверены/не выполнены. Полная инструкция — `audit/GIT_ACCESS.md`.

После входа: `origin` будет личным fork, `upstream` — causalis-causalcraft/Causalis. Каждый законченный commit можно пушить в личную ветку. Никогда не push в upstream/main и не force-push историю для обычной синхронизации. Upstream updates сначала fetch/diff, sensitivity review отдельно; merge/rebase выбирается по actual divergence, без потери собственных commits.

## Последующие улучшения, после correctness

В порядке отдачи для текущего ядра: repeated cross-fitting → group/cluster-aware DML → external OOF predictions/manifest → DR/R CATE → held-out nuisance/CATE validation → inference families → weak-IV LATE → HonestDiD → policy costs/capacity. Это самостоятельные feature blocks с explicit assumptions/target и validation, не добавления к одному bugfix commit. Sensitivity extensions остаются вне текущего scope.

## Текущий статус

- B00: ветка и документы готовы; локальный checkpoint commit создаётся в этом этапе.
- B01: выбран как первый небольшой блок; реализация/проверки записываются в `audit/BLOCK01_RCT.md`.
- B02–B06: запланированы, не начаты.
- Sensitivity: отложено по прямой инструкции пользователя; дата возобновления не назначена.
