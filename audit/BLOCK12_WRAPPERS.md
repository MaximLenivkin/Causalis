# B12 — имена, augmentation и projection DGP wrappers

Дата: 2026-10-07, Europe/Moscow. Frozen baseline: **eb6dfe23f0a97991b6e3d6109febc1b0170e128d**. Source/tests checkpoint: **0b30db33fd2593dc25ea1b823a91795c789e0191**, ordinary push в origin/codex/correctness-roadmap выполнен. Root и три существующих CLI субагента независимо разобрали контракт, написали regressions и провели review.

## Реализованное поведение

Шесть library paths: общий ancillary helper, binary preperiod/base/functional, IV base/functional. Добавлен только tests/data/test_wrapper_namespace_contract.py; существующие tests/CI selection не изменялись. [Implementation](B12_WRAPPER_IMPLEMENTATION.md), [contract](B12_WRAPPER_CONTRACT.md).

- Только фактически включённые pre/ancillary поля резервируют имена. Конфликты с existing columns или друг с другом дают contextual ValueError без переименования. Шесть ancillary fields защищены до draws/writes. Pre helper проверяет namespace до builder, после callback и перед присваиванием; Tweedie также защищает прямое присваивание и prospective _latent_A oracle.
- Неиспользуемый pre_name при add_pre=False не участвует в ordering или feature selection. IV instrument user_id и disabled-oracle names допустимы при отсутствии соответствующей добавленной роли. Projection выдаёт каждое поле ровно один раз.
- Автоматическая conversion выбирает фактические numeric features. Disabled oracle-looking names не теряются; enabled oracles не становятся confounders. user_id получает роль ID только при реальном ancillary addition; low-level numeric user_id остаётся feature, IV user_id — instrument. Явный confounders selection сохранён.
- Immutable metadata actual names/roles фиксируется до assembly/late IV callbacks и публикуется после успешной generate. Independent reviewer обнаружил первоначальный alias-list gap; capture tuple до callbacks исправляет conversion KeyError. Два private init=False/repr=False/compare=False поля нужны slotted dataclasses; constructor signatures сохранены, fields/asdict расширены private state.

Arithmetic и RNG operations не менялись: AST comparison пяти generate/augmentation bodies подтверждает идентичность после удаления guards/metadata/docstrings. Valid correctly classified schemas сохраняют output/RNG. Для ранее misclassified names исправление намеренно меняет features и иногда pre/ancillary values/RNG; blanket identical-output claim недопустим. Data-contract numeric/constant/finite/duplicate-value checks не ослаблены; general X shape/finite/calibration контракт не расширен.

## Независимые проверки

[Tests](B12_WRAPPER_TESTS.md), [combined provenance](block12_wrapper_test_result.json), [focused raw output](block12_wrapper_focused_tests.log), [baseline raw output](block12_wrapper_baseline_tests.log). Новые **162 passed**,0failures/errors/skips/warnings,4.74s. Exact same module на frozen baseline: **136 failed /26passed**,0errors/skips,6.53s. Parameterizations не равны числу independent bugs. Six loaded modules, wrapper/shared-helper bindings, IV inheritance, exact collection и test hash verified. Focus был precommit; исходный head_at_start не переписывался, все six source+test committed bytes linked к successful run без ненужного rerun.

[Independent review](B12_WRAPPER_REVIEW.md), [probe JSON](block12_review_probe.json): **300 wrapper configurations +80 core conversion configurations×2generations =460 exact frame/dtype/schema/contract-metadata/RNG comparisons**. Wrapper captures все созданные default_rng streams; fixtures с ancillary используют deterministic IDs. Дополнительно:45 namespace rejections,34 permitted-name checks,6 core callback/success-snapshot checks,5 wrapper/helper callback checks и2 constructor checks. Warnings0,issues[]. Eleven-module frozen dependency overlay проверяет baseline wrappers против baseline helpers/classes. Multi и scenario aliases — unchanged reference paths. Full references выполнены до commit и точные committed bytes затем verified.

[Contract baseline probe](block12_contract_result.json):133synthetic schema/role observations, baseline-only; records не сохраняются. Это не current verification и не pytest count.

## Local integration и CI

Команда .venv/bin/python audit/run_block12_integration.py использует unchanged scripts/run_tests.py --scope correctness на exact committed source. [Result](block12_integration_result.json), [selection/environment](block12_integration_selection.json), [raw log](block12_integration_tests.log): **2396passed,1failed,0errors/skips,78warnings,85.67s**,exit1,total2397. scoped_suite_clean=false и full_suite_clean=false.

Единственный failure — прежний tests/scenarios/did/refutation/test_did_post_inference_diagnostics.py::test_post_inference_report_accepts_panel_and_estimate (GREEN/YELLOW). Existing B09 exact-baseline reproduction и B10 runtime proof сохранены. B12 statically verifies прежние bytes fixture и всей пятифайловой package closure из B10 runtime; six changed paths вне closure. Новый B12 cell-value probe не запускался. Threshold/assert/exclusions не ослаблялись; numerical-zero policy требует отдельной численной и математической задачи.

CI run [37598926037](https://github.com/MaximLenivkin/Causalis/actions/runs/37598926037), exact source 0b30db33fd2593dc25ea1b823a91795c789e0191: **completed/success**. Все шесть downloaded job artifacts: **2397 passed каждый**,0failures/errors/skips. [CI manifest](block12_ci_result.json):matrix_verified=true,issues[]. Snapshot UTC2026-10-07T09:15:10.818155. Actual Python3.10.21latest/legacy,3.11.16,3.12.14,3.13.15,3.14.7.

Ровно семь прежних sensitivity modules deferred; full sensitivity, standalone Sphinx, release и новые performance measurements не проверялись. Нового ускорения не заявляем.

## Остаток и граница этапа

Separate confirmed scenario residual: generate_classic_rct_26(add_pre=True,pre_name='conversion',add_ancillary=False,return_causal_data=False) после valid wrapper generation делает y→conversion rename и возвращает duplicate conversion labels; frozen/current совпадают. Contract output отклоняет дубликат. CUPED26 имеет свой reserved-name guard. Это следующий ограниченный scenario-boundary пункт, затем numerical-zero DiD diagnostic/fixture policy и прежний correctness backlog.

Source/tests frozen после 0b30db33fd2593dc25ea1b823a91795c789e0191; финальный audit checkpoint определяется git log -1. Ordinary final push и remote/local equality+clean tree проверяются на завершении. PR/upstream sync/release/external messages не выполнялись. Portable handoff дополнен; CI/artifact validation завершены; финальный audit checkpoint сохраняет результат, затем работа остановлена на границе B12.
