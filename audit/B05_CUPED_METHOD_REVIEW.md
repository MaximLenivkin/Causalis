# B05: независимое ревью численной реализации CUPED

Дата: 2026-10-05. Scope: SC-06/07/12; дизайн Lin, поддерживаемые HC/nonrobust covariance, относительный эффект и повторное использование разложения. Sensitivity analysis исключено. Этот документ ведёт отдельный reviewer; он не редактирует library source/tests и не управляет Git.

## Исходная проверка и рекомендации

Прочитаны `AGENTS.md`, `NEXT_SESSION.md`, `FIX_PLAN.md`, `SCENARIOS_REVIEW.md`, CUPED model/refutation/config и существующие CUPED tests. Установленные исходники statsmodels прочитаны через обязательную `.venv\Scripts\python.exe`; Python subprocess в sandbox не вернул stdout, поэтому проверка выполнена разрешённым запуском той же local `.venv`.

Установленный `statsmodels.regression.linear_model.OLS.fit` намеренно пересчитывает pseudoinverse, normalized covariance, rank и singular values при каждом вызове. Подстановка этих полей перед последующим `.fit()` не экономит разложение. Рекомендуется owned design decomposition один раз на comparison, вычисление outcome coefficients как `P @ y` и public `OLSResults` constructor. Constructor, его covariance/use_t parameters и методы inference описаны в [официальном API](https://www.statsmodels.org/dev/generated/statsmodels.regression.linear_model.OLSResults.html). Проверенные web docs относятся к dev0.15.1, локальные исходники — установленной0.15.0; equivalence нельзя выдавать за проверку полного version matrix.

Чтобы адаптер не запустил дополнительный rank decomposition, ему нужны известные `df_model=k-1`, `df_resid=n-k` (design full rank, intercept присутствует). HC implementation statsmodels использует `model.pinv_wexog`; результату также нужны корректные singular values для condition diagnostics. Эти зависимости нужно изолировать и тестировать в небольшом адаптере. Поддержанный public result constructor устраняет зависимость от поведения `.fit()` cache; он не превращает каждое внутреннее model attribute в отдельный гарантированный публичный API.

## Математика и численная устойчивость

Для numeric ordered design `Z=[1,D,Xc,D*Xc]` экономичный SVD `Z=U S V'` даёт `P=V S^-1 U'`, coefficients `P y`, normalized covariance `P P'` и leverage `h_i=sum_j U_ij^2` для retained directions. Это вывод reviewer, а не новая статистическая спецификация. Для full-rank accepted designs `diag(Z P)` эквивалентна leverage; row-square U избегает cancellation. Gram pseudoinverse `pinv(Z'Z)` не требуется.

Full-rank validation и condition number должны использовать то же singular-value set. Следует сохранить исходный scale-dependent rank policy (NumPy tolerance) или явно документировать изменение cutoff. При full rank обе validated degrees of freedom равны существующим OLS values. Отрицательная/нулевая residual df требует такой же ясной policy, как прежний estimator; не добавлять молча новую статистическую трактовку.

HC covariance при фиксированном design вычисляется как `P diag(a) P'`:

| Covariance | a_i |
| --- | --- |
| HC0 | e_i² |
| HC1 | n/(n-k) e_i² |
| HC2 | e_i²/(1-h_i) |
| HC3 | e_i²/(1-h_i)² |
| nonrobust | covariance = RSS/(n-k) P P' |

Формулы соответствуют [официальному описанию HC covariance](https://www.statsmodels.org/dev/generated/statsmodels.regression.linear_model.OLSResults.HC2_se.html) и [HC3](https://www.statsmodels.org/dev/generated/statsmodels.regression.linear_model.OLSResults.HC3_se.html). Существующие use_t/threshold/alpha policies надо сохранить; [get_robustcov_results](https://www.statsmodels.org/dev/generated/statsmodels.regression.linear_model.OLSResults.get_robustcov_results.html) применяет выбранную covariance ко всем последующим inferential summaries.

### Проверка public constructor без library helper

Reviewer выполнил независимый inline NumPy/OLSResults prototype; source/test files не создавались. Seed731, n400, treatment Bernoulli.47, два центрированных Gaussian covariates, outcome `7+1.8D+2X1-.5X2+.5DX1+noise`. Один independent SVD, все пять covariance types. Manual sandwich использовал row-square U; statsmodels result — public constructor и shared P.

| Covariate scale | trace(h), expected6 | max h SVD/QR error | max HC2 covariance discrepancy | max HC3 discrepancy | tau | HC3 SE |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 6.000000000000004 | 4.17e-17 | 8.67e-19 | 8.67e-19 | 1.75494175498 | .104862135268 |
| 3e7 | 6.000000000000004 | 4.86e-17 | 4.32e-14 | 8.83e-14 | 1.75494175413 | .104862135216 |
| 1e8 | 6.000000000000001 | 2.78e-17 | 2.41e-13 | 4.94e-13 | 1.75494175467 | .104862135252 |

HC0/1 and nonrobust discrepancies were below9e-19 for these cases. This confirms the constructor strategy for ordinary/full-rank scaled designs, rather than a version-general guarantee.

### Дополнительный risk: HC2/3 внутренняя Gram contraction

Даже при точном P установленный statsmodels HC2/3 вычисляет leverage через contraction `Z(P P')Z'`. Это уже не Gram inversion, но близкая коллинеарность может дать cancellation. Независимый seed735, n400, covariates `[x,x+noise*v]`, full interacted design, outcome `7+1.8D+2x+.5Dx+noise_y`:

| Covariate perturbation | condition(Z) | statsmodels leverage trace (expected6) | max h error vs row-square U | HC3 tau variance relative error |
| --- | --- | --- | --- | --- |
| 1e-3 | 5729.20 | 5.9999999980 | 7.14e-11 | -1.06e-11 |
| 1e-5 | 572952.51 | 6.0000009716 | 2.91e-7 | 3.80e-9 |
| 1e-7 | 57295284.42 | 6.1091050413 | .00722554 | .000608219 |

Последний case ниже default condition warning threshold1e8, поэтому чистый rescaling test недостаточен. Recommended implementation computes HC2/3 with cached stable h and P, retaining the same HC formulas. A small subclass of the public OLSResults class can override the two covariance properties, or a clearly documented owned result adapter can set the same covariance; tests must cover ordinary statsmodels parity and independent QR near-collinear reference. Changes to selected estimator/covariance name are not required.

## Collision-safe design и вспомогательные пути

Смысл столбцов должен определяться явными indices/metadata, а не именами пользователя. Dictionary overwrite удаляет D для treatment=`intercept` или `x__centered`. Suffix/prefix selection также ошибочен: treatment label с suffix `__centered` включается в beta, raw names с colon/суффиксом могут включать interactions в main effects/refutation.

Безопасная схема: упорядоченный numeric matrix, index0 intercept, index1 treatment, explicit main and interaction position lists. Label allocator может сохранять обычные readable labels при отсутствии collision; это сохраняет existing private-introspection tests. Labels должны оставаться уникальными даже при повторном allocator suffix, а beta/gamma extraction и refutation main covariates должны использовать metadata независимо от label.

Одна и та же builder logic нужна naive и bootstrap design. Bootstrap сохраняет stratified sampling within arms, full-resample global recentering и denominator selection. Original bootstrap OLS допускает rank-deficient resamples через pseudoinverse; shared full-rank fit validation не должна молча менять accepted draws. Winsorized outcome refit имеет тот же design, поэтому coefficients `P @ winsorized_y` достаточно; covariance не используется для возвращаемого tau, дополнительное `.fit()` не нужно.

## Raw-control relative CI: сохраняемый scope

В текущем estimator coefficient empirical contribution `P[1,i]*e_i` масштабируется HC0/1/2/3 factor, затем калибруется так, чтобы sum of squares совпадала с опубликованной `var_tau`. Raw-control contribution остаётся `(Y_i-mu_c)/n_control` для control units; variance raw mean отдельно равна sample variance(ddof1)/n_control. Это существующая finite-sample policy, не обещание точной единой joint sandwich при всех covariance types. В B05 требуется заменить normal-equation coefficient weights на `P[1,:]`, leverage на cached stable h и сохранить остальные choices. Denominator zero/nonfinite и bootstrap percentile policies должны оставаться прежними.

Для adjusted-control denominator gradient использует intercept/treatment covariance из одного selected result. После stable sandwich это автоматически использует корректные cross terms. Близкий к нулю denominator всё ещё является ограничением delta inference; исправление численной проекции не устраняет ratio nonregularity.

## Обязательные независимые checks

1. Все HC0/1/2/3/nonrobust и use_t true/false: coefficients, covariance, SE, p-values, absolute CI и adjusted-control ratio CI против ordinary public statsmodels на benign numeric design.
2. Name invariance, включая treatment=`intercept`, suffix/colon names, collisions с allocator suffix, ordered beta/gamma и refutation p_main_covariates; single, batch и seeded bootstrap.
3. Design scale3e7 и extreme allowed near-collinearity: QR leverage trace/rank, Cook/studentized residuals, stable HC2/3 sandwich, raw-control ratio covariance и interval.
4. Batch per-arm subsets/global centering vs independent pairwise models и отсутствие input mutation.
5. Count owned design factorizations для many outcomes на одной arm; checks=True/default winsor не должны повторять full design factorization. Существующий pinv identity assertion надо сохранить или усилить доказательством реального shared owned decomposition.
6. Failed refit clears fit state and decomposition metadata; independent outcome results retain distinct residual/covariance caches and share only immutable design quantities.

## Final implementation review

Прочитаны фактические [owned factorization/result adapter](D:/codex/Causalis/causalis/scenarios/cuped/_ols.py), [CUPED integration](D:/codex/Causalis/causalis/scenarios/cuped/model.py), [refutation integration](D:/codex/Causalis/causalis/scenarios/cuped/refutation/regression_checks.py), [independent QR regression tests](D:/codex/Causalis/tests/statistics/test_cuped_stable_design.py) и [name invariance tests](D:/codex/Causalis/tests/statistics/test_cuped_design_names.py). Reviewer проверял рабочие файлы после names commit `bb31a4b`; stable design changes на момент review ещё были uncommitted, final checkpoint записывает root.

**Блокирующих замечаний к CUPED patch не обнаружено.** Implementation сохраняет Lin specification, covariance selections, use_t, centering и existing relative-denominator policy. `_build_design` теперь фиксирует interleaved role order `[1,D,X1,D*X1,...]`, allocates unique display names, beta/gamma берутся через role positions, refutation получает main covariates через DataFrame attrs. Ordinary safe labels сохранены. Bootstrap использует тот же builder, вновь центрирует resample и сохраняет прежний `.OLS.fit()` pseudoinverse policy.

`factor_design` делает один SVD raw design. NumPy default validation rank cutoff и statsmodels pinv1e-15 cutoff сохранены раздельно; accepted full-rank design сохраняет все необходимые направления. Model rank передаётся public result adapter: statsmodels lazy df properties получают known rank и не повторяют SVD. Все factor arrays readonly. Public result constructor создаёт отдельные residual/covariance result states. `StableOLSResults` HC2/3 использует cached U² projection, поэтому обнаруженная выше near-collinear cancellation устранена. Constructor robust covariance хранится outcome-specific; повторные direct reads HC2/3 properties могут заново вычислять sandwich, но обычные bse/p/CI используют уже выбранную covariance без нового design decomposition.

Первый outcome child вычисляет coefficients для всей response matrix через P@Y; следующие children используют соответствующую column и общий decomposition. Naive factorization отдельная, если p>0; при p=0 может использовать adjusted factorization. Rank/condition и leverage diagnostics используют cached factor; winsorized outcome использует P@y_w. Полный design decomposition не повторяется ради diagnostics или winsor.

### Собственный probe фактической реализации

Reviewer выполнил новый inline numeric probe actual library, seed735,n400. Всего30 combinations: five covariance types × use_tFalse/True × benign scale1, benign scale3e7, near-collinear pair `[x,x+1e-7*v]`. Benign reference — independent ordinary public statsmodels OLS.fit. Scaled/near-collinear projection и sandwich reference — independent economy QR/solve. Raw-control relative intervals построены отдельно из QR coefficients, calibrated coefficient contributions, raw-control sample variance/cross covariance и scipy t/normal critical values.

| Проверка | Maximum observed error |
| --- | --- |
| Benign coefficients vs ordinary statsmodels | 8.88e-16 absolute |
| Benign covariance vs ordinary statsmodels | 3.47e-18 absolute |
| Benign p-values vs ordinary statsmodels | 1.67e-15 absolute |
| Benign absolute CI vs ordinary statsmodels | 8.88e-16 absolute |
| Actual cached projection vs QR, all designs | 5.55e-17 absolute |
| Near-collinear tau covariance vs QR, all covariance/use_t | 3.07e-10 relative |
| Independently reconstructed raw-control relative CI, benign/scaled | 6.70e-9 absolute percentage points |

Probe exited0. It imported actual implementation and did not create or modify source/tests; numeric outcomes are recorded here. Root focused raw log `block05_stable_after_tests.log` separately reports **58 passed in21.05s** for its selected set; this is root test evidence, not an independently repeated pytest run. The new test explicitly forbids OLS.fit for main/batch fits and counts two design SVD calls for three outcomes, including checks=True/default winsor. Existing shared-pinv identity and separate pairwise-parity checks remain relevant; broad integration status is owned by root.

### Ограничения signoff

- Scope — SC-06/07/12 implementation, not coverage theorem or a new relative-inference policy.
- h≈1, residual df≈0, very ill-conditioned accepted designs и near-zero ratio denominator сохраняют прежние numerical/statistical limitations. HC2/3 formula не скрывает h=1 degeneracy; U² может округлиться около1.
- Для standalone rank-deficient external diagnostics validation rank и pinv projection cutoff различны по сохранённой policy; trace(h) означает retained pseudoinverse directions. Full-rank CUPED fitting guard исключает такие designs из actual estimator.
- Installed statsmodels0.15.0 проверен; dependency version matrix, broad runtime/memory benchmark и RCT finite-sample coverage simulation здесь не выполнялись.
- Reviewer source/probe signoff относится к прочитанным files. Изменения после review требуют точечной повторной проверки изменённой логики; root может commit reports без повторного numeric run, если library code остался тем же.
