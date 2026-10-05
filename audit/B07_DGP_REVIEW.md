# B07 · DGP: уточнение документации и план Gaussian-reference oracles

Дата: 2026-10-06, Europe/Moscow. Исходный checkpoint: `c234e647e010f5d8bfb805af7ece61392e327537`.

**В B07 исправлены только фактические формулировки в двух DGP docstrings.** Marginal propensity API, новые ATT targets и calibration behavior остаются отдельным B08/API follow-up. Реализация генератора, публичные параметры, имена и значения колонок не менялись. Sensitivity analysis не затрагивался.

## Что подтверждено

Для reference law `U ~ N(0,1), U independent X` обозначим

\[
p_k(x,u)=\operatorname{softmax}_k\{a(x)+b u\},\qquad
\mu_k(x,u)=h\{\ell_k(x)+s u\}.
\]

Текущие `m_<arm>` равны `p_k(x,0)`, а `m_obs_<arm>` — `p_k(x,U_i)`. Настоящий observed-X reference propensity равен

\[
q_k(x)=\int p_k(x,u)\phi(u)\,du.
\]

В общем случае `q_k(x) != p_k(x,0)`. Это уже явно описано после B02, поэтому отсутствие `q` здесь считается запланированным расширением oracle API, а не вновь исправленной ошибкой кода. Если все latent slopes одинаковы, общий softmax shift сокращается и различия нет.

Outcome columns после B02 соответствуют `g_k(x)=integral mu_k(x,u) phi(u) du` и `cate_k(x)=g_k(x)-g_0(x)`. Они не равны observational regression `E[Y|D=k,X=x]` при latent confounding. Для ATT важна другая law:

\[
\operatorname{ATT}_k=
\frac{E_X\!\left[\int\{\mu_k(X,u)-\mu_0(X,u)\}p_k(X,u)\phi(u)\,du\right]}
     {E_X[q_k(X)]}.
\]

Среднее `cate_k(X)` по treated оценивает `E[cate_k(X)|D=k]`, которое вообще не равно этой ATT. Это непосредственно следует из Bayes weighting: `U|D=k,X` имеет density `p_k(X,u) phi(u)/q_k(X)`. Для linear additive outcomes latent shift сокращается в structural contrast; тогда такого различия может не быть. Текущий scenario test `test_gamma_26_oracle_atte_is_separated_from_ate_and_shares_stay_calibrated` использует нулевые latent strengths, поэтому его ATT interpretation допустима. Нового неверного `true_ATT` обещания в runtime DGP docstrings не найдено.

Supplied `U` — vector реализованных значений, распределение которого генератор не устанавливает. Gaussian-reference `g` не превращается автоматически в oracle иной latent law. Если supplied U зависит от X или имеет другое распределение, для новой law нужна отдельная спецификация; переходить к эмпирическому распределению vector без API решения нельзя.

## Независимое воспроизведение

[block07_dgp_probe.py](D:/codex/Causalis/audit/block07_dgp_probe.py) использует отдельные SciPy `softmax` и adaptive `quad`, без вызова внутренних marginal outcome helpers. Числа и наблюдения сохранены в [block07_dgp_probe_result.json](D:/codex/Causalis/audit/block07_dgp_probe_result.json).

Воспроизведение:

```powershell
.\.venv\Scripts\python.exe audit\block07_dgp_probe.py
```

No-X, три arms, `alpha_d=[0,0,0]`, `u_strength_d=[0,1,1]`, gamma log-link, `u_strength_y=1`, `theta=[0,.7,-.4]`, seed731:

| Величина | Arm0 | Arm1 | Arm2 |
|---|---:|---:|---:|
| Current `m` at U=0 | 0.3333333333 | 0.3333333333 | 0.3333333333 |
| Gaussian-marginal q, adaptive reference | 0.3601605153 | 0.3199197423 | 0.3199197423 |
| Generated shares, n30000 | 0.3605666667 | 0.3135333333 | 0.3259000000 |
| Marginal g, adaptive reference | 1.6487212707 | 3.3201169227 | 1.1051709181 |
| Treated average of reported CATE | — | 1.6713956520 | -0.5435503526 |
| Selection-weighted population ATT | — | 2.1053345087 | -0.6846705107 |

Generated shares — вспомогательное Monte Carlo наблюдение, не эталон точности. Adaptive integrations на `[-12,12]`, `epsabs=epsrel=1e-12`; Gaussian tail probability за этими границами <4e-33. Для clipped exponential mean верхняя граница integrand multiplier `exp(20)` делает пропущенный tail contribution <2e-24; это отдельная оценка truncation, не универсальный certificate numerical quadrature error. Не выполнялись broad tests или изменения runtime.

## Фактическое уточнение target_d_rate

`_calibrate_alpha_d` решает sample-X задачу при `U=0`:

\[
\frac1n\sum_i p_k(X_i,0;\alpha)\ \text{приближается к}\ t_k.
\]

Он не калибрует `mean_i q_k(X_i)` и не рассчитывает population-X expectation. Даже без латентной компоненты конечное число iterations и sample-X approximation не дают точной гарантии population rate; realized treatment frequencies дополнительно случайны.

