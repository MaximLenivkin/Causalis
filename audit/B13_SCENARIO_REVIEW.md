# B13: независимое review namespace classic RCT scenarios

**В согласованном scope открытых существенных замечаний нет; `issues: []`.** Проверены изменения обоих helpers в одном library path `causalis/scenarios/classic_rct/dgp.py` и финальный test module `tests/data/test_scenario_namespace_contract.py` (91 cases). Baseline: `9f0a63c42308ca886d92dc73d8d8d9611d5b2c31`; source/test checkpoint: `4428be0e39bda8a2a47f1a6f184c92873da10976`. Применён навык `code-review`, прочитаны локальный `AGENTS.md` и активный `audit/NEXT_SESSION.md`. Reviewer не менял library, tests, git state и не запускал full suite.

## Подтверждённое поведение

При `add_pre=True` classic scenarios резервируют свои собственные outcome и `user_id`. Binary helper отвергает pre `conversion` до underlying generation, поэтому позднее `y → conversion` не создаёт duplicate labels. Оба helpers отвергают pre `user_id` даже при `add_ancillary=False`: scenario всё равно добавляет identifier, а numeric pre больше не принимается за готовый ID. Gamma helper сохраняет допустимый pre `conversion`, поскольку его outcome называется `y`.

Дополнительная проверка фактической DataFrame-схемы перед binary rename ловит target collision независимо от объявленного pre имени. Она выполняется до scenario ID RNG и assignments. Synthetic builder, вернувший уже существующий `conversion`, получает `ValueError`; его frame сохраняется без мутации. Проверка использует существующий shared guard, а не новую политику автоматического переименования.

При `include_oracle=False` pre-поля `m`, `m_obs`, `tau_link`, `g0`, `g1`, `cate` сохраняются в automatic feature projection вместе со своими исходными значениями. При включённых oracles их прежнее исключение из features остаётся. `add_pre=False` полностью игнорирует неиспользуемое pre имя, включая имена outcome/ID/oracle и неверные типы.

Early private check отвечает только за известные string collisions с собственными scenario roles. Неверные типы и пустое включённое pre имя по-прежнему проверяет underlying B12 wrapper после core generation. Review не утверждает новую early type-validation гарантию. Публичные сигнатуры, sampling/calibration/assignment, ID algorithms и арифметика не изменены; прямое сравнение public helper signatures проходит.

## Независимые точные references

`block13_review_probe.py` восстанавливает девять полных modules из Git baseline: shared base, binary base/preperiod/functional, IV base/functional и classic/CUPED/IV scenario modules. Во время compilation и вызовов временно связываются `sys.modules`, parent-module attributes и package class/function exports. Явно проверены old IV inheritance, old wrapper bindings и old IV scenario binding к замороженному классу. Важно: IV scenario импортирует класс из package export; одного замещения base module для корректного baseline было бы недостаточно.

Три неизменённых package alias sources (`causalis.dgp`, `causalis.dgp.causaldata`, `causalis.data_contracts`) byte-for-byte совпадают с baseline. Overlay сохраняет исходное наличие attributes через module dictionary и не запускает lazy `__getattr__` при snapshot/restore. Так old aliases вызывают old helpers, а current aliases — текущие helpers, без утечки cached frozen objects между вызовами.

**116 valid configurations** прошли полные точные old/current сравнения: DataFrame values, labels/order, dtypes, complete contract model metadata. Перехвачены все созданные `np.random.default_rng`; сравнивались их полные states и следующие 10 draws каждого stream.

Это **92 classic configurations**: оба helpers, pre/ancillary/oracle/raw/contract flags, outcome dependence, custom X и nonlinear signal, literal Unicode/whitespace/NumPy string pre имена и три public alias paths. Дополнительно **16 неизменённых CUPED** и **8 offer-IV** configurations служат controls. Offer-IV проверен с обеими ID options: его случайные customer IDs используют seeded RNG и воспроизводимы. Classic UUID identifiers при `deterministic_ids=False` не включены в exact frame references; их неизменный algorithm подтверждён source review.

