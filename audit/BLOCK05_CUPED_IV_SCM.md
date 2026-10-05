# B05 — CUPED / IV / SCM

Работа начата 2026-10-05 от `c55909491c8c50d603a8bf348b4beca11b623e02`, branch `codex/correctness-roadmap`. Исходный аудит сохраняется без изменений. Sensitivity modules, tests, formulas и SCM leave-one-out sensitivity отложены по инструкции пользователя.

## Этапы

1. SC-06: collision-safe CUPED design и явные роли столбцов, включая bootstrap и diagnostics.
2. SC-07/12: design SVD вместо Gram inverse, reuse across outcomes, согласованные HC/relative covariance и refutation checks.
3. SC-09: IV model/result diagnostics API и отсутствие stale estimate после refit.
4. SC-08: наследование ASCM configuration в nonsensitivity placebo. LOO portion остаётся deferred.
5. Проверка интеграции вне deferred sensitivity, portable documentation handoff, commits/push и остановка на границе блока.

## SC-06 checkpoint

Служебные имена теперь выделяются без перезаписи, а treatment/main effects/interactions определяются по фиксированному порядку и metadata, независимо от суффиксов/двоеточий в пользовательских именах. Обычные display labels сохранены; при collision добавляется suffix. Bootstrap использует тот же builder, но заново центрирует covariates внутри каждой resample. Input DataFrame не изменяется.

Новые 24 regression cases: шесть комбинаций имён × delta/bootstrap × checks on/off. До исправления **20 failed,4 passed**, 35.60s; после с соседними CUPED tests **63 passed**,21.77s. Evidence: `block05_names_before_tests.log`, `block05_names_after_tests.log`. Counts пересекаются с будущей общей интеграцией. Отдельные падающие cases проверяют point/CI/coefficient roles/checks, а не означают20различных defects.

## SC-07 / SC-12 checkpoint

Одна owned SVD factorization исходного design даёт P, singular values, rank/condition, normalized covariance и stable projection diagonal `sum(U**2)`. Full-rank validation использует прежний NumPy tolerance; P использует statsmodels relative cutoff1e-15. Naive design имеет отдельную factorization, если adjustment присутствует. Batch coefficients вычисляются `P @ Y` сразу для всех outcomes одного arm comparison; results/residuals/covariance остаются отдельными. Ни initial fit, ни checks/winsor не вызывают `OLS.fit` и не переписывают private result cache.

Public `OLSResults` constructor используется через небольшой adapter, который предоставляет нужные statsmodels model attributes. HC2/HC3 properties используют стабильный h: прежняя Gram contraction могла ошибаться даже при condition<1e8. HC0/1/nonrobust и use_t/alpha policies сохранены. Leverage/Cook, raw-control relative covariance и winsor fit используют ту же factorization. Bootstrap сохраняет стратификацию, recentering и прежнюю pseudoinverse policy для singular resamples.

Новые22numeric/API cases плюс прежний cache identity case: до fix **12 failed,1 passed**,17.85s (initial12new; потом добавлены10public-reference cases). Final все CUPED modules: **127 passed**,28.36s. Independent QR reference, full params/covariance/p-values/CI/df/R² против statsmodels, scale3e7/1e8, near-collinear HC2/3, raw-control cross covariance, exactly2SVD calls для3outcomes с checks/winsor включёнными. Старый cache assertion сохранён и проходит. [Независимое методологическое ревью](D:/codex/Causalis/audit/B05_CUPED_METHOD_REVIEW.md) включает30actual-library comparisons и explicit adapter/version/cutoff limitations.

### Ограниченный fit benchmark

Baseline — `bb31a4b` (SC-06 уже исправлен), extracted полный tracked package через `git archive`; текущий package — новый SVD adapter. Два sequential fresh workers, native threads1, seed2781,12000rows/4covariates/HC2/checks=True, warmup1+3repetitions, median. Construction и estimate() вне таймера, memory не измерялась.

| Outcomes | Before fit,s | After fit,s | Local speedup |
|---|---:|---:|---:|
| 1 | .076883 | .044518 | 1.73× |
| 8 | .419437 | .144759 | 2.90× |
| 32 | 1.315923 | .510088 | 2.58× |

Max point discrepancy1.58e-14; maxSE3.47e-18. [Raw summary](D:/codex/Causalis/audit/block05_benchmark_summary.json), [worker](D:/codex/Causalis/audit/benchmark_block05_cuped.py), [comparison checks](D:/codex/Causalis/audit/block05_benchmark_summary_checks.log). Это локальные наблюдения на одном design, не universal speed guarantee/other-library comparison. Первый audit worker упал на старом pandas Series integer-label access; исправлен сам benchmark (`np.asarray`) и оба workers выполнены заново sequentially; [initial diagnostic](D:/codex/Causalis/audit/block05_benchmark_initial_checks.log) не является library failure.

### Пределы numerical correction

Raw-control relative CI сохраняет прежнюю HC scaling/calibration policy, не пересматривает joint inference. Near-zero denominators, h≈1/residualdf≈0 и extreme condition не получают новых гарантий. Rank/drop thresholds по-прежнему scale-dependent. Installed statsmodels0.15.0 проверен; version matrix, broad pandas/memory benchmarks и новых causal coverage guarantees нет. Это задачи B06/отдельных methodology blocks.
