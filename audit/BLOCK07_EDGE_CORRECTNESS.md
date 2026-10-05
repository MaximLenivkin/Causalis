# B07 — граничные случаи DiD и nuisance predictions

Дата: 2026-10-06 (Europe/Moscow). Начальный checkpoint: `c234e647e010f5d8bfb805af7ece61392e327537`; ветка `codex/correctness-roadmap`.

## Scope и порядок

1. **B07-DID, P2:** восстановить earliest universal pre-treatment comparison. Фиксированный base не требует периода до target; varying base по-прежнему требует его. Проверить support, модель, event/diagnostic tables, missing pairs, anticipation, короткое pre-window и сохранение post-treatment inference.
2. **B07-NUISANCE, P2:** binary/multi IRM должны отклонять NaN и бесконечные прогнозы до clipping/normalization и сохранения. Infinity могла превращаться в допустимую propensity/outcome probability или сохраняться как continuous outcome prediction. Сохранить существующую политику для конечных прогнозов и сверить нормальный fit с независимой прежней реализацией. Финальный severity P2: это missing learner-output guard; ошибки score на корректных finite predictions не обнаружены.
3. Независимое ревью DGP oracle semantics подготовит следующую задачу. Изменение смысла `m_<arm>` и новый marginal-propensity API в этот блок не входят.

Каждый fix: воспроизведение до patch → independent regression/reference → patch → focused neighbors → отдельный commit. Затем integration с прежними семью явными sensitivity exclusions, portable documentation handoff, итоговый отчёт, continuation и push в личный fork.

Sensitivity analysis, SC-08 leave-one-donor-out, generic sensitivity/refit lifecycle, новые causal estimators, snapshot API и docs-build gate остаются вне B07. Полный исторический аудит не повторяется. Реальные результаты и commit SHA будут дописаны по завершении.

## Progress

