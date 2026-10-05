# Производительность Causalis: измерения и план оптимизации

Срез: 2026-10-05, commit `ffe2c356c115f335b74b2f10117e19fe15585d46`. Исходники библиотеки не менялись. Прототипы существуют только в [benchmark_data_path.py](D:/codex/Causalis/audit/benchmark_data_path.py); полные измерения — [JSON](D:/codex/Causalis/audit/benchmark_data_path.json), [лог](D:/codex/Causalis/audit/benchmark_data_path.log), профили [контракта](D:/codex/Causalis/audit/profile_contract.txt) и [IRM](D:/codex/Causalis/audit/profile_irm.txt).

## Что установлено

Общее утверждение «Causalis медленнее аналогов из-за pandas» **не подтвердилось** на проверенном сценарии. При одинаковых данных, nuisance learners и folds binary IRM Causalis обучился быстрее DoubleML, а predictions, ATE и SE совпали. Это узкий результат одного benchmark, не рейтинг библиотек для всех задач.

При этом есть измеримые расходы на data preparation и несколько серьёзных потенциальных расходов памяти. Хорошие первые изменения: перенести уже существующий в RctCausalData предварительный screening одинаковых колонок в CausalData; заменить сортировку outcome для проверки бинарности линейным проходом; ограничить память KDE; восстановить batch CUPED factorization reuse. Перевод всего public API с pandas на NumPy для этого не нужен.

## Условия измерений

- Windows 10, Python 3.12.14, восемь логических CPU; NumPy 2.5.3, pandas 3.0.6, sklearn 1.9.1, DoubleML 0.11.4. Полный manifest — [environment.json](D:/codex/Causalis/audit/environment.json).
- Последний benchmark выполнен без параллельных pytest/ML fits/сборки документации. Native BLAS/OpenMP threads ограничены `threadpool_limits(1)`, модель `n_jobs=1`.
- Для операций с данными: пять запусков, медиана wall time; GC перед запуском. Для fit: три запуска. Все отдельные времена сохранены. Небольшое число повторов и desktop noise ограничивают точность, поэтому проценты нельзя переносить на другое оборудование.
- Данные — float64 confounders, бинарный treatment, непрерывный outcome; размер `p` означает число confounders. Память — **пик traced allocations во время операции**, не peak RSS процесса, не полная память input+output и не гарантия видимости всех native allocations.
- Подготовка исходного DataFrame не входит во время конструктора; контракт и создание DoubleMLData не входят в fit comparison. DoubleML `.fit()` выполняет также свою framework/sensitivity работу. Сравнение полезно для практического одинакового API вызова, но не приписывает весь разрыв pandas.

## Построение контракта

| n × p | CausalData, с | RctCausalData, с | CausalData со screening, с | Ускорение прототипа против CausalData | Пик CausalData / прототип, MiB |
|---|---:|---:|---:|---:|---:|
| 100 000 × 20 | 0.1260 | 0.0500 | 0.0366 | 3.45× | 18.83 / 18.83 |
| 500 000 × 20 | 0.1618 | 0.0588 | 0.0974 | 1.66× | 114.07 / 100.08 |
| 1 000 000 × 8 | 0.1989 | 0.0844 | 0.0936 | 2.13× | 116.42 / 108.57 |

RctCausalData имеет другой контракт, поэтому его время — ориентир реализации, а не равноценная замена CausalData. Audit subclass меняет только duplicate-column screening и сохраняет остальные проверки CausalData. На случайных непрерывных колонках он избегает полного хеширования большей части данных. На почти одинаковых колонках выигрыш будет меньше.

Текущий [CausalData duplicate check](D:/codex/Causalis/causalis/data_contracts/causaldata.py:352) хеширует полные колонки. В profile 20k×8 на этот путь пришлось около 0.010 с из 0.030 с конструктора. У [RctCausalData](D:/codex/Causalis/causalis/data_contracts/rct_causal_data.py:167) уже есть проверка максимум 64 позиций: несовпадение означает различие колонок, совпадение требует полного fingerprint, совпавшие fingerprints всё равно проверяются на точное равенство. Такой перенос не должен заменять equality probabilistic hash verdict. Отдельно нужны проверки int/float equality, больших integers, dtype, duplicate columns, index и nullable types.

