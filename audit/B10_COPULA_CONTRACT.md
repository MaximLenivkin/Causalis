# B10: контракт координат categorical Gaussian copula

Дата разбора: 2026-10-07, Europe/Moscow. Точная исходная версия: `83b63836dbd0c4793c24dd95ff7dc18c443792ad`; library source соответствует завершённому B09. Этот reviewer не изменял library, tests или Git. Scope — выбор правильной Gaussian координаты для categorical confounders и связанная обработка верхнего endpoint. DiD diagnostic policy и sensitivity не входят в этот блок.

## Контракт генерации

Для d исходных confounder specs helper один раз получает матрицу независимых нормальных innovations размера `(n, d)`. Он сохраняет существующие преобразования corr: симметризация, clipping eigenvalues, нормализация диагонали и Cholesky с jitter `1e-10`. Затем строит `Z = innovations @ L.T` и `U = Phi(Z)`.

Каждый исходный spec j должен использовать собственный `U[:, j]`. Расширение одного categorical spec в несколько dummy columns не создаёт дополнительные Gaussian координаты и не сдвигает индекс следующего spec. Corr описывает latent Gaussian dependence; observed Pearson correlation после нелинейных/discrete преобразований не обязана совпадать с corr. Существующий jitter и floating-point вычисления также сохраняются, поэтому исправление не заявляет новую точность восстановления всех marginal probabilities.

Для categorical spec helper нормализует предоставленные веса прежним `probs / probs.sum()` либо создаёт равные вероятности, получает cumulative thresholds и применяет `searchsorted(..., side='right')`. Это выбирает первый cumulative threshold, строго больший данного U. При точном равенстве threshold выбирается следующий интервал; repeated thresholds нулевой массы пропускаются.

Имена и кодирование остаются прежними: первый уровень пропускается, остальные дают `f'{name}_{category}'`; single-level categorical даёт нулевой столбец `f'{name}__onlylevel'`. В copula fallback имени использует индекс исходного spec, а не количество уже расширенных columns. `clip_min`/`clip_max` для categorical по существующему control flow не применяются. B09 namespace validation остаётся отдельным контрактом multi-treatment generator.

## Почему categorical нужен raw U

Нечисловые categorical draws не имеют сингулярности inverse continuous CDF на endpoint. Поэтому для них нужен raw `U[:, j]`; clipping к `[1e-12, 1-1e-12]` произвольно исключает вполне представимые интервалы малой positive probability.

Controlled probe с весами `[5e-13, 1-1e-12, 5e-13]` и Gaussian scores `[-40,-9,-8,-7.5,0,7.5,8,9,40]` подтверждает это: raw reference выбирает крайние уровни в восьми точках, а clipped uniforms выбирают middle level во всех девяти точках. Это проверка конкретных численных входов алгоритма, не оценка частоты таких событий в случайной выборке.

Numeric marginals продолжают использовать прежний отдельный `u = np.clip(U[:, j], 1e-12, 1-1e-12)` перед ppf и остальными numeric transforms. Не следует переносить clipping выше categorical branch или менять Gaussian draws, corr repair, jitter либо numeric arithmetic.

## Endpoints и zero-probability levels

Математический `Phi(Z)` лежит внутри `(0,1)` для конечного Z; floating-point CDF может округлиться в 0 или 1. Поэтому categorical branch должна корректно обработать оба endpoint:

- При U=0, `side='right'` пропускает leading zero probabilities и выбирает первый положительный интервал.
- При U, равном внутреннему threshold, repeated thresholds пропускают intermediate zero probabilities.
- При U=1 или конечном U выше последнего threshold вследствие rounding суммы `searchsorted` может вернуть `len(cats)`. Guard должен выбирать последний уровень с **положительной нормализованной вероятностью**, а не последний уровень безусловно: trailing zero levels не должны становиться наблюдаемыми из-за численного endpoint.

Последнее уточнение связано непосредственно с raw current coordinate: прежний stale numeric `u` обычно был clipped ниже 1; после исправления current CDF может действительно равняться 1. Для обычного positive final probability выбор последнего positive level совпадает с прежним выбором последнего level.

Минимальная рекомендуемая правка:

```python
draw = np.searchsorted(thr, U[:, j], side="right")
overflow = draw == len(cats)
if np.any(overflow):
    draw[overflow] = np.flatnonzero(probs > 0)[-1]
```

Условное вычисление last-positive index не затрагивает обычные draws и не вводит новую blanket validation. `flatnonzero` явно получает плоский индекс уровня. Гарантия здесь относится к пригодной для categorical sampling конечной неотрицательной vector probabilities с положительной суммой. Длина/shape, negative/NaN/inf, пустые categories, нулевая или overflow-сумма весов и mixed-type category coercion не получают новых контрактов в B10: существующие malformed-spec ошибки либо некорректные outputs требуют отдельного разбора. Не следует использовать endpoint fix для скрытого расширения этой валидации.

