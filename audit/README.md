# Аудит Causalis

Начать с [REPORT.md](D:/codex/Causalis/audit/REPORT.md). Это итог полного ревью на commit `ffe2c356c115f335b74b2f10117e19fe15585d46`, 5 октября2026.

Текущая разработка в `codex/correctness-roadmap`: [FIX_PLAN.md](D:/codex/Causalis/audit/FIX_PLAN.md), [NEXT_SESSION.md](D:/codex/Causalis/audit/NEXT_SESSION.md). Отдельный файл автору документации — [DOCUMENTATION_HANDOFF.md](D:/codex/Causalis/audit/DOCUMENTATION_HANDOFF.md); настройка GitHub — [GIT_ACCESS.md](D:/codex/Causalis/audit/GIT_ACCESS.md). Sensitivity analysis отложено.

- [PERFORMANCE.md](D:/codex/Causalis/audit/PERFORMANCE.md) — измерения и безопасная оптимизация pandas/NumPy.
- [COVERAGE.md](D:/codex/Causalis/audit/COVERAGE.md) — все области, доказательства и пределы проверки.
- [DML_REVIEW.md](D:/codex/Causalis/audit/DML_REVIEW.md) — основной Unconfoundedness/DML аудит.
- [SCENARIOS_REVIEW.md](D:/codex/Causalis/audit/SCENARIOS_REVIEW.md) — остальные causal scenarios.
- [CONTRACTS_SHARED_DGP.md](D:/codex/Causalis/audit/CONTRACTS_SHARED_DGP.md) — contracts/shared/DGP.
- [DOCS_RESEARCH.md](D:/codex/Causalis/audit/DOCS_RESEARCH.md) — документация, статьи и идеи.
- [PLAN.md](D:/codex/Causalis/audit/PLAN.md), [PROGRESS.md](D:/codex/Causalis/audit/PROGRESS.md) — план и журнал.

Scripts/JSON/logs сохраняют воспроизведения исходного аудита, pytest и benchmark. `docs_build_check/` — изолированная копия для проверки сборки API. На этапе исходного ревью код не менялся; после него начата разработка. Выполненные fixes и tests указаны в [BLOCK01_RCT.md](D:/codex/Causalis/audit/BLOCK01_RCT.md), [BLOCK02_CONTRACTS_SHARED_DGP.md](D:/codex/Causalis/audit/BLOCK02_CONTRACTS_SHARED_DGP.md), [BLOCK03_DML_GATE_UPLIFT.md](D:/codex/Causalis/audit/BLOCK03_DML_GATE_UPLIFT.md), [BLOCK04_DID.md](D:/codex/Causalis/audit/BLOCK04_DID.md) и NEXT_SESSION.md. B04 завершён: DiD controls/full MLE-OLS IF/aggregate shares/cluster inference; **1238 passed,1 known baseline SC-12 failed**,7sensitivity test modules исключены. На границе B04 CUPED baseline fix был запланирован для B05; теперь выполнен, см. последний статус ниже. Старые audit probes описывают первоначальные defects и не все подходят как post-fix regression scripts.

Предыдущий блок **B05 завершён**: [BLOCK05_CUPED_IV_SCM.md](D:/codex/Causalis/audit/BLOCK05_CUPED_IV_SCM.md). CUPED names/stable SVD/HC/batch, IV resolver/refit state и ASCM placebo config; SC08LOO deferred. **1376 passed,0failed,77warnings**,7sensitivity modules исключены; старый SC12 failure исправлен. Local fitbenchmark1.73–2.90x при совпадающихATE/SE, scope/limits в отчёте. B06 compatibility/CI/performance завершён; актуальный результат ниже.

Предыдущий **B06**: [BLOCK06_COMPATIBILITY_PERFORMANCE.md](D:/codex/Causalis/audit/BLOCK06_COMPATIBILITY_PERFORMANCE.md). Compatibility/CI/performance завершены: **1582 passed, 0 failed/skipped, 77 warnings, 400.95s**. Pydantic>=2, full release gate, duplicate screening, linear binary checks, bounded KDE и NumPy1.x IV fix. Все6Linuxjobs прошли1582cases; exact source09e00de и [CI evidence](D:/codex/Causalis/audit/block06_ci_result.json). Owned arrays audit-only; sensitivity/Sphinx/release не подтверждались.

