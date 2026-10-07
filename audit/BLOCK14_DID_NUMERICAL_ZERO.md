# B14: exact-zero DiD regression and fitted inference diagnostics

Дата: 2026-10-07, Europe/Moscow. Branch: `codex/correctness-roadmap`. Exact baseline: `dbded76ecf8a207aad2094903b8f015fed8ae5d6`. Source/test checkpoint: **`4bdcff7d6388d1d72d5be4a546e8abb2a67a767c`**, ordinary personal-fork push выполнен. Final audit checkpoint определяется `git log -1` после сохранения отчёта; source/tests после checkpoint не меняются.

**B14 завершён: focused tests, independent mathematical/reference review, local integration и все шесть CI configurations прошли.** CI [37611862809](https://github.com/MaximLenivkin/Causalis/actions/runs/37611862809) completed/success на exact source4bdc; downloaded artifacts verified.

## Причина и результат

Frozen шестиюнитный API fixture имеет общий deterministic pre-trend, два controls для двух regression parameters и clusters, совпадающие с cohorts. Математически его pre ATT и cell variance точно нулевые. Ordinary SVD оставлял rounding residue: cell0 ATT `1.1102230246251558e-16`, SE `2.9351198205368013e-31`, |t| около `3.78e14`. Это повторяемый runtime baseline proof, а не новая интерпретация static B09 evidence.

Bounded OLS correction сохраняет единственное решение `(c,0,…)` только при exactly constant control response, unit intercept для всего prediction design и full rank, возвращённом тем же `lstsq`. Никакого epsilon/rounding/response clipping. Nonconstant, nearconstant, rank-deficient и non-unit-intercept paths сохраняют исходное least-squares решение; arbitrary cancellation не решается этой правкой.

При zero SE обычная studentization undefined, в том числе 0/0. Cell table теперь возвращает NaN, а fitted-pre check — YELLOW с соответствующим объяснением. Finite positive SE использует истинное signed ATT/SE, включая реальные очень малые эффекты; overflow остаётся signed infinity. Любая invalid/nonfinite pre cell запрещает GREEN и больше не исчезает при finite filtering. Missing ATT/SE invalidates cached statistics. Fully zero-SE bootstrap оставляет undefined simultaneous critical/bands NaN без all-NaN reduction warnings.

Normal p-value convention p=1 сохраняется только для exact ATT=SE=0; это не valid studentization. Ненулевой эффект при zero SE, отрицательная/nonfinite SE или nonfinite ATT дают NaN p. При positive finite SE normal-tail arithmetic прежняя.

Frozen original fixture теперь имеет exact-zero pre ATT/IF/SE и **обоснованный YELLOW**, а не fabricated large pretrend signal. Его прежний GREEN assertion intentionally fails в separate baseline/current probe. Обычный public API success fixture исправлен по дизайну: 36 units, 12 controls, шесть clusters spanning cohorts, seeded independent outcome noise. Все прежние assertions, model/report settings и thresholds сохранены; добавлены positive finite pre-SE assertions. Это не threshold/assertion weakening ради green suite.

## Scope и review

Изменены ровно два library paths: `causalis/scenarios/did/model.py` и `causalis/scenarios/did/refutation/post_inference.py`. Добавлен `tests/scenarios/did/refutation/test_did_studentization_contract.py` (51 cases), обновлён fixture существующего five-case API module. Source commit содержит также короткую [implementation note](B14_DID_IMPLEMENTATION.md), всего five paths, 345 insertions/35 deletions.

Public signatures, contracts, comparison eligibility, propensity optimizer, normalized ATT/IF derivatives, cluster covariance, aggregate formulas и bootstrap draws сохранены. Шесть runtime function bodies изменены в указанных двух modules; все остальные top-level function/class AST и signatures сверены. Raw pre-fit diagnostics и общий `_finite_numeric` не менялись.

Три существующих CLI agents независимо выполнили contract/reference, regression tests и review. [Contract](B14_DID_CONTRACT.md): loaded frozen/current source, explicit fixture/model/report bindings, five-path runtime closure, 11 OLS references, 14 statistic/p-value pairs на каждой стороне, seven mixed-invalid configurations, cached-input/zero-bootstrap boundaries и независимый nondegenerate prototype.

[Review](B14_DID_REVIEW.md): 16 fitted configs × two sequential estimates = **32 old/current reference pairs** (64 actual evaluations); full result tables/dtypes/metadata/diagnostics/reports и RNG states/next10 matched exactly. Отдельно 27 unchanged OLS cases, seven analytical constant cases, 28 studentization и nine p-value cases. Full references предшествовали двум последних guards; inverse byte transformation восстановила исходные SHA. Final delta проверила arithmetic, 15 mixed reports и four degenerate bootstrap cases; normal paths остались byte-equivalent, current warnings0, issues[]. Первичные HEAD/timestamps/hashes сохранены; broad references не повторяли ради metadata.

## Verification

[Focused/baseline evidence](B14_DID_TESTS.md): одни и те же final56 cases — **28 failed /28 passed** на exact baseline, errors/skips0, four old overflow warnings, 5.17 s; **56 passed**, failures/errors/skips/warnings0, 5.96 s после fix. Все five revised API tests проходят обе стороны. Twenty-eight failures — parameterizations, не distinct bug count. Source/helper/class/public/plot bindings, actual loaded hashes, exact collection и final test SHA verified.

Focused run был precommit на exact committed bytes. [Combined manifest](block14_did_test_result.json), independent review linkage и [root provenance](block14_committed_provenance.json) связывают original runtime evidence с actual4bdc Git objects; original observation не переименована в postcommit rerun. Root ledger проверяет12unique source/test/dependency paths.

**Local integration exact4bdc: 2539 passed, failures/errors/skips0, 78 warnings, 80.36 s**, exit0; process elapsed80.539s. [Selection](block14_integration_selection.json), [result](block14_integration_result.json), [raw log](block14_integration_tests.log). `scripts/run_tests.py --scope correctness` unchanged. Это clean **scoped** suite, не full sensitivity/release suite. Python3.12.14, macOS26.6.2 arm64; actual versions в selection environment. Все56focused cases входят в local JUnit. Отдельные151neighbors прошли до двух последних guards; [preliminary manifest](block14_neighbor_result.json) честно не устанавливает final-source byte linkage. Final integration покрывает их окончательную версию.

**CI: все six Linux jobs и downloaded selection/result/JUnit sets — 2539 passed каждый, failures/errors/skips0**, exact4bdc. [CI manifest](block14_ci_result.json): matrix_verified=true, issues[]. Snapshot UTC2026-10-07T11:10:36.429091+00:00; actual Python: 3.10.22 (latest), 3.10.22 (legacy), 3.11.17 (latest), 3.12.14 (latest), 3.13.15 (latest), 3.14.7 (latest). Seven exclusions и all56focused case IDs сверяются в каждом artifact; actual dependency versions в per-job environment, а не скопированы из B13.

Root [validator](verify_block14.py) проверяет four-path source/test scope, runtime AST, retained assertions/settings, loaded baseline/focus/hash/collection, committed provenance, independent references, original degenerate fixture, clean local JUnit, unchanged exclusions и six actual downloaded CI payloads.

Final artifact validation прошла: **10 Python AST files, 20 relative report links, exact baseline/focused/local JUnit и все six CI payloads**, issues[]. Root независимо подтвердил совпадение полных local/CI case sets, и reviewer отдельно проверил all56focused IDs, actual ignore arguments и environments; его CI observation сохранено в review JSON. [Validation result](block14_validation_checks.json). English handoff: **107 immutable source links verified**, issues[], external messages не отправлялись.

## Ограничения и следующий этап

Ровно семь sensitivity modules остаются deferred, список unchanged относительно B13 в selection/CI manifests. Sensitivity и SC08LOO не начинались; Sphinx standalone build, release/PyPI, upstream sync/merge, PR/external messages и новый performance benchmark не выполнялись. Coverage/identification/robustness для arbitrary causal designs не доказываются API fixture или numerical refs. General nonconstant conditioning, extreme score arithmetic и partial-zero bootstrap policy не расширялись.

Следующий самостоятельный **B15**: Gaussian marginal-oracle numerical accuracy и совместимый additive API, по proposal `B07_DGP_REVIEW.md` и актуальному `FIX_PLAN.md`; сначала точный estimand/law/accuracy reference и convergence policy. Supplied-U/selected-treatment ATT — отдельная target policy, не treated average marginal CATE. B14 завершается на своей границе; B15 начинается новым запросом пользователя.
