# B12: wrapper augmentation, ordering и actual conversion roles

Дата: 2026-10-07, Europe/Moscow. Frozen baseline: `eb6dfe23f0a97991b6e3d6109febc1b0170e128d`. Reviewer читает library/tests и меняет только этот документ и собственные [probe](block12_contract_probe.py), [result](block12_contract_result.json). Library, tests, commits/push, integration и CI этим reviewer не изменялись/не запускались. B11 core namespace context: [contract](B11_NAMESPACE_CONTRACT.md), [review](B11_NAMESPACE_REVIEW.md).

## Предлагаемый минимальный контракт

Namespace задаётся **фактически выполняемыми** стадиями. Low-level binary выдаёт `y`, `d`, actual sampled/expanded X и шесть enabled binary oracles; IV добавляет actual instrument и использует свои четырнадцать enabled oracles. Сам low-level generator не добавляет identifier. B11 string, fallback, categorical-expansion и family-specific enabled-oracle rules сохраняются.

Wrapper дополнительно резервирует только реально создаваемые поля:

| Стадия | Когда выполняется | Добавляемые роли |
| --- | --- | --- |
| Pre-period | `add_pre=True` | Единственная literal column `pre_name` |
| Ancillary | `add_ancillary=True` | Identifier `user_id`; features `age`, `cnt_trans`, `platform_Android`, `platform_iOS`, `invited_friend` |
| Tweedie latent diagnostic | `make_cuped_tweedie`, `add_pre=True`, enabled oracle branch | `_latent_A` |

Ни одна добавляемая роль не заменяет существующую колонку и не пересекается с другой добавляемой ролью. Конфликт даёт contextual `ValueError`; invalid actual added name также даёт `ValueError`. String сохраняется буквально: `np.str_` и ненулевая whitespace string допустимы, без strip/coerce/suffix. Unused `pre_name` при `add_pre=False` не создаёт pre-role и не участвует в исключении X или column projection. Например, `pre_name='y'` при disabled pre-step сохраняет один outcome `y`.

Shared ancillary helper должен проверять все шесть добавляемых имён **до** score/RNG draws и assignment; существующий `user_id` сейчас падает лишь на позднем insert, а остальные пять overwrite. Shared preperiod helper проверяет `pre_name` до `base_builder` и noise; повторный check перед assignment нужен, если callback добавил это имя во время вычислений. Caller может заранее проверить совокупность planned additions, чтобы `pre_name='age'` при enabled ancillary не выполнял ненужный pre-period computation перед предсказуемым конфликтом. Это namespace validation, без нового общего X-shape/finite/calibration контракта.

## Actual roles при conversion и ordering

Automatic confounder selection должен использовать actual sampled X names, а для wrapper — эти имена плюс реально добавленные numeric ancillary/pre features. Enabled oracle, outcome/treatment/instrument и реально добавленный identifier не являются features. Само совпадение строки с disabled oracle token не создаёт oracle-role. Строка `user_id` также не создаёт ID-role, если это actual X либо IV instrument, а ancillary stage выключен.

Следовательно:

- Binary/IV low-level actual X `user_id` остаётся feature, contract `user_id=None`.
- IV actual instrument `user_id` при ancillary off остаётся instrument; contract `user_id=None`. Если ancillary on, это actual instrument/identifier collision и guard отклоняет augmentation.
- Disabled oracle names, например binary X `m`/`g0` или IV X `r_obs`, остаются features. Эти же X используются для pre-period baseline и ancillary computation.
- IV instrument `m` либо `r_obs` допустим при disabled IV oracles и должен встречаться один раз. Family-specific names вроде IV instrument `m_obs` не становятся IV oracle-role при enabled IV oracles.
- Multi low-level/wrapper уже использует `confounder_names_`, не назначает implicit identifier и служит unchanged regression control.

Публичные explicit `confounders='name'`/list должны сохранить текущую selection/filtering policy; actual-role metadata меняет default selection. Если caller явно выбрал oracle column, существующий data contract решает допустимость её значений/вариации. B12 не должен расширять numeric, constant, finite или missing-column validation.

Стабильная raw RCT projection: реально добавленный identifier, `y`, `d`, actual X и ancillary features, реально добавленный pre-period feature, enabled binary oracles. IV: реально добавленный identifier, `y`, `d`, actual instrument, actual X и ancillary features, enabled IV oracles. Группы не повторяют одну роль, а внутри groups сохраняется прежний actual insertion order. `CausalData`/`IVCausalData` сохраняют собственную frame projection/normalization policy; ordering raw wrapper не является поводом менять data-contract classes.

Private successful-generation snapshots решают отличие actual emitted schema от текущих mutable settings. Зафиксировать literal core/oracle roles **и copy actual names** при DataFrame assembly, опубликовать после successful generation. Conversion/wrappers читают этот снимок, а не текущие `include_oracle`, `instrument_name` и unconditional token lists. В IV oracle callbacks могут выполняться после core assembly: на baseline late `g_y` меняет instrument name `z → y`, после чего conversion ошибочно выбирает outcome как instrument, хотя actual core frame содержит `z`. Если include_oracle меняется на False после входа в enabled branch, actual branch всё равно вставляет четырнадцать oracles. Snapshot перед этими callbacks отражает frame правильно. Copy actual names также избегает поздней мутации shared list от overridden `_sample_X`; для обычных built-in/custom-X sampler naming этот alias не возникает.

## Caller coverage

