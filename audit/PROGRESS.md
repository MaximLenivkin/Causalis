# Прогресс и журнал

## 2026-10-05

- Репозиторий склонирован в `D:\codex\Causalis`, commit `ffe2c356c115f335b74b2f10117e19fe15585d46`; исходный checkout чистый.
- Прочитан корневой `AGENTS.md`. Указанный macOS interpreter отсутствует на Windows; создаётся repo-local `.venv` на доступном Python 3.12.14, входящем в declared диапазон >=3.10,<3.15.
- Созданы план и шкала доказательств. Ревью без изменений библиотечных исходников.
- Открыты репозиторий и опубликованный сайт; подтверждены перечисленные сценарии.
- Инвентаризация: 130 source Python modules (без generated _version.py), 48 194 строки, 123 test files, 40 notebooks/1 062 cells. Все исходники проходят AST parse.
- Создана `.venv` Python 3.12.14 и установлены project dev/docs dependencies + DoubleML для сравнения. Первый запрос установки не выполнился из-за перегрузки auto-review; повторный запрос одобрен и успешно выполнен. Version manifest: `environment.json`.
- Общий pytest завершён: 964 passed, 3 failed, 1 error из968cases, 317.21с (`pytest_full.log`, `pytest_full.xml`). Отдельный recheck четырёх непрошедших:3 passed,1 failed. Три проблемы были sandbox process/tmp permissions, одна — реальный CUPED cache regression со statsmodels0.15. Совместно967cases подтверждены как passing; это не один полный чистый прогон.
- Воспроизведены shared/contracts/DGP дефекты: nonfinite data, zero-variance SMD, duplicate-index outlier extraction, NaN assignment weights, default UUID collisions, nonlinear latent multi oracle.
- Сабагенты подтвердили численно defects multi ATTE/relative ATT/sensitivity/refit CATE, Newcombe, DiD score/controls, CUPED name collision и другие; findings проходят дедупликацию перед финальным рейтингом.
- Извлечён markdown всех 40 notebooks, сопоставлены API modules и source. Подозрения по 27 импортам проверены: actual export errors не обнаружены.
- Первичная литература сверяется через web; современный paper не считается автоматически основанием заменить корректный existing estimator.
- Все три сабагента завершили отчёты: DML_REVIEW, SCENARIOS_REVIEW, DOCS_RESEARCH. Exact references, probes и ограничения сохранены; исходники не менялись.
- Изолированная API docs build успешно завершилась, generated131moduleHTML; оригинальный checked-in API126HTML сохранён. Файл tests/docs/test_generate_api_reference.py helper-only, реальных pytest tests нет.
- Benchmark завершён; повтор выполнен без параллельных fits/tests/docs build. Matched binary IRM Causalis0.1468с vsDoubleML0.3644с; ATE/SE/OOF predictions совпадают. Constructor/extraction timings100k–1m и allocation peaks сохранены в benchmark_data_path.json.
- Array benchmark уточнён: первая версия не выполняла binary checks, поэтому сравнение было неполным. Итоговый script сравнивает same-checks и отдельную linear-binary optimization; в финальный отчёт включены только исправленные измерения.
- Итоговая дедупликация:31code/inference/contract/release findings,11P1+20P2. DML-05/ROOT-04 объединены; docs Newcombe не считается вторым независимым багом. Отдельные top10 docs/methods/features/performance составлены.
- REPORT.md, PERFORMANCE.md и COVERAGE.md написаны. Findings содержат reproduction/source evidence и границы переноса вывода; fixes не применены, чтобы сохранить review snapshot.
- Финальная проверка артефактов:171absolute local links/line anchors проверены, missing/out-of-bounds0; все шесть таблиц содержат заявленное число пунктов (10/21/10/10/10/10). Evidence: report_validation.json, verify_audit.py. Git diff tracked source пуст.

## Состояние этапов

| Этап | Состояние |
|---|---|
| 1. Снимок/окружение | Завершён |
| 2. Корректность | Завершён в заявленных пределах; independent probes и catalogue готовы |
| 3. Документация | Завершён;40notebooks inventory, сайт/docstrings/API drift и successful build |
| 4. Исследования | Завершён; primary sources доSep2026, top10 extensions |
| 5. Производительность | Завершён; clean benchmark, profiles, top10 optimization plan |
| 6. Отчёт | Завершён; REPORT.md и тематические приложения готовы |

## Следующий этап проекта

Рекомендованный порядок дальнейшей разработки: быстрые correctness/doc fixes → inference repair и coverage validation → оптимизация data path → расширения DML/CATE/IV/DiD. Это backlog, а не незавершённая часть текущего ревью. Существующий код не исправлялся и внешние PR/issues не создавались.

## 2026-10-05 — начало исправлений по новому запросу

- Проверены Git/author/public remote. Upstream main соответствует audit SHA. `gh` отсутствует, configured helper отсутствует; noninteractive GCM check не нашёл сохранённую GitHub credential. Remote fork/push пока не выполнены; авторизация по инструкции GIT_ACCESS.md ожидается от пользователя.
- Создана branch `codex/correctness-roadmap`; checkpoint **2c26cee** сохранил аудит/evidence/план. Большие build copies/temp/cache исключены из index, raw text evidence logs сохранены.
- FIX_PLAN.md разбивает работу на6implementationblocks с commits/проверками и остановкой для очистки контекста. Sensitivity DML-07/08/10/11 и dependent lifecycle state отложены по прямому сообщению пользователя о готовящихся upstream fixes.
- DOCUMENTATION_HANDOFF.md подготовлен для автора docs;28GitHub snapshot links проверены, local-only links0. Sensitivity-specific tasks исключены.
- **B01 завершён, commitbd8a2be:** Newcombe hybrid CI, enum validation, function docstring. До source fix27testsfailed/9passed; после36conversionpassed и31neighborRCTpassed. Логи block01_*_tests.log. Полный suite/benchmark повторно не запускался, sensitivity не затрагивался.
- NEXT_SESSION.md содержит commits, scope, проверки и следующийblockB02. На границе B01 работа остановлена; внешние PR/issues не создавались.

