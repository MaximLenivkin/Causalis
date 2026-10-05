# B02 — контракты данных, общие утилиты и DGP

Дата: 2026-10-05. Проект: `D:\codex\Causalis`. Ветка: `codex/correctness-roadmap`.
Исходный аудит относится к `ffe2c356c115f335b74b2f10117e19fe15585d46`.
**Статус: завершён.** Семь grouped findings исправлены; общий B02 integration run — **606 passed**, 5 существующих warnings, 123.61 s.

## Исправления по критичности

| Finding | Приоритет | Исправление и результат |
|---|---|---|
| ROOT-01 | P1 | Natural-scale `g_<arm>` / `cate_<arm>` multi-treatment DGP интегрируют независимый Gaussian U вместо подстановки U=0. Continuous mean — аналитический; gamma/Poisson — аналитическое ожидание clipped exponential; binary — детерминированное интегрирование с отдельным устойчивым методом для сильного latent effect. |
| ROOT-02 | P2 | CausalData / IVCausalData и PanelDataSCM отвергают бесконечные analysis values до расчётов и создания validated snapshot. |
| ROOT-03 | P2 | Causal/IV/Multi/PanelDID/PanelSCM отвергают complex в числовых ролях до потери imaginary части; panel treatment проверен также в object dtype. |
| ROOT-04 + DML-05 | P2 | Полное разделение групп даёт signed Inf в shared SMD. Binary/multi DML summaries учитывают Inf в max и violation fraction, выставляют RED и pass=False. Entirely unavailable statistics не получают PASS. Это один сгруппированный defect. |
| ROOT-05 | P2 | Случайные user IDs используют полный UUID4 и retry совпадений внутри frame; deterministic IDs сохранили прежний алгоритм. |
| ROOT-06 | P2 | `outcome_outliers(return_rows=True)` выбирает строки по исходным позициям через iloc; повторяющиеся labels индекса больше не добавляют обычные строки и дубликаты. |
| ROOT-07 | P2 | Splitter отвергает NaN, ±Inf, complex/non-numeric и boolean allocation weights до hashing. Допустимые assignments, coverage и boundaries сохранены. |

Sensitivity formulas, modules, benchmarks, RV/RVa и их tests не изменялись. Основные DML scores / IF остаются предметом следующего B03.

## Проверки и доказательства

Каждая область воспроизведена до исправления. Failure counts ниже — число cases, а не число независимых bugs; некоторые случаи проверяют более ранний и понятный reject уже недопустимого ввода.

| Область | До исправления | Финальная scoped проверка | Подробности |
|---|---|---|---|
| Числовые контракты | 44 failed / 16 passed; отдельно 2 object-complex treatment failures | 147 passed | B02_VALIDATION_NOTES.md |
| Balance separation | 21 failed / 1 passed | 50 passed, 3 existing normalize warnings | B02_BALANCE_NOTES.md |
| IDs / outliers / splitter | 15 failed / 10 passed | 25 focused + 9 neighboring passed | B02_UTILITIES_NOTES.md |
| Nonlinear oracle | 15 failed / 9 passed; strong-latent intermediate GH81 failed 3 cases | 28 focused + 17 neighboring passed | B02_ORACLE_NOTES.md |

Scoped запуски пересекаются; их числа нельзя складывать как число уникальных tests. Общая интеграционная проверка B02: **606 passed**, 5 warnings, 123.61 s. Evidence — `block02_integration_tests.log`. Warnings относятся к существующей политике relative-effect baseline около нуля и normalize_ipw; новых failures нет.

Финальная проверка артефактов: 188 absolute local links и 21 изменённый/новый Python file прошли existence/line-bound и AST checks; sensitivity paths changed — 0. `verify_block02.py` сохраняет отдельный `block02_validation_checks.json`, не переписывая историческое audit evidence. В handoff проверены 36 immutable GitHub snapshot/implementation links, issues — 0. `git diff --check` пройден.

