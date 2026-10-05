# B05: наследование конфигурации ASCM для placebo refutations

Дата: 2026-10-05. Проект `D:\codex\Causalis`, блок B05. Это продолжение исторического **SC-08 P2**, ограниченное **placebo-in-space / placebo-in-time / run_placebo_tests**. **Leave-one-donor-out sensitivity остаётся отложенной**, её файл, формулы и tests не менялись. SC-08 нельзя обозначать полностью закрытым.

## Проблема и воспроизведение

Раньше каждый placebo refit конструировал `ASCM(**(model_kwargs or {}))`: без kwargs использовал defaults вместо настроек исходного estimate, а частичный kwargs сбрасывал остальные параметры. В исходном `PanelEstimate` отсутствовало поле полной конфигурации модели; diagnostics не сохраняли все constructor arguments и estimate-time inference overrides.

Изолированный historical probe выполняет только placebo, без вызова LOO/sensitivity. Для gamma DGP, seed241, `lambda_aug=1e6`, average ATT t-test отключён:

| Величина | До исправления | После исправления |
|---|---:|---:|
| Original full-sample mean post gap | 1.3314659377305926 | 1.3314659377305926 |
| Actual treated row, omitted model_kwargs | 1.371201225159669 | 1.3314659377305926 |
| Actual treated row, explicit matching partial kwargs | 1.3314659377305926 | 1.3314659377305926 |

До/после сохранены отдельно: [before JSON](D:/codex/Causalis/audit/block05_scm_before.json), [after JSON](D:/codex/Causalis/audit/block05_scm_after.json), [probe](D:/codex/Causalis/audit/block05_scm_probe.py). Probe намеренно не запускает исторический `repro_scenarios.py` целиком.

## Реализация

- [PanelEstimate](D:/codex/Causalis/causalis/data_contracts/panel_estimate.py) получил additive `model_options: dict[str, Any]`, default `{}`. Старые/manual objects остаются валидными; неизвестная конфигурация обозначается пустым словарём. Existing output paths/diagnostics fields не менялись.
- [ASCM](D:/codex/Causalis/causalis/scenarios/synthetic_control/model.py) после успешного `fit()` сохраняет snapshot всех **13** constructor arguments: five fitting settings и eight inference settings. `estimate()` возвращает отдельную копию; per-call inference overrides записываются в effective options. Failed refit очищает snapshot вместе с прежними artifacts, successful refit обновляет его.
- [Placebo refutations](D:/codex/Causalis/causalis/scenarios/synthetic_control/refutation/placebo.py) берут known ASCM constructor keys из snapshot и накладывают explicit `model_kwargs` поверх. `{}` и `None` сохраняют исходную конфигурацию. Неизвестная дополнительная result metadata игнорируется; неизвестные **explicit** kwargs отклоняются с понятной ошибкой. Mapping types проверяются, constructor выполняет прежнюю validation/coercion, attrs получают canonical validated values.
- Таблицы сохраняют прежние columns. В `DataFrame.attrs` добавлены `model_options` и `model_kwargs_overrides`; input metadata, kwargs и panel не мутируют.
- При incomplete/legacy metadata требуется заново оценить ASCM или явно восстановить все missing constructor options через kwargs. Возникает actionable `ValueError`, вместо молчаливого выбора другого estimator. Full explicit kwargs могут восстановить конфигурацию legacy result; partial known metadata можно дополнить только отсутствующими keys. Проверка выполняется и для empty placebo-in-time table.

Соседняя consistency правка: пользователь может менять public fitting attributes после fit, но cached path остаётся от исходной модели. При `estimate(alpha=..., ...)` auxiliary average/conformal inference refits временно используют записанные five fitting settings; `finally` восстанавливает текущие public attributes и inference defaults. Таким образом metadata и auxiliary inference относятся к одной fitted ASCM. Snapshot не меняется. Это не изменение ridge/SCM/inference формул.

## Проверки

[Новые tests](D:/codex/Causalis/tests/scenarios/synthetic_control/refutation/test_placebo_config_inheritance.py) строят donor/time-placebo panels самостоятельно, затем выполняют независимый direct ASCM refit со всеми исходными параметрами. Они не используют private placebo resolver/builder. Проверяются actual treated row, donor exclusion, pre/post RMSPE, mean/max gap, inference CI/p-value/rejection, partial overrides, estimate-time settings и configuration isolation. Есть JSON roundtrip самого model_options и Pydantic model_dump/model_validate roundtrip контракта; full result JSON serialization со Series здесь не заявляется.

Initial 25 cases до patch: **25 failed**, 20.88s. Часть падений отражает отсутствие нового metadata API/ошибок, это не 25 отдельных statistical defects. После первого patch те же25: **25 passed**,18.59s. Затем добавлены6 edge cases, включая canonical types, incomplete legacy restoration, empty tables, pointwise settings, failed refit и fitting-attribute/inference consistency.

Финальная scoped проверка: **67 passed**, **1 warning**,31.10s; **31 new cases +36 neighboring existing cases**. Соседние файлы: `test_placebo.py`, `test_ascm_model.py`, `test_panel_estimate.py`, `test_panel_estimate_summary.py`. Warning — существующий ASCM message о confidence set на boundary, вызванный намеренно маленькой grid_size3 в новом pointwise configuration case. Это не silent suppression и не подтверждение качества conformal coverage.

Команда:

```powershell
$env:MPLBACKEND='Agg'
$env:MPLCONFIGDIR='D:\codex\Causalis\audit\mplconfig'
.\.venv\Scripts\python.exe -m pytest tests/scenarios/synthetic_control/refutation/test_placebo_config_inheritance.py tests/scenarios/synthetic_control/refutation/test_placebo.py tests/scenarios/synthetic_control/test_ascm_model.py tests/data/test_panel_estimate.py tests/data/test_panel_estimate_summary.py -q -p no:cacheprovider --basetemp=audit/block05_scm_test_temp
```

Evidence: [before log](D:/codex/Causalis/audit/block05_scm_before_tests.log), [initial after log](D:/codex/Causalis/audit/block05_scm_after_tests.log), [final scoped log](D:/codex/Causalis/audit/block05_scm_final_tests.log), [result manifest](D:/codex/Causalis/audit/block05_scm_result.json). Counts пересекаются; их нельзя складывать с repository integration. Commit SHA и общий B05 result фиксирует root report после интеграции.

## Готовый текст для автора документации

> ASCM results now record all constructor-compatible fitting settings and the effective inference settings in `PanelEstimate.model_options`. Placebo-in-space and placebo-in-time refits inherit these settings. Pass `model_kwargs` to override selected settings; every unspecified setting retains its value from the original estimate. The returned table records the resolved settings and explicit overrides in `DataFrame.attrs["model_options"]` and `DataFrame.attrs["model_kwargs_overrides"]`.
>
> Older or manually constructed results may not contain a complete ASCM configuration. Re-estimate with ASCM, or supply all missing constructor options explicitly. Placebo refutations raise `ValueError` when the configuration is incomplete, because the original estimator cannot be reconstructed safely from its effect path alone. Leave-one-donor-out sensitivity has not been migrated in this block and still requires explicit matching model settings.

Фрагмент относится к новой branch implementation и должен выпускаться вместе с её кодом. Методология ridge augmentation, placebo ranks, accepted confidence sets и inference formulas не пересматривалась этим patch. Coverage, autocorrelation assumptions, few donors, extreme tuning и ASCM speed claims не добавлены.
