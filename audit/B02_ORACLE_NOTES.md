# B02 · ROOT-01 · Multi-treatment natural-scale oracle

Дата: 2026-10-05. Исправление в рабочей ветке `codex/correctness-roadmap`, после B01.
Область: только [multi-treatment DGP](D:/codex/Causalis/causalis/dgp/multicausaldata/base.py) и
[независимые oracle tests](D:/codex/Causalis/tests/data/test_multicausal_latent_oracles.py).
Sensitivity analysis, binary-treatment DGP и генерация ID не менялись этим исправлением.

## Методология и точная identity

Для treatment arm `k` обозначим structural location

\[
a_k(X)=\alpha_y+f_y(X)+\theta_k+\tau_k(X),\qquad U\sim N(0,1),\quad U\perp X.
\]

Natural-scale potential-outcome mean равен

\[
g_k(X)=E_U[h(a_k(X)+sU)],\qquad
\operatorname{CATE}_k(X)=g_k(X)-g_0(X),\quad s=u\_strength\_y.
\]

В прежнем коде oracle был `h(a_k(X))`, то есть mean при `U=0`. Для nonlinear links
это другая величина. Исправление интегрирует outcome mean на natural scale; знак `s`
не влияет на marginal mean вследствие симметрии Gaussian U.

Для continuous outcome `h(w)=w`, поэтому `g_k=a_k`: существующее поведение сохраняется.
Для binary outcome `h=expit` Gaussian-Hermite quadrature с 81 узлом применяется при
`|s| <= 2`. Большое `|s|` делает первоначальный integrand почти ступенчатым, поэтому
при `|s| > 2` используется другая, математически эквивалентная identity:

\[
E_Z[\operatorname{expit}(a+sZ)]
=P(L\le a+sZ)
=E_L\left[\Phi\left(\frac{a-L}{|s|}\right)\right],
\quad L\sim\operatorname{Logistic},\quad L\perp Z.
\]

Logistic-density integral считается Gauss-Legendre quadrature с 256 узлами на
`[-40,40]`. Пропущенная вероятность двух logistic tails меньше `8.5e-18`.
Это ограничение truncation error; finite quadrature error отдельно проверяется
численными reference cases и не объявляется универсально доказанной верхней границей.
Обе quadrature branches обходят узлы последовательно, используя память `O(n*K)`,
без temporary массива `n*K*nodes`. Они не используют RNG. При `include_oracle=False`
этот расчет не вызывается.

Для poisson/gamma используется тот же link clipping, что в observed draws:
`h(w)=exp(clip(w,-20,20))`. Пусть `W~N(a,sigma²)`, `sigma=|s|>0`, `L=-20`, `H=20`.
Тогда **точная математическая формула**, включая clipping tails:

\[
\begin{aligned}
E[e^{\operatorname{clip}(W,L,H)}]
={}&e^L\Phi\left(\frac{L-a}{\sigma}\right)
\\&+e^{a+\sigma^2/2}\left[
\Phi\left(\frac{H-a-\sigma^2}{\sigma}\right)
-\Phi\left(\frac{L-a-\sigma^2}{\sigma}\right)
\right]
\\&+e^H\Phi\left(\frac{a-H}{\sigma}\right).
\end{aligned}
\]

Middle term использует log-CDF и отражение в меньший tail, чтобы не вычитать два
CDF, численно равных 1. Это floating-point вычисление analytical identity, а не
заявление о произвольной точности при любой magnitude входных коэффициентов.
Формула `exp(clip(a,L,H)+sigma²/2)` неверна у границ clipping и не используется.
При `sigma=0` сохраняется обычный natural-scale link без деления на sigma.

Исторический пример `a=0,s=1,theta=[0,1,2]` теперь возвращает control mean
`exp(1/2)≈1.64872127` и CATE первого arm
`exp(1/2)*(exp(1)-1)≈2.83296780`, с numerically negligible clipping correction.

## Условия интерпретации и остающаяся проблема propensity

`g_<arm>` является `E[Y(arm)|X]` при reference law `U~N(0,1), U independent X`.
Он не является observational nuisance `E[Y|D=arm,X]`, если тот же U влияет на D.
Следовательно, при latent confounding среднее `cate(X)` по treated не автоматически
равно true ATT: для него может требоваться integrating over `U|D=arm,X`.

Аргумент `generate(..., U=vector)` переопределяет **realized latent values** для
observed treatment/outcome draws; oracle по-прежнему относится к указанному Gaussian
reference law. Код не выводит распределение U из supplied vector. Если вектор
представляет другую law или зависит от X, эти oracle не обязаны быть potential means
того alternative generating process. Это явно описано в `generate` docstring.

