# B03: binary IRM — relative ATT, веса после drop и CATE refit

Дата: 2026-10-05. Основа итерации: `790c8aba17b004e08061949f5e9e45de2ad3ab43`. Все Python-команды выполнены через `.venv\Scripts\python.exe`. Git-операции выполняет основной агент.

## Закрытые findings

| Finding | Приоритет | Результат |
|---|---|---|
| DML-02 | P2 | Baseline influence function относительного ATT учитывает оценённую долю treated; тот же IF используется в low-signal guard |
| DML-04 | P2 | Полные input weights валидируются до nuisance fitting, сохраняются отдельно от пользовательских arrays, затем подрезаются общей overlap mask и нормируются на retained sample |
| DML-03, только CATE | P1 | После успешного нового fit удаляются четыре lazy T-learner cache artifacts; следующий predict обучает models заново |

Generic scalar estimate/sensitivity state, unsuccessful-fit transactional state, sensitivity formulas/modules/tests не исправлялись. CATE остаётся lazy full-sample T-learner, без новых orthogonal CATE scores или CATE CI. Удаление scoring cache выполняется после успешного fit, а не после отдельной смены learner без refit.

## Независимый вывод relative ATT IF

Для `p=E[D]`, `o(X)=m(X)/(1-m(X))` определим ненормированные наблюдаемые signals:

```text
a = D*(Y-g0) - (1-D)*o*(Y-g0)
b = D*g0 + (1-D)*o*(Y-g0)
A = E[a], B = E[b]
theta_ATT = A/p
mu0_ATT = B/p
relative_ATT = 100*A/B
```

При известных nuisances либо обычных DML conditions производные ratio functionals дают:

```text
IF_theta = (a - D*theta)/p
IF_mu0   = (b - D*mu0)/p
IF_relative = 100*(IF_theta/mu0 - theta*IF_mu0/mu0^2)
            = 100*(a*B - A*b)/B^2
```

В исходной binary absolute ATT реализации `IF_theta` уже учитывал denominator. Ошибка состояла в `IF_mu0 = b/p - mu0` вместо `b/p - (D/p)*mu0`. Теперь [model.py](D:/codex/Causalis/causalis/scenarios/unconfoundedness/model.py:1333) выбирает IF по score; ATE сохраняет предыдущую approximate inference для Hájek/custom normalization. Variance relative ratio считается по общему IF, поэтому covariance между effect и baseline входит автоматически.

Проверки не ограничиваются повторением IF формулы: на публичном fit с неизменными `Y(0)=10,Y(1)=12` relative ATT должен быть ровно 20%, а оба IF — нулевые при любой достаточной доле treated. Это проверено для 2, 12 и 60 treated из 120 и обоих `normalize_ipw` значений. При 2 treated старый baseline guard ошибочно объявлял постоянный baseline low signal. Для noisy heterogeneous outcomes, включая negative baseline, independent central finite difference по contamination weights дифференцирует directly `100*mean(a)/mean(b)` и сравнивает весь CI. Отдельно проверяется, что удаление covariance меняет SE существенно.

Canonical ATTE игнорирует `normalize_ipw=True`, как и ранее: новые relative tests проверяют одинаковую empirical ratio derivative при обоих значениях. Известный warning об игнорировании normalization сохранён.

## Ограниченная sampling calibration

[test_irm_atte_relative_if.py](D:/codex/Causalis/tests/inference/test_irm_atte_relative_if.py:107) выполняет 600 IID repetitions по 600 наблюдений при известных propensity/outcome means. Seed `40317`. `X` равновероятно -1/+1; propensity .25/.75, baseline `4+.7X`, effect `1+.6X`, additive N(0,1) noise. Следовательно `E[X|D=1]=.5`, true ATT=1.3, true baseline=4.35, true relative ATT=29.88505747%.

| Метрика | Значение |
|---|---:|
| Nominal coverage | 95% |
| Observed coverage | 95.5% (573/600) |
| Mean estimate | 29.56238317% |
| Empirical SD | 2.98448191 процентных пункта |
| Mean reported SE | 2.98702829 процентных пункта |
| Mean SE / empirical SD | 1.00085320 |

Это fixed-seed sanity check sampling/inference в одном oracle DGP, а не доказательство coverage для обучаемых nuisances, overlap clipping/drop, clusters или всех размеров выборки. Monte Carlo variability nominal coverage около .009. Проверка допускает широкий заранее заданный диапазон coverage .91–.98 и SE/SD .85–1.15; numeric evidence сохранено в raw log.

## Weight snapshot contract и совместимость

[_score_utils.py](D:/codex/Causalis/causalis/scenarios/unconfoundedness/_score_utils.py:114) вынес raw-vector validation из normalization. Поддержанные ранее `(n,)`, single row/column vectors и dictionary `weights_bar` forms, включая first-column behavior `(n,r)`, сохранены. Multi-column warning теперь выдаётся при fit-time canonicalization. `_store_fit_sample` сначала валидирует новые веса и только затем заменяет full snapshot; ошибка invalid weight config до cross-fitting сохраняет существующий snapshot. Это узкая гарантия weight validation, не общий transactional refit.

