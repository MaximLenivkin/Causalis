# B04 — DiD inference

Начало: 2026-10-05. Base checkpoint `f57f2d32d232e5ab0b358153f6ac564e615d19c3`, branch `codex/correctness-roadmap`. Local/remote checkpoint совпадают; рабочее дерево на старте чистое.

## Scope и ход работы

- SC-02: единые правила controls для support, модели и refutation; исключение собственной когорты и untreated на обе даты с anticipation. Реализовано, проверено parallel agent и root.
- SC-01/03: полный IF фактически используемого normalized IPW / traditional MLE+OLS DR estimator. Point estimator сохранён, учитываются nuisance estimation, ridge и clipping. Реализовано, проверено parallel agent и independent reviewer.
- SC-04: random estimated cohort/complete-pair shares в simple/calendar/event aggregation. Реализовано root; independent derivation и empirical refits проверены.
- SC-11: единый запрет inference с одним cluster, включая multiplier bootstrap. Реализовано root; covariance проверена exhaustive enumeration.
- Независимый methodology review и repository integration вне deferred sensitivity завершены.

Sensitivity implementation/tests не меняются. SC-12 CUPED остаётся известным baseline failure до B05. Исторические отчёты не переписываются. Итоговые SHA, evidence и ограничения будут записаны на границе блока.

## Checkpoint: clustered inference

SC-11 исправлен: analytical и bootstrap paths требуют >=2 clusters. `bootstrap_replications=1` теперь отвергается (sample SD с ddof=1 не определён). Cluster Rademacher draws центрируются по clusters и масштабируются на sqrt(C/(C-1)): их conditional covariance совпадает с уже существующей аналитической covariance, включая cross-cell terms. Это согласование second moments, не гарантия coverage при малом числе clusters.

Before: **8 failed, 2 passed**, 20 warnings, 14.55s. После: **10 passed**, 7.32s. Evidence: `block04_cluster_before_tests.log`, `block04_cluster_after_tests.log`. Независимая проверка перечисляет все 2^3 sign patterns и сравнивает с centered cluster sandwich. Seeded public bootstrap воспроизводим; approximate SE agreement проверен на 2000 repetitions.

## Реализация остальных findings

SC-02: общий pure helper `causalis/data_contracts/_did_comparison_units.py` используется contract support, estimator и refutation. Own cohort всегда исключён; adoption должен быть позднее max(base,target)+anticipation. Complete pairs фильтруются после eligibility; unit rows больше не дублируются/не перезаписывают IF. Public `comparison_units` сохраняет post-only guard и off-axis dates, добавляет optional `base_time`/`anticipation`. На old SHA21fail8pass29проверок с исправленным fixture; после30new+26neighbors **56 passed**,69.81s, затем2M/Mpublic-datecases **2 passed**,11.12s. Finalnewfile32cases. Initial8fixture mistakes и interim процесс с old model import объяснены в `B04_ALIGNMENT_NOTES.md`.

SC-01/03: ATT вычисляется прежними normalized weights и MLE/control OLS. IF теперь учитывает обе ratio normalizations, OLS coefficients и penalized likelihood coefficients. Propensity derivative использует raw expit для likelihood и zero clipped-odds derivative вне clipping interior; score центрируется при fixed penalty. Control OLS и penalized likelihood inverse maps вычисляются через design SVD. Для intercept-only nuisance terms точно сокращаются. Cell scores остаются на общей original-unit axis с прежним complete-case embedding. Before **18 failed,10 passed**,20.84s; after28pass22.09s. Шесть additional scale invariance checks сначала failed с Gram inverse, после augmented-design SVD final **34 passed**,23.09s. Соседние45pass19.01s до последнего numeric refinement; окончательная integration проверит finalcode.

SC-04: simple/calendar/event IF включает оценивание фактических complete-pair shares. Для cell indicators R_ij и q_j=mean(R_j), S=sum(q_j), aggregate alpha=sum(q_j*theta_j)/S:

