# B04 — DiD inference

Начало: 2026-10-05. Base checkpoint `f57f2d32d232e5ab0b358153f6ac564e615d19c3`, branch `codex/correctness-roadmap`. Local/remote checkpoint совпадают; рабочее дерево на старте чистое.

## Scope и ход работы

- SC-02: единые правила controls для support, модели и refutation; исключение собственной когорты и untreated на обе даты с anticipation. В работе, parallel agent.
- SC-01/03: полный IF фактически используемого normalized IPW / traditional MLE+OLS DR estimator. Сохранить point estimator, учитывать nuisance estimation, ridge и clipping. В работе, parallel agent.
- SC-04: random estimated cohort/complete-pair shares в simple/calendar/event aggregation. В работе, root; независимая derivation подтверждена review agent.
- SC-11: единый запрет inference с одним cluster, включая multiplier bootstrap. В работе, root.
- Независимый methodology review; после focused checks — suite вне deferred sensitivity.

Sensitivity implementation/tests не меняются. SC-12 CUPED остаётся известным baseline failure до B05. Исторические отчёты не переписываются. Итоговые SHA, evidence и ограничения будут записаны на границе блока.

## Checkpoint: clustered inference

SC-11 исправлен: analytical и bootstrap paths требуют >=2 clusters. `bootstrap_replications=1` теперь отвергается (sample SD с ddof=1 не определён). Cluster Rademacher draws центрируются по clusters и масштабируются на sqrt(C/(C-1)): их conditional covariance совпадает с уже существующей аналитической covariance, включая cross-cell terms. Это согласование second moments, не гарантия coverage при малом числе clusters.

Before: **8 failed, 2 passed**, 20 warnings, 14.55s. После: **10 passed**, 7.32s. Evidence: `block04_cluster_before_tests.log`, `block04_cluster_after_tests.log`. Независимая проверка перечисляет все 2^3 sign patterns и сравнивает с centered cluster sandwich. Seeded public bootstrap воспроизводим; approximate SE agreement проверен на 2000 repetitions.
