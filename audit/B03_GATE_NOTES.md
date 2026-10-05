# B03 — численная устойчивость GATE / GATET

Finding DML-09 P2. Изменён только `causalis/scenarios/gate/model.py`; новые regression tests — [test_gate_numerical_stability.py](D:/codex/Causalis/tests/inference/test_gate_numerical_stability.py).

## Независимая формула

Для saturated no-intercept regression на disjoint group indicators `beta_g=mean(phi_g)`, leverage каждой строки `h_ii=1/n_g`. HC0 variance group mean равна `sum((phi_i-beta_g)^2)/n_g^2`; HC1 умножает её на `n/(n-k)`, HC2 делит каждый residual square на `1-1/n_g`, HC3 — на квадрат этого множителя. Это прямой sandwich расчёт с centered residuals, независимо от production `bincount` implementation.

Старый compact path вычислял SSE как `sum(phi²)-sum(phi)²/n_g`. При `phi=1e8±1` теряются единицы variation, а SE становилась 0 вместо 0.1. Другие порядки/значения дают negative SSE и RuntimeError. Новый path сначала вычисляет group means, затем `bincount` квадратов центрированных отклонений. Сложность O(n+k) и compact partition сохраняются.

У GATET эта unstable formula использовалась только для descriptive `std_phi`; covariance уже использовала centered ATT moment residuals. Исправлена descriptive SSE, поскольку она могла дать неверный spread или остановить корректную inference через RuntimeError. Формула GATET covariance не менялась.

## Evidence

- До source fix: **20 failed**, 13.27 s, `block03_gate_before_tests.log`.
- После source fix первый run: **64 passed, 4 failed**, 17.64 s; все 4 failures были опечаткой нового теста (`GateContrastEstimate.value`, а не nonexistent `estimate_diff`), после успешной covariance assertion. Исправлен test field, библиотечный код после этого не менялся. Сохранён `block03_gate_after_tests.log`.
- Финальный run новых tests + existing GATE/GATET: **68 passed**, 15.12 s, `block03_gate_final_tests.log`.

```powershell
$env:MPLBACKEND='Agg'
$env:MPLCONFIGDIR='D:\codex\Causalis\audit\mplconfig'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=audit\block03_gate_final_test_temp tests\inference\test_gate_numerical_stability.py tests\inference\test_irm_gate.py tests\inference\test_irm_gatet.py
```

Cases: HC0/1/2/3, shifts +1e8/-1e8/+1e12, unequal/interleaved groups, public result covariance/contrast/p-value, permitted treated-only GATET with overlap warning. Публичный test использует известные canonical DR nuisance arrays и полноценный CausalData/id contract; не зависит от качества обученного learner.

## Ограничения

Нет обещания точности при любых extreme IEEE values: mean summation и input representability по-прежнему ограничены double precision; squared residuals могут переполниться. Здесь исправлено subtractive cancellation, не estimator-wide finite-output policy. Performance benchmark не запускался: алгоритмическая сложность сохранена, measured speed claim не делаем. Scope не затрагивает sensitivity.
