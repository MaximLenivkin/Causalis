# B04 / SC-02: eligibility и unit alignment

Дата: 2026-10-05. Исходный checkpoint B03: `f57f2d32d232e5ab0b358153f6ac564e615d19c3`. Это заметки по SC-02; полный блок B04 также меняет cell/aggregate inference отдельно.

## Подтверждённая проблема

При `include_pre_periods=True` собственная когорта попадала одновременно в treated и not-yet-treated control population. При universal base control eligibility проверялась только по более раннему target: controls могли уже получить treatment к более позднему base. В cell повторялись unit IDs, ATT менялся, а сборка full-panel scores перезаписывала один вклад другого. Ошибка затрагивала support contract, estimator и raw/balance/design refutations; локального patch одного estimator недостаточно.

Независимый placebo fixture: focal cohort в мае, target февраль, universal base апрель; focal untreated slope 2, допустимые controls slope 0. Верный placebo ATT = `2 × (1 − 3) = −4`. Ранее early/middle cohorts с эффектом +100 и собственная focal cohort ошибочно входили в controls. Тест проверяет ручную разность изменений, уникальные unit IDs и точную membership, а не повторяет score formula.

## Единое правило

Для каждой пары `(base, target)` используем analysis-period cutoff `max(index(base), index(target)) + anticipation`. Comparison unit:

- никогда не принадлежит оцениваемой cohort;
- never-treated допустим только для `never_treated` / `not_yet_or_never`;
- будущая cohort допустима только для `not_yet_treated` / `not_yet_or_never` и если её first-treatment index строго больше cutoff;
- complete pair дополнительно требует обе наблюдаемые outcome rows.

Для post cells threshold совпадает с прежним target rule. Universal pre cells используют поздний base, varying pre cells — поздний target. Конструкция обеспечивает disjoint treated/control populations до nuisance fitting и сохраняет исходный порядок units. Support available counts и complete counts имеют разные значения при unbalanced panel и проверяются отдельно.

Это соответствует control-cohort exclusion и threshold по позднему outcome period в [официальном `did::compute.att_gt` implementation](https://raw.githubusercontent.com/bcallaway11/did/master/R/compute.att_gt.R), проверенном 2026-10-05, строки 340–344 и 404–407 текущего источника. Это reference eligibility, а не заявление о полной численной идентичности библиотек или повторная проверка identification assumptions.

## Реализация и API

- Новый pure helper [\_did_comparison_units.py](../causalis/data_contracts/_did_comparison_units.py) принимает validated unit/cohort/time metadata; не зависит от estimator или pandas и не создаёт import cycle.
- [PanelDataDID](../causalis/data_contracts/panel_data_did.py) использует helper в `att_gt_cells` и public `comparison_units`.
- [DID refutation diagnostics](../causalis/scenarios/did/refutation/diagnostics.py) использует тот же helper для raw event study, covariate balance и control-design tables.
- Root интегрировал helper в [DID model](../causalis/scenarios/did/model.py): внутренний wrapper получает `cohort`, `base_time` и `target_time`, `_fit_cell` передаёт полную пару.

Public `comparison_units(cohort, time)` сохраняет существующий post-only guard и default results. Добавлены optional keyword `base_time=None`, `anticipation=0`; omitted base использует `time`. Query за пределами наблюдаемой post axis остаётся допустимым: локальный time index расширяется ordinal offsets, делёнными на frequency multiplier. Проверены monthly `M` и `2M`. Контракт уже требует gap-free глобальную time axis; incomplete unit histories разрешены как прежде. Общая existing integer coercion anticipation в B04 не менялась.

Migration: pre-placebo ATT/SE и diagnostic counts могут измениться, ранее fake-supported cells могут исчезнуть. Stored estimates требуют повторного fitting; старые payloads не исправляются при чтении. Never-treated control policy не затронут этой конкретной membership correction. Увеличение скорости не измерялось; preprocessing/NumPy caching остаётся отдельной задачей.

## Проверка

[Новые regression properties](../tests/scenarios/did/test_did_control_alignment.py): 32 cases.

- 24 combinations: три control policies × universal/varying × anticipation 0/1 × balanced/unbalanced. Все support cells сверяются с независимым treatment-date rule, модель и raw/balance/design diagnostics — с membership и complete counts. Arbitrary duplicated DataFrame index и shuffled row order; contract snapshot остаётся неизменным.
- 4 independent exact placebo cases: `dr`/`ipw` × два not-yet control policies.
- 1 unsupported cell, когда единственная untreated cohort — собственная; zero-controls reason обязателен.
- 1 public compatibility case: post guard, default pools, anticipated cutoff, вне-axis post query.
- 2 monthly/multiple-frequency API cases: M/2M, поздний base и extrapolated query.

Baseline [block04_alignment_baseline_checks.log](block04_alignment_baseline_checks.log): source трёх оригинальных modules прочитан через read-only `git show f57f2d3:<path>` и исполнен в изолированных module names; corrected regression functions применены к этим классам. **21 assertion failures / 8 passes** среди 29 checks; новый keyword API не включён. Это сильная baseline проверка исходного checkpoint после исправления ошибки test fixture, без checkout/reset рабочего дерева.

Первый [before log](block04_alignment_before_tests.log): **30 failed, 71.73s**. В 8 never-treated cases причиной была ошибка нового теста: design table запросил default `post_only=True`, хотя проверялись pre cells. Исправлено `post_only=False`; эти восемь failures не являются дефектами библиотеки. Остальные 22 cases включали одну проверку нового optional API.

Промежуточный [after log](block04_alignment_after_tests.log): **20 failed / 10 passed, 56.90s**. Этот Python process импортировал старый model wrapper до применения root integration; contract/refutation уже были обновлены. Он не проверяет завершённую реализацию.

Финальный [focused + existing neighbors log](block04_alignment_final_tests.log): **56 passed, 69.81s**, без warnings — первые 30 новых cases плюс existing panel-data и DID pre-fit refutation tests. Два последних frequency/date API cases проверены отдельно: **2 passed / 30 deselected, 11.12s**, без warnings, [date API log](block04_alignment_date_api_tests.log). Общий B04 integration должен включить все 32 cases; counts этих focused runs нельзя складывать с пересекающимися suite counts.

## Отдельный follow-up

Существующая `att_gt_cells` enumeration начинает любой pre target с index 1. Varying base требует предыдущую observation, но universal base допускает сравнение index 0 с более поздним fixed base; earliest universal placebo сейчас отсутствует. В SC-02 эту enumeration сознательно не расширяли: поведение требует отдельного API/support change, проверки порядка и downstream event tables. Этот пункт не считать исправленным B04.

Sensitivity implementation/tests не редактировались. Эти properties проверяют comparison population и row alignment; identification и general Monte Carlo coverage не следуют из их прохождения.

## Готовый английский migration paragraph

> Pre-treatment placebo cells now exclude their own treatment cohort from the comparison group. A not-yet-treated comparison unit must remain untreated, including the anticipation window, at both the base and target dates. For universal pre-treatment bases, eligibility is therefore evaluated at the later base date. Support counts, fitted cell populations and raw, balance and design diagnostics use the same rule. Refit existing estimates to obtain corrected placebo estimates and inference. The public `comparison_units` convenience method remains restricted to post-treatment queries and accepts optional `base_time` and `anticipation` keywords.
