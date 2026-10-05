# B03 — DML / GATE / Uplift

Статус: **завершён**, 2026-10-05. Начальный commit `790c8aba17b004e08061949f5e9e45de2ad3ab43`; ветка `codex/correctness-roadmap`. Четыре code commits и итоговый documentation checkpoint сохраняются в personal fork. Новых integration failures нет; известный SC-12 остаётся в B05.

Scope: DML-01 multi ATTE ratio influence function, DML-02 binary relative ATT baseline, DML-04 overlap drop/custom weights, DML-03 только независимый CATE cache, DML-09 stable GATE variance и DML-06 честная fold diagnostic. Balance DML-05 закрыт в B02. Sensitivity implementation/tests остаются отложенными.

Работа разделена между тремя сабагентами (multi, binary, OOS diagnostics) и root (GATE, integration, docs/checkpoints). Оригинальные audit reports остаются историческими.

## Проверка методологии

Используем независимые ratio derivatives и saturated-regression HC sandwich, noiseless potential outcomes, fresh-fit equivalence и shift invariance. Score/Jacobian notation проверено по [официальному DoubleML score guide](https://docs.doubleml.org/stable/guide/scores.html#binary-interactive-regression-model-irm), в частности original ATT score с `psi_a=-D/E_n[D]`. Это reference notation; локальные многоармовые derivations и tests нужны отдельно. Наличие cross-fitting не превращает агрегированную residual identity в калиброванный validation test.

## Журнал

- Проверены AGENTS.md, NEXT_SESSION.md, FIX_PLAN.md; рабочая ветка соответствует сохранённому checkpoint, чужих tracked edits нет.
- GATE regression: добавлены проверки HC0/1/2/3 при shifts 1e8, -1e8, 1e12, unequal/interleaved groups, публичный contrast и GATET descriptive spread. Перед source patch выполняется failing baseline.
- GATE сохранён в commit `c9259072a24f5325f944cd37c4f203f33c39a5e7`: 68 cases passed. В первом post-patch run четыре новых tests ссылались на неверное имя поля контраста; это исправлено в тесте, полный raw log сохранён.
- Общий integration run окончательного кода: **1143 passed, 1 failed, 76 warnings, 299.18s**. Единственный failure совпадает с original SC-12, новый failure отсутствует.

## Исправления по приоритету

| Finding | Severity | Изменение / результат |
|---|---|---|
| DML-01 | P1 | Multi ATTE теперь использует `psi_a_k=-d_k/p_k`; root сохраняется, IF/SE учитывают random arm share. Relative baseline скорректирован одновременно для правильного сокращения общего знаменателя |
| DML-03, CATE part | P1 | После успешного refit удаляются четыре lazy T-learner cache attributes; новые predictions соответствуют fresh fit на новых outcomes/features/learner |
| DML-02 | P2 | Binary relative ATT baseline IF теперь `signal_mu-(D/p)*mu`; исправлены covariance delta method и baseline-low-signal guard |
| DML-04 | P2 | Original-row weights валидируются до training, snapshot хранится независимо от caller, тот же overlap mask применяется к weights/weights_bar, normalization использует retained mean |
| DML-09 | P2 | GATE centered two-pass SSE сохраняет within-group variation при большом сдвиге. GATET descriptive spread использует такой же стабильный расчёт; его inference formula не меняется |
| DML-06 | P2 | Cached cross-fit fold scores больше не выдаются за независимый OOS test: legacy t/p values NaN, inference unavailable, flag NA; добавлены descriptive ranges/gaps/RMS |

Это шесть пунктов scope, **DML-03 закрыт только частично**: generic scalar estimate/sensitivity state остаётся отложенным. DML-05 balance уже закрыт в B02 и здесь не считается повторно. Не заявляем, что весь DML backlog устранён.

## Независимые численные проверки

Multi ATTE noiseless equal/unequal shares: прежняя SE `[0.163572,0.327144]` для effects `[2,4]` сменяется нулевой, как требует идентичность constant potential outcomes. Influence vector также сверяется с central derivative empirical contamination, а permutation active arms/outcome shift сохраняют нужные свойства.

В отдельном IID oracle DGP, 600 repetitions × 600 observations, fixed seed: coverage nominal95% multi intervals `[0.9400,0.9433]`; reported/empirical SD `[0.9640,1.0143]`. Binary relative ATT: coverage `0.9550`; mean SE `2.98703` процентных пункта, empirical SD `2.98448`. Это ограниченная sampling-calibration проверка при известных nuisances, не доказательство uniform coverage для произвольных learners, propensity clipping или всех targets.

Relative ATT public cases проверяют exactly proportional potential outcomes, finite-difference ratio derivative с covariance и baseline разных знаков. Old multi relative numerator/baseline IF errors могли сокращаться друг с другом; исправлены обе части вместе, и сохранено это сокращение при правильных ratio IFs.

GATE public HC0/1/2/3 проверяются через независимый saturated-regression sandwich; большие shifts +1e8/-1e8/+1e12 не меняют SE/std_phi. Сложность остаётся O(n+groups); это не measured performance claim.

## Миграция поведения

- Multi `psi_a_` и diagnostic `psi_a` имеют shape `(n,K-1)` для ATTE, `(n,)` для ATE. Пользовательский consumer должен выбирать коэффициент нужного contrast. `psi_` — corrected influence function; point estimates/return result shapes сохраняются.
- Custom weights соответствуют **original input rows**. Изменение публичного `weights`/caller array после fit требует нового fit, чтобы повлиять на estimate. Fit snapshots read-only; после drop normalization выполняется на retained rows. Это alignment fix; existing custom-weight/Hájek ATE approximate inference metadata/warnings остаются.
- `oos_moment_test.available=False` относится к inference; `fold_diagnostics_available` отдельно показывает доступность descriptive table summaries. `fold_theta_range`, `fold_theta_gap_max_abs`, `fold_score_mean_rms`, `fold_score_mean_max_abs` описывают differences, но не имеют calibrated p-values/traffic thresholds. Настоящая held-out validation остаётся самостоятельной feature.
- Cached multi ATTE `psi`, несовместимая с `psi_b+psi_a*theta`, реконструируется с явной provenance metadata. Старые сохранённые estimates всё равно надо переоценить для исправленных confidence intervals.

## Commits и focused evidence

| Commit | Scope | Проверка |
|---|---|---|
| `c9259072a24f5325f944cd37c4f203f33c39a5e7` | Stable GATE/GATET descriptive SSE | 68 passed / 15.12s |
| `e6a92759f3c8844999c53bd065a673e31330d604` | Multi ATTE ratio IF, paired relative baseline и psi_a payload | 63 passed / 19.78s; final fixture refinement 10 passed / 12.61s |
| `6084b34d799e9af34228136c0a2e9549063638ac` | Binary relative ATT, aligned immutable fit weights, CATE cache | Final focused 42 passed / 13.83s; neighbors 119 passed / 27.39s |
| `113c693a0dd721c6e77dfe84bc647d2ffb4c7841` | Descriptive fold diagnostics, ratio reconstruction/cache provenance | Final focused 36 passed / 12.49s; neighbors 50 passed / 25.93s |

Наборы пересекаются и **не суммируются** как unique coverage. Все raw before/after/interim/final logs сохранены; fixes подтверждены independent properties/derivatives, а не только существующими assertions. Ошибки новых test fixtures (неверное contrast field; constant confounder; explicitNone в deferred sensitivity field при roundtrip) описаны в notes, не выдаются за library regressions.

Подробные derivations, commands и evidence: [B03_MULTI_IF_NOTES.md](D:/codex/Causalis/audit/B03_MULTI_IF_NOTES.md), [B03_BINARY_NOTES.md](D:/codex/Causalis/audit/B03_BINARY_NOTES.md), [B03_GATE_NOTES.md](D:/codex/Causalis/audit/B03_GATE_NOTES.md), [B03_OOS_NOTES.md](D:/codex/Causalis/audit/B03_OOS_NOTES.md). Документ для автора — [DOCUMENTATION_HANDOFF.md](D:/codex/Causalis/audit/DOCUMENTATION_HANDOFF.md).

## Ограничения и следующий блок

Sensitivity modules/formulas/tests не исправлялись. Integration исключает 7 явно sensitivity-named test modules; точный список сохранён в `block03_integration_selection.json`. Обычные estimator tests могут запускать существующую внутреннюю сборку sensitivity fields как часть diagnostic payload; это не отдельная sensitivity validation. Dependencies/version matrix и broad performance benchmarking относятся к B06. Extreme floating-point values и normalized custom-weight ATE ratio-aware IF требуют отдельного scope.

## Итоговая интеграционная проверка

Запуск в разрешённой Windows среде, чтобы проверить Joblib/process pipes и tmp fixtures без известных sandbox artifacts:

```powershell
.\.venv\Scripts\python.exe audit\run_block03_integration.py
```

Runner устанавливает `MPLBACKEND=Agg`, task-owned MPLCONFIGDIR, `SKIP_DOCS_BUILD=true`, `-p no:cacheprovider` и writable `audit/block03_integration_test_temp`; manifest сохраняет точные pytest arguments/exclusions. Результат: **1143 passed, 1 failed, 76 warnings in 299.18s**. Raw log — [block03_integration_tests.log](D:/codex/Causalis/audit/block03_integration_tests.log), machine-readable result — [block03_integration_result.json](D:/codex/Causalis/audit/block03_integration_result.json).

Failure: [test_cuped_rct.py:80](D:/codex/Causalis/tests/statistics/test_cuped_rct.py:80), `test_shared_design_and_input_unchanged`. Assert требует object identity `first_ols.pinv_wexog is second_ols.pinv_wexog`. На statsmodels0.15 decomposition пересчитывается; values совпадают, identity нет. Этот failure воспроизводился в original audit; CUPED source/tests B03 не изменял. Не скрыт через xfail/ignore и не снят assertion. Обоснованное исправление cache/batched least squares запланировано в B05. **Это не полностью зелёный suite**; проверен весь repository suite вне explicit deferred sensitivity area и docs build.

76warnings включают existing baseline/normalization policies, SCM degenerate interval warning и IV docstring invalid escape warnings. Corrected binary ATT baseline может менять numeric values low-signal warnings; число warnings не используется как доказательство регрессии. OOS aggregate All-NaN grading warning устранён вместе с invalid inference.

Артефакты проверены `.\.venv\Scripts\python.exe audit\verify_block03.py` и `audit\verify_handoff.py`: **217 local links, 45 immutable GitHub links, 19 Python files AST, issues0, sensitivity paths0**. Source freeze соответствует четырём code commits в таблице; после интеграции менялись только documentation/check scripts, без повторного широкого pytest. Scope checker сохраняет отдельные JSON, проверяет links/AST и отсутствие sensitivity path изменений относительно B03 start.

После завершения B03 остановиться. Следующий B04 — DiD: eligibility/pre-controls, normalized cell IF, nuisance-estimation IF, cohort-share aggregation и cluster guards. DGP marginal propensity follow-up из B02 также остаётся отдельным.
