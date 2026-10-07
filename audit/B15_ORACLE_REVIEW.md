# B15: независимое review Gaussian marginal propensity oracle

**Открытых существенных замечаний к source и финальным tests нет; `issues: []`.** Baseline: `71f6a619b04e0ab8fab388fb95b7d0f3d6631b96`; source/test checkpoint: `9a57e91942a4b90b0401c0f8e3ebe6f5b4d82cdf`. Применён `code-review`, прочитаны `AGENTS.md`, `B07_DGP_REVIEW.md` и active `NEXT_SESSION.md`. Reviewer не редактировал library/tests/git и не запускал integration или CI. Все probe fixtures synthetic.

## Target, совместимость и schema

Новый opt-in `include_marginal_propensity=False` добавлен последним public positional parameter generator и functional wrapper. Исходные parameters/defaults/order сохранены. Это новый public dataclass field; repr/asdict естественно отражают его наличие, byte compatibility repr не заявляется. При enabled option требуется `include_oracle=True`; принимаются только Python bool и NumPy bool scalar. Constructor, каждый generate и final callback boundary повторно проверяют option. Новые enabled oracle names резервируются совместно с treatment, actual expanded X и existing oracle roles; overwrite/rename не допускаются. Disabled marginal-like feature names остаются допустимыми.

`m_marginal_<arm>` интегрирует **calibrated nominal softmax scores** по independent reference `U ~ N(0,1)`. Это не замена existing `m` при U=0 или `m_obs` при realized U. Supplied non-Gaussian/X-dependent U не изменяет reference law; target calibration остаётся sample-X/U=0. При `ensure_all` новая q также относится к nominal model, а не к conditioned/repaired sample. Latent-selected ATT не вводится и не подменяется средним marginal CATE.

Raw frame получает ровно K новых columns в конце. Functional wrapper имеет zero latent treatment strength, поэтому его q точно совпадает с m. При conversion `MultiCausalData` по прежнему контракту проецирует df на outcome/treatments/actual features и удаляет oracle columns; q не становится feature и не меняет converted df. Проверены functional/direct conversion, включая actual features с disabled `m_marginal_*` именами. Первоначально reviewer fixture ошибочно ожидал сохранение oracle columns в contract.df; исправлен только собственный fixture, исходный failed attempt сохранён в log и не считается source finding.

## Численная проверка

Runtime интегрирует distinct score rows через adaptive vector quadrature на [-12,12], с pairwise crossings и transition neighborhoods. Common affine shifts предварительно удаляются; equal latent slopes дают **точную копию m**. Gauss-Hermite fixed-order guess не используется. Проверяются backend success, finite error estimate <=1e-10, finite/nonnegative probabilities, bounds и total mass до rounding normalization. Nonconvergence, unrepresentable integration geometry и subdivision-budget exhaustion дают explicit ValueError, без fallback к m или guessed probability. Error estimate — проверяемый численный критерий, а не rigorous certificate для произвольных coefficients.

Working storage — O(nK + K² + LK): unique rows/inverse/output, per-row pairwise partition и bounded adaptive backend state; n×K×nodes tensor не создаётся. Default option не вызывает integration. Изменение не заявляет performance improvement; varying-X opt-in может быть медленным. Gaussian omitted mass за [-12,12] меньше 4e-33 и ограничивает probability tail contribution отдельно от quadrature error.

Independent reference использует **scalar QUADPACK для каждого arm**, SciPy softmax и Decimal crossing arithmetic с другими transition offsets, не вызывает internal oracle helper и не повторяет vector backend. Проверены **34 adaptive configurations**: K2/K3/K5, strengths 0/.1/1/2/5/10/50/1000/1e6, B07 example, equal/nearly equal slopes, rare/narrow intermediate arm, shifted narrow region и tail transition. Maximum observed absolute q error **2.78e-16**; finite bounds и row sum подтверждены. Это результат указанного stress set, не универсальная accuracy guarantee. B07 q `[0.36016051533665233, 0.31991974233167386, 0.31991974233167386]` воспроизведён.

Дополнительно проверены common intercept/slope shifts, latent sign reversal и arm permutation. Supported coefficients порядка1e306 с logistic crossing U=1 дают `[Phi(1), Phi(-1)]` с independent step-limit reference: ошибка smoothing ограничена `2 log(2)/(s sqrt(2pi)) < 6e-307`. При intercepts ±1e308 и slopes ±5e306 mathematical crossing U=20 находится вне domain, несмотря на overflow numerator при его float calculation; q `[1,0]` корректна с absolute tolerance. Supported envelope объясняет безопасность этого случая: in-domain crossing требует N<=min(sum|A|,12sum|B|), а сумма двух envelopes <=2F означает N<=F. Поэтому overflowed intercept difference не скрывает in-domain transition в поддерживаемой geometry. Общая extreme-score numerical policy не менялась.

**11 initial rejection/mutation cases** и отдельные **8 convergence/budget cases** проходят через public generation. Mock backend проверяет unsuccessful status даже с plausible unit-mass result, чрезмерный/nonfinite error, NaN/negative/out-of-range probabilities и неверную mass. Numeric references backend не подменяют. Проверены early conflicting flags, actual/categorical collisions, late callback enable into feature collision и unsupported geometry. Дополнительный boundary review содержит **10 conversion/projection cases**, оба NumPy bool values и exact q invariance к трём supplied U.