## Подготовка X/y/d для IRM

| n × p | Текущий `_check_data`, с | Owned arrays с теми же проверками, с | Owned arrays + линейная binary check, с | Ускорение последнего против текущего |
|---|---:|---:|---:|---:|
| 100 000 × 20 | 0.0274 | 0.0275 | 0.0087 | 3.15× |
| 500 000 × 20 | 0.1283 | 0.1522 | 0.0403 | 3.18× |
| 1 000 000 × 8 | 0.2192 | 0.1447 | 0.0375 | 5.85× |

Это **время одного этапа**, не всей модели. Простое удаление DataFrame copy не дало стабильного ускорения при сохранении проверок. Основной дополнительный выигрыш — замена [np.unique/sort](D:/codex/Causalis/causalis/scenarios/unconfoundedness/_utils.py:11) на проверку «все значения 0/1, присутствуют обе категории». Непрерывный outcome сортировать целиком для ответа «не бинарный» особенно дорого. NumPy version может влиять на реализацию unique, поэтому утверждать универсальную сложность каждого backend не требуется: конкретный путь измерен здесь.

Benchmark проверяет идентичность X/y/d и флага binary outcome исходному пути; отдельно сверяет empty/constant/0–1/NaN/Inf/третью категорию. Для production нужны дополнительные проверки типов; сохранение current semantics для constant [0] и [1] существенно.

Текущий [IRM._check_data](D:/codex/Causalis/causalis/scenarios/unconfoundedness/model.py:340) делает `get_df()` с копией, затем arrays. [CausalData.X](D:/codex/Causalis/causalis/data_contracts/causaldata.py:535) и [get_df](D:/codex/Causalis/causalis/data_contracts/causaldata.py:548) также возвращают копии. При 1m×8 только `get_df()` занимает 0.0262 с, `X` — 0.0319 с. Расход важен при повторных estimate/diagnostic/benchmark проходах, но в дорогом boosting fit learners могут доминировать.

## Сопоставленный binary IRM

20 000 строк, восемь X, три stratified folds с seed17; `LinearRegression` для g и `LogisticRegression(max_iter=100)` для m. DoubleML получает те же sample splits. В сценарии не менялись estimand или overlap threshold ради скорости.

| Показатель | Causalis | DoubleML |
|---|---:|---:|
| Медиана fit, с | 0.1468 | 0.3644 |
| ATE | 1.991232213420928 | 1.991232213420928 |
| SE | 0.014538774984069918 | 0.014538774984069996 |
| Максимальная разность m/g0/g1 predictions | 0 / 0 / 0 | reference |

SE Causalis вычислен из сохранённой IF; совпадение до machine precision подтверждает этот базовый ATE путь. Оно не подтверждает multi ATTE, relative ATT, sensitivity или остальные DGP. Отношение времени — 2.48× в пользу Causalis в этом запуске. Heavy learners, categorical features, multiarm, parallel Windows/Linux, число folds и повторов могут изменить результат.

Profile IRM занял около 0.173 с; cross-fitting — около 0.148 с, learner fit wrappers — 0.095 с. Следовательно, даже заметное ускорение extraction не обязательно значительно ускорит обучение на этом размере. Стоит измерять constructor, extraction, nuisance fitting, score, inference и plotting отдельно.

## Память KDE: отдельный приоритет

[outcome_plots.py:44](D:/codex/Causalis/causalis/shared/outcome_plots.py:44) создаёт матрицу `n_group × n_grid` для Gaussian KDE; [grid](D:/codex/Causalis/causalis/shared/outcome_plots.py:404) содержит 800 точек. При миллионе наблюдений **в одной группе** одна float64 матрица требует 6.4 GB (5.96 GiB). `diff` и `kern` вместе — 12.8 GB, промежуточные массивы увеличивают пик. Это расчёт из shapes и dtype, не выполненный OOM эксперимент.

Безопасное исправление: считать сумму Gaussian kernels порциями наблюдений, сохранять прежний bandwidth и grid, делить на общий n. Рабочая память тогда зависит от размера блока, а не n. Округление суммы немного изменится, допустимую погрешность надо зафиксировать. Sampling/FFT KDE — отдельные, явно маркированные approximations; они не обязательны для первого исправления.

## Топ-10 оптимизаций