`IF_aggregate = sum_j (q_j/S)*IF_cell_j + sum_j R_ij*(theta_j-alpha)/S`.

На balanced panel это обычный cohort-share IF. На incomplete panel нельзя подставлять whole-cohort indicator при denominator из complete-pair counts. Cohort table равномерно усредняет включённые post cells; эти веса фиксированы и дополнительного share term не требуют. Point effects/weight policy сохранены. Root checks: **29 passed**,25.67s (19aggregation +10cluster). 16aggregationcases independently perturb every original-unit mass and refit normalized cell means/count weights; included missingness/noisy effects/all4aggregatefamilies. Before17fail2pass из-за отсутствующего нового privatehelperargument — это не17independentdefects; исходная numerical bug отдельно подтверждена историческим probe и его final recheck. Review probe не импортирует library aggregation и даёт max derivative error7.25e-10 в4cases.

## Границы inference

Это traditional MLE/OLS, не improved IPT/WLS estimator. Fixed ridge/active clipping могут менять probability limit; правильная sandwich uncertainty не убирает этот bias. Нужны regular nuisance solutions, стабильные rank/clipping/support и causal assumptions. При missingness target остаётся mixture observed complete-pair populations; full-cohort causal ATT не идентифицируется автоматически. Few-cluster coverage не гарантируется. В helper scale tests nuisance predictions заданы эквивалентно: они проверяют numeric IF map, не BFGS optimizer invariance.

Deferred independent follow-up: universal pre-period enumeration пока начинается с analysis-index1, пропуская earliest valid universal placebo. Состав cells не расширялся в этом bugfix. Cross-fitting/IPT-WLS и alternative few-cluster inference — отдельные future methods.

## Источники и evidence

