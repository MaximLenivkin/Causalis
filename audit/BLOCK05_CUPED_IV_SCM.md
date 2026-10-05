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