Full weights привязаны к исходному порядку input rows; `_store_cross_fitted_predictions` применяет ту же `overlap_mask_` к обеим weight vectors. Retained mean weights должен быть положительным и конечным. `_get_weights` нормирует retained vectors; первоначальные input arrays и `CausalData.df` не меняются. Snapshot arrays скопированы и помечены read-only. При `weights=None` такие arrays не выделяются; custom weighting добавляет две full vectors и две retained vectors, без обещания ускорения или нового memory benchmark.

**Migration:** изменение исходного массива или `model.weights` после fit теперь не меняет результаты estimate. Новую weight configuration нужно применить через повторный `fit()`. Это согласует weights с уже сохранёнными y/d/nuisance snapshots. Approximation warning/metadata привязаны к fit-time usage, поэтому установка `model.weights=None` после weighted fit не убирает `se_approx_weight_norm=True`. Повторный fit всегда берёт исходные full-length weights, а не уже подрезанный cache.

Drop regression tests используют uneven nonconstant weights/weights_bar, duplicate row index labels и unique user IDs, проверяют retained value/SE against manual score с теми же held-out predictions, diagnostic row positions, input preservation, no-diagnostics mode и fresh-fit equivalence после mutation/refit. Неправильная length/nonfinite/zero-mean/missing-key configuration отвергается до первого propensity learner fit.

## CATE lifecycle

[IRM.fit](D:/codex/Causalis/causalis/scenarios/unconfoundedness/model.py:1213) после успешной cross-fitting/overlap стадии удаляет `_uplift_g0_model_`, `_uplift_g1_model_`, `_uplift_feature_names_`, `_uplift_y_is_binary_`. Public tests проверяют refit с новым outcome/effect, новой schema и новым outcome learner, затем equivalence со свежим IRM и повторное cache reuse без новых fit calls. Настоящая смена target sample для T-learner здесь не вводилась: scoring models по-прежнему используют полный исходный training sample, как описано в существующем uplift module.

## Evidence и команды

Initial regression run, до patch: **35 failed, 5 passed, 17.04s** — [block03_binary_before_tests.log](D:/codex/Causalis/audit/block03_binary_before_tests.log). Это 10 relative ATT cases, 14 drop/shape cases, 2 weight snapshot cases, 6 ранних validation cases и 3 CATE refit cases; 5 original CATE cases проходили. Sampling test и narrow invalid-config refit test добавлены позже.

First after-run: **41 passed, 14.07s** — [block03_binary_after_tests.log](D:/codex/Causalis/audit/block03_binary_after_tests.log).

Final focused: **42 passed, 13.83s**, source frozen — [block03_binary_final_tests.log](D:/codex/Causalis/audit/block03_binary_final_tests.log).

```powershell
$env:MPLBACKEND='Agg'
$env:MPLCONFIGDIR='D:\codex\Causalis\audit\mplconfig'
$env:SKIP_DOCS_BUILD='true'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=audit\block03_binary_final_test_temp tests/inference/test_irm_atte_relative_if.py tests/inference/test_irm_fit_weight_alignment.py tests/scenarios/uplift/test_irm_predict_cate.py
```

Neighbor run сначала закончился Windows sandbox `PermissionError: [WinError 5] Access is denied` в pytest temp fixture/session cleanup — [block03_binary_neighbor_sandbox_tests.log](D:/codex/Causalis/audit/block03_binary_neighbor_sandbox_tests.log). Это process/tmp permission limitation, без признания новой ошибки библиотеки. Тот же набор повторён с разрешённым escalated launch и fresh basename:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=audit\block03_binary_neighbor_escalated_test_temp tests/inference/test_irm_estimator.py tests/inference/test_irm_relative_ci.py tests/inference/test_irm_att_normalize_ipw.py tests/inference/test_irm_score_identities.py tests/inference/test_irm_gate.py tests/inference/test_irm_gatet.py tests/scenarios/uplift/test_policy_tree.py tests/refutation/test_uncofoundedness_refutation_api.py
```

**119 passed, 10 existing warnings, 27.39s** — [block03_binary_neighbor_tests.log](D:/codex/Causalis/audit/block03_binary_neighbor_tests.log). Warnings: baseline low signal, ATE custom normalization approximation, Hájek approximation и canonical ATTE ignoring normalization. После этого сделана только узкая validation-before-snapshot assignment adjustment и добавлен её test; final focused run выше проверяет окончательный код. Root выполняет общую B03 integration проверку.

Sensitivity-targeted тесты здесь не запускались. Обычный `estimate(store_diagnostics=True)` продолжает существующую внутреннюю сборку diagnostic payload, которая включает sensitivity elements; эти вычисления не менялись и не валидировались как отдельное sensitivity исправление.