С latent strength `[0,2,2]`, target `[.2,.3,.5]`, no-X: mean current `m` совпадает с target, но Gaussian population rates `[.2997287005,.2626017373,.4376695622]`; в draw n30000 shares `[.3022666667,.2591333333,.4386]`. Разница не исчезает с ростом n: в no-X примере нет X-sampling approximation. Ранее `approximate when u_strength_d != 0` не объясняло эту систематическую разницу.

В [base.py](D:/codex/Causalis/causalis/dgp/multicausaldata/base.py) parameter и Notes теперь явно описывают sample-X / U=0 calibration, отсутствие integration over latent noise и отсутствие population-rate guarantee. В [scenario dgp.py](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/dgp.py) gamma/binary wrappers уточняют sample-average probabilities и случайность realized shares. Их latent strengths равны нулю; менять реализацию calibration сейчас не требуется. High-level functional wrapper не предоставляет latent-strength arguments, поэтому его generic target wording не объявляется latent-calibration дефектом.

## Фактическое уточнение Gaussian copula

Scenario docstrings раньше приписывали Toeplitz correlation `0.3^|i-j|` observed X. Эта матрица задаёт latent Gaussian Z; marginal transforms, discrete thresholding и clipping могут изменить observed Pearson correlations. Определение Gaussian copula связывает R с multivariate-normal distribution, что подтверждается [официальной документацией statsmodels](https://www.statsmodels.org/stable/generated/statsmodels.distributions.copula.api.GaussianCopula.html).

Independent conditional-normal integration для двух Bernoulli(.5) marginals и latent correlation .3 даёт observed population Pearson correlation `0.1939733680`, а actual helper draw n200000 seed731 — `0.1975802948`. Sample number служит иллюстрацией и не заменяет population reference. Docstrings обеих scenario функций теперь используют Corr(Z), различая его и Corr(X).

## Проверка doc-only scope

[block07_dgp_doc_check.py](D:/codex/Causalis/audit/block07_dgp_doc_check.py) сравнивает executable AST после удаления настоящих module/class/function docstrings. `git show` читается явно как UTF-8. Оба пути совпадают с checkpoint c234e64; issues0. Evidence: [block07_dgp_doc_checks.json](D:/codex/Causalis/audit/block07_dgp_doc_checks.json). Отдельные tests, которые повторяли бы prose, не добавлялись.

## Конкретное предложение B08, не реализовано

Совместимый минимальный вариант: opt-in `include_marginal_propensity=False` у generator; при `include_oracle=True` и включении option добавлять `m_marginal_<arm>`. Existing `m_<arm>` и `m_obs_<arm>` сохраняют имена и значения. Gaussian reference law должен быть явно указан в документации, включая supplied U caveat. Не определять новые колонки как propensity иной supplied-U law.

Опция должна быть явно additive и без RNG draws. Default frame schema и generated observations остаются прежними. Сочетание `include_oracle=False` с enabled marginal option требует явного решения контракта (предпочтительно reject conflicting flags). Калибровку actual Gaussian-marginal rates стоит вводить отдельным explicit mode, сохраняя default U=0 mode: новая колонка сама по себе не меняет D generation.

Узел marginal integration ограничить памятью O(n*K), последовательно обходя quadrature nodes или blocks. Fixed 81-node GH для произвольных latent slopes не имеет доказанной достаточной точности: при большой разности slopes softmax может становиться почти ступенчатым. Сначала нужен independent adaptive reference, затем проверяемый convergence/accuracy policy; можно начать с медленного opt-in reference implementation. Public certificate и произвольные latent laws не обещать.

Validation plan:

1. Zero/equal-slope cancellation, sign reversal, common-shift invariance, arm permutation, K2/K3/K5 и independent adaptive Gaussian integration на varying X.
2. Latent slopes 0/.1/1/2/5/10/50, asymmetric intercepts и переходы между dominant arms; absolute probability error, bounds[0,1] и row sum1. Для adaptive reference сохранять error estimate и convergence warnings.
3. Default vs enabled marginal option: identical generated D/Y/X, RNG state и existing columns; no extra work when oracle disabled; explicit flags/type/shape/finite contract.
4. Supplied U under non-Gaussian/dependent laws: reference q сохраняет Gaussian meaning; `m_obs` описывает realized latent values. Новые natural-law targets требуют отдельного API.
5. Проверить empirical-X calibration и population-X distinctions; новый mode actual marginal calibration нельзя объявлять точным population-X target.
6. ATT extension — отдельно от q: добавить target, который интегрирует `structural_delta * p_k`; существующий CATE не переименовывать. Reference checks для zero-latent, linear common-shift cancellation, nonlinear selected-U case выше.
7. `_draw_multinomial` при редких/малых samples делает retries и может принудительно вставлять отсутствующие arms. Returned D тогда не является строго независимым multinomial draw с probabilities m_obs. Перед точными small-n oracle claims отдельно выбрать conditional-sampling policy и documentation, сохраняя backward compatibility. В данном n30000 примере все arms присутствуют при первом draw; редкие-arm retry mechanism не служит объяснением различий таблицы.

Для численного reference используются [SciPy quad](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.quad.html), а возможный Gaussian quadrature backend описан в [roots_hermitenorm](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.roots_hermitenorm.html). Это источники алгоритмов integration; приведённые target identities выведены из law of total expectation/Bayes weighting для конкретной structural DGP.