Derivations: [B04_CELL_IF_NOTES.md](D:/codex/Causalis/audit/B04_CELL_IF_NOTES.md), [B04_ALIGNMENT_NOTES.md](D:/codex/Causalis/audit/B04_ALIGNMENT_NOTES.md), [B04_METHOD_REVIEW.md](D:/codex/Causalis/audit/B04_METHOD_REVIEW.md). Независимо проверены official [DRDID traditional source](https://github.com/pedrohcgs/DRDID/blob/85807cfbddbd64cc6f3f8ba37f52d07c6c3acc65/R/drdid_panel.R), [did aggregation](https://github.com/bcallaway11/did/blob/74b88eb07f1faa644df1271055a0f77848f6550c/R/compute.aggte.R), papers Sant'Anna–Zhao и Callaway–Sant'Anna; это source/derivative comparison, не исполнение R-пакетов.

IID known-cell-effects cohort-share experiment:600replications×n600,seed4704,trueeffect5.2; mean5.19508, empiricalSD.201847, RMSSE.202300, ratio1.002245, **95%coverage.958333**. Это onlyrandomshares, не nuisancepipeline. [JSON](D:/codex/Causalis/audit/block04_aggregate_oracle_result.json).

Estimated-nuisance DR experiment:600×n600 для каждого из2DGP,constantATT2,seed48129,ridge0/noactiveclip. PS-correct/OR-misspecified: **coverage.935**,MCSE.0101, meanSE/empSD.9163 (RMSratio.9418); finite-nheavy-tail gap сохранён. OR-correct/PS-misspecified: **coverage.956667**,MCSE.0083,meanSE/empSD1.0293. Oldcoverage.941667/.943333: universal improvement не заявляется. [JSON](D:/codex/Causalis/audit/block04_cell_coverage.json). Это cell pipeline, не весь support/aggregation/clustering.

## Коммиты и интеграционная граница

- `87228e267aed3dc71dadd4bbe19b969a95463591` — cluster guard/covariance и10cases.
- `57dbba1e2ecc0c1cab413b1da7f40cfdd8b22131` — full cell IF/control alignment/population aggregation, source docstrings,85newcases и detailed evidence. Это source checkpoint общей проверки; source/tests после неё не менялись. Вместе с первым commit добавлены95cases.
- Final documentation checkpoint сохраняет integration/status/handoff; actual HEAD доступен через `git log -1`. На границе блока выполняется обычный push в personal fork и проверка remote/local SHA.

Historical probes повторены отдельно, без запуска остальных scenarios/sensitivity: [correctness JSON](D:/codex/Causalis/audit/block04_correctness_result.json). IPW common trend1000: SE.375205828834 → .375205828834, исходное258.24исчезло; pre-effect -1→**-2**,duplicate rows0; traditional DR SE.04438196748→**.038875673514**, совпадает с независимым DRDID translation; deterministic heterogeneous aggregate SE≈0→**.495741868315**, совпадает с cohort-share IF. One-clusterbootstrap отвергается.

## Воспроизводимость

Windows Python3.12.14 через repo-local `.venv\Scripts\python.exe`; версии окружения сохраняются в `audit/environment.json`. Tests используют Agg/local MPLCONFIGDIR, pytest cache отключён, каждый runner имеет отдельный task-owned basetemp. Общая integration выполняется в разрешённом запуске, чтобы не повторять известные Windows process/tmp sandbox failures.

```powershell
.\.venv\Scripts\python.exe audit\run_block04_integration.py
.\.venv\Scripts\python.exe audit\verify_block04.py
.\.venv\Scripts\python.exe audit\verify_handoff.py
```

Перед focused tests установить `MPLBACKEND=Agg`, `MPLCONFIGDIR=D:\codex\Causalis\audit\mplconfig`; для raw evidence использовать отдельные `block04*_tests.log`/`block04*_checks.log`. `block04_cell_coverage.py`, `block04_aggregate_oracle_probe.py`, `block04_aggregate_review_probe.py` и `block04_correctness_probe.py` воспроизводят только соответствующие experiments. Historical `repro_scenarios.py` целиком не запускался: новый wrapper вызывает лишь5DiDprobes. Runtime/memory benchmark, Sphinx rebuild и version matrix не выполнялись в B04.

Отдельный переносимый файл автору сайта обновлён: [DOCUMENTATION_HANDOFF.md](D:/codex/Causalis/audit/DOCUMENTATION_HANDOFF.md),49immutable Causalis snapshot links проверены, issues0. Новые public/source docstrings corrected; остальные прежние generator examples остаются docs-author tasks. Upstream Causalis не fetch/merge/rebase; PR/issues/external messages не создавались.

## Итог integration и следующий блок

**1238 passed,1 failed,76 warnings,340.04s**, exit code1. Это repository suite вне7deferred sensitivity test modules, а не fullygreen/full sensitivity run. Новых failures0. Единственный failure — исходный **SC-12** `tests/statistics/test_cuped_rct.py::test_shared_design_and_input_unchanged`, identity of `pinv_wexog` на statsmodels0.15. CUPED source/tests не изменялись, assert не удалялся/не скрывался. Его исправление остаётся B05.

Evidence: [raw log](D:/codex/Causalis/audit/block04_integration_tests.log), [selection/exclusions](D:/codex/Causalis/audit/block04_integration_selection.json), [result JSON](D:/codex/Causalis/audit/block04_integration_result.json), [scope/artifact checks](D:/codex/Causalis/audit/block04_validation_checks.json). Warnings относятся к прежним relative-effect/normalization policies, degenerate SCM inference и IV docstring escapes; новых DiD warnings в этом run нет.

Artifact checks: **229local links,49immutable Causalis handoff links,15PythonAST,issues0**. Library paths5, sensitivity paths0. Проверяется фактический failing node иexit1, исключения не скрывают SC-12. Послеintegration менялись только audit/status artifacts; source/tests соответствуют проверенному checkpoint57dbba1.

**B04 завершён:** SC-01/02/03/04/11 закрыты в stated scope, исходные findings reports остаются historical snapshots. Прежние DiD results надо re-fit/re-estimate; site migration выпускается вместе с code. На границе блока работа останавливается. Следующий **B05 CUPED/IV/SCM** начинается по новому запросу пользователя; sensitivity остаётся deferred.
