# B15 · Gaussian marginal propensity oracle

Дата: 2026-10-07, Europe/Moscow. Baseline **`71f6a619b04e0ab8fab388fb95b7d0f3d6631b96`**. Source/test checkpoint **`9a57e91942a4b90b0401c0f8e3ebe6f5b4d82cdf`**, обычный push в `origin/codex/correctness-roadmap` выполнен. Final audit checkpoint определяется `git log -1` после завершения. Source/tests после9a57 заморожены.

Root и три прежних CLI субагента разделили implementation, mathematical contract, public regressions и independent review. Изменены два library paths (`causalis/dgp/multicausaldata/base.py`, `functional.py`) и добавлен один79-case test module. Sensitivity остаётся отложенным.

## Результат и контракт

Новая opt-in опция `include_marginal_propensity=False` у `MultiCausalDatasetGenerator` и `generate_multitreatment` добавляет K колонок `m_marginal_<arm>` после всех existing columns. Она требует `include_oracle=True` и принимает bool/NumPy bool. Старые positional arguments сохранены; enabled actual namespace и callback mutations проверяются без переименования. Отключённые marginal-like names доступны для confounders/treatments. Data-contract projection сохраняет прежние outcome/treatments/features и удаляет oracles из analysis frame.

Для уже откалиброванных affine scores a(X) target — **q_k(X)=E[softmax_k(a(X)+bZ)]**, независимый Z~N(0,1). Existing m=softmax(a) и m_obs=softmax(a+bU) сохраняют свои значения. Supplied U задаёт realized values, не новую latent law. При ensure_all q описывает nominal softmax system; retries/repair меняют assignment law возвращённого sample. target_d_rate продолжает sample-X/U=0 calibration. Selected-U ATT требует другого weighted integral и не добавляется этим API.

Пример:

```python
from causalis.dgp.multicausaldata import MultiCausalDatasetGenerator

generator = MultiCausalDatasetGenerator(
    k=0, u_strength_d=[0.0, 1.0, 1.0],
    include_marginal_propensity=True, seed=731,
)
frame = generator.generate(100)
```

При одинаковых intercepts m=[1/3,1/3,1/3], но q≈[.3601605153,.3199197423,.3199197423]. Functional wrapper пока не предоставляет latent-strength parameters; его q=m при нулевых latent slopes. Нетривиальная Gaussian marginalization доступна через класс.

## Numerical policy

Equal slopes сокращают общий latent shift и возвращают exact m. Иначе каждый distinct score row интегрируется через [SciPy quad_vec](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.quad_vec.html) с max-norm estimated absolute target1e-10, epsrel0, domain[-12,12], budget4096 subintervals. Pairwise crossings и neighborhoods ±1/4/16/40 divided by slope difference показывают узкие transitions/intermediate arms. Common intercept/slope shifts удаляются до evaluation.

Gaussian omitted probability mass3.553e-33 ограничивает truncation error каждого q. Backend convergence/error, finite probability bounds и mass проверяются до rounding normalization. Unsupported float geometry, excessive breakpoints или nonconvergence дают explicit opt-in ValueError, без fallback к m. Returned error — numerical estimate, а не rigorous uniform certificate для любых coefficients или relative accuracy rare probabilities. [SciPy quad](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.quad.html) также документирует риск пропуска узких features; это учитывается в независимом scalar reference.

Working memory O(nK+K²+LK), L bounded by4096, memoization262144bytes; n*K*nodes tensor не создаётся. Integration не потребляет RNG, но может быть медленной при varying X. Failed generation после sampling не откатывает RNG/callback effects. Existing outcome integration/sampling/calibration/assignment bodies сохранены; default path не выполняет новую quadrature.

## Проверки

**79 новых public cases passed**,0failures/errors/skips/warnings,6.99s. Тот же final module на exactbaseline: **74failed/5passed**,0errors/skips/warnings,6.11s. Все74 failures означают отсутствие нового API:67unknown-keyword TypeErrors и7missing-field AttributeErrors; это не74старых numerical bugs. Historical full positional call и disabled-name compatibility controls проходят baseline.

Первый focused run выявил near-duplicate crossings в независимом scalar reference (несколько ULP), вызвавшие QUADPACK warning. Reference knots coalesced within32ULP; integrand/domain, warning/error rejection и probability atol2e-9 сохранены. Final baseline/focus повторены на одинаковых исправленных test bytes; initial78pass/1referencefailure не входят в окончательный proof. [Tests note](B15_ORACLE_TESTS.md), [combined manifest](block15_oracle_test_result.json), [reference-knot probe](block15_oracle_reference_knot_probe.json).

Independent [contract](B15_ORACLE_CONTRACT.md):31private mathematical q references,4invariances,8public baseline/candidate frame/RNG pairs. Max q discrepancy3.89e-16. Отдельно GH32/GH64 согласуются до2.22e-16, но промахиваются на.000399/.00399 в shifted binary/narrow-middle examples; это воспроизведение против fixed-order convergence assumptions. Frozen multi/binary/IV и actual shared-helper closure pinned; functional hash read-only в этом probe, wrapper runtime проверен другими evidence.

Independent [review](B15_ORACLE_REVIEW.md):56defaultconfigs×2=112exact old/current pairs и20enabledconfigs×2=40additivepairs, включая все4outcome families, raw/contract wrappers, successive calls, complete schema/dtypes/metadata/callbacks/RNG states/next10.34adaptive q refs including slopes1e6, narrow regions, rare arms, tail transitions and supported extreme geometry; max discrepancy2.78e-16. Bounded pass дополнительно проверяет10projection cases,8backend/error/probability/mass/budget failures, NumPy booleans и exact q invariance для3 supplied-U configurations. Открытых material findings нет. Два inherited `_softmax` subtraction-overflow warnings принадлежат extreme baseline/control fixture; их нельзя выдавать за отсутствие всех warnings. Large-K budget fixture также наследует pandas fragmentation warnings от старой сборки DataFrame; library/tests ради этих stress warnings не менялись.

