# Прогресс и журнал

## 2026-10-05

- Репозиторий склонирован в `D:\codex\Causalis`, commit `ffe2c356c115f335b74b2f10117e19fe15585d46`; исходный checkout чистый.
- Прочитан корневой `AGENTS.md`. Указанный macOS interpreter отсутствует на Windows; создаётся repo-local `.venv` на доступном Python 3.12.14, входящем в declared диапазон >=3.10,<3.15.
- Созданы план и шкала доказательств. Ревью без изменений библиотечных исходников.
- Открыты репозиторий и опубликованный сайт; подтверждены перечисленные сценарии.
- Инвентаризация: 130 source Python modules (без generated _version.py), 48 194 строки, 123 test files, 40 notebooks/1 062 cells. Все исходники проходят AST parse.
- Создана `.venv` Python 3.12.14 и установлены project dev/docs dependencies + DoubleML для сравнения. Первый запрос установки не выполнился из-за перегрузки auto-review; повторный запрос одобрен и успешно выполнен. Version manifest: `environment.json`.
- Общий pytest завершён: 964 passed, 3 failed, 1 error из968cases, 317.21с (`pytest_full.log`, `pytest_full.xml`). Отдельный recheck четырёх непрошедших:3 passed,1 failed. Три проблемы были sandbox process/tmp permissions, одна — реальный CUPED cache regression со statsmodels0.15. Совместно967cases подтверждены как passing; это не один полный чистый прогон.
- Воспроизведены shared/contracts/DGP дефекты: nonfinite data, zero-variance SMD, duplicate-index outlier extraction, NaN assignment weights, default UUID collisions, nonlinear latent multi oracle.
- Сабагенты подтвердили численно defects multi ATTE/relative ATT/sensitivity/refit CATE, Newcombe, DiD score/controls, CUPED name collision и другие; findings проходят дедупликацию перед финальным рейтингом.
- Извлечён markdown всех 40 notebooks, сопоставлены API modules и source. Подозрения по 27 импортам проверены: actual export errors не обнаружены.
- Первичная литература сверяется через web; современный paper не считается автоматически основанием заменить корректный existing estimator.
- Все три сабагента завершили отчёты: DML_REVIEW, SCENARIOS_REVIEW, DOCS_RESEARCH. Exact references, probes и ограничения сохранены; исходники не менялись.
- Изолированная API docs build успешно завершилась, generated131moduleHTML; оригинальный checked-in API126HTML сохранён. Файл tests/docs/test_generate_api_reference.py helper-only, реальных pytest tests нет.
- Benchmark завершён; повтор выполнен без параллельных fits/tests/docs build. Matched binary IRM Causalis0.1468с vsDoubleML0.3644с; ATE/SE/OOF predictions совпадают. Constructor/extraction timings100k–1m и allocation peaks сохранены в benchmark_data_path.json.
- Array benchmark уточнён: первая версия не выполняла binary checks, поэтому сравнение было неполным. Итоговый script сравнивает same-checks и отдельную linear-binary optimization; в финальный отчёт включены только исправленные измерения.
- Итоговая дедупликация:31code/inference/contract/release findings,11P1+20P2. DML-05/ROOT-04 объединены; docs Newcombe не считается вторым независимым багом. Отдельные top10 docs/methods/features/performance составлены.
- REPORT.md, PERFORMANCE.md и COVERAGE.md написаны. Findings содержат reproduction/source evidence и границы переноса вывода; fixes не применены, чтобы сохранить review snapshot.
- Финальная проверка артефактов:171absolute local links/line anchors проверены, missing/out-of-bounds0; все шесть таблиц содержат заявленное число пунктов (10/21/10/10/10/10). Evidence: report_validation.json, verify_audit.py. Git diff tracked source пуст.

## Состояние этапов

| Этап | Состояние |
|---|---|
| 1. Снимок/окружение | Завершён |
| 2. Корректность | Завершён в заявленных пределах; independent probes и catalogue готовы |
| 3. Документация | Завершён;40notebooks inventory, сайт/docstrings/API drift и successful build |
| 4. Исследования | Завершён; primary sources доSep2026, top10 extensions |
| 5. Производительность | Завершён; clean benchmark, profiles, top10 optimization plan |
| 6. Отчёт | Завершён; REPORT.md и тематические приложения готовы |

## Следующий этап проекта

Рекомендованный порядок дальнейшей разработки: быстрые correctness/doc fixes → inference repair и coverage validation → оптимизация data path → расширения DML/CATE/IV/DiD. Это backlog, а не незавершённая часть текущего ревью. Существующий код не исправлялся и внешние PR/issues не создавались.

## 2026-10-05 — начало исправлений по новому запросу

