# Аудит Causalis

Начать с [REPORT.md](D:/codex/Causalis/audit/REPORT.md). Это итог полного ревью на commit `ffe2c356c115f335b74b2f10117e19fe15585d46`, 5 октября2026.

Текущая разработка в `codex/correctness-roadmap`: [FIX_PLAN.md](D:/codex/Causalis/audit/FIX_PLAN.md), [NEXT_SESSION.md](D:/codex/Causalis/audit/NEXT_SESSION.md). Отдельный файл автору документации — [DOCUMENTATION_HANDOFF.md](D:/codex/Causalis/audit/DOCUMENTATION_HANDOFF.md); настройка GitHub — [GIT_ACCESS.md](D:/codex/Causalis/audit/GIT_ACCESS.md). Sensitivity analysis отложено.

- [PERFORMANCE.md](D:/codex/Causalis/audit/PERFORMANCE.md) — измерения и безопасная оптимизация pandas/NumPy.
- [COVERAGE.md](D:/codex/Causalis/audit/COVERAGE.md) — все области, доказательства и пределы проверки.
- [DML_REVIEW.md](D:/codex/Causalis/audit/DML_REVIEW.md) — основной Unconfoundedness/DML аудит.
- [SCENARIOS_REVIEW.md](D:/codex/Causalis/audit/SCENARIOS_REVIEW.md) — остальные causal scenarios.
- [CONTRACTS_SHARED_DGP.md](D:/codex/Causalis/audit/CONTRACTS_SHARED_DGP.md) — contracts/shared/DGP.
- [DOCS_RESEARCH.md](D:/codex/Causalis/audit/DOCS_RESEARCH.md) — документация, статьи и идеи.
- [PLAN.md](D:/codex/Causalis/audit/PLAN.md), [PROGRESS.md](D:/codex/Causalis/audit/PROGRESS.md) — план и журнал.

Scripts/JSON/logs сохраняют воспроизведения исходного аудита, pytest и benchmark. `docs_build_check/` — изолированная копия для проверки сборки API. На этапе исходного ревью код не менялся; после него начата разработка. Выполненные fixes и tests указаны в [BLOCK01_RCT.md](D:/codex/Causalis/audit/BLOCK01_RCT.md), [BLOCK02_CONTRACTS_SHARED_DGP.md](D:/codex/Causalis/audit/BLOCK02_CONTRACTS_SHARED_DGP.md), [BLOCK03_DML_GATE_UPLIFT.md](D:/codex/Causalis/audit/BLOCK03_DML_GATE_UPLIFT.md), [BLOCK04_DID.md](D:/codex/Causalis/audit/BLOCK04_DID.md) и NEXT_SESSION.md. B04 завершён: DiD controls/full MLE-OLS IF/aggregate shares/cluster inference; **1238 passed,1 known baseline SC-12 failed**,7sensitivity test modules исключены. На границе B04 CUPED baseline fix был запланирован для B05; теперь выполнен, см. последний статус ниже. Старые audit probes описывают первоначальные defects и не все подходят как post-fix regression scripts.

Предыдущий блок **B05 завершён**: [BLOCK05_CUPED_IV_SCM.md](D:/codex/Causalis/audit/BLOCK05_CUPED_IV_SCM.md). CUPED names/stable SVD/HC/batch, IV resolver/refit state и ASCM placebo config; SC08LOO deferred. **1376 passed,0failed,77warnings**,7sensitivity modules исключены; старый SC12 failure исправлен. Local fitbenchmark1.73–2.90x при совпадающихATE/SE, scope/limits в отчёте. B06 compatibility/CI/performance завершён; актуальный результат ниже.

Предыдущий **B06**: [BLOCK06_COMPATIBILITY_PERFORMANCE.md](D:/codex/Causalis/audit/BLOCK06_COMPATIBILITY_PERFORMANCE.md). Compatibility/CI/performance завершены: **1582 passed, 0 failed/skipped, 77 warnings, 400.95s**. Pydantic>=2, full release gate, duplicate screening, linear binary checks, bounded KDE и NumPy1.x IV fix. Все6Linuxjobs прошли1582cases; exact source09e00de и [CI evidence](D:/codex/Causalis/audit/block06_ci_result.json). Owned arrays audit-only; sensitivity/Sphinx/release не подтверждались.

Предыдущий **B07 завершён**: [BLOCK07_EDGE_CORRECTNESS.md](D:/codex/Causalis/audit/BLOCK07_EDGE_CORRECTNESS.md). Восстановлена earliest universal DiD pre-cell; binary/multi и shared IV helper отклоняют неконечные nuisance predictions до probability repair. DGP calibration/copula docstrings уточнены без runtime изменений. **147 новых cases; 1729 passed, 77 warnings, 404.84 s** локально; каждый из6CIjobs —1729passed без failures/errors/skips. Final sourcea2109a6,7sensitivitymodules deferred; [CI evidence](D:/codex/Causalis/audit/block07_ci_result.json). Portable handoff дополнен B07,81immutablelinks проверены. B08 выполнен; актуальный статус ниже.

Текущий **B08 завершён**: [BLOCK08_DGP_CONTRACTS.md](D:/codex/Causalis/audit/BLOCK08_DGP_CONTRACTS.md). DGP finite/shape contracts, stable target-weight normalization, singleton-safe coverage repair и explicit iid policy. **187newcases;1916passed0failures/errors/skips78warnings400.69s** local; each6Linuxjobs1916passed, [verified CI](D:/codex/Causalis/audit/block08_ci_result.json). Source9fb8041,7sensitivitymodulesdeferred,85handofflinksverified. Следующий candidate — confirmed P2 namespace collisions; B09 не начат.