Focused test SHA256 **`3e6ade34ff0d7faadd172eab87ab15a9ccc24b968564c81302ede8a686f8df37`**; model SHA **`c46c1e090b0e033b59a6aa4eb65ba7cb9a1fdbb5aba4cde05132b19f903ea982`**, functional SHA **`e3b074a2ff2cd57de9756cd81b4f01bdbbaa8fd728b87de5517d692b37723d43`**. [Committed provenance](block15_committed_provenance.json) связывает11unique source/test/dependency paths с exactGitbytes9a57, сохраняя исходные precommit HEAD/timestamps; numerical runs ради linkage не повторялись. Root AST check удаляет только named additive branches/option/docstrings и подтверждает совпадение остального executable AST обоих library modules с baseline.

## Local integration и CI

**Локальная correctness integration на exact source9a57: 2618 passed, 0 failures/errors/skips, 78 warnings, 179.77s**, exit0. Все 79 новых cases включены. Python3.12.14, macOSarm64; фактические версии и аргументы записаны в [selection](block15_integration_selection.json), итог в [result](block15_integration_result.json), исходный вывод в [log](block15_integration_tests.log). Число warnings совпадает с B14; скорость по этим запускам не оценивается.

**CI [37628255646](https://github.com/MaximLenivkin/Causalis/actions/runs/37628255646) completed/success** на exact9a57. Все шесть скачанных selection/result/environment/JUnit sets дают **2618 passed каждый**, без failures/errors/skips. Snapshot UTC2026-10-07T13:29:16.809213. [CI manifest](block15_ci_result.json) хранит actual payloads, versions и jobIDs.

| Linux configuration | Actual Python | NumPy | SciPy | Passed |
|---|---|---|---|---|
| 3.10 latest | 3.10.21 | 2.2.6 | 1.15.3 | 2618 |
| 3.10 legacy | 3.10.22 | 1.26.4 | 1.11.4 | 2618 |
| 3.11 latest | 3.11.17 | 2.4.6 | 1.17.1 | 2618 |
| 3.12 latest | 3.12.14 | 2.5.3 | 1.18.1 | 2618 |
| 3.13 latest | 3.13.16 | 2.5.3 | 1.18.1 | 2618 |
| 3.14 latest | 3.14.7 | 2.5.3 | 1.18.1 | 2618 |

Root validator и независимый reviewer проверили по actual downloaded XML/JSON все шесть полных2618case sets против local JUnit, все79newcases, actual argv и прежние7exclusions. Reviewer дополнительно закрепил hashes18payloads, run-status и local JUnit в `ci_review`; issues[]. Ровно семь прежних sensitivity modules исключены; selected_full_suite=false и sensitivity_validated=false. Это clean scoped correctness suite. Standalone Sphinx, full sensitivity и release не validated. После source checkpoint меняются только audit files; audit-only push не запускает повторную matrix.

[Final evidence validator](block15_validation_checks.json) подтверждает exact scope/source hashes, preserved default AST, original final baseline/focused/local JUnit counts и case IDs, frozen numerical provenance, bounded review и committed linkage, independent CI review с actual artifact hashes. AST8Pythonfiles и24relative report links проверены; issues[]. [Handoff validator](handoff_validation.json) проверил **110immutable links**, включая3newB15links; английские ready-to-use paragraphs сохранены локально, внешние сообщения не отправлялись.

## Следующий этап и ограничения

**B16 — binary/IV marginal outcome accuracy.** B15 reference measurements подтвердили existing fixed-GH21/GH31 errors, runtime этих paths не менялся. При logistic a=-5,s50 independent mean.4601982453, binary publicg0.3666787193 иIVpotentialmean.3898474050. При clipped-exponential a=-25,s10 binary относительная ошибка40.66%; приa0,s10IV13.81%. Это отдельный observed numerical defect, не supplied-U target mismatch.31outcome configs и exactsource/configs доступны в [contract result](block15_contract_result.json).

Начальный B16 scope: binary g0/g1 иIV `_potential_outcome_means`, Gaussian target/independent adaptive reference, observed draws/RNG compatibility. Compound `_g_by_z`, `_r_by_z`, Tweedie joint-latent means требуют собственного target и scope решения: product of independent marginals не заменяет integral с shared U. Existing multi outcome algorithms уже GH81/logistic-normal convolution/analytic clipped-exp; на измеренном наборе они согласуются с independent reference и остались byte-equivalent по executable AST.

Sensitivity/SC08LOO, latent-selected ATT, произвольные latent laws, actual-marginal calibration, learner shape/complex/IV storage, extreme score/IF arithmetic, snapshot ownership и dedicated Sphinx build сохраняются отдельными задачами. Нет новых performance/coverage/release/full-sensitivity claims. Upstream sync, PR, release и внешние сообщения не выполнялись. **Остановиться на границе B15; B16 начинается отдельным запросом.**

Reproduce focused checks отдельно: `.venv/bin/python audit/block15_oracle_test_runner.py --mode baseline` и `.venv/bin/python audit/block15_oracle_test_runner.py --mode focused`; committed integration: `.venv/bin/python audit/run_block15_integration.py`; final source/AST/evidence validator: `.venv/bin/python audit/verify_block15.py --source 9a57e91942a4b90b0401c0f8e3ebe6f5b4d82cdf`. [Implementation note](B15_ORACLE_IMPLEMENTATION.md), [contract probe](block15_contract_probe.py), [review probe](block15_review_probe.py).