Размер: S — локальная правка; M — несколько путей/API; L — существенная архитектура. Предполагаемый эффект вне измеренных случаев — гипотеза, которую надо benchmark.

| Приоритет | Изменение | Основание / ожидаемый эффект | Размер | Что сохранять и проверять |
|---:|---|---|---|---|
| 1 | Screening одинаковых колонок для CausalData/IV/Multi | Прототип CausalData 1.66–3.45×; обход full-column hash на разных sampled values | S–M | Точное equality после совпадения sample/hash; те же errors и roles |
| 2 | Линейная проверка бинарности | Extraction с array prototype 3.15–5.85×; убрать unique continuous Y | S | 0/1 + обе категории, constant/missing/inf/dtype semantics |
| 3 | Chunked KDE с memory budget | Устранить n×800 peak memory; особенно большие outcome plots | S | Тот же grid/bandwidth/density в числовой tolerance |
| 4 | Один owned array snapshot на fit | Сократить get_df/X copies и повторные conversions во всех estimators | M | Labels/schema/IDs, readonly arrays, mutation detection, refit invalidation |
| 5 | CUPED batched QR/SVD для многих Y | Уже обнаружена потеря cache reuse на statsmodels0.15: SC-12 | M | Robust HC0–HC3 и joint relative covariance для каждого Y; стабильный rank |
| 6 | Column-wise validation и reuse проверенных masks | Меньше full-frame boolean tables и повторной finite/role проверки | M | Не убрать finite/real/assignment validation ради времени |
| 7 | DID panel index/masks/pivots подготовить один раз | Повторная cell выборка/pair construction; много cohorts×periods | M | Сначала исправить SC-01–04/11; сохранять unit IF, missingness и anticipation |
| 8 | ASCM Gram/factorization reuse и warm starts | Placebo, donor LOO и conformal повторяют близкие solve | M–L | Наследовать config SC-08, tolerance/constraints и прежний inferential target |
| 9 | Thread budget и memory-aware fold scheduling | Управлять fold jobs × learner threads × BLAS, избегать oversubscription | M | Fixed seeds/splits; параллельный результат соответствует sequential |
| 10 | External OOF predictions/cache + bootstrap batching | Убрать повторные expensive ML fits, ограничить bootstrap temporary arrays | M–L | Row/fold/provenance contracts, cache key/version, независимость evaluation |

`to_numpy(copy=False)` не означает гарантированного отсутствия копии: dtype coercion и структура frame могут требовать allocation. Это прямо указано в [официальной документации pandas](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_numpy.html). В pandas3 Copy-on-Write есть дополнительные правила ownership; blindly возвращать writable view public mutable frame нельзя. Контракт immutable snapshot или явная invalidation нужен раньше кэша.

Nested threads и поддержанные способы ограничения описаны в [официальной документации sklearn](https://scikit-learn.org/stable/computing/parallelism.html). Оптимальный n_jobs — измеряемая настройка, а не «максимум CPU» по умолчанию.

## Как внедрять без потери статистического качества

1. Зафиксировать data schema/row order/retained mask, folds, seeds, nuisance predictions, score, estimand и inference target до изменения data path.
2. Для механической оптимизации сравнить arrays, predictions, IF/covariance и все результаты с исходным путём; добавить adversarial dtype/index/duplicate/mutation cases.
3. Измерять median time и memory отдельно при n=20k/100k/1m, p=8/20/100, binary/continuous Y, нескольких outcome/arms; дешёвый и дорогой learner, NumPy/pandas поддержанных версий.
4. Для изменений score/inference сначала исправить методологические defects и проверить oracle/reference/invariance, затем bias/coverage в Monte Carlo. Performance benchmark не заменяет coverage evidence.
5. Сохранять число folds, held-out preprocessing, precision, overlap policy и statistical checks. Изменение любого из них — отдельный statistical tradeoff с документацией.

## Воспроизведение

Из `D:\codex\Causalis`, при отсутствии других fits:

```powershell
$env:MPLBACKEND = 'Agg'
.\.venv\Scripts\python.exe audit\benchmark_data_path.py *> audit\benchmark_data_path.log
```

Не требуется повторять benchmark после чтения отчёта; outputs уже сохранены. Скрипт перезапишет JSON/profiles/log. Репозиторные исходники он не изменяет.