По согласованному scope `m_<arm>` пока сохраняет прежний `softmax(scores at U=0)`;
`m_obs_<arm>` — propensity at realized U. При latent treatment noise `m_<arm>` обычно
**не** равен `P(D=arm|X)=E_U[softmax_arm(scores+u_d*U)]`. Class docstring теперь прямо
описывает это различие. Marginal propensity требует отдельного исправления/решения API,
а не незаявленного расширения ROOT-01. До этого его нельзя использовать как true
observed-X propensity в latent-confounded benchmark.

Binary oracle остается deterministic numerical approximation. Tests включают
`|s|` от 0.6 до 10 и проверку рядом с переключением branches. Универсальная error
certificate, произвольные latent laws и extreme coefficient guards не входили
в этот блок; например, `sigma²` за пределами floating-point диапазона потребует
отдельной численной обработки. Корректность типичных finite coefficients подтверждена
independent adaptive integration, а не Monte Carlo agreement.

## Воспроизводимость и результаты

Все pytest команды выполнены repo-local `.venv\Scripts\python.exe`,
`MPLBACKEND=Agg`, `MPLCONFIGDIR=D:\codex\Causalis\audit\mplconfig`,
`-p no:cacheprovider`, writable audit basetemp. Исторические audit reproductions
не перезаписывались.

1. Исходная версия library, первоначальные 24 новых cases:
   **15 failed, 9 passed**, 21.17s.
   Evidence: [before log](D:/codex/Causalis/audit/block02_oracle_before_tests.log).
   Failing cases: nonlinear Gaussian MGF, independent adaptive logistic integration,
   clipped exponential means около `a=-21,-19,19,21`.
2. Первая implementation (GH81 для всех binary strengths), те же 24 cases:
   **24 passed**, 19.04s.
   [Intermediate log](D:/codex/Causalis/audit/block02_oracle_after_tests.log).
3. После расширения reference cases на strong latent noise GH81 недостаточен:
   **3 failed, 3 passed, 21 deselected**, 35.98s. Максимальная reported ошибка
   при `s=-10` около `0.00180402`.
   [Strong latent before log](D:/codex/Causalis/audit/block02_oracle_strong_latent_before_tests.log).
4. Финальная implementation с logistic-convolution branch:
   **28 passed**, 38.74s.
   [Final focused log](D:/codex/Causalis/audit/block02_oracle_final_tests.log).
5. Соседние existing semantics и multi scenario DGP:
   **17 passed**, 12.05s.
   [Neighbors log](D:/codex/Causalis/audit/block02_oracle_neighbors_tests.log).
   Этот прогон был до добавления strong-latent branch; последняя branch полностью
   покрыта финальным focused прогоном, а existing cases не требуют ее.

Focused test команда:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=audit\block02_oracle_test_temp tests\data\test_multicausal_latent_oracles.py
```

Neighbors команда:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=audit\block02_oracle_neighbors_test_temp tests\data\test_multicausal_generator_semantics.py tests\data\test_generators_u_and_sigmoid.py tests\data\test_generators_semantics_and_categorical.py tests\data\test_effect_scale_and_propensity_columns.py tests\scenarios\multi_unconfoundedness\test_dgp_gamma_26.py tests\scenarios\multi_unconfoundedness\test_dgp_binary_26.py tests\scenarios\multi_unconfoundedness\test_dgp_multi_dml_cx_26.py
```

Дополнительный deterministic probe сравнивает binary branch с independent
`scipy.integrate.quad(expit(a+s*z)*norm.pdf(z), -12, 12)` на 23 locations
`linspace(-0.6,1.6,23)`, `epsabs=epsrel=1e-13`:

| sigma | Maximum absolute error |
|---|---:|
| 0.6 | 4.44e-16 |
| 1.5 | 1.33e-15 |
| 2 | 3.97e-12 |
| 2.00001 | 1.12e-14 |
| 3 | 1.02e-14 |
| 5 | 9.99e-15 |
| 10 | 8.77e-15 |

Raw evidence: [quadrature errors](D:/codex/Causalis/audit/block02_oracle_quadrature_checks.log).
Reproduction: [probe script](D:/codex/Causalis/audit/block02_oracle_quadrature_probe.py),
запускается через `.venv\Scripts\python.exe` из repo root.
Это измеренная accuracy конкретных reference cases. Финальные tests требуют
binary absolute error <= `2e-9` и CATE <= `4e-9`, clipped exp relative error
<= `2e-11`, analytic unclipped-regime MGF relative error <= `2e-13`.
Zero-latent behavior, sign symmetry, heterogeneous effects, supplied-U reference-law
semantics и observed draws equality при `include_oracle` on/off также проверяются.

Source/tests готовы для root integration и commit. Subagent не stage/commit/push.