Предыдущий **B07 завершён**: [BLOCK07_EDGE_CORRECTNESS.md](D:/codex/Causalis/audit/BLOCK07_EDGE_CORRECTNESS.md). Восстановлена earliest universal DiD pre-cell; binary/multi и shared IV helper отклоняют неконечные nuisance predictions до probability repair. DGP calibration/copula docstrings уточнены без runtime изменений. **147 новых cases; 1729 passed, 77 warnings, 404.84 s** локально; каждый из6CIjobs —1729passed без failures/errors/skips. Final sourcea2109a6,7sensitivitymodules deferred; [CI evidence](D:/codex/Causalis/audit/block07_ci_result.json). Portable handoff дополнен B07,81immutablelinks проверены. B08 выполнен; актуальный статус ниже.

Предыдущий **B08 завершён**: [BLOCK08_DGP_CONTRACTS.md](D:/codex/Causalis/audit/BLOCK08_DGP_CONTRACTS.md). DGP finite/shape contracts, stable target-weight normalization, singleton-safe coverage repair и explicit iid policy. **187newcases;1916passed0failures/errors/skips78warnings400.69s** local; each6Linuxjobs1916passed, [verified CI](D:/codex/Causalis/audit/block08_ci_result.json). Source9fb8041,7sensitivitymodulesdeferred,85handofflinksverified. Namespace follow-up выполнен в B09.

Предыдущий **B09 завершён**: [BLOCK09_NAMESPACE.md](BLOCK09_NAMESPACE.md). Полный guard фактических output names отклоняет outcome/treatment/expanded confounder/enabled oracle collisions без переименования. Source1e2b544, **123 новых cases**. Все шесть Linux jobs и artifacts — **2039 passed каждый**, [CI evidence](block09_ci_result.json). Локально Mac: **2038 passed,1 confirmed baseline DiD failure**,0errors/skips,80warnings117.46s; suite не считается чистым. [Failure note](B09_LOCAL_INTEGRATION_NOTE.md) доказывает то же поведение исходного кода и численную хрупкость практически нулевых preATT/SE. 64 reference configs×2 generations дали точное совпадение values/schema/RNG; handoff88immutablelinksverified. Sensitivity/Sphinx/release deferred. Следующие кандидаты: categorical copula coordinate bug и numerical-zero DiD policy; B10 начинается отдельным запросом. Windows links выше сохраняют историческое происхождение, новые B09 links переносимые.

Предыдущий **B10 завершён**: [BLOCK10_COPULA.md](BLOCK10_COPULA.md). Correct current-coordinate categorical copula и saturated upper endpoint; source95a8b75,33newcasespassed,126neighborspassed. Local2071passed1confirmedpre-existingDiDfailure78warnings90.27s; [result](block10_integration_result.json). Numeric-only exactreference36helper+96publicframecomparisons. Все6CIjobs/artifacts2072passed каждый: [CI evidence](block10_ci_result.json). Sensitivity/Sphinx/release неvalidated. На границеB10 остановиться; следующий кандидат — binary/IV namespace guards; numerical-zero DiD policy остаётся отдельной задачей.


Предыдущий **B11 завершён**: [BLOCK11_NAMESPACE.md](BLOCK11_NAMESPACE.md). Binary/IV core namespace guard отклоняет коллизии, учитывает expanded confounders, enabled family oracles и callback mutations перед assembly. Sourcecdc2c95; 163 новых cases passed, baseline103 failed / 60 passed; 200 exact frame/schema/RNG comparisons. Local2234 passed, 1 прежний DiD failure, 78 warnings, 84.59 s: [result](block11_integration_result.json). Все шесть CI jobs/artifacts —2235 passed каждый: [CI](block11_ci_result.json).94 immutable handoff links verified. На границе B11 остановиться; следующий B12 — wrapper augmentation/ordering/conversion namespace, затем numerical-zero DiD policy. Sensitivity/Sphinx/release deferred.


Предыдущий **B12 завершён**: [BLOCK12_WRAPPERS.md](BLOCK12_WRAPPERS.md). Guards защищают добавляемые pre/ancillary поля, ordering и automatic feature projection учитывают actual roles. Source0b30db3; 162 новых cases passed, baseline136 failed /26passed; 460 exact frame/metadata/RNG comparisons. Local2396 passed и один прежний DiD failure,78warnings,85.67s: [result](block12_integration_result.json). Все шесть CI jobs/artifacts —2397 passed каждый: [CI evidence](block12_ci_result.json). 101 immutable handoff links verified; sensitivity/Sphinx/release deferred. Историческая точка B12: поздний classic-RCT scenario rename оставался следующим пунктом.

