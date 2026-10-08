# План исправлений и поэтапной разработки

Обновлён: 2026-10-07. Проект: root через `git rev-parse --show-toplevel`; текущий Mac checkout `/Users/m.lenivkin/Documents/tclaude_folder/git-lab-projects/Causalis`. Рабочая ветка: **`codex/correctness-roadmap`**, создана от `main` на `ffe2c356c115f335b74b2f10117e19fe15585d46`. Исходный аудит — `audit/REPORT.md`; он остаётся историческим snapshot, а не переписывается после каждого исправления.

## Решение о scope

Разработчики upstream уже исправляют sensitivity analysis. **Все sensitivity formulas, benchmarks, bounds, RV/RVa, nuisance derivatives и связанные sensitivity tests/docstrings отложены.** Мы не создаём конкурирующую реализацию и не подгоняем новый код под старые sensitivity outputs.

Отложены целиком DML-07, DML-08, DML-10, DML-11, sensitivity-specific документационные замечания и generic refit/sensitivity scalar state часть DML-03. Возврат: после получения upstream commit, проверка diff/API/score contracts, новый короткий аудит, перенос либо закрытие прежних findings. Сообщение разработчиков о будущей правке не означает, что текущие defects уже исправлены.

Независимая часть DML-03 — **CATE learner cache после refit** — остаётся в плане. Изменения общих scores/IF DML-01/02 допускаются, но sensitivity modules/tests в этих commits не редактируются. Если upstream change затрагивает те же contracts, фиксируем зависимость и переносим конкретный пункт до синхронизации. Sensitivity-targeted Monte Carlo и новые sensitivity функции сейчас не выполняются.

## Сначала correctness, затем скорость и новые методы

| Блок | Приоритет / scope | Findings исходного аудита | Критерий готовности | Размер |
|---|---|---|---|---|
| **B00. Основа проекта** | Ветка, сохранение аудита, план, handoff документации, Git access и файл продолжения | Инфраструктура работы | Локальный commit создан; remote auth ограничения записаны; всё для следующего контекста в файлах | S |
| **B01. RCT inference** | Правильный Newcombe hybrid CI; строгие `ci_method`/`se_for_test` | **SC-05 P1**, SC-10 P2 | Statsmodels reference на rare/boundary/unequal-n, symmetry, invalid options; RCT tests; отдельный commit | S |
| **B02. Contracts / shared / DGP** | Finite/real checks, separation SMD, positional outliers, NaN split weights, UUID uniqueness, nonlinear multi oracle | ROOT-01/02/03/04/05/06/07; DML-05 | Repro → focused tests; строгий row/schema/ID contract; oracle analytic identity; не менять sensitivity implementation | M |
| **B03. DML / GATE / Uplift** | Multi ATTE ratio IF, binary relative ATT IF, drop+weights, OOS diagnostic, stable GATE variance, независимый CATE cache | **DML-01 P1**, DML-02/04/06/09, DML-03 только CATE | Oracle IF/SE, same-split reference, invariance, fresh-fit equivalence; исправить ошибочные existing assertions | M–L |
| **B04. DiD inference** | Pre-controls, normalized IPW IF, nuisance-estimation IF, population cohort-share IF, one-cluster guard | **SC-01/02/03/04/11 P1** | Derivations и official-source reference; unit uniqueness; common-trend invariance; analytic/bootstrap; затем targeted coverage simulation | L |
| **B05. CUPED / IV / SCM** | Collision-safe design, stable leverage/covariance, публичный batched QR/SVD, IV diagnostic resolver, ASCM config inheritance | SC-06/07/08/09/12 | Scale/name invariance, HC/relative covariance, batch-vs-single, original-config refutations; existing suite | M–L |
| **B06. Compatibility / CI / performance** | Pydantic minimum, release pytest gate, tested versions; duplicate screening, linear binary checks, bounded-memory KDE, owned arrays | ROOT-08/09, performance top10 | Чистая install matrix; no false release pass; identical arrays/scores/IF; documented time/memory benchmark | M–L |
| **B07. Edge correctness / factual docs** | Earliest universal DiD pre-cell; non-finite binary/multi/IV learner outputs; DGP calibration/copula wording | Follow-ups B04/B02 и independent boundary review, P2 | Independent date/ATT/IF references; finite fits unchanged; 147 new cases; 1729 local + 1729 в каждом из 6 CI jobs, 7 sensitivity modules deferred | M |

B02–B06 — большие тематические блоки, внутри которых можно делать несколько небольших законченных commits. Размер S/M/L — сравнительная сложность, не календарное обещание. P1 задачи B03/B04 имеют более высокий риск, но B01 первым даёт короткий независимый correctness commit; внутри B02 сначала устраняем silent invalid results и wrong oracle.

## Порядок commits внутри больших блоков

