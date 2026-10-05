# B05 — CUPED / IV / SCM

**B05 завершён.** Работа 2026-10-05 от `c55909491c8c50d603a8bf348b4beca11b623e02`, branch `codex/correctness-roadmap`. **1376 passed,0failed,77warnings,438.20s** в repository integration вне7deferred sensitivity modules. SC-06/07/09/12 закрыты; SC-08 только placebo, LOO deferred. Исходный аудит сохраняется без изменений. Sensitivity modules, tests, formulas и SCM leave-one-out sensitivity отложены по инструкции пользователя.

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

## SC-09: IV diagnostics и refit state

Общий resolver принимает model.result_, estimate и diagnostic payload во всех4entrypoints. Lazy computations получают options/LATE из сохранённого estimate. Unfitted/fit-only/wrong payload возвращают понятные ошибки. Necessary adjacent fix: каждая fit attempt очищает26own fitted/inference attributes, поэтому failed refit не допускает stale estimate/properties; сохранённые estimates остаются доступными. Nuisance/score/inference formulas не менялись.

Новые60cases и13neighbors: **73 passed**,19.33s. Исходный31APIcase baseline15failed/16passed;16lifecyclecases beforeguard14failed/2passed. Исторический probe теперь принимает first_stage(model), table7×5, прежнийLATE2.0599090331725676. [IV notes](D:/codex/Causalis/audit/B05_IV_NOTES.md), [result manifest](D:/codex/Causalis/audit/block05_iv_result.json), [final log](D:/codex/Causalis/audit/block05_iv_final_tests.log).

## SC-08: placebo часть исправлена, LOO deferred

PanelEstimate получил additive model_options default{}. ASCM сохраняет полный13constructor-option snapshot успешного fit и effective per-estimate inference settings. Placebo-space/time наследуют их; partial overrides сохраняют остальные значения, returned attrs записывают resolved options. Legacy/incomplete metadata требует re-estimation или explicit missing options; silent default estimator больше не выбирается. Auxiliary inference refits временно используют исходные five fitting settings, даже если public attrs изменены после fit, с finally restoration.

Новые31cases+36neighbors: **67 passed**,31.10s,1 existing ASCM grid-boundary warning в deliberately tiny-grid test. Independent manually rebuilt panels/refits, donor contamination exclusion, partial/legacy overrides, snapshot immutability и refit consistency. Original actualtreated meanpostgap1.3314659377305926 теперь совпадает с defaultplacebo, прежнее1.371201225159669. [SCM notes](D:/codex/Causalis/audit/B05_SCM_NOTES.md), [manifest](D:/codex/Causalis/audit/block05_scm_result.json), [final log](D:/codex/Causalis/audit/block05_scm_final_tests.log).

**SC-08 закрыт частично**: leave_one_donor_out_sensitivity не менялась и не проверялась, её default configuration по-прежнему нельзя считать наследующей original estimate. Эта часть исключена из текущей работы по прямой инструкции пользователя.

## Сохранённые code checkpoints

| Commit | Результат |
|---|---|
| bb31a4b09c20046faafbbd29a541e5acbe50b99d | CUPED collision-safe names/roles/bootstrap |
| 5e0379507bac4b6ec9f561e7978e8835194c2247 | IV resolver/fit lifecycle |
| 3c000b10eed1b5366f46cc038870500791b75579 | CUPED owned SVD/batch/HC/projection/benchmark |
| 1b2477755c9b89bd2f69f260fd094002bdc26fe2 | ASCM snapshots/placebo config |

Последний code checkpoint — источник общей интеграции. Final documentation commit добавляется после проверки; actual final SHA через git log-1. Causalis upstream не fetch/merge/rebase, PR/issues/external messages не создавались.

## Финальная интеграция и артефакты

Команда: `.venv\Scripts\python.exe audit/run_block05_integration.py`, Agg/local MPLCONFIGDIR, SKIP_DOCS_BUILD=true, no pytestcache, task-owned basetemp, разрешённый Windows process/tmp run. **1376 passed,0failed,77warnings,438.20s**, exit0. [Raw log](D:/codex/Causalis/audit/block05_integration_tests.log), [exact selection/exclusions](D:/codex/Causalis/audit/block05_integration_selection.json), [structured result](D:/codex/Causalis/audit/block05_integration_result.json).

Добавлены **137 new cases**: names24,stable22,IV60,SCM31. Предыдущий source имел1238passed+1SC12failure; теперь исходный cache-reuse тест также проходит. Нет удаления/xfail этого assertion и нет новых failures. 77warnings:76existing warning emissions плюс1existing conformal-grid warning в новом tiny-grid case. Это зелёная **выбранная** интеграция, не validation sensitivity/full docs build/version matrix. Exact7exclusions перечислены вmanifest; ordinary DML estimator по-прежнему может строить старый sensitivity payload, его formulas здесь не проверялись.

После integration library/tests не менялись: diff относительно1b24777 пуст. [verify_block05.py](D:/codex/Causalis/audit/verify_block05.py) проверяет source checkpoint, PythonAST, sensitivity path guard, local file/line links и raw pytest summary: [validation JSON](D:/codex/Causalis/audit/block05_validation_checks.json), [log](D:/codex/Causalis/audit/block05_checks.log). Portable [documentation handoff](D:/codex/Causalis/audit/DOCUMENTATION_HANDOFF.md) имеет58verified immutable Causalis source links; он готов для пересылки, автору внешними инструментами не отправлялся.

NEXT_SESSION/FIX_PLAN/PROGRESS/GIT_ACCESS обновлены. Обычный push идёт только вpersonal `origin/codex/correctness-roadmap`; final remote/local equality и cleanstatus проверяются после documentation commit. Пользователь может очистить контекст. **B06 не начат**: compatibility/Pydantic minimum/release pytestgate/dependency matrix, затем scoped pandas/NumPy/KDE time/memory optimization. Sensitivity/SC08LOO и ранее записанные DGP/DiD support followups остаются отдельными.
