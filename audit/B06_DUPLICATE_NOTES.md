# B06: безопасный screening одинаковых колонок

База блока — `bf2ea87534e4eaf82266cb61d905b7e876cc2e1d`. Этот подблок меняет только поиск одинаковых значений в `CausalData`, `IVCausalData`, `MultiCausalData` и общий helper уже существовавшего screening в `RctCausalData`. Statistical estimators, row selection, validation ролей и sensitivity не менялись. Commit/push и общий sequential benchmark выполняет главный агент; этот файл не объявляет неподтверждённый SHA или измеренное ускорение.

## Изменение

В [CausalData._column_value_signatures](D:/codex/Causalis/causalis/data_contracts/causaldata.py:405) при более чем 64 строках сначала fingerprint вычисляется для 64 равномерно расположенных позиций. Колонки с единственным sampled fingerprint не требуют полного хеширования. Совпавшие samples требуют full-column fingerprints, а совпавшие full fingerprints требуют точного сравнения. Для 0–64 строк сохраняется один full fingerprint без повторного hashing.

Общие функции находятся в [_duplicate_columns.py](D:/codex/Causalis/causalis/data_contracts/_duplicate_columns.py:11). Точный verdict использует прежнюю `np.array_equal` над object values, но выделяет boxed arrays максимум на 65 536 позиций каждой колонки одновременно. При различии последнего значения после границы блока проверка не завершится ложным равенством. Порядок строк и значения индекса на verdict не влияют, как и раньше.

Для CausalData/IV/Multi после screening retained candidates сохраняют исходный глобальный порядок колонок. Это существенно: простая итерация по sampled groups меняла бы первый reported duplicate, когда группы пересекаются по порядку появления. RCT исторически использует вложенные sampled/full groups; его порядок сохранён отдельно. Внутренний `screen=False` предотвращает повторный screening уже отобранной RCT группы. `ThreadPoolExecutor.map` по-прежнему сохраняет порядок full hashes; размер worker pool определяется размером таблицы кандидатов.

## Сохранённая семантика и границы

- Numeric/bool fingerprints по-прежнему основаны на float64 copy; `0.0` и `-0.0` canonicalized одинаково. Numeric equality разных dtypes, включая nullable numeric и bool после существующей нормализации, сохраняется.
- Float64 rounding используется только для screening. Разные integers выше `2**53`, которые имеют одинаковый float64 fingerprint, различаются object equality; real hash collision также не превращается в duplicate verdict.
- Optional object/string/datetime user ID сохраняет историческую отдельную fingerprint category. Например, object ID `[10,11,...]` и numeric outcome с такими же Python-equal значениями **по-прежнему разрешены**, если ID уникален. Этот подблок не расширяет прежнее значение «dtype-agnostic» между numeric/object categories. Рекомендация для будущей отдельной API правки — явно определить, должны ли одинаковые object/numeric IDs запрещаться; не менять это незаметно в performance patch.
- Число outcome/treatment/instrument/confounder колонок, их роли, normalized dtypes, returned frame/index и input mutation behavior сохраняются. Ошибки для multiple duplicates совпадают с прежним алгоритмом каждого контракта.
- Аналитические колонки contracts уже ограничены real numeric/bool. Helpers предназначены для validated contract columns, а не для arbitrary object/object tables с контекстно зависимой pandas factorization.
- Почти одинаковые колонки с совпавшими samples продолжают полностью хешироваться. Speedup для такого случая не гарантируется; 64-position overhead может добавить небольшое время. Full hashes по-прежнему могут выделять O(n) numeric arrays для кандидатов; memory boxing точного сравнения ограничен, но общий peak memory не объявляется O(1).

## Проверка

Новые [test_duplicate_screening.py](D:/codex/Causalis/tests/data/test_duplicate_screening.py) содержат **71 case**:

| Случаи | Количество | Что подтверждают |
|---|---:|---|
| Public contracts × 10 adversarial вариантов | 40 | int/float, nullable, signed zero, bool, большие integers, unsampled difference, object/datetime ID, duplicate/non-monotonic index, input не мутируется |
| Пересекающиеся sampled groups | 4 | Прежняя первая ошибка отдельно для RCT и остальных contracts |
| Принудительные collisions × duplicate/различные значения | 8 | Точный verdict после sample/full hash collision |
| Distinct continuous columns | 4 | Все hashing calls имеют только 64 позиции, full columns не хешируются |
| Размеры 0/1/64/65/257 | 5 | Нет повторного full hashing для коротких таблиц |
| Chunk boundaries × equality/различие | 8 | 65 535/65 536/65 537/131 073 строк и точное различие последнего большого integer |
| Разные lengths | 1 | Exact helper не объявляет такие колонки равными |
| Принудительный parallel full hash | 1 | Порядок candidate groups сохраняется |

Public reference временно заменяет новые candidate signatures независимым прежним full-column fingerprint grouping и заменяет equality каждого contract независимым full-column `np.array_equal(...dtype=object)`. Сравнивается complete stored DataFrame или complete error string, затем original input frame. Это reference equivalence проверки, а не Monte Carlo inference/coverage claim.

Итог focused suite: **156 passed, 0 failed, 0 warnings, 15.94 s** — 71 новых case плюс 85 existing соседних case. Повторный focused run оправдан усилением reference equality; counts двух runs не суммируются. Raw evidence: [block06_duplicates_tests.log](D:/codex/Causalis/audit/block06_duplicates_tests.log), [block06_duplicates_result.json](D:/codex/Causalis/audit/block06_duplicates_result.json).

Команда из repo, `MPLBACKEND=Agg`, `SKIP_DOCS_BUILD=true`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/data/test_duplicate_screening.py tests/data/test_causaldata_new_features.py tests/data/test_causaldata_robustness_issues.py tests/data/test_causaldata_user_id.py tests/data/test_causaldata_validation_and_x_property.py tests/data/test_iv_causal_data.py tests/data/test_rct_causal_data.py -p no:cacheprovider --basetemp=audit/block06_duplicates_test_temp_final
```

Общий B06 integration, version matrix и timing/peak-memory benchmark в этот focused результат не входят. Один mock call-count case подтверждает удаление full hashing на distinct columns, но сам по себе не измеряет latency.