- B02: finite/complex validation → balance separation → outlier/split/IDs → multi DGP oracle. Изменение contract не должно автоматически impute/replace invalid values. Проверить explicit migration, если ранее принимавшиеся данные теперь отвергаются.
- B03: multi ATT IF + diagnostics → relative ATT baseline IF → drop mask/weights → CATE cache → stable GATE variance → заменить бессодержательный OOS aggregate test. Общие influence payloads сверять с потенциальными upstream sensitivity changes.
- B04: eligibility/unit alignment → normalized cell IF → nuisance-estimation strategy → aggregation weight IF → cluster validation. Последний простой guard можно сделать отдельным ранним commit. Full MLE/OLS IF и improved IPT/WLS — выбор реализации после review derivation, а не смешение обеих процедур.
- B05: CUPED names → scale-stable leverage → batch least-squares/covariance → IV resolver → ASCM config. Не снимать cache identity assertion без восстановления обещанного ускорения.
- B06: implementation и локальная integration завершены: **1582 passed, 0 failed/skipped, 77 warnings, 400.95s**. 206 новых cases, 7 sensitivity modules явно исключены. Pydantic>=2, full release pytest gate, CI matrix, duplicate screening, linear binary detection, bounded Gaussian KDE и NumPy1.x IV fix. Все шесть clean Linux jobs и artifacts прошли; каждый — 1582 cases без failures/errors/skips. Финальный source09e00de; evidence в BLOCK06_COMPATIBILITY_PERFORMANCE.md. Owned arrays остаются audit-only; полный sensitivity/release/docs build не подтверждался.

## Документация: отдельный рабочий поток

`audit/DOCUMENTATION_HANDOFF.md` — переносимый файл для автора сайта, с GitHub snapshot links, приоритетами и готовыми английскими формулировками. Он не содержит локальных D-drive ссылок и sensitivity-specific tasks.

Текущие inaccuracies можно исправлять сразу; описание изменяемого поведения Newcombe/CI/diagnostics должно выпускаться вместе с соответствующим кодом. Generated API пересобирать из нужного release commit, а не редактировать HTML вручную. Изначальные отчёты описывают старый commit и должны сохранять этот marker.

## Правила проверки и границы блока

1. Перед изменением прочитать `AGENTS.md`, этот файл и `audit/NEXT_SESSION.md`; проверить branch/status и не затрагивать чужие изменения.
2. Выбрать **один блок** и небольшой законченный commit. Источник finding → независимое reproduction/property/reference → patch → focused tests.
3. Python — только repo-local `.venv` entrypoint: `.venv/bin/python` на текущем macOS checkout, `.venv\Scripts\python.exe` на Windows. Исторические machine backing paths не переносить. Environment/versions сохраняются в manifest конкретного run.
4. При Windows sandbox failures process/tmp использовать разрешённый запуск или writable `--basetemp`, не считать их bug библиотеки.
5. После focused проверки запускать необходимые соседние tests. Suite вне отложенной sensitivity области — на интеграционных границах B03/B04/B05/B06; исключённые modules перечислять в evidence manifest. При текущем baseline учитывать известный SC-12, пока он не исправлен; не выдавать такой run за fully green/full sensitivity validation.
6. Не повторять большой benchmark/весь suite после правки только prose. Для score changes нужны independent IF и coverage evidence; passing mirrored-formula tests недостаточно.
7. Commit включает завершённую code/test/docstrings правку и короткий block log. Отчёт показывает, что закрыто, что осталось, как проверено и известные ограничения.
8. Обновить `NEXT_SESSION.md`, отметить block/commit/test commands/следующее действие. **Остановиться на границе блока**, чтобы пользователь мог очистить контекст. Следующий блок начинается отдельным запросом пользователя.

## Git и синхронизация upstream

Локальный Git и author identity работают. Авторизация **MaximLenivkin** подтверждена после browser login. Личный fork `MaximLenivkin/Causalis` создан; branch `codex/correctness-roadmap` успешно pushed и отслеживает origin. Upstream main всё ещё исходный audit SHA. Полная текущая информация — `audit/GIT_ACCESS.md`.

Фактически `origin` — личный fork, `upstream` — causalis-causalcraft/Causalis. Каждый законченный commit можно пушить в личную ветку. Никогда не push в upstream/main и не force-push историю для обычной синхронизации. Upstream updates сначала fetch/diff, sensitivity review отдельно; merge/rebase выбирается по actual divergence, без потери собственных commits.

## Последующие улучшения, после correctness

В порядке отдачи для текущего ядра: repeated cross-fitting → group/cluster-aware DML → external OOF predictions/manifest → DR/R CATE → held-out nuisance/CATE validation → inference families → weak-IV LATE → HonestDiD → policy costs/capacity. Это самостоятельные feature blocks с explicit assumptions/target и validation, не добавления к одному bugfix commit. Sensitivity extensions остаются вне текущего scope.

## Текущий статус

