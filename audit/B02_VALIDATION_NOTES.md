# B02: ROOT-02 / ROOT-03 — числовые контракты

Дата: 2026-10-05. Рабочая ветка: `codex/correctness-roadmap`.
Этот блок проверяет входные данные; sensitivity analysis не изменялся.

## Исправление

- `CausalData` отвергает Infinity / -Infinity в числовых ролях до создания нормализованного DataFrame. `IVCausalData` наследует эту проверку для outcome / confounders; инструмент остаётся строго бинарным.
- `CausalData`, `IVCausalData` и `MultiCausalData` отвергают complex dtype в outcome, covariates, treatment и instrument до приведения к float или вычисления fingerprint. Нулевая imaginary часть не делает complex dtype допустимым.
- `PanelDataSCM` отвергает бесконечные outcomes после штатного `pd.to_numeric`, в том числе строки `inf` / `-inf`.
- `PanelDataDID` / `PanelDataSCM` отвергают complex outcomes; DID также отвергает complex covariates. Бинарные treatment columns проверяются на complex как в native complex dtype, так и при mixed real/complex значениях в object dtype. Это предотвращает `ComplexWarning`, потерю imaginary части и утечку `TypeError` из `astype(int)`.
- Docstrings входных контрактов теперь явно ограничивают данные конечными вещественными значениями. Формат хранения, порядок колонок и доступные параметры не изменились.

Изменённые source files:

1. `causalis/data_contracts/causaldata.py`
2. `causalis/data_contracts/iv_causal_data.py`
3. `causalis/data_contracts/multicausaldata.py`
4. `causalis/data_contracts/panel_data_did.py`
5. `causalis/data_contracts/panel_data_scm.py`

Новый regression module: `tests/data/test_numeric_contract_boundaries.py` — 65 случаев. Все invalid-input tests используют отдельные реальные DataFrames и проверяют отклонение данных; accepted-input tests проверяют сохранение значений и отсутствие изменения исходного frame.

## Воспроизведение и проверки

| Проверка | Результат | Evidence |
|---|---:|---|
| Первые 60 regression cases до source fix | **44 failed / 16 passed**, 8.27 s | `block02_validation_before_tests.log` |
| Те же 60 после source fix | **60 passed**, 5.39 s | `block02_validation_after_tests.log` |
| Эти regressions + 82 существующих tests числовых контрактов | **142 passed**, 12.38 s | `block02_validation_neighbors_tests.log` |
| Дополнительные object-complex treatment cases до их guard | **2 failed**, 7.63 s; наружу выходит `TypeError` | `block02_validation_object_before_tests.log` |
| Финальные 65 regressions + 82 существующих tests | **147 passed**, 14.96 s | `block02_validation_final_tests.log` |

44 baseline failures включают как реально принятые invalid данные (12 случаев Infinity), так и complex cases с неверным diagnostic / lossy conversion. Некоторые complex treatment inputs и раньше отвергались; новый контракт гарантирует явный `ValueError` с ролью/именем колонки до complex-to-real conversion. Эти 44 случая не являются 44 независимыми дефектами.

Каждый запуск использовал `.venv/Scripts/python.exe` (Python 3.12.14), `MPLBACKEND=Agg`, `MPLCONFIGDIR=D:\codex\Causalis\audit\mplconfig`, `-p no:cacheprovider` и отдельный writable `--basetemp`. Категория `ComplexWarning` проверяется по имени, без зависимости tests от `numpy.exceptions` (доступного только в новых NumPy).

Финальный PowerShell command:

```powershell
$env:MPLBACKEND = 'Agg'
$env:MPLCONFIGDIR = 'D:\codex\Causalis\audit\mplconfig'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider `
  --basetemp=audit\block02_validation_final_test_temp `
  tests\data\test_causaldata_numeric_df.py `
  tests\data\test_causaldata_new_features.py `
  tests\data\test_causaldata_robustness_issues.py `
  tests\data\test_causaldata_user_id.py `
  tests\data\test_causaldata_validation_and_x_property.py `
  tests\data\test_iv_causal_data.py `
  tests\data\test_panel_data_scm.py `
  tests\data\test_panel_data_did.py `
  tests\data\test_numeric_contract_boundaries.py
```

Baseline command использовал только новый regression module и `--basetemp=audit\block02_validation_before_test_temp`; дополнительные object-treatment случаи запускались с `-k complex_treatment_in_object` и `--basetemp=audit\block02_validation_object_before_test_temp`.

## Совместимость и границы

- Finite nullable `Float64` / `Int64`, nullable binary `boolean`, обычные int/float/bool сохраняются. Panel contracts по-прежнему принимают numeric strings для y / covariates; cross-sectional contracts по-прежнему требуют numeric dtype.
- Identifier columns не получают новых числовых ограничений. Существующие правила missing IDs, уникальности и panel support сохраняются.
- Ранее допустимые Infinity и complex analysis values теперь вызывают `ValueError`. Данные не заменяются, не обрезаются и не приводятся silently к реальной части.
- Полная матрица версий Python / pandas / NumPy и весь estimator suite в этом scoped блоке не прогонялись. Финальные 147 проверок покрывают data contracts и входные compatibility cases.
- Отдельный finite guard на estimator outputs не внедряется в это исправление. Он требует estimator-specific политики, поскольку конечные входы могут приводить к численной degeneracy / overflow в расчётах.
- Публичные DataFrame у cross-sectional contracts остаются mutable. Изменение такого frame после construction может нарушить прошедший валидацию контракт; immutable snapshots PanelDataDID / PanelDataSCM продолжают использоваться как раньше. Этот блок не меняет lifecycle или cache semantics.
- Никакие sensitivity files / tests, shared utilities или DGP не редактировались. Исторические audit JSON не перезаписывались. Git stage/commit/push выполняет основной агент.

`git diff --check` для этих source files и нового regression module проходит; предупреждения Git про LF → CRLF отражают локальную Windows-конфигурацию.
