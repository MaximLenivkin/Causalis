# Продолжение после очистки контекста

Проект `D:\codex\Causalis`; branch **`codex/correctness-roadmap`**. Base audit commit `ffe2c356c115f335b74b2f10117e19fe15585d46`.

## Что попросил пользователь

Создать свою рабочую ветку, вести исправления по приоритетному плану, делать commits между небольшими этапами. Разбить работу на крупные тематические блоки и останавливаться на их границах: пользователь будет очищать контекст. Подготовить отдельный файл для автора документации. **Sensitivity analysis отложено**, потому что upstream команда уже его переписывает.

## Читать сначала

1. `AGENTS.md` — локальная `.venv` обязательна; macOS path из инструкции недоступен на Windows, здесь `.venv\Scripts\python.exe`3.12.14.
2. `audit/FIX_PLAN.md` — порядок блоков, scope gates и deferred findings.
3. Этот файл, `audit/BLOCK01_RCT.md` и `audit/BLOCK02_CONTRACTS_SHARED_DGP.md` — текущее состояние реализации.
4. `audit/REPORT.md` — исторический аудит исходного SHA, не текущий residual bug count.

## Git

GitHub авторизация завершена пользователем и проверена: **MaximLenivkin**, keyring, scopes repo/workflow. Fork и tracking настроены; commits B00/B01 и B02 сохраняются в `origin/codex/correctness-roadmap`. Актуальный checkpoint: `git log -1`; проверить remote tracking перед новым блоком. `origin`=`https://github.com/MaximLenivkin/Causalis.git`, `upstream`=`https://github.com/causalis-causalcraft/Causalis.git`. Upstream push прав нет; personal fork push/admin есть. Не повторять создание fork/rename remotes и не push в upstream/main.

GitHubCLI2.102.0: `& 'C:\Program Files\GitHub CLI\gh.exe' ...` — использовать полный путь, если текущий Codex PATH ещё не обновлён. Авторизацию повторно запрашивать не требуется. Git mutations/network в ограниченной среде могут требовать разрешённого запуска; пользователь уже авторизовал commits/push в личную ветку. PR не создавался. Полная текущая информация — GIT_ACCESS.md.

## Текущая работа

B00 завершён, checkpoint **2c26cee**. B01 завершён: SC-05 Newcombe hybrid formula и SC-10 runtime enum validation. Fix commit **`bd8a2be2dc363400a572c6d369cda887fb17aad9`**. До fix27new casesfailed; после36conversioncasespassed и31соседний RCTcasepassed. Status/commands/ограничения — `BLOCK01_RCT.md`.

B02 завершён: ROOT-01–07, включая grouped ROOT-04/DML-05. Code commits: **817c24c9b00e8896bb578b3568476c178bc024e4**, **add2f36652a7bb7d814975234255f7993f96f240**, **a5a6e3a4887c7ac22aa86b36883398a34bbb5d76**, **c27e74406ffacee460ee6deb7c4be7669d1394e1**. Финальная общая проверка: **606 passed**, 5 existing warnings, 123.61 s; evidence `block02_integration_tests.log`. Это scoped integration run, не полный suite. Полный итог и compatibility notes — `BLOCK02_CONTRACTS_SHARED_DGP.md` и B02_*_NOTES.md.

**Следующий рабочий блок B03**: DML / GATE / Uplift, по FIX_PLAN. Multi ATTE ratio IF → binary relative ATT baseline IF → drop mask/custom weights → independent CATE cache → stable GATE variance → OOS diagnostic. Balance finding DML-05 уже закрыт в B02. Нужны независимые derivations / oracle IF / property tests; некоторые existing assertions закрепляют прежний неверный score и должны быть исправлены обоснованно. Начинать после нового запроса пользователя. Sensitivity modules/formulas/benchmarks/tests не редактировать.

Документация для пересылки готова в `DOCUMENTATION_HANDOFF.md`; дополнена B02 migration/oracle semantics и ссылками на implementation commits. GitHub snapshot file/line links проверяются `verify_handoff.py`; local-only links нет (`handoff_validation.json`). Нет необходимости заново выполнять полный аудит или broad benchmark.

Новый отдельный DGP follow-up: `m_<arm>` по-прежнему softmax при U=0, не marginal P(D=arm|X) при latent treatment noise. Это явно документировано. Outcome g/cate fix закрыт в рамках Gaussian reference law; arbitrary supplied U и true latent-confounded ATT требуют отдельной интерпретации. Не менять молча propensity API в B03.

## Baseline и ограничения

- Аудит:31grouped findings,11P1+20P2; sensitivity subset отложен. CSV inventory130modules,40notebooks.
- Original suite968cases:964passed/3failed/1error; recheck3passed/1failed. Реальный baseline failure — `tests/statistics/test_cuped_rct.py::test_shared_design_and_input_unchanged` на statsmodels0.15, SC-12. Не считать его регрессией B01.
- Windows sandbox process pipes/tmp могут вызвать PermissionError; при необходимых tests использовать разрешённый запуск с local basetemp.
- Audit snapshots/copies/runtime caches не включать в commits как whole directory tree. `audit/.gitignore` исключает copied docs build, temp/cache; small evidence logs намеренно разрешены.
- Оригинальные отчёты имеют absolute Windows links для локальной работы. `DOCUMENTATION_HANDOFF.md` переносимый, с GitHub SHA links для отправки автору.

## На завершении любого блока

Записать status, actual commit SHA, tests и оставшиеся ограничения; проверить git status; законченный commit; после доступного remote — push в личный fork. Остановиться и сообщить пользователю результат блока. Не автоматически начинать следующую большую область до его нового запроса.