- B00: завершён; локальный checkpoint **2c26cee** сохранил аудит/план/документы.
- B01: завершён; commit **bd8a2be**, **67passing cases** в focused+neighbor checks; детали в `audit/BLOCK01_RCT.md`.
- B02: завершён; commits **817c24c / add2f36 / a5a6e3a / c27e744**. ROOT-01–07, включая grouped DML-05, исправлены. Общая проверка: **606 passed**, 5 existing warnings; подробности в `audit/BLOCK02_CONTRACTS_SHARED_DGP.md`.
- B03: завершён; commits **c925907 / e6a9275 / 6084b34 / 113c693**. DML-01/02/04/06/09 и independent CATE part DML-03. Integration: **1143 passed, 1 known baseline SC-12 failed**, 76 warnings, 299.18s; 7 sensitivity modules исключены. Итог — `BLOCK03_DML_GATE_UPLIFT.md`, raw logs и selection/result JSON. New failures0; это не полностью зелёный suite.
- B04: завершён; commits **87228e2 / 57dbba1**. SC-01/02/03/04/11: aligned controls, full normalized MLE/OLS cell IF, estimated complete-pair aggregate shares, cluster guard/covariance. Integration: **1238 passed,1 known SC-12 failed**,76warnings,340.04s;7sensitivity modules исключены. Итог — `BLOCK04_DID.md`, independent derivations и raw evidence. Добавлены95testcases. Не полностью зелёный suite.
- B05: завершён. Integration на1b24777: **1376 passed,0failed,77warnings,438.20s**,7sensitivity modules исключены. SC-06/07/09/12 исправлены, SC-08 только placebo (LOO deferred). CUPED127/IV73/SCM67 focusedpass; new137cases. Code commits bb31a4b/5e03795/3c000b1/1b24777; итог — BLOCK05_CUPED_IV_SCM.md. Исторический SC-12 assertion сохранён и проходит. Local fitbenchmark1.73–2.90× при совпадающихATE/SE; неuniversalclaim.
- B06: implementation и локальная integration завершены: **1582 passed, 0 failed/skipped, 77 warnings, 400.95s**. 206 новых cases, 7 sensitivity modules явно исключены. Pydantic>=2, full release pytest gate, CI matrix, duplicate screening, linear binary detection, bounded Gaussian KDE и NumPy1.x IV fix. Все шесть clean Linux jobs и artifacts прошли; каждый — 1582 cases без failures/errors/skips. Финальный source09e00de; evidence в BLOCK06_COMPATIBILITY_PERFORMANCE.md. Owned arrays остаются audit-only; полный sensitivity/release/docs build не подтверждался.
- Sensitivity: отложено по прямой инструкции пользователя; дата возобновления не назначена.
- B07 завершён: commits 43f0b3e/d3b6709/a2109a6; final source a2109a6. Earliest universal DiD pre-cell и raw non-finite learner guards исправлены; DGP runtime unchanged, factual docs уточнены. 147 новых cases; **1729 passed, 0 failures/errors/skips, 77 warnings, 404.84 s** локально; все 6 Linux CI jobs и artifacts — 1729 passed каждый. CI37385736343; report — BLOCK07_EDGE_CORRECTNESS.md. 7 sensitivity modules deferred.
- B08 завершён: sourcecheckpoint9fb8041 — DGP numeric/callback contracts, targetsumoverflow и singleton-safe assignment repair;187newcases и optiniid. Local1916passed0failures/errors/skips78warnings400.69s;actualCI37420288433all6jobs/artifacts1916passed каждый. Report BLOCK08_DGP_CONTRACTS.md;7sensitivitymodulesdeferred.
- B09 завершён: source1e2b544 — полный actualgeneratednamespaceguard с clearcollisionerrors безrename,123newcases. Все6LinuxCIjobs/artifacts2039passedкаждый,run37530152376; localMac2038passed1confirmedbaselineDiDfailure80warnings117.46s,неclean. Reference64configs×2generations exactvalues/schema/RNG. Report BLOCK09_NAMESPACE.md;7sensitivitymodulesdeferred.
- B10 завершён, source95a8b75: categoricalcopula usesownrawcoordinate, saturatedupperguardlastpositivelevel;33newpassed,30baselinefail3pass,126neighborspassed. Local2071passed1confirmedbaselineDiDfailure78warnings90.27s. CI37532909989 completed/success, все6jobs/artifacts2072passed каждый; report BLOCK10_COPULA.md. Numeric-only36helper/96publicframe exactrefs; malformed-speccontractsне расширены.
- B11 завершён: sourcecdc2c95 — actual binary/IV core namespace guard,163 новых cases passed; local2234 passed,1 прежний DiD failure,78 warnings,84.59 s. Все шесть CI jobs/artifacts —2235 passed, run37589241406.200 exact valid frame/schema/RNG comparisons; callbacks не обходят final assembly guard. Report BLOCK11_NAMESPACE.md.
- B12 завершён: source0b30db3, wrapper actual-enabled augmentation guards, ordering и numeric feature projection; 162 новых cases passed, baseline136 failed /26passed,460 exact frame/metadata/RNG references. Local2396 passed,1 known DiD failure,78warnings,85.67s,total2397; CI37598926037 completed/success, все6jobs/artifacts2397passed каждый. Report BLOCK12_WRAPPERS.md.
- B13 завершён: source4428be0, один classic-RCT scenario module и новый91-case test module. Outcome/ID role collisions отклоняются, disabled-oracle pre features сохраняются. Baseline28failed/63passed, focused91passed; independent116exact frame/metadata/RNG references,13rejects,40allowed probes. Local2487passed/1knownDiDfailure,78warnings,109.60s,total2488. CI37607784481 completed/success, все шесть jobs/artifacts2488passed каждый. Report BLOCK13_SCENARIO_NAMESPACE.md; handoff103immutablelinksverified.
- B14 завершён: source4bdcff7 — unique exact-constant/full-rank/unit-intercept OLS, undefined zero-SE studentization и all-cell fitted-pre caution, exactzero-only p1 convention, zero-bootstrap undefined bands without warnings. 51new+5existingfocused56passed, baseline28failed/28passed; original GREEN assertions/thresholds preserved through genuinely nondegenerate fixture. Independent32fullreferencepairs and finalguarddelta verified. **Local2539passed**,0failures/errors/skips,78warnings80.36s; CI37611862809 allsixartifacts2539passed each. Report BLOCK14_DID_NUMERICAL_ZERO.md; handoff107immutablelinksverified. Sensitivity/Sphinx/release/coverage/benchmark notvalidated.
- B15 завершён: source9a57e91 — opt-in Gaussian marginal propensity q=E[softmax(a+bZ)] и append-only bool API `include_marginal_propensity=False`; existing m/m_obs/default outputs/RNG сохранены. Adaptive integration с transition points/estimated error1e-10/budget4096, explicit ValueError при неподдерживаемой geometry/nonconvergence. 79newcasespassed, baseline74planned API-absence failures/5compatibility passes; independent31qrefs+8publicpairs и review112default+40additivepairs/34qrefs. Local2618passed,0failures/errors/skips,78warnings179.77s; CI37628255646 sixartifacts2618passed каждый. Report BLOCK15_GAUSSIAN_ORACLE.md; handoff110immutablelinksverified. Supplied-U law/ensure_all/selected-U ATT/calibration limits описаны; source/testsfrozen.
- Следующий самостоятельный **B16 новым запросом — binary/IV marginal outcome numerical accuracy**. B15 independent references подтвердили existing fixed-GH21/GH31 defects (logistic absolute errors .09352/.07035; clipped-exp relative errors40.66%binary/13.81%IV на зафиксированных configs). Начальный scope binaryg0/g1 и IV `_potential_outcome_means`; Gaussian target, independent adaptive reference и explicit accuracy/failure policy, compatibility observed draws/RNG. Compound IV/Tweedie shared-latent means требуют отдельного scope/target решения, без замены joint integral произведением marginals. Затем learner shape/real/complex/IVstorage, extreme scores/IF, normalizedcustomATE, duplicate/snapshot/refit/Sphinx; features после correctness. Sensitivity/SC08LOO/selected-U ATT deferred.

