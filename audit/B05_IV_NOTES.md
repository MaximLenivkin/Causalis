# B05: IV diagnostics API and model refit state (SC-09)

SC-09 исправлен: `instrument_overlap`, `first_stage`, `reduced_form` и `instrument_overlap_plot` принимают документированный `IIVM` после успешных `fit().estimate()`. По-прежнему поддерживаются `IVCausalEstimate` и `IVDiagnosticData`. Технические изменения ограничены IV resolver, его docstrings и необходимой очисткой состояния IV model; nuisance/score/inference formulas не менялись.

Базовый checkpoint этого блока — `c55909491c8c50d603a8bf348b4beca11b623e02`. Commit/push делает главный агент после B05 integration; этот файл не объявляет неподтверждённый SHA.

## Почему прежнее поведение было неверным

В [diagnostics.py](D:/codex/Causalis/causalis/scenarios/iv/refutation/diagnostics.py:134) resolver искал исключительно `source.diagnostic_data`, хотя модель хранит результат в `source.result_.diagnostic_data`. Поэтому обещанные docstrings четыре entrypoints отвергали даже модель с уже завершённым `estimate()`.

Новый общий `_resolve_result` извлекает `result_` перед чтением payload. Такое же разрешение применяется к `model_options` и `late_value` при lazy recomputation. Это существенная часть исправления: threshold берётся из snapshot результата, а не из текущей изменяемой конфигурации модели или ошибочного default. Неподходящий тип diagnostic payload даёт `TypeError`, отсутствующий payload/estimate — `ValueError` с инструкцией вызвать `estimate()`.

Самостоятельный `IVDiagnosticData` не содержит `model_options`; при отсутствии cached first-stage payload сохраняется прежний default `weak_iv_threshold=1e-2`. Для воспроизведения пользовательской конфигурации следует передать estimate или estimated model.

## Дополнительно найденное соседнее нарушение жизненного цикла

Первоначальный `IIVM.fit()` оставлял старые `result_`, nuisance arrays и inference attributes. Новый model diagnostics API мог бы показывать результат предыдущих данных; после failed refit даже `estimate()` мог снова использовать предыдущие nuisance predictions. Для SC-09 главный агент явно согласовал дополнительное изменение [IIVM.fit](D:/codex/Causalis/causalis/scenarios/iv/model.py:594).

Каждая fit attempt теперь сначала очищает все собственные fitted/inference attributes: arrays/predictions/models/folds/data reference, result, коэффициенты/SE/p-values/CI/summary и score arrays. Параметры конструктора и learner configuration сохраняются. Nuisance estimation не изменена: после её полного успеха fit публикует новые arrays. Неудачная fit attempt оставляет model unfitted; `estimate`, `diagnostics_`, `coef`, `se`, `pvalues`, `summary`, `confint` больше не возвращают прошлое состояние. У IIVM нет публичного predict entrypoint.

Успешный refit требует нового `estimate()` для inference и public post-inference diagnostics. Ранее возвращённые `IVCausalEstimate` остаются доступными: удаление ссылок в модели не меняет их payload. Это конкретная IV state correction; generic DML/sensitivity state здесь не исправлялся.

## Воспроизведение и проверки

Новый [test_iv_model_diagnostics.py](D:/codex/Causalis/tests/scenarios/iv/refutation/test_iv_model_diagnostics.py:61) содержит **60 parametrized regression cases**:

- Все три public tables: model/estimate/bare payload equivalence при cached и lazy вычислении; plot сравнивает histogram heights/positions и propensity mean markers, а не только существование Figure.
- Все четыре entrypoints: unfitted/fit-only/missing result payload/wrong payload type; TypeError не заменяется ложным missing-payload ValueError для вложенного объекта.
- Lazy first stage сохраняет `weak_iv_threshold=0.9` из estimate даже после изменения `model.weak_iv_threshold` на `.01`; reduced-form payload сохраняет estimate LATE value.
- Latest successful estimate становится model source; сохранённый предыдущий estimate не меняется.
- Успешный refit и failed refit требуют нового estimate; старый сохранённый result остаётся пригодным для diagnostics.
- Неудача ранней input validation и ошибка learner fitting блокируют **семь** fit/inference accessors; восстановление после failed refit совпадает с independently fresh model на новых данных.
- Пять inference accessors после successful refit не возвращают old result, затем доступны после нового estimate.

| Проверка | Результат | Evidence |
|---|---|---|
| Исходные 31 API cases до resolver fix | 15 failed,16 passed;15.36s | [block05_iv_before_tests.log](D:/codex/Causalis/audit/block05_iv_before_tests.log) |
| Interim resolver/cache-result fix +39new cases/13 neighbors | 52 passed,2 existing SyntaxWarnings;15.13s | [block05_iv_after_tests.log](D:/codex/Causalis/audit/block05_iv_after_tests.log) |
| 16 lifecycle cases до full fit-state clearing | 14 failed,2 passed,39deselected;14.20s | [block05_iv_lifecycle_before_tests.log](D:/codex/Causalis/audit/block05_iv_lifecycle_before_tests.log) |
| Final 60 new cases +13 neighboring IV cases | **73 passed;19.33s** | [block05_iv_final_tests.log](D:/codex/Causalis/audit/block05_iv_final_tests.log) |

Final command: repo-local `.venv\Scripts\python.exe -m pytest tests/scenarios/iv/refutation/test_iv_model_diagnostics.py tests/scenarios/iv/refutation/test_iv_diagnostics.py tests/scenarios/iv/refutation/test_iv_confounders_balance.py tests/inference/test_iivm.py tests/scenarios/iv/test_dgp.py -q -p no:cacheprovider --basetemp=audit/block05_iv_final_test_temp`, `MPLBACKEND=Agg`, local `MPLCONFIGDIR`. Counts пересекаются между runs; не суммировать.

[block05_iv_probe.py](D:/codex/Causalis/audit/block05_iv_probe.py) исполняет только исторический `iv_fit_and_diagnostics()` из `repro_scenarios.py`, не его full main. Он подтверждает `first_stage(model)` accepted и `first_stage(estimate)`7×5, LATE `2.0599090331725676`: [result JSON](D:/codex/Causalis/audit/block05_iv_probe_result.json), [raw log](D:/codex/Causalis/audit/block05_iv_probe_checks.log). LATE/inference formulas не менялись.

## Готовый текст для документации (English)

> `instrument_overlap`, `first_stage`, `reduced_form`, and `instrument_overlap_plot` accept an `IIVM` model after a successful `fit().estimate()`, its `IVCausalEstimate`, or an `IVDiagnosticData` payload. Calling `fit()` alone does not create post-inference diagnostic data. Each new fit attempt clears the model's previous fitted and inference state; a failed refit leaves the model unfitted, and a successful refit requires a new `estimate()`. Previously returned estimates remain usable independently of the model. Lazy diagnostics called with a model use the latest estimate's saved options and LATE value.

## Границы

Этот fix закрывает promised API и stale IV state. Он не меняет IV identification assumptions, weak-IV inference, cross-fitting scheme, nuisance estimators, diagnostic formulas или heuristic strength thresholds. Existing invalid-escape SyntaxWarnings в математических IV docstrings видны в interim run; они не устранялись отдельной несвязанной правкой. Final focused run не заменяет общий B05 integration и не является compatibility matrix. Sensitivity modules/tests не редактировались и не запускались.
