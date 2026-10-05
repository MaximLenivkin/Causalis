# B07 · независимое финальное review изменений

Дата: 2026-10-06. Сравнение source diff и executable AST с `c234e647e010f5d8bfb805af7ece61392e327537`; review после добавления hard-label fallback guard.

**Открытых замечаний, блокирующих bounded B07 scope, не найдено.** В ходе независимого review обнаружен дополнительный способ скрыть invalid nuisance output; он исправлен до integration. Полный integration/CI checkpoint и результаты фиксирует root отдельно.

## Найденный и исправленный sanitation-order gap

Binary `_predict_prob_or_value` поддерживает classifier с одной probability column без reliable `classes_`. В этом случае он пытается вывести class1 из `predict()`. Первоначальный B07 guard проверял raw `predict_proba` и final result, но между ними `np.where(isclose(pred_f,1),1,0)` превращал NaN/±inf hard labels в 0.

Independent direct probe с конечной one-column probability matrix и `predict()=+inf` действительно вернул `[0,0,0,0]` до исправления. Final source проверяет `isfinite(pred_f)` после успешной numeric conversion и до hard-label mapping; `RuntimeError` находится вне conversion-error fallback и не перехватывается как `TypeError/ValueError`. Existing finite hard-label mapping сохраняется.

Public-fit regression подтверждает этот путь для binary IRM и shared-helper IV: [before](D:/codex/Causalis/audit/block07_nuisance_fallback_before_tests.log) — **6 failed / 4 passed / 94 deselected**, 11.08s. Все шесть failures — ожидаемое отсутствие exception на NaN/±inf у двух estimators; четыре finite legacy mappings прошли. В финальном [after+neighbors](D:/codex/Causalis/audit/block07_nuisance_final_tests.log) — **191 passed, 1 existing warning, 25.75s**: 104 новых cases и 87 neighbors. Более ранние 222 passes в intermediate after log не включали финальное fallback расширение и не являются final verification checkpoint. Это проверка агента реализации; reviewer повторно просмотрел final diff, regression definitions и этот log, не запускал тот же набор заново.

## Порядок остальных guards и совместимость

Binary utility проверяет весь raw numeric `predict_proba` до выбора positive-class column или single-class repair; numeric `predict` проверяется до propensity clipping. Multi propensity utility проверяет raw matrix до class alignment, clipping и renormalization. Multi binary outcome probability проверяется до class selection, а outcome predictions — до binary clipping. Binary/multi storage boundary проверяет complete cross-fit arrays до probability transforms и сохранения predictions; multi cross-fit return отдельно проверяет assembled matrices.

Storage regression использует public `fit()` с injected cross-fit arrays, поэтому fit metadata готовится обычным путём. Independent [exact-old-method probe](D:/codex/Causalis/audit/probe_block07_storage_baseline.py) берёт две прежние storage methods из c234e64. Его [15 failures](D:/codex/Causalis/audit/block07_nuisance_storage_before_tests.log) состоят из **10 отсутствующих Inf rejections** и **5 NaN-message differences**: NaN уже отклонялся раньше. Эти пять cases нельзя считать пятью ранее отсутствовавшими validity guards. Ранние ошибки подготовительных fixtures не выдаются за library defects.

Отбрасывание invalid values в probability columns, которые не выбраны downstream, — сознательная новая policy: learner должен вернуть конечную numeric probability matrix целиком. Existing finite out-of-range policy остаётся warning+clip/normalize; в B07 она не заменяется strict probability-range rejection. Finite class0/class1 single-class semantics сохраняются. Неверная shape, complex dtype policy и metadata validation не становятся новым контрактом этого блока.

IV использует тот же helper для m, g0/g1 и r0/r1, поэтому получает raw non-finite rejection транзитивно. Его собственная assembled-prediction storage check остаётся NaN-only: B07 не следует представлять как полную переработку IV storage boundary или failed-refit lifecycle. Public-fit raw-output tests охватывают эти learner roles; finite IV inference также сравнивается с independent finite sklearn adapter.

## DiD earliest universal pre-cell

Runtime change в `PanelDataDID.att_gt_cells` ограничен первым target index. Universal policy при `include_pre_periods=True` начинает enumeration с 0; существующие правила затем требуют `target < universal_base`, наблюдаемые distinct dates, eligible comparison units и complete pairs. При base index0 никакой ложный zero-cell не появляется. Varying starts1 и сохраняет preceding-date requirement. Post-only startscohort и не меняет enumeration.

Comparison eligibility всё ещё проверяется общей функцией с base/target dates и anticipation; добавление earliest target не ослабляет support. Unsupported cells не превращаются в estimates. Анализ M/2M uses analysis-period index, включая обрезанную начальную дату; это проверяется независимыми date-pair definitions.

Новые regression references содержат реальные ненулевые placebo ATT/SE и независимые contamination derivatives разности средних, а не только повторяют enumeration. Post point estimates, full unit-score vectors, analytic inference и post-only aggregates сопоставляются по cohort/time; cell IDs закономерно могут сдвигаться. Uniform bands/joint pre-tests имеют расширенное семейство и могут меняться. Такого invariance обещания tests/report не дают. Intermediate design-table fixture issue исправлена агентом и не считается defect library.

Evidence: [B07_DID_NOTES.md](D:/codex/Causalis/audit/B07_DID_NOTES.md), финальные **43 passed** и ранее **58 existing neighbor passes** относятся к двум отдельным runs, а не вымышленному combined run.

## Scope и AST

Reviewer сравнил все top-level/class method ASTs после удаления настоящих docstrings, UTF-8 `git show` против working files. Executable differences ограничены:

| Path | Изменённые executable функции |
|---|---|
| binary `_utils.py` | `_predict_prob_or_value` |
| binary `model.py` | `IRM._store_cross_fitted_predictions` |
| multi `_utils.py` | `_predict_propensity_matrix` |
| multi `model.py` | `_predict_binary_outcome_probability`, `_fit_one_outcome_nuisance`, `_cross_fit_nuisances`, `_store_cross_fitted_predictions` |
| `panel_data_did.py` | `PanelDataDID.att_gt_cells` |
| DiD `model.py` / `refutation/diagnostics.py` | Нет; entire executable module AST равен baseline |

Все остальные функции совпадают, включая score, IF/Jacobian, estimation и aggregate formulas. Два DGP paths также имеют executable AST equality ([doc check evidence](D:/codex/Causalis/audit/block07_dgp_doc_checks.json)); их ограниченные фактические уточнения и proposed oracle API описаны в [B07_DGP_REVIEW.md](D:/codex/Causalis/audit/B07_DGP_REVIEW.md).

Остаются вне B07: sensitivity и SC08LOO, generic failed-refit lifecycle, shape/complex contracts, overflow score/IF от очень больших конечных predictions, near-boundary custom normalized-ATE policy, Gaussian-marginal propensity и latent-selected ATT API, изменение target-rate calibration behavior. Validating finite nuisance outputs не доказывает identification assumptions или finite-sample coverage и не гарантирует конечность любых downstream arithmetic operations.
