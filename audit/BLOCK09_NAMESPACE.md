# B09 · Уникальность имён multi-treatment DGP

Начат 2026-10-06, завершён 2026-10-07 (Europe/Moscow). Baseline: `74145665127f8fa5a0bf038d769697ab880854b8`. Ветка: `codex/correctness-roadmap`.

**B09 завершён в ограниченном namespace scope.** Source/tests checkpoint: **`1e2b544f7f91a57ad3e049572915a4b3891b084a`**, обычный push в личный fork выполнен. После него только audit artifacts; source/tests заморожены. Шесть Linux CI jobs полностью зелёные в выбранном scope. Локальная macOS integration содержит один подтверждённый failure исходного DiD-кода и не считается чистой.

## Исправление и совместимость

Outcome, treatment, actual expanded confounders и включённые oracle columns теперь имеют единый namespace guard. Коллизия вызывает ValueError с конкретным именем и конфликтующими ролями. Пустые и non-string фактические имена отклоняются явно; scalar-string treatment container не принимается за список букв.

Проверяются все пересечения ролей, в том числе уникальные treatment names `['a','obs_a']`, которые порождают один `m_obs_a` из двух oracle families. Categorical expansion учитывает одноуровневый suffix, пересечение с scalar confounder и одинаковое строковое отображение различных уровней.

Непустые строки сохраняются буквально, включая whitespace; нет strip, переименования или добавления suffixes. Отключённые oracle и отсутствующий control CATE не резервируются. Ordered tuple и NumPy string-array containers сохраняют совместимость. Custom X использует прежние фактические имена без categorical expansion.

Treatment/oracle subset проверяется при construction и перед каждым generate; полный namespace — после успешного `_sample_X`, до U, structural callbacks, treatment и outcome draws. Проверяется и соответствие числа names ширине X. Изменение публичных настроек между вызовами не обходит guard. Ошибка существующего sampler может произойти до полной проверки схемы.

Scope: два library paths `multicausaldata/base.py`, `functional.py` (последний — docstring), один новый test module. Sampling arithmetic, estimator formulas и sensitivity не менялись. Root реализовал guard и integration, три субагента независимо разобрали контракт, написали regressions и выполнили adversarial review/CI verification.

## Независимые проверки

- Новые regression tests: **123 passed, 0 failures/errors/skips/warnings, 3.65 s**. Exact baseline тех же tests: **87 failed, 36 passed, 0.99 s**; это параметризации нескольких нарушений контракта, а не 87 отдельных bugs.
- Baseline повторно воспроизводится через [git-show runner](block09_namespace_baseline.py); его exit1 ожидаем, итог также87failed/36passed. Initial101 runs и один исправленный test-fixture assertion сохранены с отдельными labels.
- Соседние numeric/assignment/semantics/latent-oracle modules: **217 passed, 6.91 s**. Counts пересекаются с integration, не суммируются.
- Exact old/current reference: **64 конфигурации ×2 последовательные генерации =128 comparisons**. Все DataFrame values/dtypes/schema/confounder names и следующие10RNGdraws совпали. Четыре outcome families, oracle on/off, callbacks on/off, default/categorical/numeric-copula/custom-X paths.
- Независимый reviewer дополнительно проверил18corruption cases,3allow cases,11validconfigs×2generations,5mutations и9malformedname cases. Material patch findings не обнаружены; это отдельные probes, не дополнительный pytest count.

Детали: [implementation](B09_NAMESPACE_IMPLEMENTATION.md), [contract](B09_NAMESPACE_CONTRACT.md), [tests/provenance](B09_NAMESPACE_TESTS.md), [method review](B09_METHOD_REVIEW.md). [Namespace results](block09_namespace_tests_result.json), [reference results](block09_finite_reference_result.json), [focused log](block09_namespace_current_tests.log), [neighbor log](block09_neighbor_tests.log).

## Actual integration и CI

Локально macOS arm64/Python3.12.14, native threads1/Agg: **2038 passed,1 failed,0 errors/skips,80 warnings,117.46 s**, exit1, total2039=1916+123. Все новые namespace cases прошли. [Raw log](block09_integration_tests.log), [exact selection/environment](block09_integration_selection.json), [result](block09_integration_result.json). Raw JUnit retained в ignored `block09_integration_test_temp/junit.xml`. `scoped_suite_clean=false`, `full_suite_clean=false`, `sensitivity_validated=false`; failure не исключался из selection.

Единственный failure — прежний `test_post_inference_report_accepts_panel_and_estimate`: ожидаетсяGREEN, полученоYELLOW. На детерминированной fixture pre-cellATT=`1.1102230246251558e-16`, SE=`2.9351198205368013e-31`, |t|≈`3.7825e14`. Диагностика воспринимает машинный остаток как большую standardized pretrend. Точная исходная версия7414566 на этом окружении даёт тот же failure, flag и cell values; fixture и весь вызванный package code неизменны, два изменённых DGP paths вообще не вызываются. Изолированные pytest baseline/current оба1failed. [Причина и provenance](B09_LOCAL_INTEGRATION_NOTE.md); существующий assert не ослабляли. Это отдельный numerical-zero/fixture follow-up, не B09 regression и не доказательство уникальности ошибки для macOS.

[GitHub run37530152376](https://github.com/MaximLenivkin/Causalis/actions/runs/37530152376) **completed/success** на exact source1e2b544. Скачанные selection/environment/result/JUnit artifacts всех шести Linux jobs проверены: **2039 passed в каждом,0 failures/errors/skips**. Python3.10–3.14 latest-compatible и3.10representativelegacy; [CI result](block09_ci_result.json), matrix_verified=true, verified_successful_jobs=6,issues0. SnapshotUTC2026-10-06T20:59:35.609244+00:00. Это representative stacks, не все combinations/OS.

Ровно семь прежних sensitivity modules исключены и перечислены в selection/CI JSON. Standalone Sphinx, full sensitivity и release не проверялись. Новый speed benchmark не выполнялся. [Portable documentation handoff](DOCUMENTATION_HANDOFF.md) дополнен готовым английским текстом и immutable source links.

## Остаток и граница этапа

1. Shared categorical Gaussian copula использует uniforms предыдущей координаты. Первый categorical вызывает UnboundLocalError; normal→categorical с identity correlation даёт `category_1 == (normal>0)` во всех1000rows,seed731. Ошибка подтверждена и требует отдельного sampling fix/reference; B09 её не исправляет.
2. Numerical-zero DiD pretrend diagnostic/fixture policy на текущем Mac stack: failure воспроизводится на исходном code. Следующий correctness block должен отдельно определить поведение при практически нулевых ATT/SE, не просто скрывать assertion.
3. Extreme Gaussian oracle accuracy, additive marginal propensity и selected ATT остаются отдельными numerical/API задачами. Затем learner shape/complex/IV storage, finite score/IF arithmetic, normalized custom ATE, duplicate policy/owned arrays/Sphinx и feature blocks по плану.

Sensitivity и SC08 leave-one-donor-out deferred; upstream не merge/rebase, PR/issues/messages/release не создавались. Итоговая artifact проверка фиксируется в [validation JSON](block09_validation_checks.json). На границе B09 работа остановлена; B10 начинается новым запросом.