Дополнение B04: сохраняются traditional MLE/OLS и прежний complete-pair estimand. Correct IF не убирает fixed ridge/clipping bias и не гарантирует finite-sample/few-cluster coverage. Earliest universal pre placebo (analysis-index0) пока пропущен прежним enumeration: отдельный support follow-up. Численная устойчивость IF map проверена, optimizer scale invariance не заявляется.

Статус этого исторического B04 follow-up: earliest universal pre-cell закрыта в B07. Нормализованная zero row не добавляется; новые cell IDs/event-time ranges и совместные pre-tests/bands требуют refit. Post point estimates, IF и обычные analytic intervals сохранены.

## Дополнение после B02

Multi-treatment `m_<arm>` при latent treatment noise пока означает softmax при U=0. Для true observed-X propensity требуется интегрирование softmax по Gaussian U; новые class docstrings явно различают эти величины. Отдельный follow-up после основного correctness backlog: выбрать совместимый API для marginal propensity oracle и определить ATT/oracle semantics при supplied U. Это новое соседнее замечание, не повторно открытый ROOT-01 outcome fix. Extreme DGP coefficient guards, estimator output finite policy и SMD near-zero scale invariance также требуют отдельных scope/validation решений.

## Остаток после B07 и кандидат следующего блока

B07 закрыл finite-output guard для real numeric learner outputs и earliest universal pre-cell. Он не является полной проверкой всех output types или floating-point arithmetic. Приоритет дальнейшей работы:

1. **DGP reference contracts:** finite/extreme config и callback outputs; small/rare-arm retries могут менять assignment law. Сначала независимые reproductions и explicit policy, затем marginal-oracle API.
2. **Additive Gaussian-reference propensity:** opt-in `m_marginal_<arm>`, сохранение existing m/m_obs/RNG; accuracy/convergence policy, bounded-memory integration и independent adaptive reference. Concrete proposal и validation plan — `B07_DGP_REVIEW.md`. Selection-weighted latent ATT — отдельная target/API задача; не заменять его treated average marginal CATE.
3. **Learner shape/real contract:** malformed row/column outputs, complex predictions и IV assembled-storage boundary. Existing successful finite behavior и single-class mapping требуют явного совместимого решения; B07 этих contracts не расширял.
4. **Extreme finite score/IF arithmetic** и normalized custom-ATE near-boundary policy: сначала реальные reproductions и target/normalization analysis, не blanket `nan_to_num` или clipping outputs.
5. **Numeric/object duplicate policy, snapshot arrays и dedicated Sphinx build:** отдельные compatibility/design gates; owned views нельзя кэшировать без ownership/refit invalidation contract.

B08 реализовал ограниченные centralgenerator config/output/rare-arm contracts; additive oracle остаётся отдельно. Найденные B08 namespace overwrites закрыты вB09 полным guardactualexpandednames/enabledoracle. B09 independentreview дополнительно подтвердил sharedcategoricalcopula coordinate bug; localMacverification показала unchangedbaseline DiD near-zeroATT/SE diagnosticfailure. Этидваcorrectnessfollow-up требуютсобственныхindependentreferences/политик, затем численнуюaccuracypolicy/additiveoracle. Repeated cross-fitting и прочие features сохраняют прежний порядок после correctness follow-up. Не включать sensitivity до отдельного upstream sync/review.