## 2026-10-05 — GitHub подключён

- Пользователь завершил browser login. Проверен активный GitHub account **MaximLenivkin**, keyring и scopesrepo/workflow; credentials не выводились.
- Создан [личный fork](https://github.com/MaximLenivkin/Causalis); API подтвердил parentcausalis-causalcraft/Causalis и push/admin права. Upstream доступен read, без push.
- Исправлена команда в GIT_ACCESS.md: установленный gh2.102.0 не принимает `--remote=false` вместе с explicitrepository; создание выполнено с `--clone=false`.
- Origin переименован в upstream; новыйorigin указывает на personalfork. Ветка `codex/correctness-roadmap` pushed с commits2c26cee/bd8a2be/a3846ba, local tracking настроен. Code tests не повторялись: на этом этапе менялась только Git setup/documentation.
- Проверка первогоpush:remote/localHEAD совпадают — `a3846baa0a07e7d81c3ea8850e130cb2de6d6ba4`; remote копия трёх commits подтверждена.
- NEXT_SESSION/FIX_PLAN/DOCHANDOFF обновлены; sensitivity остаётся отложенным, B02 не начат, PR не создан.

## 2026-10-05 — B02 завершён

- По новому запросу пользователя выполнен один следующий блок: contracts/shared/DGP. Три сабагента независимо исправили numeric validation, utilities и latent-U outcome oracle; root исправил shared/binary/multi balance, проверил diffs и выполнил интеграцию.
- Закрыты ROOT-01–07, включая grouped ROOT-04/DML-05: один P1 и шесть P2. Sensitivity files/formulas/tests не менялись; проверка paths относительно начала B02 не нашла sensitivity изменений.
- До source fixes сохранены failing regressions. Scoped passes: contracts 147, balance 50, utilities 34, oracle 45; эти наборы пересекаются и не суммируются как unique coverage.
- Общая проверка финального кода: **606 passed**, 5 existing warnings, 123.61 s. `block02_integration_tests.log` охватывает data/shared, multi DGP, публичные balance/Love plot, outliers и соседние RCT inference tests. Полный suite и performance benchmark не повторялись; известный SC-12 остаётся в B05.
- Созданы code commits **817c24c / add2f36 / a5a6e3a / c27e744**, каждый с code/tests/evidence. Итоговый отчёт — BLOCK02_CONTRACTS_SHARED_DGP.md; B02_*_NOTES.md сохраняют derivations, commands и compatibility limits.
- DOCUMENTATION_HANDOFF.md дополнен готовыми английскими migration/oracle текстами и immutable GitHub code links. verify_handoff.py теперь проверяет snapshot links как upstream audit, так и personal implementation commits.
- Финальная проверка artifacts: 36 GitHub handoff links и 188 absolute local links, issues 0; 21 changed/new Python files AST parsed; sensitivity paths changed 0. Новый verify_block02.py сохраняет отдельный validation JSON и не переписывает original report_validation.json.
- Новый соседний DGP follow-up: marginal propensity oracle вместо softmax при U=0. Текущее поведение явно описано; изменение propensity API не входит в B03. Extreme coefficient guards, estimator output policy и near-zero SMD scale invariance также записаны как отдельные follow-ups.
- NEXT_SESSION/FIX_PLAN обновлены для B03. На границе B02 работа остановлена; следующий блок начинается после нового запроса. Внешние PR/issues не создавались. Коммиты сохраняются в ранее подключённой личной ветке через обычный push.

## 2026-10-05 — B03 начат

- Пользователь попросил перейти к следующему блоку. Рабочий checkpoint `790c8ab`, branch/tracking совпадают с планом.
- Три параллельных задания: multi ATTE IF, binary relative ATT/drop weights/CATE cache, OOS fold diagnostics. Root занимается stable GATE и итоговой интеграцией.
- Sensitivity modules/tests не изменяются; upstream ещё не синхронизирован. Полный новый аудит и broad performance benchmark не повторяются.

## 2026-10-05 — B03 завершён

- Пользовательский scope выполнен: DML-01/02/04/06/09 и только independent CATE part DML-03. Root исправил centered GATE/GATET descriptive SSE; три агента независимо реализовали multi ratio IF, binary baseline/weights/cache и честную fold diagnostics. Root проверил diffs/derivations, staged законченные fixes и выполнил интеграцию.
- Четыре code commits: **c9259072a24f5325f944cd37c4f203f33c39a5e7**, **e6a92759f3c8844999c53bd065a673e31330d604**, **6084b34d799e9af34228136c0a2e9549063638ac**, **113c693a0dd721c6e77dfe84bc647d2ffb4c7841**. Каждый сохраняет source/tests/notes/raw evidence. Source/tests после последней проверки не менялись.
- Independent contamination derivatives, constant/proportional potential-outcome identities, outcome shift/permutation и fresh-fit equivalence проверены. Oracle IID sampling600×600: multi95%coverage0.9400/0.9433, binary relative coverage0.9550. Это ограниченная inference sanity check, не coverage fitted learners во всех DGP.
- Итоговая repository integration вне sensitivity modules: **1143 passed, 1 failed, 76 warnings, 299.18s**. Единственный failure — прежний SC-12 `test_shared_design_and_input_unchanged`, line80 identity of statsmodels0.15 `pinv_wexog`. Этот assert не скрыт/не снят; CUPED source/tests не менялись. Новых failures нет, но suite не полностью зелёный.
- `run_block03_integration.py` сохраняет exact args/exclusions. Семь sensitivity-named test modules не запускались; обычная estimator diagnostics по-прежнему может собирать existing sensitivity payload. Sensitivity formulas/fields/tests не исправлялись, generic scalar/sensitivity refit state остаётся deferred. Upstream не fetch/merge/rebase.
- `BLOCK03_DML_GATE_UPLIFT.md` и B03_*_NOTES.md содержат mathematical derivations, compatibility и actual test evidence. Handoff дополнен готовыми английскими migration paragraphs и immutable personal-fork code links; публиковать вместе с соответствующим release, автору файл не отправлялся внешними инструментами.
- Scope/artifact checks: **217 local links, 45 immutable GitHub handoff links, 19 Python AST, issues0**; 7 library paths, sensitivity paths0. Separate JSON сохраняет integration result и baseline failure; original audit snapshots не переписывались.
- NEXT_SESSION/FIX_PLAN/README/GIT_ACCESS обновлены. После final documentation checkpoint выполняется обычный push в `origin/codex/correctness-roadmap` и проверка remote/local SHA. На границе B03 работа остановлена; следующий B04 DiD начинается по новому запросу пользователя. PR/issues не создавались.

## 2026-10-05 — B04 завершён

- По новому запросу пользователя реализован один следующий блок DiD. Три parallel agents: control alignment, full cell IF, independent methodology review; root исправил cluster inference иcomplete-pair population aggregation, выполнил integration.
- Закрыты SC-01/02/03/04/11P1. Code commits **87228e267aed3dc71dadd4bbe19b969a95463591**, **57dbba1e2ecc0c1cab413b1da7f40cfdd8b22131**. Добавлены95cases (10cluster,34cell,32alignment,19aggregation). Исторические snapshots не переписывались.
- Traditional MLE/OLS ATT сохранён; fullIF учитывает обе нормировки,nuisance params,penalty/clipping policy. Augmented-designSVD избегает Gram-direction loss. Единые controls disjoint иuntreated наmax(base,target)+anticipation. AggregateIF использует фактические observedtreated pairs; equalcohortcellweights fixed. Clusterbootstrap center/scale covariance соответствует analyticalfinitecluster convention; cluster>=2,b0или>=2.
- Independent96unit×12configuration contamination refits; allaggregatefamilies/missingness empiricalrefits; exhausted8signpatterns; immutableprimarysource review. Originalprobes теперьtrend-invariantIPWSE,preATT-2vs-1,DRSE.03887567matchingreference,populationmixtureSE.49574187vs0.
- Estimated-nuisance DRMC600×n600 each2DGP:coverage.935/.956667. Первыйfinite-ngapmeanSE/empSD.9163 сохранён в отчёте, universalimprovementнеclaimed. Shares-onlyoraclecoverage.958333. Fixedridge/clipping,targetmissingness иfewclusters caveats записаны.
- Repository integration source57dbba1: **1238 passed,1 failed,76warnings,340.04s**,exit1. Единственный прежнийSC-12CUPEDcacheidentity наstatsmodels0.15. Newfailures0; assert/sourceCUPEDнеменялись. Seven sensitivity modules исключены; selection/resultJSON/rawlog сохранены. Это неfullygreen/full sensitivitysuite.
- `BLOCK04_DID.md`,B04_*notes,probes,logs готовы; DOCHANDOFF дополненreadyEnglishmigration и49провереннымиimmutableCausalislinks. Source defaults/baseperiod/warning policy docstrings исправлены. PR/issues/externalmessages не создавались. Causalisupstreamнеfetch/merge/rebase.
- `verify_block04.py` проверяетscope,PythonAST,localartifactlinks иactualintegrationresult. Исправлен first-generation self-output link ordering в самомauditrunner; librarycode не менялся послеintegration.
- NEXT_SESSION/FIX_PLAN/README/GIT_ACCESS обновлены. Finaldocumentationcommit иобычныйpush в personalfork сохраняютcheckpoint; remotelocalSHA equality проверяется на завершении. На границеB04 работа остановлена; B05 начинается отдельным запросом. Sensitivity остаётсяdeferred. Earliest universalprecellindex0 остаётся отдельнымsupportfollowup.

## 2026-10-05 — B05 завершён

- По новому запросу пользователя выполнен блок CUPED / IV / SCM. Три subagents занимались IV, SCM placebo и независимым математическим ревью CUPED; root реализовал CUPED и общую интеграцию.
- Закрыты SC-06, SC-07, SC-09, SC-12. SC-08 исправлен для placebo; leave-one-donor-out sensitivity остаётся отложенной. Изменений sensitivity modules/tests/formulas нет.
- Code commits: **bb31a4b**, **5e03795**, **3c000b1**, **1b24777**. Последний — source checkpoint интеграции. Добавлены **137 cases**: 24 names, 22 numerical/API, 60 IV, 31 SCM. Исходный cache assertion не снят и проходит.
- CUPED использует collision-safe labels и явные роли, одну SVD дизайна для всех outcomes и stable HC2/HC3 projection. Refutation/winsor/raw-control covariance используют ту же factorization. Independent QR и public statsmodels reference подтверждают covariance и inference; обычная bootstrap policy сохранена.
- IV diagnostics принимают estimated model/result/payload; lazy computations сохраняют estimate options/LATE. Каждая новая fit attempt очищает прежние fitted/inference attributes; failed refit не отдаёт старый estimate, сохранённые результаты остаются доступными.
- ASCM сохраняет 13 constructor-compatible options и effective inference settings. Placebo наследует их, partial overrides сохраняют прочие настройки; incomplete legacy metadata требует восстановления. Actual treated placebo воспроизводит исходный mean gap 1.3314659377 вместо прежнего 1.3712012252.
- Scoped sets: CUPED **127 passed**, IV **73 passed**, SCM **67 passed** с одним известным grid-boundary warning. Counts пересекаются с общей интеграцией.
- Общая repository integration: **1376 passed, 0 failed, 77 warnings, 438.20 s**, exit0; семь sensitivity modules исключены, docs build пропущен. Raw log и точный selection/result manifest сохранены. Это зелёный выбранный suite, не полная sensitivity/version validation.
- Sequential local fit benchmark: 12000 rows, 4 X, HC2, checks=True, 1/8/32 outcomes, native threads1. Medians дали **1.73/2.90/2.58×**; max ATE discrepancy 1.58e-14, SE 3.47e-18. Construction/estimate/memory вне timing. Initial benchmark-only Series-index error исправлен в audit worker; final measurements выполнены заново.
- BLOCK05 report, method review, IV/SCM notes, probes и logs готовы. Portable documentation handoff содержит **58 проверенных immutable Causalis links**; external messages/PR/issues не отправлялись. Historical audit и Causalis upstream state не изменены.
- Final artifact checks: source/tests совпадают с1b24777, Python AST/local links/sensitivity guard проходят. После documentation commit — обычный push в личную ветку и проверка remote/local equality. На границе B05 работа остановлена. **B06** compatibility / CI / pandas-NumPy-KDE performance начинается отдельным запросом; sensitivity и SC08LOO остаются deferred.

## 2026-10-05 — B06, первая проверка

- По новому запросу пользователя выполнены compatibility/CI/performance fixes. Agents: CI/dependencies, duplicate screening, KDE; rootbinaryfastpath, controlledbenchmark, review/integration/handoff.
- ROOT08metadata теперьpydantic>=2; ROOT09fullpytestgate реально передbuild/publish, failure/emptyexitblocked, tag/main/versionrulespreserved. BranchCI6representativejobs has explicit7sensitivityexclusions, newmodule requiresreview; audit-onlypushes don'tcancelmatrix.
- Four main codecommits f31b743/5977bb8/74c0ff0/d292b3c, CIauditfilter1be6b67, benchmarkevidence50ad33e. Lastsourcechangeonlyhelperdocstring, executableASTvsd292identical; no tests changed. Sensitivitysource/tests untouched, upstream notsynced.
- New193cases:CI11,duplicates71,binary74,KDE37. Focused sets111/156/40/11pass, intersections notsummed ascoverage. Numerichelper before2fail72pass demonstrates sortcost, notstatisticalbug. Exactframe/error/collision/chunkreference, binary/multi/IVfullfoldpredIF/CIreference andsame-bandwidthSciPy/denseKDE passed.
- Local integration **1569passed,0failed,0skipped,77warnings,481.47s**,exit0. Sevenexplicit deferredmodules,SKIP_DOCS_BUILD=true; fullrelease/sensitivity/docsbuild notvalidated. OriginalSC12assertcontinuespassing. Exactselection/result/JUnit/rawlog retained.
- Sequentialfreshworkersbaselinebf2ea87/currentd292,native1,seed731,median5reps(KDE/fit3):constructors1.22–2.24×,extraction1.37–4.14×,KDE30k×800tracedpeak549.32→8.13MiB,maxdensitydiff5.88e-15. MatchedIRMfit1.24×,ATE/SE/folds/preds/IFexact. TracemallocnotRSS,fitexcludeconstructor/estimate,desktoplimits documented. Ownedcandidateaudit-only, no new snapshotAPI.
- GitHub matrixrun37372133090 on1be6b67 executes cleanLinuxPython3.10–3.14+representativelegacy3.10stack. Initiallyqueued duringprimaryGitHubActionsrunnerdelayincident3q1yb5m7ltvb; actual perjobresults/versions/artifacts willbe recorded inblock06_ci_result.json. Initialrun37371536543 supersededCIconfigpush, cancellations notlibraryfailures. Release/publicationnottriggered.
- PortableDOCHANDOFF68immutableCausalislinksverifiedissues0; localartifactAST/links/scopechecksissues0. Finalreport/continuation retain actualmatrixstate, noautomaticnextfeatureblock.

## 2026-10-06 — B06, финальный checkpoint

- Реальная legacy matrix выявила NumPy1.x IV string-add bug:1516pass/53fail с одной причиной. Failure сохранён отдельно от canceled status job; latest-stack successes не считались доказательством старого stack.
- Commit09e00de исправил joint labels через np.char.add без смены split policy. До fix один simulated compatibility case упал; после focused156pass. Добавлены13cases, суммарно206new.
- B06: implementation и локальная integration завершены: **1582 passed, 0 failed/skipped, 77 warnings, 400.95s**. 206 новых cases, 7 sensitivity modules явно исключены. Pydantic>=2, full release pytest gate, CI matrix, duplicate screening, linear binary detection, bounded Gaussian KDE и NumPy1.x IV fix. Все шесть clean Linux jobs и artifacts прошли; каждый — 1582 cases без failures/errors/skips. Финальный source09e00de; evidence в BLOCK06_COMPATIBILITY_PERFORMANCE.md. Owned arrays остаются audit-only; полный sensitivity/release/docs build не подтверждался.
- Raw initial/final integration, prior legacy failure, before_fix/current CI versions/JUnit и последовательный benchmark сохранены. Source/tests совпадают с09e00de; sensitivity paths0. DOCHANDOFF дополнен IV migration и immutable source/test links.
- Финальный audit commit и normal push сохраняют отчёт и continuation; remote/local equality проверяется на завершении. Новый feature block не начат, upstream не merge/rebase; PR/issues/externalmessages/release не создавались.

## 2026-10-06 — B07 завершён

- По запросу пользователя продолжен следующий ограниченный correctness block. Root реализовал DiD enumeration/docs и integration/Git; три subagents выполнили independent DiD regressions, nuisance guard и DGP/method review. Sensitivity/SC08LOO не затрагивались.
- **43f0b3e**: universal inclpre enumeration теперь включает первый analysis target при существующем позднем fixed base. Varying/post-only и прежние support filters сохранены. Baseline29fail/14pass; final43newcasespassed28.23s. Ручные ATT/nonzeroSE/IF, M/2M, anticipation, missing pairs и post inference verified. Earlier58neighborspassed;12new assertion-fixture failures исправлены и сохранены отдельно.
- **d3b6709**: два DGP paths изменены только в docstrings. target_d_rate = sample-X/U=0 calibration; latent marginal rates могут систематически отличаться. CopulaToeplitz = latent Corr(Z), а не observed Corr(X). Adaptive Gaussian integration/correlation probes и конкретный additive oracle proposal сохранены; marginal/latentATT API не реализованы.
- **a2109a6**: raw real numeric NaN/±inf отвергаются до probability transforms и storage в binary/multi; shared helper также защищает IV learner outputs. Independent reviewer обнаружил hard-label fallback gap; добавлен guard до np.where. Finite clipping/normalization/folds/scores/IF/inference сохранены. Final104new+87neighbors=191passed1knownwarning25.75s. Earlier222passset пересекается; initial83/81failures не являются количеством новых defects. Exact-old public-storage probe:10missinginfguards+5oldNaNmessages без fixture errors; fallback:6missingrejections/4finitepasses.
- Final source a2109a6 отправлен в личный fork. Local repository integration: **1729 passed, 0 failures/errors/skips, 77 warnings, 404.84 s**, exit0,147newcases. Семь sensitivity modules явно excluded прежним runner; standalone Sphinx/full sensitivity/release не validated. Raw selection/result/log/JUnit сохранены.
- **Actual CI37385736343 completed/success**: каждый из6Linuxjobs и artifacts проверен на exactsource,1729passed0failures/errors/skips. Python3.10–3.14latest-compatible +3.10legacy; full package versions/JUnit в block07_ci_result.json. Snapshot2026-10-05T23:02:17.8244687Z. B06 results не подменяют новые проверки.
- BLOCK07 report, three detailed notes/review, raw baselines/final logs, integration/CI/probes готовы. PortableDOCUMENTATION_HANDOFF содержит B07 migration/factual paragraphs и81verified immutable source links. Source/function whitelist,4doc-onlymoduleAST,9librarypaths,PythonAST/local links и no-sensitivity scope проверяются verify_block07.py; actualcounts/diagnostics в block07_validation_checks.json.
- FIX_PLAN/NEXT_SESSION/README/GIT_ACCESS обновлены. Новый B08 не начат; кандидат — DGP reference contracts/rare-arm law, затем marginal Gaussian oracle accuracy/API. Ordinary finalauditcommit/push и local/remote equality сохраняют checkpoint. На границе B07 работа остановлена; upstream merge/rebase,PR/issues/externalmessages/tag/PyPI не выполнялись.

## 2026-10-06 — B08 завершён

- User запросил следующий блок; root и3agents разобрали centralDGPcontracts/sampling/independentmethodreview. Scope ограничен generator/wrapper; sensitivity/SC08LOO untouched.
- Source/tests commit **9fb8041300410b560da80a45cabac4b541d1629d** ordinary pushed. Finite real config/X/U/callback/intermediate/outputguards, complexprecastchecks, singleton-U normalization, scalar/oneelementcallbackcompatibility, targetsumoverflow stable scaling. Exactbaseline112newtests100failed12passed7.00s; original21baseline17failed4passed3.77s сохранён отдельно.
- Assignmentpolicy appended послеoldparams: defaultensure_all preserves10retries/safeRNGproposals, singleton-erasinginsertions заменяетsurplusdonors; optiniid singleindependentdrawpermitsn<K/missingarms. ExactB07generator+wrapperbaseline75cases29failed46passed2.33s:19coveragecases+10absentnewAPI, не29distinctbugs. Mixed-stateearlierbaseline/regexfixtureerror отдельноdocumented.
- Finalfocused149passed1intentionaloverflowwarning46.14s (112new+37neighbors),75samplingpassed8.45s;16fullframe/schema/next10RNGexactconfigs vsB07 oncommittedsource. Counts пересекаются сintegration, не суммировать.
- Localintegration **1916passed0failures/errors/skips78warnings400.69s**,exit0,source9fb8041;187newcases. Sevennamed sensitivity exclusions unchanged. All6LinuxCIjobs/artifacts verified **1916passed каждый**,run37420288433completed/success,exactsource;versions/JUnit/selection inblock08_ci_result.json.
- Independentmethodreview found no bounded-scope blocker; confirmed P2 names overwrites remainnextblock. ExtremeGaussian oracle arbitrarystrength accuracy/referenceq/selectedATT deferred; no speedbenchmark/Sphinx/fullrelease/sensitivity/upstreamsync.
- Mainreport,3notes,exactbaseline/focused/integration/CI/referenceevidence и portableDOCHANDOFF готовы;85immutablelinksissues0. Source/tests remainfrozen;finalartifactcheck/commit/push сохраняетcheckpoint. На границеB08остановиться;B09только поновомузапросу.

## 2026-10-07 — B09 завершён

- Пользователь запросил следующий пункт и параллельную работу субагентов через CLI. Root реализовал namespace guard, три субагента независимо разобрали контракт, написали regression tests и проверили patch/CI. Текущий Mac environment восстановлен ранее: `.venv/bin/python`3.12.14; старую `.venv` с другого компьютера не переносили.
- Source/tests commit **1e2b544f7f91a57ad3e049572915a4b3891b084a** обычным push сохранён в personal fork. Изменены только два library paths (functional.py docstring) и один новый test module,123newcases. Коллизии полного actual namespace outcome/treatment/expanded confounder/enabled oracle вызывают ValueError с именем и ролями. Нет rename/strip; disabled oracle/control CATE имена доступны. Повторная validation покрывает mutation между generate attempts.
- Exact baseline123cases: **87failed/36passed**; patch **123passed0warnings3.65s**. Первоначальный101case run и один исправленный fixture assertion сохранены отдельно. Neighbors217passed6.91s. Reference64configs×2generations=128 exactframe/dtype/schema/RNGcomparisons; независимый reviewer material source findings не нашёл.
- Local Mac integration наcommittedsource: **2038passed,1failed,0errors/skips,80warnings,117.46s**, exit1, total2039. Единственный failure — unchanged DiD diagnostic assertion GREENvsYELLOW: практически нулевые preATT≈1.11e-16 иSE≈2.94e-31 дают |t|≈3.78e14. Exactbaseline7414566 наэтомstack даёттотжеflag/cellvalues/assertfailure; fixture и5calledcodepaths unchanged, changedDGPpaths невызываются. Assert неослабляли, testcase неисключали; local suite неclean. Raw one-node baseline/currentJUnit, aggregateprobes иnote retained.
- Actual **CI37530152376 completed/success** наexactsource1e2b544: downloaded artifacts всех6Linuxjobs проверены, **2039passedкаждый**,0failures/errors/skips. Python3.10–3.14latest-compatible плюс3.10legacy. Versions/selection/JUnit вblock09_ci_result.json. Семьnamed sensitivityexclusionsunchanged; standaloneSphinx/full sensitivity/release неvalidated.
- B09 reports, provenance, rawlogs, portableEnglishDOCHANDOFF иcontinuation готовы;88immutablelinksverified. Partialclone lazyfetch историческихblobs выполнен в разрешённом network запуске дляhandoffchecker, безupstreamsync. Source/tests после1e2 неменялись. verify_block09.py проверяет честныйfailedlocalstatus иrawbaselineproof отдельно отgreenLinuxmatrix.
- Подтверждён новый отдельный residual: sharedcategoricalcopula использует`u` предыдущейкоординаты, firstcategoricalUnboundLocalError; normal→categoricalidentityCorr даётполнуюложнуюзависимость в1000rowsseed731. Samplingfix иDiDnumerical-zero diagnosticpolicy кандидаты B10; дальшеGaussianoracleaccuracy/API иостальнойплан. Sensitivity/SC08LOO остаютсяdeferred.
- Finalauditcommit иordinarypersonalpush сохраняют артефакты; remote/local equality и clean status проверяются на завершении. На границе B09 работа остановлена. Upstream push/merge/rebase, PR/issues, внешние сообщения и release не выполнялись.

## 2026-10-07 — B10 завершён

- По новому запросу пользователя выполнен следующий bounded correctness block. Root и три CLI субагента: contract/callers, независимые tests, review/CI. Shared categorical copula теперь использует текущую raw Gaussian координату; saturated upper endpoint не выбирает trailing zero probability. Numeric transforms, Gaussian draws, PSD repair, schema и API сохранены. Один library path и один новый test module; sensitivity/DiD formulas не менялись.
- Source/tests commit **95a8b7599fb129fb2c5973f50e9b4a8018732f6c** pushed в personal branch. 33 новых cases passed,0warnings,3.84s; frozenbaseline83b6383 того же module:30failed3passed,4.29s. Source/test hashes совпали, fixtures не корректировались. Neighbors126passed0warnings3.71s.
- Independent reviewer:36 exact numeric-helper и96 valid public binary/multi/IV frame/schema/RNG comparisons,9 coordinate refs и7 boundaries. Candidate boundary flaw с trailing zero probability найден и закрыт до source commit. Первоначальная reviewer fixture attribute/name проблема исправлена в isolated harness; библиотека не менялась. Material patch findings нет.
- Local integration committed95a:2071passed1failed0errors/skips78warnings90.27s,total2072,exit1. Единственный failure — тот же прежний DiD GREEN/YELLOW numerical-zero assertion; current probe подтверждает одинаковые B09 values, fixture и5called files unchanged, shared sampler не вызывается. Assert/threshold/exclusions не ослабляли. Scoped/full suite clean=false.
- CI **37532909989 completed/success** на exact95a: все6Linuxjobs иdownloaded artifacts проверены, каждый2072passed безfailures/errors/skips. Ровно7sensitivitymodulesdeferred; Sphinx/full sensitivity/release неvalidated. Ни performance claim, ни новый benchmark не добавлялись.
- Reports, reproducible runners/provenance, portable documentation handoff и NEXT_SESSION обновлены. Source/tests остаются frozen; final audit-only commit/push сохраняет результаты. На границеB10 остановиться; следующий кандидатB11 — binary/IV namespace guards (confirmed confounder d overwrites treatment); numerical-zero DiD diagnostic/fixture policy сохраняется отдельно, затем Gaussian oracle accuracy/API и остальной correctness backlog. Upstream sync/PR/issues/messages/release не выполнялись.

- Final verify_block10: scoped source/test hashes, local known failure, six CI artifacts, independent reference counts и portable links verified без issues. Documentation handoff:91immutablelinksverified. Current fixture-name review дополнительно подтвердил прежний binary/IV d-overwrite; root включил bounded namespace guard в continuation, source B10 не расширял.


## 2026-10-07 — B11 завершён

- Пользователь запросил следующий этап. Root и три существующих CLI субагента реализовали bounded binary/IV core namespace guard, независимо проверили контракт, regressions, reference compatibility и CI. Source/tests commit **cdc2c9590246c5b049d2184ba3479324217b2b00** ordinary pushed; два library paths, один новый module163cases. Constructor/eachgenerate/postsample/finalassembly checks; disabled/family-specific names и legacyk0containers preserved, no rename/strip. Public API/arithmetic/RNG дляvalidconfigs unchanged.
- Samefinalmodule:163passed0warnings4.14s; exactbaseline4d6b814103failed60passed0errors/skips5.81s. Frozenbinary/IVparent+realwrapperbindingsverified; identicalcollection/source/testhashes связаны сcommittedcdc, focusedrun честноprecommit. Noexistingtestsweakened.
- Independentreviewcommittedsource:80validconfigs×2+6family-specific×2+14k0containers×2=200exactframe/dtype/schema/next10RNGcomparisons;45reject11mutationprobes,issues[]. Initialcallbackmutationguardgap устранёнfinalcheckдоDFconstruction доsourcecommit. Frozencontractprobe46namespace/16container/5wrappercases сохранён отдельно.
- Localintegrationcdc:2234passed1failed0errors/skips78warnings84.59s,total2235,exit1;local/fullclean=false. ОдинпрежнийDiD GREEN/YELLOW numerical-zero failure. Currentfixture+entireB10runtimecalledpackageclosure hashes unchanged; changedDGPpaths внеclosure. Этоstaticlinkage кexistingruntimeproof, неnewB11cellprobe. Assert/threshold/exclusionsunchanged.
- CI **37589241406 completed/success** наexactcdc;6actualdownloadedartifactsets verified, каждый2235passed0failures/errors/skips. ActualPython3.10.21latest/3.10.22legacy,3.11.16,3.12.15,3.13.15,3.14.7. Ровно7sensitivityexclusions прежние; standaloneSphinx/full sensitivity/release неvalidated.
- Reports/runners/provenance,portableEnglishhandoff94immutablelinks иNEXT_SESSION сохранены; aftercdc source/testsfrozen,finalauditonlycommit/push. NextboundedB12 — wrapper preperiod/ancillarynamespace, ordering/projection; confirmed y/ageoverwrite иIVduplicatedcolumns. CoreB11guard нерасширен blanketwrapperreservation. Затем mathematicalnumerical-zeroDiDpolicy/GaussianoracleAPI иостальнойcorrectnessbacklog.
- На границеB11 остановиться; B12 только поновомузапросу. Upstreamsync/PR/issues/externalmessages/release не выполнялись. Finalremote/localequality+cleanstatus проверяются послеordinaryauditpush.


## 2026-10-07 — B12 завершён

- Root и три существующих CLI агента: 133 frozen-baseline contract probes, 162 независимых regressions, 460 exact frame/metadata/RNG references. Source/tests **0b30db33fd2593dc25ea1b823a91795c789e0191** ordinary pushed; шесть library paths и один новый test module. Actual-enabled pre/ancillary guards, immutable assembly metadata, unique ordering, actual numeric feature projection. User_id role только при ancillary addition; disabled oracle names сохраняются. Private fields исключены из constructor/repr/compare, fields/asdict их включают.
- Focus162passed,0warnings,4.74s; exact same-module baseline136failed/26passed,6.53s. Original precommit HEAD сохранён; committed source/test hashes соответствуют run. Review45rejects/34allowed,6corecallbacks,5wrappercallbacks,2constructors; warnings0,issues[]. Full refs precommit, точные committed12filebytes verified. Пять AST numeric bodies preserved. Intended changes для misclassified features/RNG явно описаны.
- Local committed integration:2396passed,1failed,0errors/skips,78warnings,85.67s,total2397,exit1; suite не считается clean. Прежний DiD failure; fixture и B10 called closure байтидентичны, DGP paths вне closure. Static linkage, новый cell-value probe не запускался. Assert/threshold/exclusions не ослаблены.
- CI37598926037 completed/success на exact0b30: шесть downloaded artifacts,2397passed каждый,0failures/errors/skips; matrix_verified=true,issues[]. Snapshot UTC2026-10-07T09:15:10.818155. Actual Python3.10.21latest/legacy,3.11.16,3.12.14,3.13.15,3.14.7. Семь sensitivity modules deferred.
- Reports/runners/provenance/handoff101links и NEXT_SESSION сохранены. Source/tests frozen после0b30; финальный audit-only commit и ordinary push сохраняют checkpoint. Следующий B13 candidate — confirmed classic-RCT scenario outcome rename collision; затем numerical-zero DiD policy и прежний backlog. Sensitivity/Sphinx/release/performance/upstream sync/PR/external messages не выполнялись. Работа остановлена на границе B12; remote/local equality и clean tree проверяются после final push.


## 2026-10-07 — B13 завершён

- Пользователь возобновил работу; baseline9f0a63c и clean personal branch проверены локально и через live remote. Root и три существующих CLI агента выполняли implementation, frozen contract map, independent regressions и review параллельно.
- Source/tests **4428be0e39bda8a2a47f1a6f184c92873da10976** обычным push сохранены в личной ветке. Runtime scope — один classic-RCT scenario DGP module, обе функции. Enabled pre не занимает scenario outcome/ID; actual-schema guard защищает поздний binary rename; disabled-oracle pre features сохраняются. Gamma pre conversion и unused pre-name policy сохранены. Numerical arithmetic, signatures, shared paths и CUPED/IV source не менялись.
- Новый91-case module: focused91passed/0warnings/4.37s, exact final-module baseline28failed/63passed/4.79s. Начальная fixture учитывала raw/contract treatment dtype неверно; до final runs исправлена явной treatment int8 normalization, остальные dtype comparisons strict. Final manifest сохраняет original precommit provenance и matching committed bytes восьми unchanged dependencies; full tests не повторялись ради HEAD metadata.
- Baseline-only contract100records; independent review116exact valid frame/dtype/schema/full metadata/RNG-state/next10 references,13rejects,40allowed/projection checks. Runtimewarnings0, issues []; existing frozen IV-docstring SyntaxWarning отдельно. Thirteen reviewed source/alias/test files связаны с committed bytes; окончательный test module independently reviewed.
- Local integration exact4428: **2487passed,1failed,0errors/skips,78warnings,109.60s**, total2488, exit1; scoped/full clean=false. Only прежний DiD GREEN/YELLOW failure. Fixture и вся пятифайловая B10 runtime closure unchanged; B13 path вне closure. Static linkage, новый cell-value probe не запускался. Assertions/thresholds/seven scope exclusions не ослаблены.
- CI **37607784481 completed/success** на exact4428; шесть downloaded selection/environment/JUnit sets проверены, **2488passed каждый**,0failures/errors/skips. SnapshotUTC2026-10-07T10:33:36.694587. ActualPython3.10.21latest/legacy,3.11.16,3.12.14,3.13.16,3.14.7. Seven sensitivity modules остаются deferred.
- Report BLOCK13_SCENARIO_NAMESPACE.md и отдельные contract/implementation/tests/review notes, runners/probes/manifests сохранены. Handoff103immutablelinksverified; NEXT_SESSION активен дляB13, B12 перемещён в historical checkpoint. Root checker проверяет scope/hashes, signatures/runtime AST, baseline/focused/JUnit, review, previous DiD closure, six CI payloads и portable report links.
- Source/tests frozen после4428. Final audit-only commit и ordinary push сохраняют checkpoint; remote/local equality и clean tree проверяются на завершении. СледующийB14 — mathematical numerical-zero DiD diagnostic/fixture/reference policy без blanket tolerance/clipping/threshold changes ради green status. Работа остановлена на границеB13; sensitivity/Sphinx/release/performance/upstream sync/PR/external messages не выполнялись.


**B14 завершён**: [BLOCK14_DID_NUMERICAL_ZERO.md](BLOCK14_DID_NUMERICAL_ZERO.md). Exact-constant OLS сохраняет математический ноль; undefined/invalid fitted-pre statistics требуют caution, tiny real effects не обнуляются. API fixture исправлен по дизайну с сохранением GREEN assertion/thresholds. Source4bdcff7; **51новых+5existingfocused56passed**, baseline28failed/28passed; independent32fullreferencepairs plusfinaldelta. **Local2539passed**,0failures/errors/skips,78warnings80.36s: [result](block14_integration_result.json). Все шесть CI jobs и actualartifacts **2539passed каждый**: [CI](block14_ci_result.json). 107immutablehandofflinksverified; no fullsensitivity/Sphinx/release/coverage/benchmarkclaim. Следующий B15 — Gaussian oracle numerical accuracy/compatibleadditiveAPI. Работа остановлена на границе B14; finalauditcheckpoint gitlog-1, ordinarypersonalpush/remoteequality+cleantree проверяются на завершении.


## 2026-10-07 — B15 завершён

- Source/tests9a57e91942a4b90b0401c0f8e3ebe6f5b4d82cdf ordinary pushed в personal branch. Root и3существующих CLI агента разделили implementation/contract/regressions/review. Два library paths и один новый79-case module. Additive opt-in Gaussian marginal propensity, old positional API/m/m_obs/observations/callbacks/RNG сохранены; supplied-U/ensure_all/calibration targets явно разделены.
- Finalfocus79passed,0warnings,6.99s; finalsame-filebaseline74failed/5passed,6.11s,planned API absence. Independentreference near-duplicate knots corrected within32ULP, finaltests rerun при сохранённых integrand/domain/error checks. Contract31privateqrefs+4invariances+8publicpairs; review112default/40additivepairs+34adaptiverefs,10projection/8failure-policy cases. Exact committed source/dependency linkage сохраняет initialprovenance, без повторения broadrefs.
- Local committed correctness integration2618passed,0failures/errors/skips,78warnings,179.77s,exit0. CI37628255646 completed/success наexact9a57: allsixdownloaded artifacts2618passed each. Actual Python3.10.21latest/3.10.22legacy,3.11.17,3.12.14,3.13.16,3.14.7. Actual selection/environment/JUnit/fullcaseIDs verified,7sensitivity exclusions прежние.
- Reports/runners/provenance/English handoff110links/NEXT_SESSION сохранены; finalsourceAST/additive scope/evidence validator и независимый CI review. Final audit-only commit/push и live remote/local equality+clean tree закрывают блок; audit-onlypush не запускает matrix.
- B15 обнаружил existing binary/IV Gaussian outcome errors до9.35percentagepoints logistic и40.66%relative clipped-exp на конкретныхstressconfigs. B16 исправляет binaryg0/g1 и IVpotentialmeans после Gaussian target/reference policy; compound shared-latent IV/Tweedie не заменять продуктом marginals. Остальной correctness backlog сохраняется послеB16. Sensitivity/SC08LOO/selected-U ATT/Sphinx/release/performance/upstreamsync/PR/externalmessages вне этого блока. На границе B15 остановиться.


## 2026-10-07 — B16 завершён локально

- Source/tests **1c91b0d39c8c12ac01d6a61c81d1bcd29c12b658**. Три library paths
  (новый Gaussian outcome helper +binary/IV integration), два новых test modules
  с121cases. Fixed GH21/GH31 outcome bias исправлен; independent Gaussian
  potential means и clipped exponential target, accuracy/failure/batching policy.
  Outcome oracle_nuisance использует тот же helper; num_quad остаётся для m.
- Baseline exact62publiccases37failed/25passed; finalfocus121passed0warnings5.17s.
  Neighbors1359passed2warnings14.11s. Probe96exact valid frame/schema/dtype/
  metadata/calibration/RNGpairs,140independentreferences; binaryabs4.44e-16,
  Gammarel1.59e-15. Rootreview, без subagents. StatefulIVcallbacks неэквивалентны:
  nonlinear potential means дают2calls вместо62; explicitmigration записан.
- **Local committed correctness2739passed**,0failures/errors/skips,78warnings,
  140.70s,exit0. Seven sensitivityexclusions unchanged. Finalvalidator проверяет
  scope/22unchangedmethods/7committedhashes/actualcaseIDs/provenance,issues[].
- **Push и CI не подтверждены**: git ls-remote/git push DNSfailure github.com.
  Escalation disabled; ограничения не обходились. Local tracking ref неliveproof.
  Нужны ordinarypersonalpush и sixLinuxCI/artifactverification в будущей
  network-enabledsession. Login/fork/envreinstall не повторялись.
- Primaryreport BLOCK16_BINARY_IV_OUTCOME_ACCURACY.md, probes/manifests/runners,
  EnglishDOCHANDOFF и NEXT_SESSION обновлены. Runtime source/tests frozen после1c91;
  finalaudit-onlycommit сохраняет локальные результаты. Temppytestdata удалены,
  rawJUnit/selection/result/evidence retained.
- Следующий B17 — Gaussian treatment propensity и jointshared-U IV/Tweedieaccuracy.
  Residualg_by_z errors≈0.073–0.075, m/Tweedie0.0935195. Jointtargets нельзя заменить
  productofmarginals. Затем learner/IF/normalizationbacklog. Sensitivity/selectedATT/
  Sphinx/release/performance остаются отдельно. На границеB16 остановиться.

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
