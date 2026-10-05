# B03 / DML-01: ratio influence function для multi-arm ATTE

Дата: 2026-10-05. Исправление P1 исходного `DML_REVIEW.md`, без изменений sensitivity implementation. Исторический аудит относится к `ffe2c356c115f335b74b2f10117e19fe15585d46`; этот файл описывает новую реализацию.

## Что исправлено

Для каждого active arm k теперь `psi_a_k = -d_k / p_k`, а не общий `-1`. Средний Jacobian остаётся -1, поэтому point estimates сохраняются с точностью floating point. Меняются influence function, absolute SE/CI, t-statistics и p-values. В известном noiseless примере с эффектами [2, 4] и 100 наблюдениями в каждом из трёх arms прежние SE [0.1635721640, 0.3271443280] теперь равны нулю. Ошибка variance в общем случае может иметь любое направление через covariance; пример показывает завышение.

Solver поддерживает как прежний 1-D ATE Jacobian, так и отдельный n × (K−1) ATTE Jacobian. Model diagnostic payload получает additive optional `psi_a`; score diagnostics используют этот derivative для reconstruction, включая payload после сериализации через `model_dump(exclude_none=True)`. Эта contract правка и reconstruction реализованы совместно с B03 OOS направлением.

## Независимый вывод

Обозначим `r_k(X)=m_k(X)/m_0(X)` и

```text
A_ik = d_ik (Y_i − g_0(X_i)) − d_i0 r_k(X_i) (Y_i − g_0(X_i))
p_k  = E[d_k]
theta_k = E[A_k] / p_k.
```

Производная ratio functional по contamination `P_epsilon=(1−epsilon)P+epsilon delta_i`:

```text
IF_theta,ik = (A_ik − theta_k d_ik) / p_k.
```

Следовательно, canonical score имеет `psi_b_ik=A_ik/p_k`, `psi_a_ik=−d_ik/p_k`, Jacobian `J_k=E[psi_a_k]=−1` и `IF_k=−psi_k/J_k`. Замена `psi_a_ik` его средним сохраняет root, но удаляет denominator derivative. Cross-fitting и orthogonality остаются необходимыми условиями контроля nuisance error; вывод не обещает корректные intervals при произвольных learners/overlap.

Counterfactual baseline among arm-k units — второй ratio:

```text
Q_ik = d_ik g_0(X_i) + d_i0 r_k(X_i) (Y_i − g_0(X_i))
mu_0k = E[Q_k] / p_k
IF_mu,ik = (Q_ik − mu_0k d_ik) / p_k
IF_relative,ik = 100 (IF_theta,ik / mu_0k − theta_k IF_mu,ik / mu_0k²).
```

Multi baseline IF исправлен вместе с numerator IF. **Прежние multi relative intervals сами по себе не являются ещё одним найденным defect**: ошибки двух старых fixed-share IFs пропорциональны theta и mu и взаимно сокращаются в delta ratio. Исправление только numerator создало бы новую ошибку relative CI; paired correction сохраняет прежние relative results. Проверки подтверждают numerical invariance и независимо сравнивают relative IF с contamination derivative. При пропорциональных potential outcomes `Y(k)=1.2Y(0)`/`1.4Y(0)` relative effect всегда [20%,40%] и его interval вырожден, хотя absolute ATT имеет ненулевую uncertainty из-за состава treated X.