B10 закрыл shared categorical copula coordinate bug и связанный upper endpoint с trailing zero probabilities. Pre-existing DiD near-zero diagnostic failure остаётся отдельным follow-up. Numeric-only exact-reference evidence не означает новую categorical malformed-spec validation или identical downstream categorical datasets.

B10 reviewer подтвердил отдельный binary/IV namespace defect: при normal confounder `d`, explicit copula, n30,seed731,include_oracle=False обе raw frames содержат 30 nonbinary treatment values. Assignment source unchanged; B09 guard покрывал только multi-treatment. Следующий schema fix должен проверять полный фактический namespace без переименования.


B11 уточнил отдельный wrapper-layer backlog: `generate_rct(pre_name='y')` может перезаписать outcome и создаёт duplicate projection даже с add_pre=False; IV instrument `user_id` или disabled-oracle `m` повторяется при ordering; ancillary names (например age) перезаписывают confounder либо IV instrument. Automatic conversion исключает oracle-like confounder names независимо от enabled flag. Evidence: `block11_contract_result.json`, `block11_review_probe.json`. B12 реализовал actual enabled namespace и actual feature-selection policy в шести DGP paths; low-level не резервирует несуществующие wrapper роли. Отдельный classic_rct_26 late y→conversion rename residual, доказанный в block12_review_probe.json, **исправлен B13** вместе со scenario ID conflict и disabled-oracle pre-feature projection.


## B16 — текущий локальный checkpoint

[B16 report](BLOCK16_BINARY_IV_OUTCOME_ACCURACY.md): source1c91b0d, accurate
Gaussian marginal outcome means для binary/IV и outcome nuisance-callables.
121focusedcases;96exact compatibility/RNGpairs,140scalarreferences;
local2739correctnesscasespassed,7sensitivitymodulesdeferred. Stateful IV callbacks
изменяют call counts, explicit contract/migration сохранён. Push/CI пока
неподтверждены из-за DNS/network sandbox; после ordinary personal push проверить
шесть CIjobs/artifacts для exactsource.

Следующий отдельный B17: Gaussian propensity m/r и compound shared-U IV/Tweedie
means по reproductions block16_probe_result.json. Сначала joint target и adaptive
reference; product of marginals не заменяет shared-U expectation. Затем прежний
learner shape/real/IV storage и extremeIF/normalizedATE backlog. Остановиться
послеB16; B17 новым запросом после очистки контекста.

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

## B21 завершён — 8 October 2026

Source `1780d8c715a15182137d51313e502280d6982dd9`, baseline `2db4802`.
[Report](BLOCK21_SPHINX_GATE.md). Standalone Sphinx gate with warnings as errors,
--check without publication, explicit prior MyST rendering/root-only __all__;
NumPy/RST migration remains documentation debt. CI and release require the gate;
release full sensitivity scope unchanged. No library bytes changed.
Eight regressions: baseline7failed/1passed; focused docs11passed.
Same144HTMLpages/1296inventoryrecords (matched generated _version.py).
Committed local3367passed, no failures/errors/skips,91warnings/115.39s;
SKIP_DOCS_BUILD=false. Standalone localexit0/15.90s.
CI37740334131 on exactsource: all six jobs3367passed each and standaloneexit0.
Full local/focus/CIcase sets, scope/argv, docs source/environment/log hashes checked.
SnapshotUTC2026-10-08T07:00:19.131486+00:00; actual Python3.10.21 both stacks,
3.11.16,3.12.15,3.13.15,3.14.8. Seven sensitivity exclusions preserved.
[CI manifest](block21_ci_result.json), [root validation](block21_validation_result.json),
issues[]. Handoff132immutablelinks, issues[]. Source frozen after1780d8c;
only audit changes follow. Owned build copies and recorded integration basetemp
removed; aggregate JUnit retained. Final checkpoint via gitlog-1; ordinary personal
push/live equality and clean state checked at completion. No notebook/website
execution/publishing, release, upstream merge or sub-agents.
Next B22 repeated cross-fitting: explicit API/splits/RNG/aggregation/inference
contract first. GroupCF, externalOOF, DR/R-CATE afterward. Sensitivity, SC08LOO,
selected-U ATT deferred. Stop after B21 for user context cleanup/new request.


## B22 — завершён: repeated binary IRM (8 October2026)

Source `ede6deda2eb82c518ed3d7f5b48780d39cdfe5f0`, baseline357e16e.
Binary IRM repeated ATE/ATTE through n_rep; median-variance SE, common sample,
local recorded split seeds, separate relative aggregation and per-repeat
results/diagnostics. n_rep=1 exactcompatibility16fits/24estimates/8rejections.
Strict integer repetition counts; M>1 drop/GATE/GATET/CATE/sensitivity
aggregation unavailable; multi/IV repetition remains a separate follow-up.
Sensitivity algorithms unchanged; two new repeated-fit entry guards only.
67newcases; focused221passed; committed correctness3434passed/no failures,
errors or skips,116warnings,115.66s; seven exclusions unchanged. Strict
Sphinx exit0 on committed source. Favorable synthetic MC200x600,R3 coverage
.965 bothscores, no general guarantee. Root verifies six non-audit paths,
43unchanged IRMmethodASTs, source/completecase/evidence hashes, issues[].
Handoff136immutable implementation URLs verified locally; implementation pushed.

