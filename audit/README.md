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

Scripts/JSON/logs сохраняют воспроизведения исходного аудита, pytest и benchmark. `docs_build_check/` — изолированная копия для проверки сборки API. На этапе исходного ревью код не менялся; после него начата разработка. Выполненные fixes и tests указаны в [BLOCK01_RCT.md](D:/codex/Causalis/audit/BLOCK01_RCT.md) и NEXT_SESSION.md. Старые audit probes описывают первоначальные defects и не все подходят как post-fix regression scripts.
