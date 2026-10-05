# B02 — balance separation

Дата: 2026-10-05. ROOT-04 + DML-05 — одна сгруппированная проблема.

Shared balance теперь возвращает signed infinity при нулевой pooled variance и различающихся means, zero при одинаковых constants, NaN при недоступных moments. Конвенция denominator остаётся sqrt((s0²+s1²)/2); исправлено прежнее неточное обозначение Cohen's d.

Binary/multi weighted diagnostics включают Inf в maximum и fraction violations, сравнения и общий summary получают RED и pass=False. NaN остаётся недоступной статистикой; entirely unavailable summary имеет NaN metrics, pass=False. Existing finite-value threshold rules не менялись. Это диагностика наблюдаемого баланса, а не доказательство unconfoundedness.

Regression tests используют публичный report API с вручную заданными propensity predictions: ATE/ATTE, normalize true/false, only separated/mixed balanced features, multi pairwise pass/fail. Дополнительно signed shared separation, identical constants и unavailable moments. Existing balanced reports/Love plot проверены соседними tests.

| Проверка | Результат | Evidence |
|---|---|---|
| 22 regression cases до source fix | 21 failed, 1 passed, 13.13 s | block02_balance_before_tests.log |
| Regressions + shared/binary/multi balance + Love plot | 50 passed, 3 existing normalize_ipw warnings, 14.43 s | block02_balance_after_tests.log |

```powershell
$env:MPLBACKEND='Agg'
$env:MPLCONFIGDIR='D:\codex\Causalis\audit\mplconfig'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=audit\block02_balance_test_temp tests\refutation\test_balance_separation.py
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=audit\block02_balance_test_temp tests\refutation\test_balance_separation.py tests\statistics\test_confounders_balance.py tests\refutation\test_uncofoundedness_balance.py tests\refutation\test_uncofoundedness_balance_extras.py tests\refutation\test_multi_unconfoundedness_diagnostics.py tests\refutation\test_love_plot.py
```

Sensitivity modules/formulas/tests не менялись. Сохраняется прежняя near-zero variance tolerance в DML diagnostics; изменение этого численного правила требует отдельного scale-invariance review.
