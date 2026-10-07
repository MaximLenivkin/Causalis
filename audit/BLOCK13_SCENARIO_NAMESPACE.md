# B13: namespace classic RCT scenario

Дата: 7 октября 2026, Europe/Moscow. Branch: `codex/correctness-roadmap`. Baseline: `9f0a63c42308ca886d92dc73d8d8d9611d5b2c31`. Source/tests checkpoint: **`4428be0e39bda8a2a47f1a6f184c92873da10976`**, обычный push в личную ветку выполнен. Source/tests после этого checkpoint не менялись.

## Результат и scope

Изменён один library path `causalis/scenarios/classic_rct/dgp.py`, оба публичных helpers. Enabled pre-period поле больше не может занять имя scenario outcome или `user_id`; идентификатор присутствует в этих scenarios даже при отключённых ancillary полях. Дополнительный shared guard проверяет фактическую схему перед поздним binary `y → conversion` rename. Automatic conversion сохраняет numeric pre-поля с именами отключённых oracle columns.

`add_pre=False` игнорирует неиспользуемое pre имя. Gamma scenario допускает pre `conversion`, поскольку его outcome — `y`. Literal names сохраняются; automatic rename нет. Invalid/empty enabled names проверяет прежний underlying B12 guard, без новой гарантии early type validation. Public signatures, numerical formulas, sampling, calibration, assignment и ID algorithms сохранены.

Для корректно классифицированных допустимых schemas проверено точное совпадение frame values, схемы, типов, contract metadata и RNG. Для formerly dropped disabled-oracle pre признаков намеренно меняется feature list; raw values и schema сохраняются. Outcome/ID collisions теперь отклоняются. CUPED/IV, shared DGP, contracts, inference, DiD и sensitivity source не менялись.

Подробности: [contract map](B13_SCENARIO_CONTRACT.md), [implementation](B13_SCENARIO_IMPLEMENTATION.md), [tests](B13_SCENARIO_TESTS.md), [independent review](B13_SCENARIO_REVIEW.md).

## Baseline и focused regressions

Новый `tests/data/test_scenario_namespace_contract.py` — **91 passed**, 0 failures/errors/skips/warnings, 4.37 s. Точный предыдущий checkpoint с тем же окончательным модулем — **28 failed / 63 passed**, 0 errors/skips, 4.79 s. Parameter counts не равны числу отдельных bugs. Reference raw-to-contract явно учитывает штатное treatment `int8`; остальные dtype comparisons строгие.

[Combined manifest](block13_scenario_test_result.json), [baseline](block13_scenario_baseline_test_result.json), [focused](block13_scenario_focused_test_result.json), [runner](block13_scenario_test_runner.py), raw logs `block13_scenario_baseline_tests.log` / `block13_scenario_focused_tests.log`. JUnit хранится в ignored `block13_scenario_test_temp`.

Baseline pin восстанавливает изменённый classic scenario module до первого импорта, verifies real aliases/helper bindings и unchanged bytes восьми DGP dependencies/control modules. Exact collection и test hash совпадают. Focused process был precommit; committed source/test bytes связаны с результатом без повторного run и изменения original process HEAD/time.

## Независимые probes и review

[Baseline-only contract probe](block13_contract_result.json) — **100 synthetic records** на точном baseline, восемь frozen modules с проверенными helper/class bindings, schemas/roles и sanitized errors. Это не pytest count и не candidate verification.

[Review probe](block13_review_probe.json) — **116 exact valid configurations**: 92 classic, 16 CUPED, 8 offer-IV. Nine-module frozen graph и реальные package exports исключают смешивание old/current helpers/classes. Сравнивались полные frames/dtypes/schemas/contract metadata и states/следующие 10 draws каждого созданного default_rng. Дополнительно 13 rejection и 40 allowed/projection probes; runtime warnings 0, issues []. Existing frozen IV-docstring SyntaxWarning записан отдельно. Classic UUID entropy/identity не заявляется проверенным exact references.

Full reference process был precommit; 13 referenced source/alias/test files сверены с exact committed bytes. Final test module independently reviewed. Reviewer не повторял focused/full integration и не менял library/tests/git.

## Local integration

На exact `4428be0e…`: **2487 passed, 1 failed, 0 errors/skips, 78 warnings, 109.60 s**, total 2488, exit 1. [Selection](block13_integration_selection.json), [result](block13_integration_result.json), [runner](run_block13_integration.py), raw `block13_integration_tests.log`; ignored JUnit `block13_integration_test_temp/junit.xml`.

Единственный failure — прежний `tests/scenarios/did/refutation/test_did_post_inference_diagnostics.py::test_post_inference_report_accepts_panel_and_estimate`, ожидает GREEN, получает YELLOW. B09 exact-baseline reproduction и B10 runtime numerical-zero proof сохранены. B13 проверяет прежние bytes fixture и пятифайловой package closure статически; изменённый scenario path находится вне этой closure. Новый B13 cell-value probe не запускался. Assert, thresholds и exclusions не ослаблялись. `scoped_suite_clean=false`, `full_suite_clean=false`, `sensitivity_validated=false`.

## GitHub CI

Run [37607784481](https://github.com/MaximLenivkin/Causalis/actions/runs/37607784481) **completed/success** на exact source `4428be0e39bda8a2a47f1a6f184c92873da10976`. Все шесть jobs и downloaded selection/environment/JUnit artifacts проверены: **2488 passed каждый**, 0 failures/errors/skips. [CI evidence](block13_ci_result.json), [artifact summarizer](summarize_block13_ci.py); matrix_verified=true, issues []. Snapshot UTC `2026-10-07T10:33:36.694587+00:00`.

Actual Python: 3.10.21 latest и legacy, 3.11.16, 3.12.14, **3.13.16**, 3.14.7. Версии остальных зависимостей записаны отдельно для каждой конфигурации в evidence. Это шесть representative Linux stacks, не все OS/dependency combinations. Audit-only final push не перезапускает source matrix.

`verify_block13.py` проверяет bounded source/test scope, committed-byte linkage, unchanged numeric runtime AST apart from namespace/projection, focused/baseline collection и JUnit, independent probes, local failure provenance и actual payloads всех шести CI artifacts. `verify_handoff.py` проверяет 103 immutable source/test links. Validation manifests сохраняются отдельно от исторических snapshots.

## Границы и продолжение

Ровно семь прежних sensitivity modules deferred через неизменённый `scripts/run_tests.py --scope correctness`. Full sensitivity, standalone Sphinx, release, все OS/dependency combinations и новый performance benchmark не validated. No PR, upstream sync/push или внешние сообщения.

Следующий самостоятельный B14: математически и численно обоснованная политика DiD diagnostics при нулевом истинном pre-effect и variance, а также fixture/reference policy. Не использовать blanket tolerance, clipping, увеличение thresholds или ослабление assertions ради зелёного статуса. Затем oracle numerical accuracy / marginal-propensity API и прежний correctness backlog. На границе B13 остановиться; B14 только по новому запросу пользователя.
