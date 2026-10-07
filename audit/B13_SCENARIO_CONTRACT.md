# B13: поздний namespace classic RCT scenario

Дата: 2026-10-07, Europe/Moscow. Точная frozen baseline: `9f0a63c42308ca886d92dc73d8d8d9611d5b2c31`. Branch на начале проверки — `codex/correctness-roadmap`, working tree clean. Независимый reviewer меняет только этот документ, [probe](block13_contract_probe.py) и [result](block13_contract_result.json). Library/tests/Git не менялись; integration/CI не запускались.

Контекст: [B12 wrapper contract](B12_WRAPPER_CONTRACT.md) и [B12 review](B12_WRAPPER_REVIEW.md). B12 защищает underlying генерацию/augmentation, но не поздние scenario additions, renames и conversion projection.

## Bounded scope

Согласованный runtime scope — **один** module `causalis/scenarios/classic_rct/dgp.py`, обе функции `generate_classic_rct_26` и `classic_rct_gamma_26`. Подтверждены три связанных дефекта публичных параметров этого layer:

1. Binary scenario переименовывает `y → conversion` после underlying wrapper. Enabled pre-period `pre_name='conversion'` сначала создаётся как отдельный корректный X, затем rename создаёт два `conversion` labels.
2. Обе scenario functions всегда добавляют либо используют identifier `user_id`, даже при `add_ancillary=False`. Enabled pre-period `pre_name='user_id'` создаёт numeric feature; scenario принимает её за существующий identifier и не создаёт настоящий ID.
3. Обе automatic conversions исключают все шесть binary oracle tokens независимо от enabled branch. Поэтому при `include_oracle=False` валидный pre-period feature `m`, `m_obs`, `tau_link`, `g0`, `g1` либо `cate` пропадает из CausalData.

Underlying functional classic helpers, shared DGP paths, IV/CUPED scenario runtime, data-contract classes, inference, DiD и sensitivity не требуют изменений для этих трёх механизмов. Нет общего расширения schema/type/finite/numeric policy.

## Фактически выдаваемые роли

| Функция | Scenario core | Fixed actual X | Optional additions |
| --- | --- | --- | --- |
| `generate_classic_rct_26` | `user_id`, `conversion`, `d` | `platform_ios`, `country_usa`, `source_paid` | Pre feature при add_pre; пять numeric ancillary features при add_ancillary; шесть enabled binary oracles |
| `classic_rct_gamma_26` | `user_id`, `y`, `d` | Тот же набор из трёх X | Те же optional additions |

ID добавляется underlying ancillary stage либо поздней scenario stage, но его scenario-role существует в обеих ветках. Это отличается от low-level binary/IV generator, который не добавляет identifier, и от generic RCT wrapper при ancillary off. B12 разрешает underlying pre feature `user_id`; запрещать его глобально в shared generator было бы неверно.

Ancillary numeric names: `age`, `cnt_trans`, `platform_Android`, `platform_iOS`, `invited_friend`. Enabled oracle names: `m`, `m_obs`, `tau_link`, `g0`, `g1`, `cate`. Actual raw order: identifier, outcome, treatment, три X и actual ancillary features, actual pre feature, enabled oracles. Rename не меняет позиции. Без optional additions raw schema имеет шесть столбцов; pre добавляет один, ancillary пять дополнительных numeric columns, oracles шесть. CausalData сохраняет собственную normalization/projection policy.

`conversion` резервируется только binary scenario outcome. Gamma `pre_name='conversion'` при enabled pre остаётся допустимым признаком. `user_id` резервируется обеими scenario functions. При `add_pre=False` параметр `pre_name` не создаёт роли и полностью игнорируется для namespace/ordering/projection; например, `pre_name='conversion'` в binary scenario тогда валиден.

Literal names сохраняются без strip/coerce/suffix; whitespace string и NumPy string scalar остаются допустимы. Underlying B12 guards остаются владельцами проверки actual added-name type/length и столкновений с core, fixed X, enabled oracles и enabled ancillary columns. B13 не дублирует весь их sampling/expansion contract.

## Минимальное размещение исправления

Нужен короткий scenario preflight только enabled pre-period field: literal `kwargs.get('pre_name', 'y_pre')` при `add_pre=True` проверяется против scenario-reserved identifier и, только для binary, final outcome. Проверка действует независимо от return type и add_ancillary. Guard до underlying DGP даёт contextual ValueError без запуска callbacks/RNG для заведомого scenario collision. Disabled pre field не проверяется как emitting role.

Перед поздним binary rename дополнительно проверить **фактический** incoming frame: отсутствие duplicate labels и уже существующего target `conversion`, конфликт которого rename иначе создаст. Эта проверка защищает actual transformation, а не полагается только на заранее известный pre argument. При scenario-only ID addition нельзя принимать другой actual feature с именем `user_id` за созданный identifier. Для нормальных публичных calls preflight и B12 guards закрывают этот путь.

Automatic feature exclusion в обоих scenario conversions включает outcome/treatment/actual scenario ID и oracles только если соответствующая branch включена. Disabled-oracle-named pre feature остаётся numeric confounder. Explicit numeric/constant/finite/duplicate-record checks принадлежат CausalData; они не ослабляются для прохождения regression fixtures.

Для корректно classified schemas изменение guards/exclude не должно менять arithmetic, callbacks, seed handling, ID draws, dtypes, raw insertion order или RNG. Исправление потерянного disabled-oracle pre feature намеренно меняет contract-selected columns; raw DGP frame для этого случая может остаться прежним. Invalid rename/ID overlaps теперь должны отклоняться раньше вместо corrupt raw frame либо позднего validation error.