```powershell
$env:MPLBACKEND='Agg'
$env:MPLCONFIGDIR='D:\codex\Causalis\audit\mplconfig'
$env:SKIP_DOCS_BUILD='true'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=audit\block02_integration_test_temp tests\data tests\shared tests\statistics\test_confounders_balance.py tests\statistics\test_outcome_outliers.py tests\refutation\test_balance_separation.py tests\refutation\test_uncofoundedness_balance.py tests\refutation\test_uncofoundedness_balance_extras.py tests\refutation\test_multi_unconfoundedness_diagnostics.py tests\refutation\test_love_plot.py tests\scenarios\multi_unconfoundedness tests\scenarios\unconfoundedness\test_dgp_rich.py tests\inference\test_conversion_z_test.py tests\inference\test_diff_in_means.py
```

Независимые references: analytic Gaussian MGF в обычных log-link cases; `scipy.integrate.quad` для sigmoid и clipped lognormal у обеих границ; controlled UUID collisions; вручную заданные propensity weights для публичных balance reports; positional expected DataFrames и half-open assignment boundaries. Фиксация RNG/observed draws проверяет, что oracle integration не меняет сгенерированные observations.

## Совместимость и границы

- Inf и complex в analysis columns теперь вызывают ValueError. Автоматической замены или imputation нет. Nullable finite real/bool поддерживаются; panels сохраняют numeric-string coercion. Identifier columns сохраняют прежние contracts.
- Случайные UUID IDs имеют длину 32 вместо 5 hex-символов и не зависят от random_state. Гарантия уникальности относится к одному сгенерированному набору.
- Allocation weights ограничены finite `numbers.Real`; bool, strings и Decimal, не зарегистрированный как Real, отвергаются. Сумма весов не нормализуется.
- Outcome oracle относится к Gaussian reference law U independent X. Supplied U меняет realized draws; произвольный иной закон U требует отдельного oracle. При latent confounding `g_<arm>` — potential-outcome mean, а не observational outcome regression `E[Y|D=arm,X]`.
- `m_<arm>` пока сохраняет softmax при U=0. Это явно описано и не выдаётся за marginal `P(D=arm|X)`. Вопрос отдельного marginal propensity oracle внесён в backlog.
- Binary integration приближённая; точность проверена независимыми references на умеренных и сильных latent strengths и рядом с переключением метода. Универсальной гарантии для произвольных extreme float parameters нет.
- Estimator output finite guards, mutable-frame lifecycle, версия dependency matrix и SMD near-zero variance tolerance не менялись. В будущем требуют отдельных проверок.
- Исторические audit probes/results не перезаписывались. Full suite с известным CUPED / statsmodels 0.15 defect не повторялся; этот defect остаётся в B05. Performance benchmark в B02 не проводился.

## Коммиты

| SHA | Изменение |
|---|---|
| `817c24c9b00e8896bb578b3568476c178bc024e4` | finite / real contracts + regression evidence |
| `add2f36652a7bb7d814975234255f7993f96f240` | shared и DML separation diagnostics |
| `a5a6e3a4887c7ac22aa86b36883398a34bbb5d76` | unique UUIDs, positional outliers, validated allocation |
| `c27e74406ffacee460ee6deb7c4be7669d1394e1` | Gaussian-marginal nonlinear outcome oracles |

Каждый code commit содержит tests и evidence notes. Итоговый documentation checkpoint содержит этот отчёт, integration log, обновлённые план, handoff и файл продолжения. Remote backup проверяется push/remote SHA check перед передачей результата пользователю; актуальный checkpoint доступен через `git log -1`.

## Следующее действие

После завершения B02 — остановка для очистки контекста. Следующий запрос пользователя запускает B03: multi ATTE IF, relative ATT IF, drop/weights alignment, CATE cache, GATE variance и OOS diagnostics. Sensitivity остаётся отложенным до upstream rewrite.