User explicitly allowed push: «Разрешаю пуш в нашу ветку»; ordinarypersonal
branch pushes remain authorized, no repeat confirmation. Implementationede6ded
and initial evidence d99ea8f pushed. CI37751321348 completed/success on exact
head `d99ea8ffea853e48f750ca642a3918769cc38004` (audit-only changes fromimplementation):
all six jobs3434passed each plus strictSphinxexit0. Executablecode/CIconfig
unchanged; no claim that CIran directly onede6ded. FullcaseIDs/local221new67,
normalizedargv/exclusions/source/dependencies and5artifacthashes/job checked.
SnapshotUTC2026-10-08T08:44:54.121787+00:00; actualPython3.10.22bothstacks,
3.11.16,3.12.15,3.13.15,3.14.8. [CI manifest](block22_ci_result.json),
[root validation](block22_validation_result.json), [report](BLOCK22_REPEATED_CROSSFIT.md).
Source frozen; latercommits audit-only. Finalcheckpoint gitlog-1; ordinaryfinal
push/livelocalremoteequality/cleantree checked atcompletion. Ownedcopies and
recorded integration pytest-temp removed. No release/PR/upstream/sub-agents.

Next B23: group-aware binaryIRM split and inference contracts before changes.
Multi/IV repetition, externalOOF, DR/R-CATE follow-ups remain separate.
Sensitivity/SC08LOO/selected-UATT/NumPyRST debt deferred. Stop after B22 for
contextcleanup/newuserrequest. Do not repeatlogin/fork/setup/oldbroadtests.


## B23 — завершён: one-way cluster binary IRM (8 October 2026)

Source `b1adeb291870c965825c60712144d23ea4c31ce9`, baseline `1409e95`.
IRM(..., cluster_groups=labels) snapshots positional membership (Series index
must match exactly), holds whole clusters out with recorded shuffled group
KFold seeds, and uses row-weighted scalar CR1 for absolute/baseline/relative
ATE/ATTE inference. Repetitions aggregate cluster SEs using B22's policy.
No row fallback/retry; each training complement needs both treatment arms.
The inherited input gate additionally requires at least n_folds rows per arm;
two supplementary support probes document this conservative limitation.
Drop/fixed folds and cluster GATE/GATET/CATE/sensitivity reject; exported
GATE/CATE adapters also enforce the guard. Few-cluster/multiway/multi/IV
contracts remain separate. Original approximate weight/Hajek flags retained.

87 new cases; focused364passed/38warnings/18.87s. Exact iid compatibility:
32 fit configurations, 48 estimates, 16 weighted-ATTE rejections.
Committed correctness3521passed/no failures/errors/skips,125warnings/211.90s;
seven sensitivity exclusions unchanged. Strict standalone Sphinx exit0/23.928s.
45 unchanged IRM method ASTs; two sensitivity bodies unchanged except new guards;
GATE/uplift adapters only gain guards. MC400 samples,80 independent clusters:
ATE R1/R3 coverage .945/.945, ATTE .9525/.9425; same-fit iid SE comparator
.4825/.475 and .495/.505. MCSE about .011, one favorable DGP only.