- Проверены Git/author/public remote. Upstream main соответствует audit SHA. `gh` отсутствует, configured helper отсутствует; noninteractive GCM check не нашёл сохранённую GitHub credential. Remote fork/push пока не выполнены; авторизация по инструкции GIT_ACCESS.md ожидается от пользователя.
- Создана branch `codex/correctness-roadmap`; checkpoint **2c26cee** сохранил аудит/evidence/план. Большие build copies/temp/cache исключены из index, raw text evidence logs сохранены.
- FIX_PLAN.md разбивает работу на6implementationblocks с commits/проверками и остановкой для очистки контекста. Sensitivity DML-07/08/10/11 и dependent lifecycle state отложены по прямому сообщению пользователя о готовящихся upstream fixes.
- DOCUMENTATION_HANDOFF.md подготовлен для автора docs;28GitHub snapshot links проверены, local-only links0. Sensitivity-specific tasks исключены.
- **B01 завершён, commitbd8a2be:** Newcombe hybrid CI, enum validation, function docstring. До source fix27testsfailed/9passed; после36conversionpassed и31neighborRCTpassed. Логи block01_*_tests.log. Полный suite/benchmark повторно не запускался, sensitivity не затрагивался.
- NEXT_SESSION.md содержит commits, scope, проверки и следующийblockB02. На границе B01 работа остановлена; внешние PR/issues не создавались.

## 2026-10-05 — GitHub подключён

- Пользователь завершил browser login. Проверен активный GitHub account **MaximLenivkin**, keyring и scopesrepo/workflow; credentials не выводились.
- Создан [личный fork](https://github.com/MaximLenivkin/Causalis); API подтвердил parentcausalis-causalcraft/Causalis и push/admin права. Upstream доступен read, без push.
- Исправлена команда в GIT_ACCESS.md: установленный gh2.102.0 не принимает `--remote=false` вместе с explicitrepository; создание выполнено с `--clone=false`.
- Origin переименован в upstream; новыйorigin указывает на personalfork. Ветка `codex/correctness-roadmap` pushed с commits2c26cee/bd8a2be/a3846ba, local tracking настроен. Code tests не повторялись: на этом этапе менялась только Git setup/documentation.
- Проверка первогоpush:remote/localHEAD совпадают — `a3846baa0a07e7d81c3ea8850e130cb2de6d6ba4`; remote копия трёх commits подтверждена.
- NEXT_SESSION/FIX_PLAN/DOCHANDOFF обновлены; sensitivity остаётся отложенным, B02 не начат, PR не создан.

## 2026-10-05 — B02 завершён

- По новому запросу пользователя выполнен один следующий блок: contracts/shared/DGP. Три сабагента независимо исправили numeric validation, utilities и latent-U outcome oracle; root исправил shared/binary/multi balance, проверил diffs и выполнил интеграцию.
- Закрыты ROOT-01–07, включая grouped ROOT-04/DML-05: один P1 и шесть P2. Sensitivity files/formulas/tests не менялись; проверка paths относительно начала B02 не нашла sensitivity изменений.
- До source fixes сохранены failing regressions. Scoped passes: contracts 147, balance 50, utilities 34, oracle 45; эти наборы пересекаются и не суммируются как unique coverage.
- Общая проверка финального кода: **606 passed**, 5 existing warnings, 123.61 s. `block02_integration_tests.log` охватывает data/shared, multi DGP, публичные balance/Love plot, outliers и соседние RCT inference tests. Полный suite и performance benchmark не повторялись; известный SC-12 остаётся в B05.
- Созданы code commits **817c24c / add2f36 / a5a6e3a / c27e744**, каждый с code/tests/evidence. Итоговый отчёт — BLOCK02_CONTRACTS_SHARED_DGP.md; B02_*_NOTES.md сохраняют derivations, commands и compatibility limits.
- DOCUMENTATION_HANDOFF.md дополнен готовыми английскими migration/oracle текстами и immutable GitHub code links. verify_handoff.py теперь проверяет snapshot links как upstream audit, так и personal implementation commits.
- Финальная проверка artifacts: 36 GitHub handoff links и 188 absolute local links, issues 0; 21 changed/new Python files AST parsed; sensitivity paths changed 0. Новый verify_block02.py сохраняет отдельный validation JSON и не переписывает original report_validation.json.
- Новый соседний DGP follow-up: marginal propensity oracle вместо softmax при U=0. Текущее поведение явно описано; изменение propensity API не входит в B03. Extreme coefficient guards, estimator output policy и near-zero SMD scale invariance также записаны как отдельные follow-ups.
- NEXT_SESSION/FIX_PLAN обновлены для B03. На границе B02 работа остановлена; следующий блок начинается после нового запроса. Внешние PR/issues не создавались. Коммиты сохраняются в ранее подключённой личной ветке через обычный push.
