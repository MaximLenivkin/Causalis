# Продолжение после очистки контекста

Проект `D:\codex\Causalis`; branch **`codex/correctness-roadmap`**. Base audit commit `ffe2c356c115f335b74b2f10117e19fe15585d46`.

## Что попросил пользователь

Создать свою рабочую ветку, вести исправления по приоритетному плану, делать commits между небольшими этапами. Разбить работу на крупные тематические блоки и останавливаться на их границах: пользователь будет очищать контекст. Подготовить отдельный файл для автора документации. **Sensitivity analysis отложено**, потому что upstream команда уже его переписывает.

## Читать сначала

1. `AGENTS.md` — локальная `.venv` обязательна; macOS path из инструкции недоступен на Windows, здесь `.venv\Scripts\python.exe`3.12.14.
2. `audit/FIX_PLAN.md` — порядок блоков, scope gates и deferred findings.
3. Этот файл и `audit/BLOCK03_DML_GATE_UPLIFT.md` — последнее состояние реализации; B01/B02 reports сохраняют предыдущие checkpoints.
4. `audit/REPORT.md` — исторический аудит исходного SHA, не текущий residual bug count.

## Git

GitHub авторизация завершена пользователем и проверена: **MaximLenivkin**, keyring, scopes repo/workflow. Fork и tracking настроены; checkpoints B00–B03 сохраняются в `origin/codex/correctness-roadmap`. Актуальный checkpoint: `git log -1`; проверить remote tracking перед новым блоком. `origin`=`https://github.com/MaximLenivkin/Causalis.git`, `upstream`=`https://github.com/causalis-causalcraft/Causalis.git`. Upstream push прав нет; personal fork push/admin есть. Не повторять создание fork/rename remotes и не push в upstream/main.

GitHubCLI2.102.0: `& 'C:\Program Files\GitHub CLI\gh.exe' ...` — использовать полный путь, если текущий Codex PATH ещё не обновлён. Авторизацию повторно запрашивать не требуется. Git mutations/network в ограниченной среде могут требовать разрешённого запуска; пользователь уже авторизовал commits/push в личную ветку. PR не создавался. Полная текущая информация — GIT_ACCESS.md.

## Текущая работа

B00 завершён, checkpoint **2c26cee**. B01 завершён: SC-05 Newcombe hybrid formula и SC-10 runtime enum validation. Fix commit **`bd8a2be2dc363400a572c6d369cda887fb17aad9`**. До fix27new casesfailed; после36conversioncasespassed и31соседний RCTcasepassed. Status/commands/ограничения — `BLOCK01_RCT.md`.

B02 завершён: ROOT-01–07, включая grouped ROOT-04/DML-05. Code commits: **817c24c9b00e8896bb578b3568476c178bc024e4**, **add2f36652a7bb7d814975234255f7993f96f240**, **a5a6e3a4887c7ac22aa86b36883398a34bbb5d76**, **c27e74406ffacee460ee6deb7c4be7669d1394e1**. Финальная общая проверка: **606 passed**, 5 existing warnings, 123.61 s; evidence `block02_integration_tests.log`. Это scoped integration run, не полный suite. Полный итог и compatibility notes — `BLOCK02_CONTRACTS_SHARED_DGP.md` и B02_*_NOTES.md.

B03 завершён: **c9259072a24f5325f944cd37c4f203f33c39a5e7**, **e6a92759f3c8844999c53bd065a673e31330d604**, **6084b34d799e9af34228136c0a2e9549063638ac**, **113c693a0dd721c6e77dfe84bc647d2ffb4c7841**. DML-01/02/04/06/09 и independent CATE part DML-03. Общий integration: **1143 passed, 1 known SC-12 failed, 76 warnings, 299.18s**, raw `block03_integration_tests.log`; отдельный selection/result JSON перечисляет 7 исключённых sensitivity test modules. New failures0, не полностью зелёный suite. Focused sets: GATE68, multi63(+final10fixture), binary42+119neighbors, OOS36+50neighbors; counts пересекаются, не суммировать. Independent empirical ratio derivatives и oracle MC600×600 проверены; current CATE остаётся full-sample T-learner.

**Следующий рабочий блок B04**: DiD по FIX_PLAN — SC-01/02/03/04/11. Eligibility/unit/pre-control alignment → normalized IPW cell IF/common-trend invariance → nuisance-estimation IF (сначала выбрать обоснованную estimation strategy, не смешивать MLE/OLS с IPT/WLS derivations) → cohort-share aggregation IF → one-cluster guard. Нужны independent derivatives/reference, targeted coverage и аналитическая/cluster-bootstrap проверка. Начинать после нового запроса пользователя, не автоматически после B03. Sensitivity modules/formulas/benchmarks/tests не редактировать.

Документация для пересылки готова в `DOCUMENTATION_HANDOFF.md`; дополнена B02/B03 migration и immutable implementation links. GitHub snapshot file/line links проверяются `verify_handoff.py`; local-only links нет (`handoff_validation.json`). B03 scripts `verify_block03.py` и `run_block03_integration.py` сохраняют отдельные evidence JSON/log, не переписывая исторический audit. Нет необходимости заново выполнять полный аудит или broad benchmark.

B03 migration: Multi ATTE psi_a matrix(n,K-1), frozen original-row weights изменяются только через refit, OOS t/p fields теперь NaN/NA и отдельно descriptive fold metrics. Старые multi ATTE cached scores могут реконструироваться с `psi_cache_status`, но старые CI требуют re-estimation. Generic scalar/sensitivity refit state и sensitivity diagnostic sigma2 explicitNone annotation issue отложены. Upstream updates не merge/rebase в B03; для новой sensitivity реализации сначала нужна отдельная синхронизация/review.

Новый отдельный DGP follow-up: `m_<arm>` по-прежнему softmax при U=0, не marginal P(D=arm|X) при latent treatment noise. Это явно документировано. Outcome g/cate fix закрыт в рамках Gaussian reference law; arbitrary supplied U и true latent-confounded ATT требуют отдельной интерпретации. Не менять молча propensity API в B03.

## Baseline и ограничения

- Аудит:31grouped findings,11P1+20P2; sensitivity subset отложен. CSV inventory130modules,40notebooks.
- Original suite968cases:964passed/3failed/1error; recheck3passed/1failed. Реальный baseline failure — `tests/statistics/test_cuped_rct.py::test_shared_design_and_input_unchanged` на statsmodels0.15, SC-12. Не считать его регрессией B01/B02/B03; исправление public batched QR/SVD/cache в B05.
- Windows sandbox process pipes/tmp могут вызвать PermissionError; при необходимых tests использовать разрешённый запуск с local basetemp.
- Audit snapshots/copies/runtime caches не включать в commits как whole directory tree. `audit/.gitignore` исключает copied docs build, temp/cache; small evidence logs намеренно разрешены.
- Оригинальные отчёты имеют absolute Windows links для локальной работы. `DOCUMENTATION_HANDOFF.md` переносимый, с GitHub SHA links для отправки автору.

## На завершении любого блока

Записать status, actual commit SHA, tests и оставшиеся ограничения; проверить git status; законченный commit; после доступного remote — push в личный fork. Остановиться и сообщить пользователю результат блока. Не автоматически начинать следующую большую область до его нового запроса.
