# B11: actual namespace binary и IV generators

Дата: 2026-10-07, Europe/Moscow. Точная исходная версия: `4d6b8143db7a93c1a7eba371fcd144878d80c896`. Этот reviewer не менял library, tests или Git. Scope — два library modules: `causalis/dgp/causaldata/base.py` и `causalis/dgp/causaldata_instrumental/base.py`. Wrapper pre-period, ancillary и column-projection policies разобраны как отдельные ограничения, без расширения этой правки.

## Полный фактически выдаваемый namespace

| Семейство | Core columns | Oracle columns при include_oracle=True |
| --- | --- | --- |
| Binary CausalDatasetGenerator | `y`, `d` | `m`, `m_obs`, `tau_link`, `g0`, `g1`, `cate` |
| IV InstrumentalGenerator | `y`, `d`, `instrument_name` (default `z`) | `m`, `r_obs`, `r_z0`, `r_z1`, `g_z0`, `g_z1`, `iv_first_stage`, `iv_reduced_form`, `late_x`, `late`, `tau_link`, `g_d0`, `g_d1`, `cate` |

Actual confounder names вставляются после core и перед oracles, в sampled-X порядке. Таблица oracle lists сохраняет реальный insertion order. Для k фактических confounder columns raw binary schema содержит `2+k` столбцов без oracles и `8+k` с ними; IV — `3+k` и `17+k` соответственно.

Названия oracles должны быть **family-specific**. IV не выдаёт binary `m_obs`, `g0`, `g1`; эти имена остаются доступными для IV confounder или instrument даже при enabled IV oracles. Binary не резервирует `z` как instrument: у него такой роли нет. При disabled oracles не резервируется ни одна oracle role. Low-level generators не выдаёт `user_id`, pre-period или ancillary columns самостоятельно.

Каждое actual emitted name должно быть строкой ненулевой длины; строки сохраняются буквально, включая whitespace и NumPy string subclasses. Все роли должны быть уникальны: core между собой, actual confounders между собой, confounders против core/enabled oracles, IV instrument против enabled oracles. Нельзя silently trim, suffix, coerce или rename requested schema. Это соответствует B09; raw spec name fallback не заменяется новой blanket validation.

## Sampling paths и контейнеры

- Без specs используются имена `x1`…`xk`.
- Custom X sampler имеет приоритет. Со specs его имена — `spec.get('name', f'x{i+1}')`, без categorical expansion. Explicit None/empty name не подменяется fallback и отклоняется как invalid actual name.
- Independent built-in sampling использует `spec.get('name') or f'x{len(names)+1}'`; индекс зависит от уже expanded columns.
- Copula sampling использует `spec.get('name') or f'x{j+1}'`; индекс соответствует исходному spec. B10 coordinate fix не меняется.
- Built-in categorical sampling опускает первый level, выдаёт `f'{name}_{category}'`; single-level — нулевой `f'{name}__onlylevel'`. Разные category values с одинаковым строковым отображением тоже могут создать duplicate actual names.
- Missing/None/empty/falsy raw names, которые built-in sampler уже превращает в fallback, сохраняют существующее поведение. Nonempty numeric basename categorical может форматироваться в string; контракт проверяет actual name, а не вводит всеобщие требования к raw spec types.

Width guard не должен начинать новую общую проверку X shape/finite values или превращать X в другой контейнер перед пользовательскими callbacks. На baseline существуют рабочие случаи без actual confounder columns, у которых X — Python list либо одномерный NumPy array:

| Custom X, k=0 | Binary, oracle False/True | IV, oracle False | IV, oracle True |
| --- | --- | --- | --- |
| `[[] for _ in range(n)]`, n=30 | Оба возвращают frame | Возвращает frame | Старый AttributeError: list без `.shape` в IV oracle helper |
| `[]`, n=0 | Оба возвращают empty frame | Возвращает empty frame | Тот же старый AttributeError |
| `np.empty(0)`, n=0 | Оба возвращают empty frame | Возвращает empty frame | Возвращает empty frame |
| `np.arange(n)`, n=30 | Оба возвращают frame | Возвращает frame | Возвращает frame |

Здесь names пусты; baseline routines либо преобразуют X внутри numeric calculations, либо не индексируют confounder columns. Согласованный минимальный width check: получить `shape = np.shape(X)`, использовать `shape[1]` при существующей второй оси, иначе width=0, и сравнить с `len(names)`. Это сохраняет наблюдаемое поведение без X coercion. Случаи с nonempty names и несогласованной шириной дают contextual ValueError; прочие numeric/container contracts не расширяются.

## Размещение guard и наследование

