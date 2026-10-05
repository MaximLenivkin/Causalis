# Продолжение после очистки контекста

Проект `D:\codex\Causalis`; branch **`codex/correctness-roadmap`**. Base audit commit `ffe2c356c115f335b74b2f10117e19fe15585d46`.

## Что попросил пользователь

Создать свою рабочую ветку, вести исправления по приоритетному плану, делать commits между небольшими этапами. Разбить работу на крупные тематические блоки и останавливаться на их границах: пользователь будет очищать контекст. Подготовить отдельный файл для автора документации. **Sensitivity analysis отложено**, потому что upstream команда уже его переписывает.

## Читать сначала

1. `AGENTS.md` — локальная `.venv` обязательна; macOS path из инструкции недоступен на Windows, здесь `.venv\Scripts\python.exe`3.12.14.
2. `audit/FIX_PLAN.md` — порядок блоков, scope gates и deferred findings.
3. Этот файл и `audit/BLOCK04_DID.md` — последнее состояние реализации; B01–B03 reports сохраняют предыдущие checkpoints.
4. `audit/REPORT.md` — исторический аудит исходного SHA, не текущий residual bug count.

## Git

GitHub авторизация завершена пользователем и проверена: **MaximLenivkin**, keyring, scopes repo/workflow. Fork и tracking настроены; checkpoints B00–B03 сохраняются в `origin/codex/correctness-roadmap`. Актуальный checkpoint: `git log -1`; проверить remote tracking перед новым блоком. `origin`=`https://github.com/MaximLenivkin/Causalis.git`, `upstream`=`https://github.com/causalis-causalcraft/Causalis.git`. Upstream push прав нет; personal fork push/admin есть. Не повторять создание fork/rename remotes и не push в upstream/main.

GitHubCLI2.102.0: `& 'C:\Program Files\GitHub CLI\gh.exe' ...` — использовать полный путь, если текущий Codex PATH ещё не обновлён. Авторизацию повторно запрашивать не требуется. Git mutations/network в ограниченной среде могут требовать разрешённого запуска; пользователь уже авторизовал commits/push в личную ветку. PR не создавался. Полная текущая информация — GIT_ACCESS.md.

## Текущая работа

B00 завершён, checkpoint **2c26cee**. B01 завершён: SC-05 Newcombe hybrid formula и SC-10 runtime enum validation. Fix commit **`bd8a2be2dc363400a572c6d369cda887fb17aad9`**. До fix27new casesfailed; после36conversioncasespassed и31соседний RCTcasepassed. Status/commands/ограничения — `BLOCK01_RCT.md`.

B02 завершён: ROOT-01–07, включая grouped ROOT-04/DML-05. Code commits: **817c24c9b00e8896bb578b3568476c178bc024e4**, **add2f36652a7bb7d814975234255f7993f96f240**, **a5a6e3a4887c7ac22aa86b36883398a34bbb5d76**, **c27e74406ffacee460ee6deb7c4be7669d1394e1**. Финальная общая проверка: **606 passed**, 5 existing warnings, 123.61 s; evidence `block02_integration_tests.log`. Это scoped integration run, не полный suite. Полный итог и compatibility notes — `BLOCK02_CONTRACTS_SHARED_DGP.md` и B02_*_NOTES.md.

B03 завершён: **c9259072a24f5325f944cd37c4f203f33c39a5e7**, **e6a92759f3c8844999c53bd065a673e31330d604**, **6084b34d799e9af34228136c0a2e9549063638ac**, **113c693a0dd721c6e77dfe84bc647d2ffb4c7841**. DML-01/02/04/06/09 и independent CATE part DML-03. Общий integration: **1143 passed, 1 known SC-12 failed, 76 warnings, 299.18s**, raw `block03_integration_tests.log`; отдельный selection/result JSON перечисляет 7 исключённых sensitivity test modules. New failures0, не полностью зелёный suite. Focused sets: GATE68, multi63(+final10fixture), binary42+119neighbors, OOS36+50neighbors; counts пересекаются, не суммировать. Independent empirical ratio derivatives и oracle MC600×600 проверены; current CATE остаётся full-sample T-learner.

**B04 завершён**: code commits **87228e267aed3dc71dadd4bbe19b969a95463591**, **57dbba1e2ecc0c1cab413b1da7f40cfdd8b22131**; финальный documentation checkpoint — `git log -1`. SC-01/02/03/04/11: shared control eligibility исключает owncohort и проверяет max(base,target)+anticipation; full normalized traditional MLE/OLS cell IF (ridge/raw likelihood/clipped derivative/designSVD); complete-pair share IF aggregate; >=2cluster guard, bootstrap0или>=2 и согласованная covariance. Cell ATT/policy сохранены вне исправленного precomparison set. Diagnostic output False не отключает share IF. Public comparison_units сохраняет post-only/off-axis API и добавляет optional base_time/anticipation.

B04 integration source checkpoint57dbba1: **1238 passed,1 known SC-12 failed,76warnings,340.04s**, exit1. Newfailures0;7sensitivity modules исключены, exact selection/result JSON. New95cases:cluster10,cell34,alignment32,aggregation19. Focused counts пересекаются, не суммировать с integration. Historical DiD probes теперь дают preATT-2, trend-invariant IPW SE.3752058, DRreferenceSE.03887567, population mixtureSE.49574187. Detailed derivations/limits — BLOCK04_DID иB04_*NOTES/METHOD_REVIEW.

Estimated-nuisance DRMC600×n600 each2DGP coverage.935/.956667; первый имеет finite-nSE gap(meanSE/empSD.9163), universalcoverageimprovement не заявлен. Shares-only oracle coverage.958333. Fixedridge/activeclip могут менять target; missingsamplemixture не fullcohortATT автоматически, fewclustersnonregularrank/clipping/support требуют caveats. ScaleIFsolverchecks не optimizer invariance. Earliest universal pre enumeration index0 пока исключён: отдельный followup, не исправлялся вB04.

**Следующий рабочий блок B05**: CUPED/IV/SCM по FIX_PLAN — SC-06/07/08/09/12. Сначала collision-safe CUPEDdesign иscale-stable leverage/covariance → public batched QR/SVD/cache (исправить baseline statsmodels0.15 failure без удаления обещания reuse) → IVdiagnosticresolver → ASCMrefutationconfiginheritance в разрешённом nonsensitivity scope. Independent scale/name invariance,HC/relative covariance,batch-vs-single, matchingrefitconfig; затем repositoryintegration вне deferredsensitivity. Начинать после нового запроса пользователя, не автоматически после B04. Sensitivity modules/formulas/benchmarks/tests не редактировать.

Документация для пересылки готова в `DOCUMENTATION_HANDOFF.md`; дополнена B02/B03/B04 migration и immutable implementation links. GitHub snapshot file/line links проверяются `verify_handoff.py`;49links,issues0,local-only linksнет (`handoff_validation.json`). B04 scripts `verify_block04.py` и `run_block04_integration.py` сохраняют отдельные evidence JSON/log, не переписывая исторический audit/B03 evidence. Artifact checks229local links,15PythonAST,5librarypaths,sensitivitypaths0,issues0. Нет необходимости заново выполнять полный аудит или broad benchmark.

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