Предыдущий **B13 завершён**: [BLOCK13_SCENARIO_NAMESPACE.md](BLOCK13_SCENARIO_NAMESPACE.md). Classic scenario защищает outcome/ID roles и сохраняет pre-признаки с именами отключённых oracles. Source4428be0; **91 новых cases passed**, exact baseline28failed/63passed; 116 exact frame/dtype/metadata/RNG comparisons. Local **2487 passed, один прежний DiD failure**, 78 warnings, 109.60 s: [result](block13_integration_result.json). Все шесть CI jobs/artifacts — **2488 passed каждый**: [CI evidence](block13_ci_result.json). 103 immutable handoff links verified. Следующий B14 — mathematical numerical-zero DiD diagnostic/fixture policy. Sensitivity/Sphinx/release deferred; работа остановлена на границе B13.


Предыдущий **B14 завершён**: [BLOCK14_DID_NUMERICAL_ZERO.md](BLOCK14_DID_NUMERICAL_ZERO.md). Exact-constant OLS сохраняет математический ноль; undefined/invalid fitted-pre statistics требуют caution, tiny real effects не обнуляются. API fixture исправлен по дизайну с сохранением GREEN assertion/thresholds. Source4bdcff7; **51новых+5existingfocused56passed**, baseline28failed/28passed; independent32fullreferencepairs plusfinaldelta. **Local2539passed**,0failures/errors/skips,78warnings80.36s: [result](block14_integration_result.json). Все шесть CI jobs и actualartifacts **2539passed каждый**: [CI](block14_ci_result.json). 107immutablehandofflinksverified; no fullsensitivity/Sphinx/release/coverage/benchmarkclaim. Следующий B15 — Gaussian oracle numerical accuracy/compatibleadditiveAPI. Работа остановлена на границе B14; finalauditcheckpoint gitlog-1, ordinarypersonalpush/remoteequality+cleantree проверяются на завершении.


Текущий **B15 завершён**: [BLOCK15_GAUSSIAN_ORACLE.md](BLOCK15_GAUSSIAN_ORACLE.md). Добавлен opt-in Gaussian marginal propensity oracle с явным target, adaptive numerical policy и сохранением старых outputs/RNG. Source9a57e91; **79 новых tests passed**, baseline74planned API-absence failures/5compatibility passes; independent112default+40additive exact pairs и31contract/34review Gaussian references. **Local2618passed**,0failures/errors/skips,78warnings179.77s: [result](block15_integration_result.json). Все шесть Linux CI jobs и actual artifacts — **2618passed каждый**: [CI](block15_ci_result.json). Handoff110immutablelinksverified. Следующий B16 — выявленные binary/IV marginal outcome numerical defects; shared-latent compound targets требуют отдельного решения. Семь sensitivity modules deferred; standalone Sphinx/release/performance не validated. Работа остановлена на границе B15; final audit checkpoint — gitlog-1, обычный personal push/remote equality+clean tree проверяются на завершении.


Текущий **B16 завершён локально**: [BLOCK16_BINARY_IV_OUTCOME_ACCURACY.md](BLOCK16_BINARY_IV_OUTCOME_ACCURACY.md).
Source1c91b0d исправляет Gaussian outcome means binary/IV и nonlinear nuisance
callables;121focusedcasespassed,96exactcompatibilitypairs,140independentreferences.
[Local correctness](block16_integration_result.json):2739passed,0failures/errors/skips,
78warnings,7sensitivitymodulesdeferred. [Validation](block16_validation_result.json)
проверяет committedbytes/caseIDs/exclusions. **Push/CI не подтверждены:** session
DNSfailure github.com; после network restoration обычный personalpush и шестьCIjobs.
Следующий B17 — propensity и compoundshared-Uaccuracy; [NEXT_SESSION](NEXT_SESSION.md)
содержит точный scope, migration для statefulcallbacks и продолжение.

## B17 — Gaussian propensity and joint shared-U means (2026-10-07)

Source `e2fced5f476a8567bee2cc0bbda062ad62124eae`, baseline `aaeadd8`.
[Report](BLOCK17_GAUSSIAN_PROPENSITY_JOINT_MEANS.md): binary m/IV r accuracy;
bounded joint IV/Tweedie means, continuous IV exact identity, derived IV oracle
migration and deterministic callback policy. Public baseline45failed/12passed;
90focusedpassed;180exact observed-frame/RNGpairs;52jointscalarrefs.
Local committed correctness **2829passed**,0failures/errors/skips,78warnings,
seven sensitivity exclusions unchanged. Personal push completed; CI run37647196147.
Next B18 learner shape/real/complex/IVstorage. Stop at B17 before context cleanup.