Вывод основан на собственном differentiation ratio, а canonical binary ATT score дополнительно проверен по [официальной документации DoubleML, §5.2.2.1](https://docs.doubleml.org/stable/guide/scores.html#binary-interactive-regression-model-irm). Framework assumptions/cross-fitting — [Chernozhukov et al., Double/Debiased Machine Learning for Treatment and Causal Parameters](https://arxiv.org/abs/1608.00060). Источники открыты 2026-10-05; multi-arm extension здесь получен независимо.

## Проверки

Новый файл `tests/inference/test_multi_treatment_irm_ratio_if.py` содержит 10 cases:

- Noiseless constant effects: equal/unequal arm shares × full/lightweight diagnostics, IF/absolute SE/absolute и relative CI collapse.
- Heterogeneous oracle sample: central finite differences empirical contamination всех 240 строк, theta/control mean, IF, absolute/relative SE; explicit сохранение прежнего relative interval.
- Proportional potential outcomes: ненулевая absolute SE и zero relative SE.
- Active-arm permutation плюс общий outcome shift: equivariance effects/IF/SE.
- ATE/ATTE payload shape и roundtrip; публичный score diagnostic plugin SE совпадает с estimator SE.
- Oracle IID Monte Carlo для 600 samples по n=600, probabilities [0.5,0.2,0.3], effects [2,4], independent Normal(0,1) noise, известные outcome/propensity nuisances.

Публичный fit lifecycle используется перед oracle prediction substitution для unit/property cases, чтобы изолировать inference от learner approximation. Monte Carlo использует score/solver напрямую с true nuisances; это проверка inference calibration, **не coverage study fitted ML pipeline** и не sensitivity simulation.

Monte Carlo seed4701: before-fix nominal95% coverage **[1.0,1.0]**. After-fix coverage **[0.9400,0.9433333]**, empirical SD **[0.11263054,0.09375594]**, RMS reported SE **[0.10858054,0.09509253]**, reported/empirical ratios **[0.96404174,1.01425609]**. Monte Carlo SE coverage около0.009; один DGP/seed не доказывает универсальную calibration. Raw metrics — `block03_multi_oracle_checks.log`, воспроизведение `.\.venv\Scripts\python.exe audit\block03_multi_oracle_probe.py`.

Test evidence:

| Прогон | Результат | Evidence |
|---|---|---|
| До patch, первоначальные8independentcases | 6 failed, 2 passed, 12.40s | `block03_multi_before_tests.log` |
| После score/IF patch,8new+24existing | 32 passed, 14.63s | `block03_multi_after_tests.log` |
| Первый neighbor с2новымиpayloadcases | 58 passed,1failed,20.19s | `block03_multi_neighbor_tests.log` |
| Финальный focused + neighbors | 63 passed,19.78s; включает4additional OOS integration cases другого направления | `block03_multi_final_tests.log` |
| Финальный oracle fixture refinement | 10 passed,12.61s; сохранили oracle baseline covariate и nonconstant independent X в constant-outcome case | `block03_multi_final_fixture_tests.log` |

Neighbor includes `test_multi_treatment_irm.py`, `test_multi_treatment_irm_parallel.py`, `test_multi_score_diagnostics.py`, `test_multi_unconfoundedness_diagnostics.py`, `test_multi_residual_plots.py`. Joblib test запускался с разрешёнными Windows process pipes, local basetemp. Original assertion `psi_a=-ones` заменён на arm-specific derivative; independent finite-difference и coverage tests не опираются на прежний assertion.

Последний fixture refinement сначала получил4failure/6pass за13.52s (`block03_multi_final_focused_tests.log`): constant g0 был передан как единственный confounder, а data contract правильно запрещает constant X. Для этих4cases восстановлен independent varying X; для heterogeneous/proportional cases сохранён observed oracle covariate. Это test-fixture correction, library source после63-case neighbor run не менялся.

```powershell
$env:MPLBACKEND='Agg'
$env:MPLCONFIGDIR='D:\codex\Causalis\audit\mplconfig'
$env:SKIP_DOCS_BUILD='true'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=audit\block03_multi_final_test_temp tests\inference\test_multi_treatment_irm_ratio_if.py tests\inference\test_multi_treatment_irm.py tests\inference\test_multi_treatment_irm_parallel.py tests\refutation\test_multi_score_diagnostics.py tests\refutation\test_multi_unconfoundedness_diagnostics.py tests\refutation\test_multi_residual_plots.py
```

## Compatibility и ограничения

`model.psi_a_` теперь n × (K−1) для ATTE; ATE остаётся n-vector. Пользовательские consumers не должны flatten multi ATTE derivative или подставлять -1 при reconstruction. Estimate container shapes не изменены. Это iid population ATT inference; conditional-on-fixed-treatment-count target не добавлялся. Fit predictions, folds, normalization policy и sample target не изменены. P-values при exactly-zero SE сохраняют прежнюю NaN policy; отдельная boundary inference policy в этот scope не входит.

Первый payload roundtrip test выявил существующий contract edge: `MultiUnconfoundednessDiagnosticData.sigma2` имеет defaultNone, но его float|ndarray annotation отвергает explicitNone при reconstruction полного `model_dump()`. Использовано `exclude_none=True`; sensitivity поле не изменялось, замечание отложено до upstream sensitivity synchronization. Это не failure нового `psi_a` contract.

Sensitivity formulas/modules/tests не редактировались. ATE score/influence computation семантически сохранён. Общую B03 integration проверку и Git commits ведёт основной агент; этот subtask не выполнял Git mutations.
