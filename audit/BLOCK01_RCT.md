# B01 — Newcombe CI и параметры RCT

Дата: 2026-10-05. Ветка: `codex/correctness-roadmap`.

## Scope

- SC-05/P1: заменить subtraction Wilson endpoints на Newcombe hybrid score interval без continuity correction.
- SC-10/P2: explicit allowed-set validation для `ci_method` и `se_for_test`.
- Согласовать function docstring с точной CI формулой и независимым выбором z-test p-value.
- Source/test changes только `causalis/scenarios/classic_rct/inference/conversion_ztest.py` и `tests/inference/test_conversion_z_test.py`.
- Sensitivity analysis и остальные estimators не затрагиваются.

## Проверка

Independent reference: `statsmodels.stats.proportion.confint_proportions_2indep(..., method='newcomb', compare='diff')`. Cases: исходный counterexample7/34vs1/34, ordinary rates, zero-success arm, all-success arm, rare events, unequal sample sizes; alpha.01/.05/.10. Дополнительно group-swap sign symmetry и invalid options. Existing RCT tests проверяют сохранённые p/relative/Wald paths.

## Статус

Первый block выбран, реализация и тесты выполняются. Фактические результаты и commit будут записаны перед завершением.