## Реальные callers

| Caller | Доступ к helper | Эффект B10 |
| --- | --- | --- |
| `CausalDatasetGenerator` | `_sample_X`, когда есть specs, `use_copula=True`, отсутствует custom X | Исправляет categorical X; последующие treatment/outcome/oracle values могут измениться |
| `MultiCausalDatasetGenerator` | Тот же выбор sampling path; actual namespace guard после sampling | Исправляет categorical X и first-categorical crash; B09 guard сохраняется |
| `InstrumentalGenerator` | Наследует binary `_sample_X`; `generate_iv_data` передаёт `use_copula` и corr | Исправляет categorical covariates при explicit copula; instrument/treatment/outcome затем могут измениться |
| `generate_multitreatment` | Передаёт copula параметры multi-generator | Generic public wrapper получает исправление без нового API |
| `make_cuped_tweedie` | Explicit copula с mixed specs, categorical platform; sampler используется и для mapping names | Platform перестаёт зависеть от uniforms предыдущего discount_rate spec; downstream эффект ожидаем |
| `generate_rct`, classic-RCT wrappers | `generate_rct` явно задаёт `use_copula=False` | Не затрагиваются этой правкой |
| `generate_rct_causal_data` | Вызывает multi `_sample_X`, но создаёт sampler с default `use_copula=False`; публичного copula параметра нет | Не затрагивается при существующем API |
| `generate_cuped_binary` | Mixed categories, но default independent sampling | Не затрагивается |
| Existing multi gamma/binary scenarios | Explicit copula, но specs состоят из numeric marginals | Numeric-only compatibility должна быть exact |
| `generate_multi_dml_cx_26`, `generate_offer_iv_26` | Custom X sampler имеет приоритет над copula | Их custom sampled covariates не затрагиваются |

Custom samplers не расширяют categorical specs через этот helper. Также `use_copula=True` без specs не включает copula: стандартный normal sampling path имеет приоритет.

## Совместимость и независимый reference

На уровне helper normal draw остаётся тем же одиночным `(n,d)` вызовом; ни categorical selection, ни endpoint guard не расходуют RNG. Поэтому следующий RNG draw после helper сохраняется. Numeric columns в mixed schemas и весь numeric-only output также должны совпадать точно.

Для схем с categorical covariates исправление сознательно меняет значения X и их joint law. Не следует обещать прежние полные DataFrames либо весь последующий RNG state generator: изменённые scores, rare-arm retries или outcome samplers могут расходовать random stream иначе. Для numeric-only и отключённых copula paths exact full-generator compatibility проверяется отдельно.

Независимый probe использует известную положительно определённую 2×2 correlation matrix при rho=0,+0.6,-0.6. Gaussian координата вычисляется явной формулой Cholesky с сохранённым jitter; классы задаются Gaussian-domain cutpoints `Phi^{-1}(.2)` и `Phi^{-1}(.5)`, без shared PSD helper и без копирования `cdf/searchsorted` implementation. На 20,000 строках, seed731, in-memory candidate совпадает с reference во всех трёх конфигурациях. Baseline отличается в 12,433, 8,704 и 15,171 строках соответственно; это число несовпавших реализаций draws, не число отдельных bugs.

Controlled tests дополнительно подтверждают leading/middle/trailing zeros на U=0,0.5,1 и несколько trailing zero levels. Single-level categorical первым spec успешно даёт прежний нулевой столбец. Numeric-only probe одновременно проверяет восемь прежних distribution families на n=512, seed947: values, schema и next10 RNG draws совпадают точно.

Evidence: [reproducible probe](block10_contract_probe.py), [aggregate results](block10_contract_result.json). Probe реконструирует точную исходную версию через Git и применяет только предложенную правку **в памяти**. В evidence это явно обозначено как candidate verification; отдельно проверяется совпадение runtime AST actual helper с candidate и фиксируется hash library diff. Reviewer не запускал integration, CI, DiD или sensitivity. Тесты public callers и итоговые scope gates принадлежат root block report.

## Проверка committed правки

Финальный source/tests checkpoint: `95a8b7599fb129fb2c5973f50e9b4a8018732f6c`. Read-only проверка подтвердила, что inspected `causalis/dgp/base.py` byte-identical этому Git object; source/tests после checkpoint не изменены. Runtime body `_gaussian_copula`, исключая docstring, совпадает с независимо проверенным in-memory candidate.

Committed правка использует raw current-coordinate U и conditional last-positive fallback. Numeric clipping остаётся на прежнем месте; corr repair, Cholesky jitter, normal draw, normalization probabilities, category expansion и names не меняются. Новые Notes точно описывают bounded coordinate/endpoint контракт. В этой ограниченной правке material correctness findings не обнаружены. Это source/contract verification, а не заявление о результате ещё выполняемых root integration и CI.
