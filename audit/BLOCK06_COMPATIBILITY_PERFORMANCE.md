# B06: совместимость, CI и производительность

Работа: 5–6 октября 2026, Windows / Europe–Moscow. Ветка `codex/correctness-roadmap`, исходный checkpoint `bf2ea87534e4eaf82266cb61d905b7e876cc2e1d`, финальный code checkpoint **`09e00de5a9d3dc915c6d59627f8b0ebc875dd4e9`**. Исходный аудит и upstream history сохранены. Sensitivity analysis и SC-08 leave-one-donor-out отложены по инструкции пользователя.

## Результат

Локальная интеграция: **1582 passed, 0 failed, 0 skipped, 77 warnings, 400.95 s**, exit 0. Добавлено **206 случаев**: CI 11, duplicate screening 71, binary detection 74, KDE 37, IV compatibility 13. Это весь выбранный repository suite вне семи явно отложенных sensitivity-модулей; не полный sensitivity/release pass. Sphinx build не запускался.

Все шесть jobs и их artifacts проверены; matrix прошла. Проверяемый [CI run 37373828518](https://github.com/MaximLenivkin/Causalis/actions/runs/37373828518) использует тот же финальный source. Во время запуска GitHub сообщал о [задержках назначения runners](https://www.githubstatus.com/incidents/3q1yb5m7ltvb); это возможное объяснение очереди по внешнему статусу, а не доказанный диагноз конкретного job.

## Ошибки и исправления

| Приоритет | Проблема | Что изменено |
|---|---|---|
| P2 / ROOT-08 | Installation могла выбрать Pydantic 1, несовместимый с v2-only imports | `pydantic>=2`; проверены API и dependency metadata |
| P2 / ROOT-09 | Release job назывался test/build, но не запускал pytest | Полный pytest gate до build/publish; настоящий exit status и artifacts |
| P2 / новая incompatibility | IIVM не обучался на NumPy 1.26 из-за Unicode array addition | `np.char.add`; прежние joint labels, fallback и seeded folds сохранены |
| Performance | Causal/IV/Multi полностью хешировали разные колонки | Screening 64 позиций, затем full fingerprint и exact equality |
| Performance | Binary detection сортировала continuous outcomes | Линейные numeric 0/1 comparisons; прежние constant policies сохранены |
| Memory | KDE выделял n×800 difference/kernel matrices | Gaussian sums блоками под scratch budget 8 MiB |

### Compatibility и release

Новая matrix проверяет latest-compatible dependencies для Python 3.10–3.14 и representative legacy stack на 3.10. Legacy pins — CI fixture, а не объявленные минимумы всех зависимостей. Устанавливаются чистые job-local окружения и выполняется `pip check`. CUPED adapter проверяется полным выбранным набором, включая public statsmodels reference/reuse cases.

Release вызывает `scripts/run_tests.py --scope full`, включая sensitivity. Failure, collection error и отсутствие собранных тестов не допускают публикацию. Annotated tag, semver, package version, ancestry к origin/main и downstream PyPI/GitHub Release dependencies сохранены. Release/tag/PyPI не запускались.

Branch CI вызывает явно ограниченный correctness scope. Семь исключений перечислены в selection artifact; новый sensitivity-named module требует review. Hidden `PYTEST_ADDOPTS` запрещён. Full selection сохраняет существующие test-level skips. Docs extra и `SKIP_DOCS_BUILD=false` не подтверждают Sphinx site build: существующий docs test file не содержит collected test functions. Audit-only pushes не отменяют ongoing matrix.

Подробнее: [compatibility notes](D:/codex/Causalis/audit/B06_COMPAT_NOTES.md).

### Реальный legacy failure

Первый legacy CI успешно установил NumPy 1.26.4 / pandas 1.5.3 / SciPy 1.11.4 / statsmodels 0.14.0 / sklearn 1.3.2 / Pydantic 2.0.3 / CatBoost 1.2.8. Его pytest дал **1516 passed, 53 failed**: все failures имели одну причину — string-array `+` в IV joint labels. Последующий canceled status job не скрывает эту ошибку.

Исправление использует [операцию NumPy 1.26 char.add](https://numpy.org/doc/1.26/reference/generated/numpy.char.add.html). Независимый Python-string / StratifiedKFold reference проверяет int/float/bool, joint/fallback и два seeds. До fix локально 1 failed / 12 passed; после **156 passed** с IV diagnostics/inference и binary neighbors. Никакие IV scores или identifying assumptions не изменялись.

Сохранены [исходный legacy result](D:/codex/Causalis/audit/block06_ci_prior_legacy_result.json), [IV notes](D:/codex/Causalis/audit/B06_IV_COMPAT_NOTES.md) и первоначальный modern-only integration 1569 pass. После source fix повторены общая интеграция и CI; старые successes не смешиваются с финальным checkpoint.

### Duplicate screening и binary detection

Совпадение samples или hashes никогда не становится verdict без exact equality. Объектное сравнение ограничивает boxing блоками по 65 536 строк. Сохранены первая duplicate error, роли, normalized dtypes, индексы, отсутствие input mutation, большие integers и прежняя numeric/object fingerprint boundary. RCT сохраняет собственный nested group order. Почти одинаковые колонки могут по-прежнему требовать full hashing с небольшим sample overhead.

Binary/IV helpers требуют обе категории 0 и 1; multi helper сохраняет constant-zero/one policy. Numeric comparisons точные, без tolerance, integer truncation или удаления missing values. Остальные dtypes используют прежний fallback. Tests сравнивают folds, predictions, scores/IF, point estimates, p-values и CI с legacy path. Public pandas copy/ownership semantics не менялись.

Подробности: [duplicate notes](D:/codex/Causalis/audit/B06_DUPLICATE_NOTES.md), [binary notes](D:/codex/Causalis/audit/B06_BINARY_NOTES.md).

### Gaussian KDE

Каждая observation/grid пара вычисляется; sampling, FFT и approximation не добавлены. Bandwidth, grid, finite filtering, density/count scaling и public plot parameters сохраняются. Одна kernel matrix и partial vector занимают до 8 MiB; при grid=800 это 8 384 000 bytes. Constant bump также вычисляется блоками.

Это ограничение scratch arrays, не полного RSS: conversion, std, filtering, output и native buffers используют дополнительную линейную память. Ordinary densities могут отличаться округлением суммы. Проверены независимый dense reference, SciPy с тем же absolute bandwidth, permutation, budgets 16 bytes–8 MiB и фактический count всех пар. [KDE notes](D:/codex/Causalis/audit/B06_KDE_NOTES.md).

## Последовательный benchmark

Два последовательных fresh processes: baseline bf2ea87 и measured source d292b3c, seed 731, native threads 1. Median пяти repeats с warmup; KDE/fit — трёх. Input construction вне таймеров, constructor/extraction/fit разделены. Tracemalloc peak не является process RSS. Desktop noise и число повторов ограничивают переносимость результатов.

| Размер | Causal constructor | IV constructor | Multi constructor | IRM extraction |
|---|---:|---:|---:|---:|
|100k × 20|2.24×|1.86×|1.97×|1.37×|
|500k × 20|1.38×|1.23×|1.22×|2.61×|
|1m × 8|1.36×|1.37×|1.49×|4.14×|

Constructor traced peak практически не изменился: validation/copies доминируют. Extraction peak уменьшился 18.51→17.18, 92.52→85.84 и 93.47→80.12 MiB. Helper-alone continuous-Y acceleration 20–67× относится лишь к micro-operation.

| KDE rows × grid | Median before→after, s | Traced peak before→after, MiB | Max density absolute difference |
|---|---:|---:|---:|
|10k × 800|.39297→.23482|183.11→8.13|2.72e-15|
|30k × 800|1.23508→1.14933|549.32→8.13|5.88e-15|

Самый надёжный вывод KDE — устранение n×grid memory. Прежние две named matrices для 1m×800 требовали 12.8 GB по shapes; OOM experiment не запускался. Universal latency/RSS guarantee не заявляется.

Matched IRM 20k×8, LinearRegression/LogisticRegression, folds 3, seed 17, n_jobs 1: median fit .14919→.12057 s (**1.24×**), без constructor/estimate. Folds, nuisance predictions, psi/psi_a/psi_b совпадают byte for byte; ATE 1.9836226970682251 и SE .014460562924826548 совпадают. Statistical specification и causal coverage не менялись.

Owned extraction candidate дал 2.23/1.05/1.47× относительно текущей extraction. На среднем размере 5% могут быть noise; candidate не реализует snapshot/invalidation contract и остаётся audit-only. Это не новый public array API. IV split fix не входил в measured operations; benchmark не повторялся, неизменность measured paths проверяется отдельно.

Raw [before](D:/codex/Causalis/audit/block06_benchmark_before.json), [after](D:/codex/Causalis/audit/block06_benchmark_after.json), [summary](D:/codex/Causalis/audit/block06_benchmark_summary.json), [worker](D:/codex/Causalis/audit/benchmark_block06.py).

## Финальная CI matrix

Snapshot: 2026-10-05T21:21:54.6451704Z; exact source `09e00de5a9d3dc915c6d59627f8b0ebc875dd4e9`. Каждый подтверждённый job включает 1582 cases и семь одинаковых exclusions. Полные packages, elapsed times и JUnit counts — [CI result](D:/codex/Causalis/audit/block06_ci_result.json); raw artifacts доступны в GitHub и локальном ignored temp.

| Python / stack | Actual Python | NumPy / pandas / statsmodels / Pydantic | Status | Passed |
|---|---|---|---|---:|
|3.11 / latest|3.11.16|2.4.6 / 3.0.6 / 0.15.0 / 2.13.5|success|1582|
|3.10 / latest|3.10.21|2.2.6 / 2.3.3 / 0.15.0 / 2.13.5|success|1582|
|3.10 / legacy|3.10.21|1.26.4 / 1.5.3 / 0.14.0 / 2.0.3|success|1582|
|3.14 / latest|3.14.7|2.5.3 / 3.0.6 / 0.15.0 / 2.13.5|success|1582|
|3.12 / latest|3.12.14|2.5.3 / 3.0.6 / 0.15.0 / 2.13.5|success|1582|
|3.13 / latest|3.13.15|2.5.3 / 3.0.6 / 0.15.0 / 2.13.5|success|1582|

Это Linux CI и один Windows stack локально, не все OS/dependency cross products. Full sensitivity и production release validation не заявляются.

## Commits, evidence и продолжение

Commits: f31b743 (CI/metadata), 5977bb8 (duplicates), 74c0ff0 (binary), d292b3c (KDE), 1be6b67 (audit push filter), 50ad33e (benchmark/notes), 09e00de (legacy IV fix). Последний является полным финальным library/test source. После final artifact commit выполняется обычный push в personal fork и remote/local equality check; `git log -1` показывает documentation checkpoint.

Финальные [integration result](D:/codex/Causalis/audit/block06_integration_result.json), [selection](D:/codex/Causalis/audit/block06_integration_selection.json), [raw log](D:/codex/Causalis/audit/block06_integration_tests.log) и [validation](D:/codex/Causalis/audit/block06_validation_checks.json). Scope guard проверяет отсутствие sensitivity changes; source/tests сравниваются с09e00de, Python AST и локальные ссылки проверяются. [Portable documentation handoff](D:/codex/Causalis/audit/DOCUMENTATION_HANDOFF.md) содержит исправления для автора; внешние сообщения не отправлялись.

Дальше: отдельный backlog review для earliest universal DiD pre-cell, DGP marginal propensity/supplied-U/true-ATT contracts, finite/extreme output guards, numeric/object duplicate policy, public snapshot API и dedicated Sphinx build. Repeated/group-aware cross-fitting, external OOF и DR/R-CATE остаются самостоятельными feature blocks. Sensitivity и SC-08 LOO ожидают upstream sync. Следующий блок в этой итерации не начинается.