Runtime scope B12 согласован как шесть modules: shared `dgp/base.py`, binary `base.py`/`functional.py`, `preperiod.py`, IV `base.py`/`functional.py`. Multi sources не меняются.

- `generate_rct` и его classic/scenario aliases проходят общий binary wrapper. `add_pre=False` должен полностью исключить pre-role из ancillary-X inference и ordering.
- `obs_linear_effect` также вызывает shared ancillary helper; его X inference должен использовать actual generated X.
- `generate_cuped_binary` использует shared preperiod helper; он автоматически получает collision guard.
- `make_cuped_tweedie` вызывает `_add_tweedie_pre`, который пишет `df[pre_name]` напрямую. Ему нужен тот же added-column contract; `_latent_A` учитывается только в реально enabled latent diagnostic branch.
- `to_causal_data` наследуется IV generator. Его automatic features должны быть actual X, иначе instrument и IV-only oracle names ошибочно становятся binary confounders. Separate `to_iv_causal_data` использует actual instrument role.
- Generic multi wrapper и `to_multicausal_data` служат controls; прямые data-contract constructors с explicit user_id остаются вне runtime change.

## Frozen-baseline evidence

Probe исполняет pinned shared, preperiod, binary, IV и оба functional sources в изолированных in-memory modules с явно rebound helper imports и IV inheritance. Multi sources тоже pinned для controls. Source hashes записаны в JSON; импортируемые data-contract modules проверены byte-identical к baseline. Working-tree edits других агентов не подмешиваются в frozen generation. Evidence содержит только synthetic schemas, types, counts, selected roles и ошибки, без строк generated observations; Pydantic input-frame repr удалён из ошибок.

Всего **133 probe records**, не pytest/integration cases:

- Восьми RCT pre-name settings baseline возвращает frames. `pre_name=y/d/m` даёт duplicate projection и при add_pre=False, и при True. `pre_name=x1`, add_pre=True перезаписывает actual X без duplicate labels. Три unused-name probes также возвращают frames.
- Шесть pre/ancillary overlaps, двенадцать ancillary/confounder overlaps, шесть ancillary/instrument overlaps и шесть standalone-helper overlaps: `user_id` вызывает поздний insert error, остальные пять имён silently overwrites. IV instrument `age` становится nonbinary в 80/80 rows.
- Четырнадцать binary low-level/wrapper conversion records теряют все шесть disabled-oracle X names либо превращают actual X `user_id` в identifier. Тридцать аналогичных IV records дают тот же механизм для четырнадцати IV oracle names и user_id.
- Пятнадцать IV disabled-oracle/instrument ordering records возвращают duplicate columns: четырнадцать oracle-token instruments дублируются core/oracle; `user_id` дублируется в core. Contract return instrument `user_id` отдельно отклоняется из-за implicit identifier-role overlap.
- RCT `add_pre=True`, disabled oracles, actual X `m`/`g0`, `beta_y=[0.5]` падает в двух probes с dimension mismatch: unconditional exclude удаляет единственный X из pre-builder.
- Десять low-level/wrapper multi controls сохраняют `m_0`, `g_0`, `g_1`, `cate_1`, `user_id` как features и user_id=None.
- Восемь standalone preperiod probes допускают overwrite `y/d/x1` и invalid added names None/empty/int; NumPy string и whitespace examples проходят. Ещё один callback probe показывает поздний overwrite имени, добавленного самим base_builder.
- Два inherited IV→binary conversion probes: oracle-off включает instrument `z` в confounders; oracle-on дополнительно включает IV-only oracles и в этом fixture падает на constant r_z0. Это projection bug, не доказательство нового constant-policy defect.
- Две late-IV-mutation probes показывают wrong instrument-role selection и mutation of include_oracle после assembly. Четыре CUPED-helper probes допускают target `y`, enabled pre-step overwrites outcome; один Tweedie `_latent_A` probe допускает pre/diagnostic overwrite.
- Два controls с явно добавленным ancillary ID сохраняют user_id-role и пять ancillary features; generated-ID тесты также проверяют именно этот путь.

## Compatibility и пределы проверки

Untouched correctly classified configurations должны сохранить frames, dtypes, column order, callback arithmetic и RNG draws. Added guards сами не рисуют RNG. Baseline ID tests (`tests/data/test_dgp_user_ids.py`) проверяют ancillary-generated UUID entropy, uniqueness/retry и deterministic IDs; explicit user_id в прямых data-contract constructors остаётся прежним.

Однако полный blanket claim «все ранее valid conversions идентичны» неверен. Actual X user_id раньше implicit становился ID; теперь это feature. Disabled-oracle X раньше выпадал из features и иногда pre/ancillary X. Коррекция таких inputs намеренно меняет selected columns и иногда values/RNG: при прежнем kx=0 ancillary score не рисовал coefficient vectors, а правильный kx>0 их рисует. Для этих misclassified schemas нужна проверка нового actual-role поведения, отдельно от exact unaffected-reference equivalence. Raw disabled-oracle instruments перестают иметь duplicate projection; colliding augmentation теперь отвергается вместо overwrite.

Этот документ формулирует contract и frozen baseline findings. Он **не** заявляет, что candidate/source commit реализовал все рекомендации, прошёл regression suite или сохранил RNG на перечисленных reference cases. Final patch review, integration, CI и commit provenance принадлежат root/reviewer artifacts. DiD, sensitivity, arbitrary malformed X contracts и новые data-contract APIs вне B12 scope.
