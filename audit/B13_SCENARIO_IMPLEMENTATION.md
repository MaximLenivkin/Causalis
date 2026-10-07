# B13: namespace граница classic RCT scenario

Baseline: `9f0a63c42308ca886d92dc73d8d9611d5b2c31`. Изменён один библиотечный модуль: `causalis/scenarios/classic_rct/dgp.py`, оба публичных helper `generate_classic_rct_26` и `classic_rct_gamma_26`.

При включённом pre-period столбце helper проверяет роли, которые добавляет сам scenario: outcome (`conversion` в первом helper, `y` во втором) и идентификатор `user_id`. Scenario всегда возвращает идентификатор, даже при `add_ancillary=False`; pre-поле с таким именем теперь отклоняется через `ValueError`, а не используется как ID. Проверка срабатывает до генерации. `add_pre=False` не резервирует `pre_name`, как и в B12. Неверные типы включённого pre-имени по-прежнему проверяет underlying wrapper.

После underlying binary generation существующий shared guard проверяет фактическую DataFrame-схему перед поздним `y → conversion` переименованием и созданием scenario ID. Это защищает назначение outcome, даже если фактический schema отличается от объявленной конфигурации. Ошибка сообщает имя и конфликтующие роли; автоматического переименования нет.

Automatic conversion исключает `m`, `m_obs`, `tau_link`, `g0`, `g1`, `cate` только при включённых oracle-колонках. При `include_oracle=False` numeric pre-поля с этими именами сохраняются как признаки. `conversion` остаётся допустимым pre-признаком Gamma scenario. Numeric/finite/constant/duplicate-value проверки `CausalData` не менялись.

Публичные сигнатуры, sampling, calibration, assignment, ID algorithms и численные формулы не изменены. Для корректно классифицированных допустимых конфигураций требуется точное сравнение frames, схемы, типов, metadata и RNG с baseline. Для ранее потерянных pre-признаков намеренно меняется feature list; их исходные значения и raw schema сохраняются. Ранее некорректные конфигурации с конфликтом outcome/ID теперь завершаются ошибкой.

CUPED26 и offer-IV имеют отдельные существующие правила. Их source не менялся: CUPED с двумя pre-полями использует внутренние oracle-поля даже при их отключении в конечном output; offer-IV имеет фиксированные имена core и confounders без публичных name knobs. Эти пути служат контролями совместимости, без изменения их parameter policy. DiD numerical-zero diagnostics и sensitivity не входят в B13.

Независимые baseline/focused tests и review evidence находятся в `B13_SCENARIO_TESTS.md` и `B13_SCENARIO_REVIEW.md`. Итоговые integration/CI результаты записываются в `BLOCK13_SCENARIO_NAMESPACE.md` после проверки committed source.

Precommit focused verification: новый модуль `tests/data/test_scenario_namespace_contract.py` — **91 passed**, 0 failures/errors/skips/warnings, 4.37 s. Exact baseline на том же окончательном test module — **28 failed / 63 passed**, 0 errors/skips, 4.79 s. Эти counts относятся к параметризованным cases, не к числу отдельных дефектов. Raw-to-contract reference учитывает штатную normalization treatment к `int8`; все остальные значения и dtype comparisons остаются строгими.
