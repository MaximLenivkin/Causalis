# B11 · Защита имён binary/IV генераторов

Baseline: `4d6b8143db7a93c1a7eba371fcd144878d80c896`. Scope: `causalis/dgp/causaldata/base.py`, `causalis/dgp/causaldata_instrumental/base.py` и новый regression module `tests/data/test_binary_iv_namespace_contract.py`. Source/tests checkpoint и итоговые результаты записываются в `BLOCK11_NAMESPACE.md` после проверки и commit.

Раньше confounder `d` перезаписывал бинарное treatment, confounder `y` — outcome, повторяющиеся actual X names — предыдущий признак. Включённые oracle columns могли перезаписать confounder или IV instrument. Новый inherited validator проверяет nonempty string names и uniqueness с сообщением, содержащим имя и две конфликтующие роли.

`_output_column_roles` выбирает фактический namespace каждой семьи. Binary: `y`, `d`, шесть enabled oracles (`m`, `m_obs`, `tau_link`, `g0`, `g1`, `cate`). IV: `y`, `d`, `instrument_name`, четырнадцать enabled IV oracles (`m`, `r_obs`, `r_z0`, `r_z1`, `g_z0`, `g_z1`, `iv_first_stage`, `iv_reduced_form`, `late_x`, `late`, `tau_link`, `g_d0`, `g_d1`, `cate`). IV не резервирует binary-only `m_obs`, `g0`, `g1`; binary не резервирует IV-only names.

Fixed names проверяются при construction и на каждом `generate`. Actual confounder names и их количество относительно X width проверяются после успешного X sampling, до U, calibration, structural callbacks, treatment и outcome draws. Непосредственно перед DataFrame assembly full check повторяется: независимое ревью выявило, что callback может включить oracle или изменить `instrument_name` после раннего guard и вновь вызвать overwrite.

Имена сохраняют точное написание, включая whitespace и NumPy strings. Отключённые oracle names доступны. Категориальные names проверяются после existing expansion/string rendering, а custom sampler сохраняет прежнюю one-column-per-spec naming policy. Sampling, family-specific oracle arithmetic, RNG calls, public signatures и conversion feature selection не переработаны. Confounder-spec fallbacks не ужесточены.

Scope ограничен raw core generators. Wrappers наследуют их проверки, но собственные ancillary/preperiod fields, ordering и conversion exclusions требуют отдельной проверки. Это не обещание полной schema validation всех DGP wrappers. General custom-X shape/finite validation, arbitrary callback side effects и numerical oracle accuracy также не входят в B11.

Все проверки используют синтетические fixtures. Нет изменения estimator formulas, DiD diagnostics, sensitivity implementation или CI exclusions. Итоговые baseline/focused/reference/local/CI evidence и ограничения — в отчёте этапа.