## Baseline reproduction и provenance

Запуск: `.venv/bin/python audit/block13_contract_probe.py`. Все configs synthetic; `n=256`, `seed=731`. Probe загружает восемь pinned Git blobs в отдельные in-memory modules: shared base, binary base/functional/preperiod, IV base и три scenario modules (classic/IV/CUPED). Import bindings явно rebound к pinned helpers и class; IV inheritance и scenario/helper identity asserted. Imported CausalData/IVCausalData source bytes совпадают с baseline и проверяются hashes. Pinned export inventory хранит также пять relevant __init__ modules. Working-tree правки других агентов не участвуют в frozen generation.

Results помечены `frozen_baseline_only`: **100 records**, не pytest case count и не candidate verification.

- **16 binary outcome-rename configs:** add_pre False/True × ancillary False/True × oracle False/True × raw/contract. Восемь disabled-pre configs корректны. Четыре enabled-pre raw configs возвращают duplicate `conversion`; четыре contract variants отклоняются на duplicate-label validation. Основной trigger: `generate_classic_rct_26(n=256, seed=731, add_pre=True, pre_name='conversion', add_ancillary=False, return_causal_data=False)`.
- **16 scenario identifier configs:** обе functions × add_pre × ancillary × return type. Восемь disabled-pre configs корректны. Enabled pre/ancillary False возвращает numeric `user_id` в двух raw frames, а оба contract variants на этом exact fixture падают на duplicate-ID values. Enabled pre/ancillary True в четырёх configs уже отклоняется B12 pre/ancillary guard. Numeric pre здесь не становится legitimate ID лишь потому, что имя совпало.
- **24 disabled-oracle pre configs:** две functions × шесть names × raw/contract, include_oracle False, ancillary False. Все возвращают frames/contracts; двенадцать raw frames содержат actual pre feature, но двенадцать contracts теряют его из selected confounders.
- **10 upstream-collision controls:** pre name y/d/каждый fixed X уже отклоняется shared B12 guard, по пять для каждого scenario helper.
- **15 allowed controls:** обычный `y_pre`, literal whitespace/NumPy strings, unused pre-name, gamma pre-name conversion. Все возвращают contracts с корректными ролями.
- **8 IV controls:** enabled/disabled oracle × raw/contract × deterministic/seeded ID. Все имеют уникальный final namespace; four contract outputs сохраняют twelve X, actual instrument `offer_eligible`, outcome `net_revenue_90d`, treatment `accepted_offer`, identifier `user_id`.
- **8 CUPED controls:** add_pre False/True × y/user_id/_latent_A/safe_pre. Disabled-pre names игнорируются; три enabled reserved names уже отклоняются existing guard; safe enabled name работает.
- **3 underlying functional controls:** enabled pre conversion/user_id/m при ancillary False и oracle False остаётся valid raw schema. Это подтверждает, что дополнительные reservations принадлежат scenario layer.

Retained JSON содержит schemas, dtypes, feature/ID/core roles, counts и sanitized error text. Individual generated observations и Pydantic input-frame repr не сохраняются. Load-time warnings записаны отдельно от per-config warning counts; invalid-escape SyntaxWarning в frozen IV scenario docstring не является regression runtime finding.

## Aliases и реальные callers

Обе classic scenario functions экспортируются через `causalis.dgp.causaldata` и `causalis.dgp`; lazy exports в `causalis.data_contracts` направляют к тому же DGP export. `causalis.scenarios.classic_rct` экспортирует `dgp` module; основной direct path — `causalis.scenarios.classic_rct.dgp`. Functional names `generate_classic_rct`/`classic_rct_gamma` — нижний layer без позднего scenario outcome rename/always-ID policy и не должны получать дополнительные scenario reservations.

Реальные local callers inspected: classic DiffInMeans и ttest/conversion_ztest/permutation-test examples; `notebooks/scenarios/classic_rct.ipynb`, `notebooks/research/generate_classic_rct_26.ipynb`, `notebooks/research/classic_rct_gamma_26.ipynb`. Они используют обычные default names; default frame/order/RNG compatibility относится к этим paths. Runtime notebooks не исполнялись, outputs не экспортировались, published website/docbuild не проверялись.

IV scenario `generate_offer_iv_26` делает late y/d/z business-name renames и fixed projection, но public signature не принимает pre-name, instrument-name, confounder schema или callbacks. Its twelve fixed X names не пересекаются с fixed business core, ID и oracle names. Module-internal constant mutation не объявляется новым public schema API. Existing IV DGP tests и `notebooks/scenarios/iv.ipynb` используют этот fixed path; eight frozen controls не выявили рассматриваемого late-namespace дефекта. IV runtime change не нужен.

CUPED26 имеет свой reserved pre-name guard, строит required oracle/latent columns internally и затем их удаляет при requested oracle False. Эта existing policy не расширяется/не унифицируется с B13 classic reservations. Remaining scenario DGP modules просмотрены статически на rename/add/projection hotspots; full runtime audit multi/unconfounded/DiD/SCM в B13 не заявляется.

## Границы доказательства

Этот contract/result фиксирует baseline и согласованный минимальный дизайн. Проверка candidate/source commit, exact reference/RNG equivalence, regression pytest counts, integration и CI принадлежат root/test/reviewer artifacts. Проверки здесь не доказывают random-ID entropy/uniqueness для произвольного n и не изменяют прежний ID algorithm. Нет нового numerical-zero DiD, Gaussian oracle, sensitivity, release или performance claim.
