# B11 · Имена столбцов binary/IV генераторов

Дата: 7 октября 2026, Europe/Moscow. Baseline: `4d6b8143db7a93c1a7eba371fcd144878d80c896`. Source/tests checkpoint: **`cdc2c9590246c5b049d2184ba3479324217b2b00`**, ordinary push выполнен в personal `origin/codex/correctness-roadmap`. Root и три CLI субагента выполнили реализацию, контракт, независимые regressions и review. Source/tests после этого commit заморожены; итоговый audit checkpoint — `git log -1`.

## Исправление

`CausalDatasetGenerator` и `InstrumentalGenerator` отклоняют коллизии полного фактически создаваемого core namespace: outcome `y`, treatment `d`, IV instrument, actual expanded confounders и enabled family-specific oracle columns. Ошибка `ValueError` содержит имя и обе конфликтующие роли. Ранее confounder `d` заменял treatment произвольными числовыми значениями, `y` заменял outcome, duplicate X names теряли признаки, enabled oracles заменяли confounders или instrument.

Fixed roles проверяются при construction и перед каждым generate; actual names и их количество — после sampling X, до U/calibration/callbacks/assignment. Final check перед DataFrame assembly закрывает подтверждённые callback mutations: включение colliding oracles или изменение instrument name. Late rejection сохраняет уже произошедшие callbacks/RNG draws; rollback не обещается.

Scope — два library paths и один новый test module. Имена не обрезаются и не переименовываются; whitespace/NumPy strings, existing fallbacks, custom-X naming и categorical expansion сохранены. Отключённые oracles доступны, IV не резервирует binary-only `m_obs`, `g0`, `g1`. Width check сохраняет работавшие zero-confounder list/1D-array containers без преобразования X для callbacks. Arithmetic, draw order и public signatures сохранены; AST comparison подтверждает, что в generate добавлены только guards. [Implementation](B11_NAMESPACE_IMPLEMENTATION.md), [contract](B11_NAMESPACE_CONTRACT.md).

## Проверки

- **163 новых cases passed**, без warnings/errors/skips, **4.14 s**. Тот же final module на exact baseline: **103 failed, 60 passed**, без errors/skips, **5.81 s**; это parameterizations, не число отдельных bugs. Collection, IV inheritance и real wrapper bindings проверены. Focused run выполнен до commit на идентичных committed source/test bytes. [Tests](B11_NAMESPACE_TESTS.md), [provenance](block11_namespace_test_result.json).
- Independent reviewer: **80 valid configs × 2 generations**, ещё **6 family-specific name configs × 2** и **14 zero-confounder containers × 2**: всего **200 exact frame/dtypes/schema/next10RNG comparisons**. Проверены **45 rejected schemas** и **11 mutation cases**. Finalassembly gap найден и закрыт до source commit. Material source findings после correction отсутствуют. [Review](B11_NAMESPACE_REVIEW.md), [committed-source probe](block11_review_probe.json).
- Frozen contract probe: **46 namespace reproductions**, 16 container observations, 5 wrapper residuals. Только synthetic schemas/counts/errors; individual records не сохранялись. [Baseline evidence](block11_contract_result.json).

- **Local Mac integration: 2234 passed, 1 failed, 0 errors/skips, 78 warnings, 84.59 s**, exit1, total2235. Это **не clean local suite**. [Result](block11_integration_result.json), [selection/environment](block11_integration_selection.json), [raw log](block11_integration_tests.log).

Единственный local failure — прежний `test_post_inference_report_accepts_panel_and_estimate`, GREEN assertion получает YELLOW. B09 exact-baseline reproduction и B10 runtime probe установили numerical-zero fragility: preATT ≈1.11e-16, SE ≈2.94e-31, |t| ≈3.78e14. B11 artifact checker повторно проверяет неизменность fixture и всей package closure, вызванной B10 probe; оба изменённых DGP paths находятся вне этой closure. Это static provenance linkage с предыдущим runtime evidence, а не новый B11 cell-value probe. [Previous exact-baseline proof](B09_LOCAL_INTEGRATION_NOTE.md), [B10 runtime evidence](block10_did_provenance.json). Existing assertion/threshold/scope не ослаблялись.

## CI

Run [37589241406](https://github.com/MaximLenivkin/Causalis/actions/runs/37589241406) **completed/success** на exact source `cdc2c9590246c5b049d2184ba3479324217b2b00`. Все шесть Linux jobs и downloaded selection/environment/JUnit artifacts проверены: **2235 passed каждый**, без failures/errors/skips. Actual Python: 3.10.21 latest, 3.10.22 legacy, 3.11.16, 3.12.15, 3.13.15, 3.14.7. [Verified matrix](block11_ci_result.json): `matrix_verified=true`, issues пуст; snapshot UTC2026-10-07T07:48:19.487537. Семь sensitivity exclusions совпадают с local и B10. Versions записаны по фактическим artifacts, а не скопированы из предыдущего этапа.

## Ограничения и следующий пункт

Core guard распространяется через aliases/wrappers, вызывающие generate. Собственные pre-period/ancillary additions, ordering и conversion exclusions остаются отдельным scope. Подтверждены pre_name=`y` overwrite/duplicate projection, ancillary `age` overwrite, IV projection с duplicate `user_id` или disabled-oracle instrument `m`, и автоматическое исключение disabled-oracle-named confounders при conversion. [Contract residuals](B11_NAMESPACE_CONTRACT.md), [independent probe](block11_contract_result.json). Следующий bounded **B12** — wrapper schema/ordering/projection policy, после него отдельная mathematical/numerical-zero DiD diagnostic policy и Gaussian oracle accuracy/API. Нельзя заявлять, что B11 гарантирует безопасность любых custom wrapper schemas.

General X shape/finite contracts, arbitrary callback side effects, numerical oracle accuracy и learner/score backlog не переработаны. Ровно семь прежних sensitivity exclusions сохраняются; full sensitivity, standalone Sphinx, release и универсальная OS/dependency compatibility не проверены. Benchmark/speedup не заявлены. Только synthetic repository fixtures; corporate/client data не использовались. Upstream sync/PR/issues/external messages/release не выполнялись.

## Воспроизведение

```bash
.venv/bin/python audit/block11_namespace_test_runner.py --mode baseline  # expected exit1
.venv/bin/python audit/block11_namespace_test_runner.py --mode focused
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLBACKEND=Agg MPLCONFIGDIR=.venv/matplotlib .venv/bin/python audit/block11_review_probe.py
.venv/bin/python audit/run_block11_integration.py
.venv/bin/python audit/verify_block11.py
.venv/bin/python audit/verify_handoff.py
```

Raw JUnit/CI downloads/cache остаются в ignored owned temp paths; воспроизводимые scripts и aggregate evidence сохранены. [Artifact checker](verify_block11.py) сохраняет результат в `block11_validation_checks.json`; portable documentation handoff содержит готовый текст и **94 verified immutable source links**, issues пуст. **B11 завершён**; на границе этапа остановиться, B12 начинается новым запросом пользователя.
