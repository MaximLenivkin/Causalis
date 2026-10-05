# B02: идентификаторы, строки выбросов и allocation weights

Дата: 2026-10-05. Ветка: `codex/correctness-roadmap`. Подзадача ROOT-05/06/07; sensitivity analysis не изменялся.

Исправлено:

- **ROOT-05 (P2):** `causalis/dgp/base.py` больше не обрезает UUID до пяти hex-символов. `_random_ids()` сохраняет полный UUID4 `.hex` и перегенерирует идентификатор при совпадении внутри текущего набора. `deterministic_ids=True` использует прежний алгоритм и прежний RNG; random UUID не зависит от `random_state`. Случайные ID теперь имеют длину 32 вместо 5 символов: потребителям нельзя полагаться на прежнюю длину. Публичный контракт по-прежнему получает string ID. Гарантия уникальности ограничена генерируемым набором.
- **ROOT-06 (P2):** `outcome_outliers(..., return_rows=True)` сохраняет позиции до удаления missing rows и выбирает исходные строки через `iloc`. Повторяющиеся labels исходного pandas index сохраняются, обычные строки с таким же label больше не попадают в ответ, а выбросы не размножаются. Формулы IQR/z-score, summary и прежний порядок групп сохранены.
- **ROOT-07 (P2):** `assign_variants_df()` отвергает NaN, ±Infinity, non-real/non-numeric и boolean weights до hashing. Допустимы finite `numbers.Real` (включая NumPy integer/float) с прежними ограничениями на знак и суммарную coverage. Веса не нормализуются. Strings/complex/None/pandas.NA теперь дают ясный `ValueError`; bool теперь явно запрещён. Hash, sorting variants, boundaries и assignments для допустимых весов не менялись. `Decimal`, не зарегистрированный как `numbers.Real`, также отвергается; annotation API остаётся `Dict[str, float]`.

## Проверки

Добавлены `tests/data/test_dgp_user_ids.py`, `tests/shared/test_split.py`; расширен `tests/statistics/test_outcome_outliers.py`.

- UUID: controlled distinct UUID с одним общим five-character prefix воспроизводят старую коллизию детерминированно через публичный `generate_rct(..., return_causal_data=True)`. Отдельно принудительная полная UUID-коллизия проверяет retry; deterministic mode остаётся unique/reproducible и не вызывает uuid4.
- Outliers: binary/MultiCausalData × IQR/z-score; все 20 строк имеют один index label, четыре действительных выброса должны вернуться ровно один раз с полными исходными columns/index, без изменения входных данных.
- Split: invalid weights отвергаются до hashing; проверены старые zero/negative/coverage ограничения, half-open границы и partial coverage, zero arm, duplicate entity IDs, custom output column, отсутствие мутации входа, full coverage и независимость от порядка mapping. Missing assignment проверяется через `isna()`, поскольку pandas 3 string inference может представлять исходный `None` как NaN.

| Проверка | Результат | Доказательство |
|---|---|---|
| Тот же targeted suite до source fixes | 15 failed, 10 passed, 13.13 s | `block02_utilities_before_tests.log` |
| Targeted suite после fixes | 25 passed, 8.11 s | `block02_utilities_after_tests.log` |
| Neighbors: ancillary leakage, CausalData user IDs, rich DGP | 9 passed, 9.51 s | `block02_utilities_neighbors_tests.log` |

Это 34 scoped passing cases; full suite и benchmark не запускались в этой подзадаче. Before failures включают consistent exception/message hardening для уже отвергавшихся Infinity, а не 15 независимых bugs.

Команды из repo root, через обязательный `.venv`:

```powershell
$env:MPLBACKEND='Agg'
$env:MPLCONFIGDIR='D:\codex\Causalis\audit\mplconfig'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=audit\block02_utilities_test_temp tests\data\test_dgp_user_ids.py tests\statistics\test_outcome_outliers.py tests\shared\test_split.py
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=audit\block02_utilities_test_temp tests\data\test_rct_ancillary_no_leakage.py tests\data\test_causaldata_user_id.py tests\scenarios\unconfoundedness\test_dgp_rich.py
```

Исторические audit reproductions/results не перезаписывались. Ничего не stage/commit/push из подзадачи; интеграция и roadmap остаются у root.