[CI37763490246](https://github.com/MaximLenivkin/Causalis/actions/runs/37763490246)
completed/success on exact sourceb1adeb2: all6artifacts3521passed each and strict
Sphinxexit0. Fullcase sets/focus/source/dependencies/normalizedargv/exclusions
and five hashes/job verified. Python3.10.21latest/3.10.22legacy,3.11.16,3.12.15,
3.13.16,3.14.7. SnapshotUTC2026-10-08T10:31:35.169995+00:00.
[Report](BLOCK23_GROUP_CROSSFIT.md), [CI](block23_ci_result.json),
[root validation](block23_validation_result.json), issues[]. Handoff141links
verified; source pushed. Owned probe copies and exact integration pytest-temp
removed; code/test JUnits/metadata/logs retained. Source/tests frozen; later
changes audit-only. No login/setup, subagents, PR/release/upstream or messages.
User push authorization persists for the personal branch. Final checkpoint via
gitlog-1; final ordinary push/live local-remote equality and clean tree checked
at completion. Stop at B23 for context cleanup/new user request.

Next B24: external OOF predictions for binary IRM, beginning with manifest,
alignment, ownership and leakage contracts. Multi/IV repetitions, multiway/
few-cluster inference and DR/R-CATE remain separate; sensitivity/SC08LOO/
selected-UATT/NumPyRST debt deferred. Do not repeat login/fork/setup/old suites.

## B24 — завершён: external OOF binary IRM (8 October 2026)

Final source `7e947f44e3d5a0ca9dbbe0b68bf7f070fc6150fd`, baseline3668eec; initialfeature2652d9f.
[Report](BLOCK24_EXTERNAL_OOF.md). Public make_oof_manifest + fit with complete
external_predictions/oof_manifest supports ATE/ATTE, R1/repetitions, iid/one-way
clusters. Version1 binds ordered numeric sample/index/roles, prediction/cluster
hashes, whole folds, full train complements with both arms and supplied uint32
seeds. Fit invokes no nuisance learner methods and draws no split RNG. Manifest
checks caller declarations/alignment, not external training/preprocessing/tuning
history or absence of leakage; hashes have no cross-version/platform stability
promise. Clip only, minKrows-per-arm guard retained. Partial nuisances/arbitrary
train subsets/independent external training samples/time-series need separate
contracts. Existing row-weighted score/SE/relative/B22 aggregation unchanged;
no M divisor. GATE/GATET/CATE/sensitivity and direct adapters reject.

Final correction7e947f4 normalizes overlap changed through set_params in staged
fit; factory validates without mutating configuration. Initial source2652d9f
passed3646local/CI cases but this review correction required final gates;
initial evidence and raw artifacts retained separately, not used as final gate.
Final new127cases,491focuspassed/58warnings/32.15s;64exactinternalfitpairs,
96estimates,32weightedATTErejections. 50existingIRMmethodASTs unchanged;
sensitivity/GATE/uplift algorithms only gain entry guards. Final committed
correctness3648passed/0failures/errors/skips/145warnings/132.65s, seven exclusions
unchanged. StrictSphinxexit0/23.040s. [Local](block24_integration_result.json),
[docs](block24_docs_result.json), [validation](block24_validation_result.json).

[CI37772289364](https://github.com/MaximLenivkin/Causalis/actions/runs/37772289364)
completed/success on exact7e947f4: all6artifacts3648passed each plus strictdocs0.
Full local/CI cases/focus/source/normalizedargv/exclusions/env/5hashes perjob
verified. ActualPython 3.10.22 latest, 3.10.21 legacy, 3.11.16 latest, 3.12.15 latest, 3.13.15 latest, 3.14.8 latest; snapshotUTC2026-10-08T11:51:49.085206+00:00.
[CI manifest](block24_ci_result.json). Root verifier --source7e947f4 --require-ci
checks source/AST/provenance/rawlocal+initial+finalCI/docs/cleanup/report/handoff,
issues[]. Handoff146immutablelinks checked. Source/tests frozen after7e947f4;
final changes audit-only, no CI rerun. Owned source copies and exact focus/
integration pytest-temp removed; code-testJUnits/logs/metadata retained.
Synthetic fixtures only. No subagents/login/setup/install/upstream/PR/release/
messages/notebooks/website. Ordinary personal-branch push permission persists;
do not ask again. Final commit via gitlog-1, final audit push/live local-remote
identity and clean state checked at completion. Stop at B24 for context cleanup.

Next B25: DR/R-CATE, honest learning/target/prediction contracts first; evaluation
and inferential guarantees explicitly scoped. Sensitivity/SC08LOO/selected-UATT,
multi-IV repetition/grouping, multiway/fewcluster and NumPyRST debt remain
separate/deferred. Do not repeat login/fork/setup/old suites or auto-start B25.


## B25 — завершён: DR/R CATE (8 October 2026)

Source `8604060282b803b73e00595b705867ddff351a32`, baselineebf940f.
[Report](BLOCK25_DR_R_CATE.md). New DRLearner/RLearner consume already fitted
internal, single-partition, iid, unweighted binary IRM with clipping; default
final LinearRegression. Frozen scoring schema, owned model/arrays, failed-refit
retention, raw-value reality guards and strictly interior fitted propensities.
DR unnormalized AIPW targets; R residual loss with q=(1-e)*g0+e*g1 and mandatory
sample_weight=(D-e)^2. Scalar score/normalization does not change CATE targets.
Existing T-learner and all scalar/cluster/repeated/external/sensitivity algorithms
are byte-identical; only existing uplift exports change. Four non-audit paths.
Unsupported external/group/repeated/drop/custom-weight contexts reject.

Each nuisance is OOF; final regression trains on all rows. Its training
predictions are in-sample. Independent evaluation/nested full-pipeline outer
refits required; ordinary CV of precomputed signals can leak. Restricted-class
approximation/projection, R's population projection weights e*(1-e). Binary
risk-difference scale, no forced bounds, automatic calibration, individual
counterfactual or CATE CI/rate/coverage/superiority promise. No separate marginal
outcome pilot; derived q inherits all three pilots' errors. Custom R regressors
must honor weights and squared loss; estimator controls regularization.

124 new cases,584focusedpassed/64warnings/30.47s. Independent DR conditional
moments (including binary and robustness/negative control), direct residual-design
R-loss oracle, constant projections, new-covariate noiseless recovery, fold spies,
schema/lifecycle/numerical/context guards. Eight pre-correction complex regressions
failed and now pass. Committed correctness3772passed/149warnings/143.57s, zero
failures/errors/skips; seven sensitivity exclusions unchanged. Strict standalone
Sphinxexit0/20.254s. Existing3648case set preserved;152pre-existing source/scripts/
workflowfiles byte-identical. Handoff149immutablelinks checked,issues[]. Owned
exact pytest-temp dirs removed; synthetic observations only, JUnits/logs/code/
source/environment evidence retained. No client records downloaded or used.

[CI37795625225](https://github.com/MaximLenivkin/Causalis/actions/runs/37795625225) completed/success on exact source: all6jobs3772passed each and strictdocs0.
Full local/CI case sets/focus/source/normalizedargv/sevenexclusions/env and5hashes
perjob verified; [CI manifest](block25_ci_result.json). ActualPython
3.10.22bothstacks,3.11.17,3.12.15,3.13.16,3.14.8; snapshotUTC2026-10-08T14:55:07.367935+00:00.
[Root validation](block25_validation_result.json),issues[]; --source 8604060282b803b73e00595b705867ddff351a32
--require-ci checks rawlocal/CI evidence and source isolation. Ordinary source push succeeded
using user's persistent «Разрешаю пуш в нашу ветку» authorization, with no
approval rejection. No environment setup/install/login/fork/subagents/upstream/
PR/release/notebooks/website/external messages. Final source/evidence gates complete; audit checkpoint via gitlog-1. Ordinary
final audit push, live local/remote identity and clean tree checked at completion. Source/tests frozen after8604060;
changes since then are audit-only, including verification script metadata repair.

Next B26: held-out nuisance/CATE validation, starting with target, independent
sample/nested-refit and leakage contracts; inference remains separate. Do not
auto-start B26. Stop at B25 for context cleanup and a new user request.


## B26 — завершён: held-out nuisance/CATE validation (8 October 2026)

Source `38378424fbfc422236ed81ba8162222ea39e6849`, baseline `4876103`.
[Отчёт](BLOCK26_HELD_OUT_VALIDATION.md). Новый
`HeldOutCATEValidation(learner=None).fit(irm).evaluate(validation_data)` обучает
собственные копии DR/R learner и отдельных full-training nuisance-моделей.
Используются current ml_g/ml_m templates; evaluation pilots отличаются от
удалённых fold models IRM. Контексты источника — как в B25: internal, R1, iid,
unweighted, clip. Уникальные непустые stable user_id обязательны на обеих
выборках; пересечение отклоняется. Совпадение ролей и признаков, оба treatment
arms, real/finite observations и predictions проверяются до расчётов.
`evaluate` вызывает только predict. Объекты и массивы принадлежат валидатору;
неудачный refit сохраняет прежнюю модель. Старые IRM/DR/R/T/policy/sensitivity
алгоритмы не менялись; 153 существующих library/scripts/workflow файла идентичны.

Frozen aggregate result: factual outcome MSE по arm, raw propensity Brier/log
loss/range/clipping count, mean CATE/DR signal, DR/R loss и DR gain vs zero.
DR loss включает шум и не является наблюдаемой CATE MSE. R loss использует
q=(1-e)*g0+e*g1; его oracle excess risk взвешен e*(1-e). Estimated pilots,
active clipping и confounding могут смещать критерии. Для сравнения нужны та
же validation-выборка и те же evaluation pilots. Stable IDs не доказывают
независимость и не обнаруживают relabelling/hidden preprocessing leakage.
После model selection нужен новый independent test или nested outer refits
всего pipeline. Внешние разбиения и preprocessing API не оркестрирует.
Нет CATE CI, calibration/identification test, individual effects или rate claim.

102 новых cases; финальный focus 686 passed /64 warnings /32.48s. Проверены
независимые finite-support risk identities, noise/negative control, factual
sklearn scorers, ownership/lifecycle, raw/schema/context guards, scalar/T
preservation; nested three-fold пример с training-only scaler и spies всех
nuisance/effect fit calls. Development fixture failures отдельно описаны.
Committed correctness 3874 passed /149 warnings /129.66s, zero failures/errors/
skips; семь sensitivity exclusions неизменны, не full release gate. Strict
standalone Sphinx exit0 /16.822s. Все прежние 3772 case IDs сохранены.
Handoff:153 immutable links, issues[]. Exact owned pytest-temp/private files
удалены, JUnits/logs/code/source/environment evidence сохранены. Synthetic
fixtures only; клиентские записи не запрашивались и не скачивались.

[CI37806099397](https://github.com/MaximLenivkin/Causalis/actions/runs/37806099397)
completed/success на exact source: все6jobs по3874passed и strictdocs0.
Raw artifacts/local case sets/focus/source/env/normalizedargv/7exclusions и
5hashes/job проверены. Python3.10.22bothstacks,3.11.17,3.12.15,3.13.16,3.14.8;
snapshotUTC2026-10-08T16:11:09.123760+00:00.
[Root validation](block26_validation_result.json), --require-ci, exit0, issues[].
Source/tests frozen; после3837842 только audit changes. Ordinary source и
финальный audit push в personal branch выполнены по постоянному разрешению
пользователя «Разрешаю пуш в нашу ветку»; повторная авторизация не нужна.
Final audit checkpoint через git log -1, live local/remote identity и clean tree
проверены при завершении. No subagents/login/setup/fork/upstream/main/forcepush/
PR/release/notebooks/website/external messages.

Next B27: inference families — сначала estimand, assumptions и supported fit/
evaluation contexts. Sensitivity/SC08LOO/selected-UATT/multi-IV grouping and
repetition/few-multiway clusters/NumPyRST debt остаются отдельными. Stop after
B26 for context cleanup; не начинать B27 без нового запроса пользователя.