Два captured `overflow encountered in subtract` warnings принадлежат прежнему `_softmax` на extreme outside-crossing fixture. Independent disabled/enabled comparison подтверждает те же source lines, два warnings, existing frame values и RNG state с обеих сторон. Это inherited behavior, не новый integration warning; all-warnings-zero claim для reviewer stress run не делается. Large-K budget fixture также проходит прежние repeated DataFrame assignments и может выдавать inherited pandas fragmentation warnings. Их suppression/performance fix вне B15.

## Exact defaults и финальные tests

Заморожен полный graph shared base, multicausal base/functional и scenario control module из точного baseline. Проверены old copula binding, wrapper class binding и scenario-to-wrapper binding; public package aliases корректно переключаются и восстанавливаются. Unchanged shared/package/contract sources сверены byte-for-byte. Baseline не использует current generator под другим именем.

**56 valid default configurations ×2 calls =112 exact old/current reference pairs** покрывают все четыре outcome families, zero/latent/supplied U, calibration, nonlinear callbacks, copula/categorical/custom sampling, iid/ensure_all, include_oracle on/off, functional raw/contract и direct `to_multicausal_data`. Полностью сравнивались frame values/schema/order/dtypes, converted model metadata, callback order/count, все созданные RNG streams, их full states и next10 draws. Дополнительно **20 enabled configurations ×2 calls =40 additive reference pairs** сохраняют все прежние columns, observations, callback calls и RNG; меняется только raw tail schema. Generation repeated calls проверены без reseeding generator.

Reviewer прочитал весь final `tests/data/test_multicausal_marginal_propensity.py`: **79 cases**, public APIs и independent scalar references. Scalar reference coalesces machine-precision partition knots без изменения integrand/domain/tolerance и проверяет numerical error/warnings. Test module SHA256: `3e6ade34ff0d7faadd172eab87ab15a9ccc24b968564c81302ede8a686f8df37`. Final focused **79 passed /0 warnings**; frozen baseline **74 failed /5 passed**, без errors/skips. Baseline failures — **67 TypeError +7 AttributeError** из-за отсутствия запланированной additive API; это не 74 найденных numerical bugs. Original positional/default compatibility controls проходят baseline.

Source SHA256, на которых выполнены references: base `c46c1e090b0e033b59a6aa4eb65ba7cb9a1fdbb5aba4cde05132b19f903ea982`, functional `e3b074a2ff2cd57de9756cd81b4f01bdbbaa8fd728b87de5517d692b37723d43`. Original working-patch `reviewed_head`, timestamps и hashes сохраняются отдельно от committed linkage; широкие references ради нового HEAD не повторяются. Evidence: `audit/block15_review_probe.py`, `audit/block15_review_result.json`, `audit/block15_review_log.log`. Sensitivity, selected ATT, alternate supplied-U law, standalone docs и release не проверяются этим review.

## Независимая проверка CI artifacts

Проверены уже скачанные artifacts [run 37628255646](https://github.com/MaximLenivkin/Causalis/actions/runs/37628255646), source checkpoint `9a57e91942a4b90b0401c0f8e3ebe6f5b4d82cdf`. Snapshot наблюдался `2026-10-07T13:29:16.809213+00:00`, независимая проверка — `2026-10-07T13:45:57.869279+00:00`. Во всех шести jobs **2618 passed, 0 failures/errors/skips**; полный набор 2618 уникальных `(classname, name)` в каждом actual JUnit точно совпадает с local integration JUnit. Все **79 новых cases** сверены с focused manifest/JUnit и присутствуют в каждом job. Проверены completed/success статусы run и jobs, exit code 0, scope correctness, actual pytest argv и неизменные семь sensitivity exclusions из B14; дополнительных selection flags нет. Это выбранный correctness suite с указанными exclusions.

Все artifacts указывают CPython на Linux и точный source commit; версии взяты из actual `selection.json`, включая различающиеся patch versions двух Python 3.10 jobs:

| Stack | Python | NumPy | pandas | SciPy | Pydantic |
| --- | --- | --- | --- | --- | --- |
| 3.10 latest | 3.10.21 | 2.2.6 | 2.3.3 | 1.15.3 | 2.13.5 |
| 3.10 legacy | 3.10.22 | 1.26.4 | 1.5.3 | 1.11.4 | 2.0.3 |
| 3.11 latest | 3.11.17 | 2.4.6 | 3.0.6 | 1.17.1 | 2.13.5 |
| 3.12 latest | 3.12.14 | 2.5.3 | 3.0.6 | 1.18.1 | 2.13.5 |
| 3.13 latest | 3.13.16 | 2.5.3 | 3.0.6 | 1.18.1 | 2.13.5 |
| 3.14 latest | 3.14.7 | 2.5.3 | 3.0.6 | 1.18.1 | 2.13.5 |

Повторно сверены committed Git blobs и current bytes всех девяти reviewed source/test/dependency paths. CI artifacts фиксируют commit metadata, но не публикуют отдельные SHA256 загруженных library files; это ограничение доказательства обозначено в `ci_review.source_hash_basis`. Raw artifact hashes, полные environment/package versions, actual argv и JUnit counts сохранены в `block15_review_result.json → ci_review`. Original reference provenance не переписана; pytest и численные probes при CI review не запускались. Итог: **matrix_verified=true, issues=[]**.