B17 final verification: CI37647196147 completed/success; six downloaded
artifact sets have2829passed each on exacte2fced5. Full caseIDs/90newtests,
actualargv/source/exclusions verified. Root verifier:5changedsource/testpaths,
21unchangedmethods/8hashes and all baseline/final/local/CI manifests,issues[].
B17 completed; B18 is learner shape/real/complex/IVstorage, after context cleanup.


## B18 — learner output contracts and IV storage (2026-10-07)

Source `df944e0ee814dbe1a631b41ba1b59def9f61ed8b`, baseline `b7cbec9`.
[Report](BLOCK18_LEARNER_OUTPUT_CONTRACTS.md): explicit real/finite row-aligned
learner outputs; IV fold/raw assembly/fit boundary guards. Supported vectors and
single columns, binary class mapping and finite probability repair retained.
Malformed geometry, complex/object-complex and mismatched class columns rejected.
Final356baseline267failed/89passed;460focusedpassed;20exactfit/36exactinference
pairs and125unchangedfunctionASTs. Committed correctness3185passed,0failures/errors/
skips,82warnings,132.54s; seven sensitivity exclusions unchanged.
CI37653023359 completed/success on exactsource: six artifacts3185passed each,
completecaseIDs/460focus/source/actualargv/exclusions verified.
[CI](block18_ci_result.json), [validation](block18_validation_result.json),issues[].
Handoff118immutablelinksverified; source/tests frozen, only final audit updates.
Next B19 extreme finite score/IF and normalized custom-ATE policy. Stop at B18
before context cleanup; sensitivity remains deferred.


## B19 — extreme finite score/IF and normalized custom ATE (2026-10-07)

Source `1993cf1040e21630844688e415ef2cf15598ffc3`, baseline `52cd6e2`.
[Report](BLOCK19_EXTREME_SCORE_ARITHMETIC.md): explicit RuntimeError at numerical
score/IPW, moment/IF/SE/absolute and relative interval boundaries; normalized
custom ATE weights must be finite (ValueError). Existing equations, overlap
policy, weight-mean floor and approximate normalization inference preserved.
Final67baseline54failed/13passed;527focusedpassed;40exactfit/72exactinference
pairs and129unchangedfunctionASTs. Committed correctness3252passed, zero
failures/errors/skips,91warnings,108.72s; seven sensitivity exclusions unchanged.
Personal source push completed; CI37663336817 completed/success on exactsource.
Six artifacts3252passed each, completecaseIDs/527focus/source/actualargv and
seven exclusions verified. [CI](block19_ci_result.json),
[validation](block19_validation_result.json),issues[]. Source/tests frozen;
only audit updates after1993cf1. Handoff123immutablelinksverified.
Next B20 duplicate numeric/object and snapshot/refit contracts; standalone Sphinx
separate. Stop at B19; sensitivity remains deferred.


## B20 — duplicate values and fitted snapshots (2026-10-07)

Source `28acf6b4fea588ee682251a35a5f23a8757f4415`, baseline `98d5478`.
[Report](BLOCK20_DATA_SNAPSHOT_CONTRACTS.md): exact numeric/object duplicate
policy, independent returned diagnostic fields, fit-time role labels and
complete binary/multi fit publication. Failed binary/multi refits retain the
previous fit; successful refits require fresh primary inference. IV retains
failed-refit→unfitted. Live private model links/shared learner effects and generic
sensitivity scalar-state behavior remain outside this guarantee.
Final107baseline86failed/21passed, focus2106passed/15existingwarnings/31.36s;
20exactfit/36exactinference pairs and132unchangedexecutablefunctionASTs.
Committed correctness3359passed,zero failures/errors/skips,91warnings/115.72s.
Seven sensitivity exclusions unchanged; source/tests frozen; personal push done.
CI37665898544 completed/success on exactsource: all6artifacts3359passed each.
FullcaseIDs/2106focus/source/actualnormalizedargv/7exclusions verified.
[CI](block20_ci_result.json), [validation](block20_validation_result.json),issues[].
Handoff127immutablelinksverified. Only audit updates aftersource; finalcheckpoint
via gitlog-1. Owned worktrees/pytesttemporarydata removed; ordinary personal
push/liveequality and clean state checked at completion.
Next B21 dedicated standalone Sphinx gate; features after correctness.
Stop at B20 before context cleanup; sensitivity remains deferred.
