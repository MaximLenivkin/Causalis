# B07: первый наблюдаемый pre-period в universal DID

Дата: 2026-10-06. Исходный checkpoint: `c234e647e010f5d8bfb805af7ece61392e327537`. Sensitivity analysis вне этого изменения.

## Подтверждение ошибки

`PanelDataDID.att_gt_cells(include_pre_periods=True)` начинал target enumeration с analysis index 1 для обоих base policies. Для varying base предыдущая наблюдаемая дата обязательна, поэтому index 0 не имеет пары. Для universal base поздняя фиксированная дата `g - anticipation - 1` позволяет контраст с первым наблюдаемым периодом. Такой контраст ошибочно отсутствовал даже при полном support. Особенно заметен случай двух наблюдаемых pre-periods: единственный ненормализованный universal placebo пропускался целиком.

Регрессии [test_did_earliest_pre_period.py](../tests/scenarios/did/test_did_earliest_pre_period.py) сначала выполнены на неизменённой реализации. [Baseline](block07_did_before_tests.log): **29 failed / 14 passed, 22.11 s**, exit 1; без warnings. Все 29 failures — отсутствие ожидаемой первой universal cell. Varying enumeration и существующие post-only effects/IF/analytic inference прошли.

Первый [after + neighbors run](block07_did_after_tests.log): **89 passed / 12 failed, 105.92 s**. Эти 12 failures относятся к ошибке нового теста: `did_base_design_table` возвращает `n_control`, но не `n_treated`. Assertion разделён для balance/design tables и дополнен независимой проверкой rank control design. Ошибки библиотеки из этого intermediate run не следуют. Все 58 существующих neighbors и остальные 31 новые cases прошли.

Финальный [исправленный regression run](block07_did_final_tests.log): **43 passed, 28.23 s**, exit 0, без warnings. Вместе с 58 неизменёнными neighbors из предыдущего run проверены 101 уникальный case; это два runs, а не один выдуманный combined pass. Весь integration запуск и его source checkpoint фиксирует root в отчёте B07. Native threads=1, matplotlib Agg; Python — `.venv/Scripts/python.exe`; basetemp и matplotlib cache находятся в ignored `audit/block07_did_test_temp`.

## Независимые проверки

43 cases, без вызова sensitivity tests:

- 16 date-pair properties: universal/varying × anticipation 0/1 × M/2M × исходная/обрезанная по start time axis. Reference строится из математических пар наблюдаемых дат; сохраняются порядок cohort/time, event-time units и уникальность cells.
- 4 коротких pre-window cases: fixed base index 0 не создаёт placebo; fixed base index 1 создаёт первый placebo. Нормализованная fixed-base row по-прежнему отсутствует.
- 12 downstream cases: три control policies × anticipation 0/1 × balanced/unbalanced panel. Поддержка, оценённая cell, raw event study, covariate balance и design diagnostics используют одну earliest pair и независимо заданные complete unit sets. Проверяются available/complete counts и ручной raw DID. DataFrame имеет shuffled rows и повторяющийся произвольный index; validated snapshot не изменяется.
- 4 exact placebo references: DR/IPW × anticipation 0/1. Intercept-only ATT совпадает с ручной разностью средних outcome changes. Гетерогенные slopes дают ненулевую SE; IF сверяется с независимыми contamination derivatives разности двух эмпирических средних, включая полный unit-score vector.
- 3 unsupported cases: нет ни одной complete treated pair, нет ни одной complete control pair, нет eligible future control cohort. Cell появляется только в unsupported support table с конкретным reason; missing-pair cases не создают estimate.
- 4 compatibility cases: anticipation 0/1 × balanced/unbalanced. Включение pre cells сохраняет post point estimates, IF, SE, обычные analytic intervals и simple/cohort/calendar/post-event aggregates; сравнение идёт по cohort/time, поскольку cell IDs закономерно сдвигаются.

## Ограничения и migration

Исправление расширяет набор диагностических pre-treatment contrasts. Оно не меняет определение post ATT, fixed/varying base, comparison eligibility или IF. Это placebo analysis, а не идентификация causal effect до treatment.

Проверены первичные источники 2026-10-06: [официальный `did::att_gt` reference](https://bcallaway11.github.io/did/reference/att_gt.html) описывает universal fixed base, дополнительную раннюю оценку и одинаковые post-treatment ATT для base policies. [Текущий `compute.att_gt` source](https://raw.githubusercontent.com/bcallaway11/did/master/R/compute.att_gt.R) использует `tfac=0` для universal и `tfac=1` для varying, включая первый observed target только для universal. Это подтверждает date enumeration; полная численная идентичность двух библиотек не заявляется. В частности, существующая политика Causalis исключает нормализованную fixed-base zero row, а неполные panels анализируются через complete pairs.

Docstrings `att_gt_cells` и estimator уточняют earliest target и разницу base policies. В refutation diagnostics root также исправил пять parameter lists `control_group`: существующая опция `not_yet_treated` ранее отсутствовала в документации. Raw-event notes теперь описывают fixed/varying base с anticipation и earliest target. Это исправления prose; eligibility runtime не изменяется.

Для старых estimates требуется refit. First universal pre cells получают новые cell IDs; event tables могут получить более ранние negative event times. Uniform bands, joint pre-tests и прочие процедуры на всём семействе cells могут измениться при расширении семейства, даже если существующие post estimates/IF совпадают. Их инвариантность намеренно не заявляется. Нормализованная fixed-base zero row не добавляется.

Проверки не доказывают parallel-trends assumptions и не заменяют Monte Carlo coverage audit. Общий B07 integration результат записывается отдельно после root verification.