Прошли ещё **13 rejection probes** и **40 permitted-name/projection probes**. Rejections проверяют known collisions до underlying builder и actual target collision до ID RNG/rename, с сохранением входного frame. Permitted probes включают все шесть disabled oracle names в обоих helpers, ancillary on/off, renamed-frame/value comparison и baseline proof потерянного pre feature; unused pre names сохраняют значения, schema и RNG. Два Gamma `pre_name='conversion'` cases точно совпадают с baseline для raw и contract output.

Для ранее неверно классифицированных schemas feature list намеренно меняется; они проверяются отдельно, а не включаются в blanket old=current claim. Для обычных допустимых schemas exact references проходят.

## Test review и предупреждения

Финальный test module просмотрен полностью. Raw/contract comparison явно переводит только treatment в штатный `int8`, затем проверяет весь frame с обычным строгим dtype check; `check_dtype=False` не используется. Остальные columns сохраняют свои generated dtypes. Public aliases, disabled oracle pre projection, early outcome/ID collisions, неизменённые CUPED и IV controls покрыты independently authored cases.

Авторский evidence на финальном одном test module: baseline **28 failed / 63 passed**, focused **91 passed**, соответственно 4.79 s и 4.37 s. Эти pytest runs выполнял regression agent; reviewer их не повторял. Failing cases не являются числом разных bugs.

Runtime probe warnings: **0**. При отдельной compilation замороженного неизменённого IV scenario возник один существующий `SyntaxWarning: invalid escape sequence '\e'` в docstring строки 177. Он записан отдельно в `frozen_compile_warnings`; это не warning изменённого runtime или новый B13 defect. IV source не исправлялся.

## Provenance, границы и готовность

Полный reference process был precommit на рабочем дереве; его исходный HEAD и timestamp сохранены. Последующая проверка сравнила **13 файлов** с Git objects source checkpoint `4428be0e39bda8a2a47f1a6f184c92873da10976`: девять modules, три alias package sources и final test module. Все committed bytes совпадают с проверенными bytes. JSON содержит source/test hashes, прежний `probe_head_at_start`, exact `reviewed_head`, отдельное время byte verification и `issues: []`. Broad references повторно не запускались ради изменения HEAD metadata.

CUPED guard и fixed offer-IV rename paths прочитаны как actual callers. Offer-IV не имеет публичных name/specification knobs, создающих аналогичный collision; произвольная мутация его module constants не включалась в публичный scope. Их source и parameter policy остались прежними. Sensitivity, DiD diagnostic policy, numeric/finite guards, standalone docs build, release и performance benchmark не проверялись в этом review.

Evidence: `audit/block13_review_probe.py`, `audit/block13_review_probe.json`, `audit/block13_review_probe.log`. Все fixtures synthetic. Для воспроизведения использовать `.venv/bin/python audit/block13_review_probe.py` с native thread limits 1, Agg и `.venv/matplotlib`. Full local integration выполнял root; reviewer её не повторял.

## Независимая проверка CI artifacts

[CI run 37607784481](https://github.com/MaximLenivkin/Causalis/actions/runs/37607784481) завершился `success` на точном source `4428be0e39bda8a2a47f1a6f184c92873da10976`; snapshot `observed_at=2026-10-07T10:33:36.694587+00:00`. Reviewer независимо прочитал все шесть скачанных `selection.json`, `result.json`, `junit.xml` и сверил их с run snapshot и `audit/block13_ci_result.json`. Во всех jobs подтверждены exact source, Linux/CPython environment, correctness scope, `collect_only=False`, `selected_full_suite=False`, `exit_code=0`; все семь exclusions и actual `--ignore` arguments совпадают с B12. Каждый JUnit содержит **2488 tests / 2488 passed / 0 failures / 0 errors / 0 skipped**, включая все **91 final scenario case IDs** из focused manifest. Actual Python versions: **3.10.21 latest и legacy, 3.11.16, 3.12.14, 3.13.16, 3.14.7**. Это версии из текущих artifacts, а не перенос прежней matrix metadata. Итог `matrix_verified=True`, `issues=[]` подтверждён; краткая независимая запись добавлена в review JSON/log. Raw artifacts сохранены под ignored `audit/block13_ci_test_temp/run-37607784481/`. Workflow не менялся и повторно не запускался. Проверка ограничена шестью Linux stacks; sensitivity, standalone Sphinx и release success не заявляются.
