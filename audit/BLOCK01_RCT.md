# B01 — Newcombe CI и параметры RCT

Дата: 2026-10-05. Ветка: `codex/correctness-roadmap`.

## Scope

- SC-05/P1: заменить subtraction Wilson endpoints на Newcombe hybrid score interval без continuity correction.
- SC-10/P2: explicit allowed-set validation для `ci_method` и `se_for_test`.
- Согласовать function docstring с точной CI формулой и независимым выбором z-test p-value.
- Source/test changes только `causalis/scenarios/classic_rct/inference/conversion_ztest.py` и `tests/inference/test_conversion_z_test.py`.
- Sensitivity analysis и остальные estimators не затрагиваются.

## Проверка

Independent reference: `statsmodels.stats.proportion.confint_proportions_2indep(..., method='newcomb', compare='diff')`. Cases: исходный counterexample7/34vs1/34, ordinary rates, zero-success arm, all-success arm, rare events, unequal sample sizes; alpha.01/.05/.10. Дополнительно group-swap sign symmetry и invalid options. Existing RCT tests проверяют сохранённые p/relative/Wald paths.

## Результат

**Завершён. Commit:** `bd8a2be2dc363400a572c6d369cda887fb17aad9` — `fix(rct): correct Newcombe intervals and reject invalid methods`. Checkpoint аудита/плана: `2c26cee`.

- [Newcombe implementation](D:/codex/Causalis/causalis/scenarios/classic_rct/inference/conversion_ztest.py:180) использует one-sided Wilson distances через `np.hypot`. Убран старый endpoint subtraction.
- Недопустимые `ci_method`/`se_for_test` отвергаются с понятным `ValueError` до доступа к данным.
- Docstring содержит точную hybrid formula без continuity correction и поясняет независимый выбор CI/p-value methods.
- [Regression tests](D:/codex/Causalis/tests/inference/test_conversion_z_test.py:180) сверяются с независимым statsmodels implementation на7cases×3alpha; проверяют swap symmetry и6invalid option cases.

| Проверка | Результат | Лог |
|---|---|---|
| Новые tests до source fix | 27failed,9passed; подтверждены обе ошибки | block01_before_tests.log |
| Conversion tests после fix | **36passed**,10.01с | block01_after_tests.log |
| Соседние DiffInMeans/t-test/permutation/SRM | **31passed**,10.90с | block01_neighbors_tests.log |
| Git diff whitespace check | Пройден; raw evidence logs intentionally exempt | git diff --check |

Итого **67passing cases** в scoped проверках. Полный968-case suite повторно не запускался: изменение локально для RCT, полный baseline и известный unrelated CUPED failure сохранены в audit. Sensitivity files/tests не изменялись и не переисполнялись.

## Команды

Из `D:\codex\Causalis`, `.venv\Scripts\python.exe`:

```powershell
$env:MPLBACKEND='Agg'
$env:MPLCONFIGDIR='D:\codex\Causalis\audit\mplconfig'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests\inference\test_conversion_z_test.py
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=audit\block01_test_temp tests\inference\test_diff_in_means.py tests\inference\test_ttest.py tests\inference\test_welch_permutation_t_test.py tests\scenarios\rct
```

## Изменившееся поведение и ограничения

Default absolute CI теперь действительно Newcombe hybrid. На audit case7/34vs1/34 он изменился с[−.04566046,.36277297] на[.01892144,.34036869]. Pooled/unpooled z-test и relative/Wald formulas не менялись. Пользовательские опечатки в enum теперь ошибка, прежний silent fallback прекращён.

Source math/reference checks подтверждают заявленную процедуру; новая собственная coverage Monte Carlo не проводилась. Все rare/boundary cases остаются ограничены поддерживаемым CausalData input contract. Опубликованные site/API ещё нужно синхронизировать при release; handoff автору docs содержит формулу и version caveat. Локальный commit не означает upstream release или remote backup.

Работа остановлена на границе B01. Следующий blockB02 стартует после нового запроса пользователя; инструкции в NEXT_SESSION.md.
