# B10 · Categorical Gaussian copula

Дата: 7 октября 2026, Europe/Moscow. Исходная версия: `83b63836dbd0c4793c24dd95ff7dc18c443792ad`. Source/tests checkpoint: **`95a8b7599fb129fb2c5973f50e9b4a8018732f6c`**, pushed в personal `origin/codex/correctness-roadmap`. После этого source/tests не менялись. Root и три CLI субагента выполнили реализацию, разбор контракта, независимые regressions и review.

## Исправление

Shared sampler теперь использует raw uniforms **собственной Gaussian координаты** каждого categorical spec. Раньше categorical на первой позиции вызывал UnboundLocalError, а остальные categorical повторяли uniforms предыдущего числового spec. Independent baseline reproduction при identity corr, seed731,n1000 дал полное совпадение category1 со знаком предыдущего normal во всех1000строках, хотя latent coordinates независимы.

Связанный endpoint guard при CDF, округлённой до1, выбирает последний уровень с положительной вероятностью. С прежним guard trailing zero-probability category могла ошибочно появиться после перехода на raw current-coordinate uniforms. Numeric inverse-CDF clipping остаётся прежним; categorical uniforms не обрезаются, чтобы сохранить допустимые probability intervals меньше1e-12.

Scope — один library path `causalis/dgp/base.py`, один новый test module `tests/data/test_copula_categorical_coordinates.py`. PSD repair/jitter, Gaussian draw shape, probability normalization, drop-first encoding, single-level names и public API сохранены. Malformed categorical probability/category contracts не расширены. [Implementation](B10_COPULA_IMPLEMENTATION.md), [contract и callers](B10_COPULA_CONTRACT.md).

В исправленных categorical schemas значения X, D, Y и oracles могут измениться. Helper не добавляет random draws; полный downstream RNG при categorical X не гарантируется, поскольку outcome/retry branches зависят от X. Для numeric-only paths проверено точное совпадение полных frames/schema/RNG. Corr относится к latent Gaussian variables, не к observed Pearson correlation one-hot columns.

## Проверки

- **33 новых cases passed**, без failures/errors/skips/warnings,3.84s. На точном baseline тот же frozen module: **30failed,3passed**,4.29s;20unbound-coordinate cases и10wrong-values cases. Это число параметризаций, не отдельных bugs. Collection и committed source/test hashes совпали. [Tests](B10_COPULA_TESTS.md), [provenance](block10_copula_test_result.json).
- Соседние существующие copula и namespace modules: **126passed**, без warnings,3.71s. [Raw log](block10_neighbors_tests.log).
- Independent reviewer:18numeric-helper configs×2calls=36exactarray/schema/nextRNG comparisons;48public binary/multi/IV configs×2generations=96exactframe/dtypes/schema/nextRNG comparisons, восемь scalar marginals и четыре outcome families. Ещё9Gaussian-coordinate partitions и7controlled boundary cases прошли. Material patch findings нет. [Review](B10_COPULA_REVIEW.md), [actual committed-source evidence](block10_review_result.json).
- Contract-agent independent Gaussian-domain reference:3configs rho0,+.6,-.6,n20000, без production PSD/CDF categorical helper; exactcandidate matches. Candidate artifacts явно отделены от read-only проверки actual committed patch. Controlled raw-vs-clipped tiny intervals и zero-probability endpoints проверены. [Contract evidence](block10_contract_result.json).
- **Local Mac integration:2071passed,1failed,0errors/skips,78warnings,90.27s**,exit1,total2072. Это **не чистый local suite**. [Result](block10_integration_result.json), [selection/environment](block10_integration_selection.json), [raw log](block10_integration_tests.log).

Единственный local failure — прежний `test_post_inference_report_accepts_panel_and_estimate`: GREEN assertion получает YELLOW из-за практически нулевых preATT/SE. На committed95a8b75 значения точно совпадают с B09: preATT1.1102230246251558e-16,SE2.9351198205368013e-31,|t|≈3.7825e14. Fixture и все пять вызванных package files byte-identical baseline83b6383; изменённый shared sampler не вызывается. [Current provenance](block10_did_provenance.json), [previous exact-baseline proof](B09_LOCAL_INTEGRATION_NOTE.md). Assertion, threshold и exclusions не ослаблялись.

## CI

Run [37532909989](https://github.com/MaximLenivkin/Causalis/actions/runs/37532909989) **completed/success** на exact source `95a8b7599fb129fb2c5973f50e9b4a8018732f6c`. Все шесть Linux jobs и downloaded selection/environment/JUnit artifacts проверены: **2072 passed каждый**, без failures/errors/skips. Actual Python: 3.10.21 latest/legacy, 3.11.16, 3.12.14, 3.13.15, 3.14.7. [Verified matrix](block10_ci_result.json): `matrix_verified=true`, six verified jobs, issues пуст. Ровно семь sensitivity exclusions совпали с B09 и local selection. Тестовые counts включают 33 новых cases.

## Воспроизведение и ограничения

```bash
.venv/bin/python audit/block10_copula_test_runner.py --mode baseline  # exit1 expected
.venv/bin/python audit/block10_copula_test_runner.py --mode focused
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLBACKEND=Agg MPLCONFIGDIR=.venv/matplotlib .venv/bin/python audit/block10_review_probe.py
.venv/bin/python audit/block10_did_provenance.py
.venv/bin/python audit/run_block10_integration.py  # exit1 expected on this Mac stack
.venv/bin/python audit/verify_block10.py
.venv/bin/python audit/verify_handoff.py
```

Интеграционный runner требует committed source/tests и сохраняет SHA, environment, selection, exitcode и реальные JUnit counts. Новые test runner/reference snapshots существуют только временно в памяти/owned temp directory. Local runtime/CI artifacts excluded; reproducible scripts и aggregate evidence сохраняются. Все данные этих проверок — synthetic repository fixtures; corporate/client data не использовались.

Ровно семь прежних sensitivity modules deferred. Full sensitivity, standalone Sphinx, release и все возможные OS/dependency combinations не проверены. Нового performance benchmark или universal speedup claim нет. Upstream sync, PR/issues/messages/release не выполнялись.

Следующий кандидат **B11** — actual namespace guards для binary/IV генераторов. Независимое ревью подтвердило, что normal confounder с именем `d` перезаписывает treatment в raw output: n30, seed731, обе семьи возвращают 30 nonbinary treatment values. Это отдельный прежний дефект caller source, не исправленный multi-only guard B09; [evidence](block10_review_namespace_followup.json). Проверять фактические имена без silent rename, включая expanded categorical и enabled oracles. Отдельный numerical-zero DiD diagnostic/fixture follow-up сохраняется: нужен математически обоснованный reference, без masking failure или blanket clipping. Затем Gaussian oracle accuracy/additive marginal-propensity API и оставшийся correctness backlog. Sensitivity/SC08LOO deferred. На границе B10 остановиться; следующий блок только по новому запросу пользователя.

Финальная проверка artifacts: [verify_block10.py](verify_block10.py) и [validation JSON](block10_validation_checks.json); portable documentation handoff — 91 immutable GitHub links verified, issues пуст. Source/tests frozen после95a; итоговый audit checkpoint — `git log -1`.
