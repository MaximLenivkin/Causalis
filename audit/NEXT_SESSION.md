# Продолжение после очистки контекста

Проект `D:\codex\Causalis`; branch **`codex/correctness-roadmap`**. Base audit commit `ffe2c356c115f335b74b2f10117e19fe15585d46`.

## Что попросил пользователь

Создать свою рабочую ветку, вести исправления по приоритетному плану, делать commits между небольшими этапами. Разбить работу на крупные тематические блоки и останавливаться на их границах: пользователь будет очищать контекст. Подготовить отдельный файл для автора документации. **Sensitivity analysis отложено**, потому что upstream команда уже его переписывает.

## Читать сначала

1. `AGENTS.md` — локальная `.venv` обязательна; macOS path из инструкции недоступен на Windows, здесь `.venv\Scripts\python.exe`3.12.14.
2. `audit/FIX_PLAN.md` — порядок блоков, scope gates и deferred findings.
3. Этот файл и `audit/BLOCK01_RCT.md` — текущее состояние реализации.
4. `audit/REPORT.md` — исторический аудит исходного SHA, не текущий residual bug count.

## Git

Local branch создана, user.name/user.email настроены. Public upstream read работает и main совпадает с audit SHA. Сохранённой GitHub авторизации нет, `gh` не установлен; fork/push пока не сделаны. Пользователь получил `audit/GIT_ACCESS.md` с инструкцией. После его входа проверить account/remote и продолжить fork/push без повторного запроса разрешения на уже согласованную работу.

## Текущая работа

B00 завершён, checkpoint **2c26cee**. B01 завершён: SC-05 Newcombe hybrid formula и SC-10 runtime enum validation. Fix commit **`bd8a2be2dc363400a572c6d369cda887fb17aad9`**. До fix27new casesfailed; после36conversioncasespassed и31соседний RCTcasepassed. Status/commands/ограничения — `BLOCK01_RCT.md`.

**Следующий рабочий блокB02**: contracts/shared/DGP, по FIX_PLAN. В первую очередь silent nonfinite/complex/separation diagnostics, затем index/weights/IDs/oracles. Начинать после нового запроса пользователя. Sensitivity modules/formulas/benchmarks/tests не редактировать.

Документация для пересылки готова в `DOCUMENTATION_HANDOFF.md`;28GitHub snapshot file/line links проверены, local-only links нет (`handoff_validation.json`). Нет необходимости заново выполнять полный аудит или broad benchmark.

## Baseline и ограничения

- Аудит:31grouped findings,11P1+20P2; sensitivity subset отложен. CSV inventory130modules,40notebooks.
- Original suite968cases:964passed/3failed/1error; recheck3passed/1failed. Реальный baseline failure — `tests/statistics/test_cuped_rct.py::test_shared_design_and_input_unchanged` на statsmodels0.15, SC-12. Не считать его регрессией B01.
- Windows sandbox process pipes/tmp могут вызвать PermissionError; при необходимых tests использовать разрешённый запуск с local basetemp.
- Audit snapshots/copies/runtime caches не включать в commits как whole directory tree. `audit/.gitignore` исключает copied docs build, temp/cache; small evidence logs намеренно разрешены.
- Оригинальные отчёты имеют absolute Windows links для локальной работы. `DOCUMENTATION_HANDOFF.md` переносимый, с GitHub SHA links для отправки автору.

## На завершении любого блока

Записать status, actual commit SHA, tests и оставшиеся ограничения; проверить git status; законченный commit; после доступного remote — push в личный fork. Остановиться и сообщить пользователю результат блока. Не автоматически начинать следующую большую область до его нового запроса.