- Начало: workspace чист, local HEAD/tracking/remote SHA совпадают; авторизация и personal fork действуют.
- Подтверждён DiD enumeration defect; primary reference проверен: [официальный did::att_gt](https://bcallaway11.github.io/did/reference/att_gt.html) и [compute.att_gt](https://raw.githubusercontent.com/bcallaway11/did/master/R/compute.att_gt.R). Universal и varying используют разные начальные targets; это не заявление о полной идентичности R/Python inference.
- Три параллельных subagents: независимые DiD tests, nuisance boundary fix, read-only DGP follow-up. Root: scope, DiD implementation, review, integration и Git checkpoints.

## Реализовано

**B07 завершён.** Финальный library/tests checkpoint: **`a2109a6ecd3c8422fbd4e8a7fd8d5d59334e8159`**, отправлен в личную ветку. Добавлено **147 cases**: 43 DiD и 104 nuisance. Локальная Windows/Python 3.12.14 integration: **1729 passed, 0 failures/errors/skips, 77 warnings, 404.84 s**, exit 0. **Все шесть CI jobs прошли: каждый — 1729 passed, 0 failures/errors/skips.** Exact source, exclusions, installed versions и JUnit artifacts подтверждены. Это весь выбранный repository suite вне семи явно отложенных sensitivity modules; полный sensitivity/release/Sphinx pass не заявляется.

| Приоритет | Подтверждённая проблема | Исправление |
|---|---|---|
| P2 / correctness | Неконечный learner output мог скрываться clipping, renormalization, class selection или hard-label fallback; continuous infinity сохранялась в fitted state | Raw finite checks до transformations, binary/multi cross-fit storage checks; shared helper защищает также IV learner outputs |
| P2 / correctness | Earliest universal DiD pre-cell пропускалась, даже когда fixed base и полный support существовали | Universal enumeration с index0; varying/post-only и последующие eligibility/complete-pair guards сохранены |
| P2 / documentation | `target_d_rate` недостаточно ясно описывался как marginal target при latent treatment noise | Explicit sample-X calibration при U=0; systematic latent discrepancy и realized sampling variability различены |
| P2 / documentation | Gaussian-copula latent correlation приписывалась observed X | Corr(Z) отличается от observed Pearson Corr(X) после transforms/clipping |

### Nuisance predictions

Finite input data не гарантируют finite learner outputs. Теперь NaN/±inf в real numeric predictions вызывают `RuntimeError` до probability repairs. Проверяется весь raw probability matrix, включая downstream unused columns, и поддерживаемый hard-label fallback до `np.where`. Последний gap обнаружен независимым review первоначального patch и закрыт до integration.

Finite warning/clip/row-normalization, single-class semantics, thresholds, folds и score/IF formulas сохранены. Binary helper переиспользуется IV для instrument/treatment/outcome nuisance predictions; IV own assembled-storage/refit lifecycle не переработан. Shape/complex contract и overflow arithmetic на огромных, но конечных значениях остаются отдельными задачами.

Final focused set: **191 passed, 1 existing warning, 25.75s** — 104 новых +87 neighboring cases. Прежний broader focused set:222passed4warnings20.90s на94new+128neighbors, до дополнительного fallback fix. Counts пересекаются и не суммируются. Шесть finite sklearn references охватывают binary/multi/IV × binary/continuous outcome, сравнивая predictions, scores и inference с независимым adapter. Serial/threaded invalid-output tests и public-fit storage boundary проверены отдельно.

Historical initial83fail и corrected81fail не являются количеством новых bugs: они включали fixture/API и прежние NaN message differences. Corrected public-fit storage probe использует exact old methods из c234e64:10 infinity rejection failures и5 message-only cases, без fixture errors. Дополнительный fallback before-set дал6missing rejections/4finite passes. Все промежуточные raw logs и интерпретация сохраняются в [B07_NUISANCE_NOTES.md](D:/codex/Causalis/audit/B07_NUISANCE_NOTES.md) и [JUnit summary](D:/codex/Causalis/audit/block07_nuisance_result.json).

### DiD support и inference

Universal fixed base позволяет target в первой наблюдаемой дате; varying base требует предыдущей даты. При двух pre-periods раньше исчезал единственный ненормализованный universal placebo. Fix меняет только начальный target index, затем действуют прежние anticipation, eligibility и complete-pair rules.

Baseline: **29 failed /14 passed,22.11s** — все failures из-за отсутствующей earliest cell. Corrected final43casespassed28.23s,0warnings. Все58existingneighbors прошли в более раннем run, где12новых assertions выявили ошибку test fixture (`design` не содержит `n_treated`); это исправлено в tests и честно сохранено в logs. Combined101case run не заявляется.

Independent date-pair references охватывают M/2M, anticipation0/1, start filtering, короткое pre-window, все control policies, unbalanced/missing pairs и unique/order checks. Ручная разность средних, ненулевая SE и contamination IF проверены для DR/IPW. Post point estimates, scores, analytic intervals и post-only aggregates совпадают при включении pre cells. Cell IDs и семейство pre contrasts могут расширяться; simultaneous bands/joint pre-tests могут измениться. Old estimates требуют refit. Normalizing zero-row не добавлена. Диагностические docstrings также перечисляют уже поддерживаемый `not_yet_treated`.

Подробности, первичные источники и logs — [B07_DID_NOTES.md](D:/codex/Causalis/audit/B07_DID_NOTES.md). Parallel-trends identification и general coverage из этих regressions не следуют.

### DGP documentation и следующая oracle задача

Два DGP paths имеют executable AST equality с начальным checkpoint: изменена только документация. `target_d_rate` калибрует sample average softmax при U=0, а не integral over latent noise. No-X example target[.2,.3,.5], latent slopes[0,2,2] даёт Gaussian-marginal rates[.299729,.262602,.437670]; такой gap не исчезает с ростом n. Copula задаёт Corr(Z), а не автоматически observed Corr(X).

`m_<arm>` и `m_obs_<arm>`, RNG и generated values сохранены. Missing marginal propensity API и selection-weighted ATT при latent confounding подготовлены как отдельное additive API предложение, включая accuracy/reference-law/rare-arm sampling policy. Это не реализованные B07 features и не повторно открытый ROOT-01 outcome fix.

Derivation, independent adaptive integration, numerical evidence и validation plan — [B07_DGP_REVIEW.md](D:/codex/Causalis/audit/B07_DGP_REVIEW.md). Независимое финальное code/method review — [B07_METHOD_REVIEW.md](D:/codex/Causalis/audit/B07_METHOD_REVIEW.md).

## Commits и проверка блока

- **43f0b3e170f28138fb0155ee99d3680d373b5d52** — DiD earliest cell, regressions, API docs и baseline evidence.
- **d3b67096dd847792b3b6f79b2a2d43749cab30b0** — factual DGP doc-only corrections, adaptive probes и последующий API plan.
- **a2109a6ecd3c8422fbd4e8a7fd8d5d59334e8159** — finite nuisance boundaries, fallback guard и focused/reference evidence; последний source/tests checkpoint.

После source checkpoint меняются только audit artifacts. Integration: [selection](D:/codex/Causalis/audit/block07_integration_selection.json), [result](D:/codex/Causalis/audit/block07_integration_result.json), [raw log](D:/codex/Causalis/audit/block07_integration_tests.log). [CI run37385736343](https://github.com/MaximLenivkin/Causalis/actions/runs/37385736343) успешно завершён на том же source. [CI artifact result](D:/codex/Causalis/audit/block07_ci_result.json): snapshot2026-10-05T23:02:17.8244687Z (6октября, Europe/Moscow),6verifiedjobs,issues0. Passing B06 matrix не подменяет B07 evidence.

| Linux job | Python actual | NumPy | pandas | sklearn | Pydantic | Cases | Runner seconds |
|---|---|---|---|---|---|---:|---:|
| 3.10 legacy | 3.10.21 | 1.26.4 | 1.5.3 | 1.3.2 | 2.0.3 | 1729passed | 132.90 |
| 3.10 latest | 3.10.21 | 2.2.6 | 2.3.3 | 1.7.2 | 2.13.5 | 1729passed | 129.00 |
| 3.11 latest | 3.11.16 | 2.4.6 | 3.0.6 | 1.9.1 | 2.13.5 | 1729passed | 124.62 |
| 3.12 latest | 3.12.14 | 2.5.3 | 3.0.6 | 1.9.1 | 2.13.5 | 1729passed | 86.70 |
| 3.13 latest | 3.13.15 | 2.5.3 | 3.0.6 | 1.9.1 | 2.13.5 | 1729passed | 111.39 |
| 3.14 latest | 3.14.7 | 2.5.3 | 3.0.6 | 1.9.1 | 2.13.5 | 1729passed | 118.97 |

Full environment manifests, SciPy/statsmodels/CatBoost versions, timestamps и per-job JUnit counts сохранены в JSON. Это representative Linux stacks, не все dependency combinations/OS; Sphinx build и sensitivity не подтверждаются. Время CI не является performance benchmark. Broad benchmark B06 не повторялся: B07 добавляет обязательные guards, а не заявляет новое ускорение.

Portable [DOCUMENTATION_HANDOFF.md](D:/codex/Causalis/audit/DOCUMENTATION_HANDOFF.md) дополнен тремя B07 migration/factual sections и immutable sources; 81 snapshot link проверяются [verify_handoff.py](D:/codex/Causalis/audit/verify_handoff.py). Source/function whitelist, doc-only executable AST, selection/JUnit/CI и local artifact links проверяются [verify_block07.py](D:/codex/Causalis/audit/verify_block07.py); результат — [validation evidence](D:/codex/Causalis/audit/block07_validation_checks.json).

Финальная проверка: **issues 0**; 17 Python AST files, 331 local artifact links, 9 library paths, 4 doc-only modules и whitelist из 8 изменённых function bodies. Score/IF/Jacobian/estimation/aggregation вне whitelist совпадают с исходным executable AST. Sensitivity paths changed:0; source changes после integration:0. Portable handoff:81immutable links, issues0. Повторные suite/benchmark runs после prose edits не требовались.

Sensitivity и SC08LOO отложены. Новый oracle API, extreme/shape/complex guards, normalized custom-ATE near-boundary policy, snapshot arrays и dedicated Sphinx gate не включены в B07. Standalone docs build, полный sensitivity suite, release/tag/PyPI и upstream merge/rebase не выполнялись. Финальный audit commit определяется `git log -1`; обычный push сохраняет все checkpoints без переписывания истории. Работа останавливается на границе B07; B08 начинается отдельным запросом пользователя. Для следующего контекста — [NEXT_SESSION.md](D:/codex/Causalis/audit/NEXT_SESSION.md).
