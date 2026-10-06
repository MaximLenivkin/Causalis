# B10 · Реализация категориальной Gaussian copula

Исходный checkpoint: `83b63836dbd0c4793c24dd95ff7dc18c443792ad`. Scope: общий sampler `causalis/dgp/base.py`, один новый regression module и audit evidence. Causal estimator formulas и sensitivity не меняются.

В categorical inverse CDF используется текущая координата `U[:, j]`. Раньше локальная переменная `u` появлялась только после categorical branch и сохраняла clipped uniforms предыдущего числового признака. Поэтому categorical на первой позиции вызывал UnboundLocalError, а следующие categorical использовали чужую координату.

Numeric `u = clip(U[:, j], 1e-12, 1-1e-12)` остаётся на прежнем месте. Категориальное преобразование не требует такого clipping: оно обрезало бы допустимые очень малые вероятности. При верхнем численном насыщении, когда draw выходит за массив категорий, fallback выбирает последний уровень с положительной вероятностью. Это предотвращает попадание в trailing zero-probability level. Нулевые начальные/внутренние интервалы по-прежнему обходятся right-sided CDF search.

Сохраняются нормализация probabilities, latent PSD correction/jitter, draw shape, one-hot/drop-first expansion и single-level schema. Validation некорректных probability/category specs не расширяется. Helper расходует прежний Gaussian draw `(n, number_of_specs)` и не делает дополнительных случайных вызовов. Numeric-only генерация сравнивается с frozen baseline по полным frames и следующим RNG draws.

Для схем с categorical исправленные X могут изменить D, Y и oracles. Полное совпадение downstream RNG для всех outcome/retry branches не обещается: некоторые из них зависят от исправленных X. Параметр corr задаёт корреляцию latent normals, а не Pearson correlation one-hot columns.

Independent contract, tests и review: [contract](B10_COPULA_CONTRACT.md), [tests](B10_COPULA_TESTS.md), [review](B10_COPULA_REVIEW.md). Результаты интеграции и CI записываются в [итог блока](BLOCK10_COPULA.md) после проверки зафиксированного source checkpoint. Известный baseline DiD near-zero failure остаётся отдельным follow-up и не скрывается изменением assertion или exclusions.
