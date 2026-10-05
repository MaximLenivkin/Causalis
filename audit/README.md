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

Последний блок **B05 завершён**: [BLOCK05_CUPED_IV_SCM.md](D:/codex/Causalis/audit/BLOCK05_CUPED_IV_SCM.md). CUPED names/stable SVD/HC/batch, IV resolver/refit state и ASCM placebo config; SC08LOO deferred. **1376 passed,0failed,77warnings**,7sensitivity modules исключены; старый SC12 failure исправлен. Local fitbenchmark1.73–2.90x при совпадающихATE/SE, scope/limits в отчёте. Следующий B06 compatibility/CI/performance начинается после нового запроса пользователя.