Достаточно private inherited `_validate_column_names(names=None)` и polymorphic `_output_column_roles()`; публичные signatures и dataclass fields сохраняются. Base validator проверяет actual strings до dictionary membership и сообщает конкретное имя и две конфликтующие роли. IV override поставляет instrument и свой oracle список, не добавляя к нему binary oracle roles.

Проверки нужны:

1. При construction: fixed core/enabled-oracle subset. IV dataclass fields уже инициализированы, когда его `__post_init__` вызывает base method, поэтому dispatch может учитывать instrument сразу. Прежние IV outcome/target-rate/first-stage validation сохраняются; только дублирующая instrument-name validation может перейти в общий guard.
2. Перед каждой generate: fixed subset повторно, для изменённых `instrument_name` и `include_oracle`.
3. Сразу после `_sample_X`: width и полный actual namespace, до U draw, calibration, structural callbacks и treatment/outcome draws.
4. Перед DataFrame assembly: полный namespace повторно. Пользовательский callback может изменить `instrument_name`, enabled-oracle flag либо shared names list во время той же generate. Один guard до callbacks не защищает actual subsequent column assignment от такой мутации.

Для корректного schema guard не меняет sampling order, числа RNG draws, arithmetic, callbacks, имена или column insertion order. Exact old/current frame/schema/RNG comparisons проверяются отдельно. Namespace error до callbacks — корректное fail-fast поведение для invalid inputs, а не обещание отсутствия всех более ранних sampler ошибок.

`IVCausalDatasetGenerator is InstrumentalGenerator`: alias получает тот же guard автоматически. `to_causal_data`, `to_iv_causal_data`, generic IV wrapper и binary wrappers проходят через `generate`, поэтому core conflicts отклоняются и при contract return. Data-contract conversion retains its separate projection/normalization/validation; namespace guard не отменяет их.

## Frozen-baseline evidence

[Probe](block11_contract_probe.py) загружает pinned binary и IV sources в память; IV inheritance явно rebound к той же pinned binary class. Functional sources тоже frozen. Generated individual rows не сохраняются: evidence содержит schemas, counts и ошибки synthetic probes. [Results](block11_contract_result.json) явно помечены `frozen_baseline_only`.

На n=30, seed731, **46 namespace cases** возвращают схемы с missing contract. Среди них outcome/treatment confounder collisions, repeated/expanded/stringified names, все шесть binary и четырнадцать IV confounder/oracle collisions, confounder/instrument и expanded instrument collision, а также каждый IV instrument/oracle collision. В treatment-overwrite случаях обе семьи возвращают 30 nonbinary treatment values. Это parameterized reproductions нескольких механизмов, не 46 независимых bugs.

Шестнадцать container configurations дают точную compatibility таблицу выше. Это frozen observations, а не pytest case count и не проверка ещё не committed candidate.

## Wrapper limitations вне двух-module core scope

Core namespace guard не покрывает дополнительные поля и ordering, которые wrapper добавляет **после** low-level generate. Frozen probes подтвердили отдельные residuals:

- `generate_rct(pre_name='y')` возвращает duplicate `y` columns; это происходит и при `add_pre=False`, потому что projection включает core y и actual_pre y одновременно. При enabled pre-period step также может перезаписаться outcome. Default wrappers используют безопасный `y_pre`, но custom pre_name требует собственного namespace policy.
- `generate_iv_data(instrument_name='user_id', include_oracle=False, add_ancillary=False)` повторяет `user_id` в projection core list. Low-level IV generator сам не создаёт отдельный ID; запрещать такое имя в core guard означало бы резервировать несуществующую роль.
- `generate_iv_data(instrument_name='m', include_oracle=False)` повторяет `m` как core instrument и presumed oracle при ordering. Low-level disabled-oracle namespace разрешает это имя, как и B09; wrapper unconditional oracle classification требует отдельного решения.
- Ancillary addition может перезаписать actual confounder `age` своим integer age. Frozen IV wrapper probe показывает такую замену; аналогичный shared helper присваивает также `cnt_trans`, `platform_Android`, `platform_iOS`, `invited_friend`. `user_id` вставляется через insert и может вместо этого вызвать existing-column error.

Conversion methods тоже используют исторические списки exclude, независимо от enabled flag: disabled-oracle-named confounder может исчезнуть из automatic selected-column contract output. Это отдельная inference/projection policy, а не low-level column overwrite. Не следует заявлять, что B11 делает любую custom wrapper schema безопасной, или расширять два-module runtime scope ради этих residuals.

Reviewer не запускал integration, CI, DiD, sensitivity и не создавал commits/push. Final source/tests provenance, implementation review, counts и block completion принадлежат root artifacts.
