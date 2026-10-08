# Продолжение после очистки контекста

Проект Causalis, root через `git rev-parse --show-toplevel`; branch **`codex/correctness-roadmap`**. Текущий checkout macOS: `/Users/m.lenivkin/Documents/tclaude_folder/git-lab-projects/Causalis`. Base audit commit `ffe2c356c115f335b74b2f10117e19fe15585d46`. Windows paths ниже относятся к историческим сессиям.

## Что попросил пользователь

Создать свою рабочую ветку, вести исправления по приоритетному плану, делать commits между небольшими этапами. Разбить работу на крупные тематические блоки и останавливаться на их границах: пользователь будет очищать контекст. Подготовить отдельный файл для автора документации. **Sensitivity analysis отложено**, потому что upstream команда уже его переписывает.

## Читать сначала

1. `AGENTS.md` — локальная `.venv` обязательна. На текущем Mac использовать **`.venv/bin/python`**, Python3.12.14, не старый backing path `/Users/ioann/...`. Окружение восстановлено из project extras dev/docs, dependencycheck и5setupsmoketests прошли. Local setup manifest `.venv/setup-environment.json`; B09 integration manifest записывает реальные проверенные версии.
2. `audit/FIX_PLAN.md` — порядок блоков, scope gates и deferred findings.
3. Этот файл и **`audit/BLOCK27_INFERENCE_FAMILIES.md`** — последнее состояние; B27 завершён, final source/local/docs/CI/root gates проверены; audit checkpoint через gitlog-1. B09–B18 — исторические checkpoints. B01–B08 reports сохраняют исторические checkpoints; local Mac DiD failure объяснён в `audit/B09_LOCAL_INTEGRATION_NOTE.md`.
4. `audit/REPORT.md` — исторический аудит исходного SHA, не текущий residual bug count.

## Git

GitHub авторизация завершена пользователем и проверена: **MaximLenivkin**, keyring, scopes repo/workflow. Fork и tracking настроены; checkpoints B00–B06 сохраняются в `origin/codex/correctness-roadmap`. Актуальный checkpoint: `git log -1`; проверить remote tracking перед новым блоком. `origin`=`https://github.com/MaximLenivkin/Causalis.git`, `upstream`=`https://github.com/causalis-causalcraft/Causalis.git`. Upstream push прав нет; personal fork push/admin есть. Не повторять создание fork/rename remotes и не push в upstream/main.

Исторический Windows GitHubCLI2.102.0: `& 'C:\Program Files\GitHub CLI\gh.exe' ...` — использовать полный путь, если текущий Codex PATH ещё не обновлён. Авторизацию повторно запрашивать не требуется. Git mutations/network в ограниченной среде могут требовать разрешённого запуска; пользователь уже авторизовал commits/push в личную ветку. PR не создавался. Полная текущая информация — GIT_ACCESS.md.

## Текущая работа

## B27 — завершён: inference families (8 October 2026)

Final source `72f6918b1eb06b8bfd743397b2bf0bde6a8ef8a0`, baseline750354b;
initial implementationf718634, root lazy export correction72f6918.
[Report](BLOCK27_INFERENCE_FAMILIES.md). New `causalis.inference.InferenceFamily`
provides owned fixed iid effect families, linear contrasts, covariance, normal
Bonferroni or Gaussian multiplier max-t simultaneous absolute bands/tests.
Frozen aggregate results, shared rows/draws, empirical centering/ddof1 covariance,
plus-one finite-draw p-values and matching order-statistic bands. Nonfinite/
complex/shape/zero variance/underflow/seed/draw resolution guards. Generic input
requires valid joint observation-scale iid influences; assumptions are caller's
responsibility. `from_irm` supports only internal R1 iid unweighted clip ATE/ATTE,
current normalize_ipwFalse, unique stable nonmissing ordered IDs/same treatment.
No fit/predict/source cache mutation/RNG consumption. Different outcomes/features/
folds allowed; external/repeated/cluster/drop/weighted/relative/CATE/GATE rejected.
No finite-sample guarantee, arbitrary growing-p theorem, nuisance bias correction,
selection/identification certification, cluster/repeated or CATE inference.

107new cases, final793focuspassed/72warnings/39.36s; committed correctness
3981passed/157warnings/132.77s,0failures/errors/skips;7sensitivity exclusions
unchanged. Final strict standalone Sphinx0/18.183s. Initial f718634 docs warning
(package omitted from root __all__) failed both standalone and old docs test:
1failed3979passed initialintegration; preserved separately, fixed by72f6918 and
lazy-export regression. Development fixture5failures corrected separately.
All3874old case IDs retained;154existing library/scripts/workflowfiles byte-identical,
root functionASTunchanged,5non-auditpaths changed. Handoff158immutablelinks.
Exact owned focus/integration pytest-temp removed; synthetic fixtures only.
Final root --require-ci validation exit0/issues[]; raw local/initial/docs/CI evidence verified. Source/tests frozen after72f6918.

Ordinary source push750354b..72f6918 succeeded under user's persistent explicit
«Разрешаю пуш в нашу ветку». [CI37809518217](https://github.com/MaximLenivkin/Causalis/actions/runs/37809518217) completed/success on exact source;
all6artifacts3981passed plus strictdocs0. Full case sets/focus/source/env/normalized
argv/7exclusions and5hashes/job verified; Python3.10.22bothstacks,3.11.17,3.12.15,
3.13.16,3.14.8, snapshotUTC2026-10-08T16:37:07.010575+00:00.
[CI manifest](block27_ci_result.json), [root manifest](block27_validation_result.json),
issues[]. One CI run, no reruns. Final audit checkpoint via gitlog-1; ordinary
final audit push/live local-remote identity and clean tree checked at completion. No subagents/login/setup/fork/upstream/main/forcepush/PR/
release/notebooks/website/external messages. NextB28weak-IVLATE only after B27
completion, context cleanup and a new request. Sensitivity/SC08LOO/selected-UATT/
multi-IVrepetitions/grouping/few-multiwayclusters/NumPyRSTdebt remain separate.


## Historical B26 checkpoint — завершён: held-out nuisance/CATE validation (8 October 2026)

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



## Historical B25 checkpoint — завершён: DR/R CATE (8 October 2026)

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


## Historical B24 checkpoint — завершён: external OOF binary IRM (8 October 2026)

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

## Historical B23 checkpoint — one-way cluster binary IRM (8 October 2026)

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

## Historical B22 checkpoint

**B22 завершён — repeated binary IRM ATE/ATTE**, 8 October2026.
Source `ede6deda2eb82c518ed3d7f5b48780d39cdfe5f0`, baseline `357e16e`.
[Report](BLOCK22_REPEATED_CROSSFIT.md). Binary IRM existing n_rep supports
ATE/ATTE repetitions via single-partition children. Scalar median-variance SE
(no M/sqrtM divisor), recorded prefix-stable local split seeds, original first
integer seed, learner RNG settings preserved. Relative effects separately
aggregate; any undefined repetition makes aggregate relative inference NaN.
RepeatedCausalEstimate contains detached repetition results/seeds, primary
diagnostic_data=None; no fabricated single nuisance or aggregate IF. Parent
scalar inference accessors aggregate; folds_repetitions_ (n,M) only with
diagnostics. Repetitions sequential; n_jobs is within-partition parallelism.
M>1 drop/fixed single-partition folds/GATE/GATET/CATE/sensitivity aggregation
reject. Multi-treatment/IV repetition remains a separate follow-up. Strict
positive integer n_rep validation replaces lossy float/string/bool coercion.
Single-partition numbers unchanged:16exactfits/24exactestimates/8same weighted
ATTE rejections. New67cases; focused221passed/29warnings/22.51s. Committed
correctness3434passed/zero failures/errors/skips/116warnings/115.66s, seven
sensitivity exclusions unchanged. Strict standalone docs exit0/17.307s on
ede6ded. Seeded synthetic MC200x600, R3: bothATE/ATTE coverage.965; meanSE/SD
1.0061/1.0266, favorableDGP only, MCSEabout.015. No general coverage guarantee.
Root verifier validates source/AST/provenance/cases/docs; issues[]. Source/tests
frozen afterede6ded; only audit files change. Handoff136 URLs verified locally;
implementation pushed to the personal branch. Owned probe copies/integration
pytest-temp removed; JUnits and code/test metadata remain. No sub-agents.

Пользователь явно подтвердил: «Разрешаю пуш в нашу ветку».
Разрешение на обычный push в MaximLenivkin/Causalis:codex/correctness-roadmap
сохраняется для завершённых блоков; повторно не спрашивать. Прежние отказы
автопроверки разрешены этим новым явным пользовательским сообщением.
Sourceede6ded и evidence d99ea8f pushed. **CI37751321348 completed/success** on
`d99ea8ffea853e48f750ca642a3918769cc38004`: all6artifacts3434passed each and strict standalone docs exit0.
CI head is audit commitd99ea8f; implementation/local test sourceede6ded.
Gitdiffede6..d99 contains audit files only; all executable source bytes match.
Do not claim CI ran directly onede6ded. Full case sets, focused221/new67,
selection/normalizedargv/sevenexclusions, source/dependencies and all5artifact
hashes/job verified. SnapshotUTC2026-10-08T08:44:54.121787+00:00. ActualPython
3.10.22bothstacks,3.11.16,3.12.15,3.13.15,3.14.8. Root verify_block22.py
--require-ci validates sourceequivalence/allrawartifacts/hashes/cases,43unchanged
IRM methodASTs and unchanged sensitivity bodies minus2newentryguards; issues[].
Only audit updates aftersource. Finalcommit via gitlog-1; ordinarypersonalpush,
livelocal/remoteequality andclean tree checked atcompletion. NoPR/release/upstream.
GH /Users/m.lenivkin/.local/bin/gh, repoMaximLenivkin/Causalis. No newlogin,
fork/environmentsetup, sub-agents or unnecessary local suite reruns.

Historical B22 next-step note: group-aware binary IRM was selected for B23;
it is now complete. Read the B23 handoff above for the current next step.

## Historical B21 checkpoint

**B21 завершён — standalone Sphinx gate**, 8 October 2026.
Source `1780d8c715a15182137d51313e502280d6982dd9`, baseline `2db4802`.
[Report](BLOCK21_SPHINX_GATE.md). Eight generator regressions (baseline 7 failed /
1 passed), focused docs 11 passed. Same 144 HTML pages / 1296 inventory records;
ignored editable-install `_version.py` matched on both comparison sides.
All library bytes and seven sensitivity exclusions unchanged. Actual entrypoint
is `scripts/generate_api_reference.py`, no `docs/` tree. Generator always uses
`-W --keep-going`; --check builds in disposable dirs without publication.
Default publishing retains its path; --output-dir replaces a dedicated output.
Package-source overlap rejected; publication exception restores prior output.
No concurrency/crash durability claim. Returned HTML is not regenerated here.
Root-only __all__, actual prior MyST docstring rendering now explicit. Broad
__all__ probe failed; RST probe had 29 warnings / 25 docutils errors. NumPy/RST
migration is separate documentation debt, not certified by this gate. No warning
suppression and no sensitivity source/docstring edits.
Standalone evidence runner ignores SKIP_DOCS_BUILD; pytest build cases can skip
explicitly or without optional deps. Local committed check exit 0; correctness
with docs enabled: 3367 passed, zero failures/errors/skips, 91 warnings / 115.39s.
Six CI jobs and release workflow now require standalone check and upload logs,
source/environment/command/results/hashes. Release full sensitivity gate intact.
CI37740334131 completed/success on exact1780d8c: six artifacts each3367passed
and standalone Sphinx exit0. Full case sets, normalized args, seven exclusions,
docs source/environment/log hashes verified. SnapshotUTC2026-10-08T07:00:19.131486+00:00.
Actual Python3.10.21 both stacks,3.11.16,3.12.15,3.13.15,3.14.8. Root verifier
checks six source paths/hashes, zero library changes, local/baseline/focus/CI
cases and docs evidence; issues[]. Final checkpoint via gitlog-1, ordinary
personal push/live localremote equality and clean tree checked at completion.
Handoff132 immutable links checked, issues[]. Only audit edits after source.
No notebooks, website publishing, release or upstream merge. No new dependency
install/setup, login, fork or sub-agents used.

Next B22: repeated cross-fitting. Begin with explicit public API, split/RNG,
repetition aggregation and inference contracts before implementation. Then group
cross-fitting, external OOF, DR/R-CATE. Sensitivity, SC08 LOO and selected-U ATT
remain deferred. Stop at B21; B22 requires a new user request/context cleanup.
Do not repeat login/fork/environment setup or old broad suites without changes.

## Historical B20 checkpoint

**B20 завершён** 7 October2026.
Source `28acf6b4fea588ee682251a35a5f23a8757f4415`, baseline `98d5478`.
[Report](BLOCK20_DATA_SNAPSHOT_CONTRACTS.md). Exact numeric/object duplicate
policy explicitly replaces B06's separate categories. Numeric-looking strings
and large-integer rounding cannot establish equality. Returned binary/multi/IV
primary diagnostic fields are copied; private model links remain live.
Successful fits freeze role labels with sample arrays. Binary/multi stage fits:
failure retains previous complete fit/data reference, success clears primary
inference until estimate(). IV retains failed-refit→unfitted. Caller parameter
mutations, shared learner/callback effects and sensitivity scalar-state contracts
are not rolled back/certified. Model attrs/contracts/config/lazy CATE/groups
remain mutable. No new ownership/view/performance optimization introduced.
Final107baseline86failed/21passed, focus2106passed/15warnings/31.36s;
20exactfit/36exactinference pairs,132unchangedexecutablefunctionASTs,8hashes.
Committed correctness3359passed,0failures/errors/skips,91warnings/115.72s;
seven sensitivity exclusions unchanged. Source/tests frozen after28acf6b.
Personal source push completed; CI37665898544 completed/success on exact28acf6b:
all6artifacts3359passed each. FullcaseIDs/2106focus/source/normalizedargv and
seven exclusions verified; snapshotUTC2026-10-07T18:23:05.139669+00:00.
ActualPython3.10.21latest/3.10.22legacy,3.11.16,3.12.15,3.13.16,3.14.7;
complete dependency/source evidence in block20_ci_result.json.
Handoff127immutablelinksverified,issues[]. Root verifier checks8source/testpaths,8hashes,132unchangedexecutablefunctions,
originalbaseline/probeprovenance and alllocal/CIcaseIDs/artifacthashes,issues[].
Supplementary8exactroundedfingerprintcollisions accepted (not added to pytest
counts). Only audit updates aftersource; finalcheckpoint via gitlog-1. Owned
worktrees/pytesttemp removed. Ordinaryfinalpush/liveequality andcleanstate
checked at completion. No PR/release/upstream merge.

Next standalone B21: dedicated standalone Sphinx build/documentation
compatibility gate. Then repeatedCF→groupCF→externalOOF→DR/R-CATE features.
Sensitivity, SC08LOO and selected-UATT deferred. Stop at B20; B21 requires a
new user request. Do not repeat login/fork/environment setup.

## Historical B19 checkpoint

**B19 завершён** 7 октября2026: extreme finite score/IF and normalized custom ATE.
Source `1993cf1040e21630844688e415ef2cf15598ffc3`, baseline `52cd6e2`.
[Report](BLOCK19_EXTREME_SCORE_ARITHMETIC.md). Explicit numerical failure in
score/IPW, moment/IF/SE/Wald and relative-effect arithmetic; finite float64
intermediates required. No stable algorithm for every extreme finite scale:
mathematically representable answers may still fail on intermediate overflow.
Custom normalized ATE w/w_bar finite required (ValueError); >1e-12 retained
mean floor, signed weights, normalization formulas and approximate IF/SE
warning policy preserved. RuntimeError for numerical score/inference failure.
IRM core cache moved after relative calculation; no general state ownership
or refit lifecycle redesign. Sensitivity/diagnostic algorithms unchanged.
Final67baseline54failed/13passed, focus527passed/13policywarnings/30.07s;
40exactfit/72exactinference pairs,129unchangedfunctionASTs,10hashes. Committed
correctness3252passed/zero failures/errors/skips/91warnings/108.72s. Seven
sensitivity exclusions unchanged. Source/tests frozen; personal push completed.
CI37663336817 completed/success on exact1993cf1, all6artifacts3252passed each.
FullcaseIDs/527focus/source/actualargv/7exclusions verified; snapshotUTC
2026-10-07T18:03:31.493318+00:00. ActualPython3.10.22latest/3.10.21legacy,
3.11.16,3.12.15,3.13.16,3.14.8; exact dependencies in block19_ci_result.json.
Root verifier checks6changedsource/testpaths,10hashes,129unchangedfunctions,
exact IV formula extraction and all baseline/local/CI manifests,issues[].
Handoff123immutablelinksverified,issues[]. Only audit updates aftersource;
final checkpoint via gitlog-1. Ordinary final push/live localremote equality
and clean state checked at completion. Owned worktree/pytest-temp removed.
No PR/release/upstream merge.

Next standalone B20: duplicate numeric/object columns and snapshot/refit
contracts. Establish public reproductions and ownership/compatibility policy
before changes. Standalone Sphinx is a later separate gate. Features follow
correctness: repeatedCF→groupCF→externalOOF→DR/R-CATE. Sensitivity, SC08LOO and
selected-UATT deferred. Stop at B19; next block requires a new user request.
Do not repeat login/fork/environment setup.

## Historical B18 checkpoint

**B18 завершён** 7 октября2026: learner shape/real and IV storage contracts.
Source checkpoint `df944e0ee814dbe1a631b41ba1b59def9f61ed8b`, baseline `b7cbec9`.
Report [BLOCK18_LEARNER_OUTPUT_CONTRACTS.md](BLOCK18_LEARNER_OUTPUT_CONTRACTS.md).
Shared real/finite validation before casting, class selection, clipping or
assignment. Predict accepts (n,) / (n,1); binary probabilities also (n,2).
Complex outputs, including zero imaginary and object-complex, scalar/row/wrong
row-count/tensor outputs fail explicitly. Real float-convertible objects/strings
preserved. Probability classes metadata must match columns; multiclass labels
must be distinct. Existing single-class/reversed-class/direct-vector adapters
and probability warning/clipping/normalization policies are retained.

IV fold validation precedes float assignment; raw assembly validation precedes
propensity clipping; fit validates all6 exact(n,) arrays before storing even if
cross-fit is bypassed. Failed refits leave model unfitted and old estimates usable.
Prediction dictionary order preserved. No ownership/snapshot policy changes.
Final356-case baseline267failed/89passed, finalfocus460passed (356new+104existing),
0failures/errors/skips/warnings. Probe20exactfitpairs/36exactinferencepairs,
125unchangedfunctions ASTchecked; original precommitHEAD/time retained.
Source/tests frozen after df944e0; push completed. Committed correctness
integration3185passed/0failures/errors/skips,82warnings,132.54s,exit0. Seven
sensitivity exclusions unchanged; four warnings are local joblib/loky cleanup
reentrancy. CI37653023359 completed/success on exactdf944e0: six artifacts each
3185passed, completecaseIDs/all460focus/source/actualargv/7exclusions verified.
SnapshotUTC2026-10-07T16:38:17.205058+00:00. ActualPython3.10.22latest/3.10.21legacy,
3.11.16,3.12.15,3.13.15,3.14.7; full environments in block18_ci_result.json.
verify_block18.py checks7changedsource/testpaths,10hashes,125unchangedfunctions,
allJUnits/CIartifacthashes and provenance,issues[]. Handoff118immutablelinksverified.
Only audit updates after source; final gitcheckpoint via gitlog-1. Ordinary
personal push/live equality/clean tree are checked at completion. No PR/release.

Next standalone **B19: extreme finite score/IF arithmetic and normalized custom
ATE near-boundary policy**. Reproduce via public fits/estimates, establish target,
normalization and independent stable calculation or failure policy; no blanket
nan_to_num or score clipping. Later duplicate/snapshot/refit and standaloneSphinx
compatibility gates, then repeatedCF→groupCF→externalOOF→DR/R-CATE features.
Sensitivity/SC08LOO/selected-UATT remain deferred. **Stop at B18; B19 requires the
next user request after context cleanup.** Do not repeat login/fork/env setup.

## Historical B17 checkpoint

**B17 завершён** 7 октября2026.
Source checkpoint `e2fced5f476a8567bee2cc0bbda062ad62124eae`, baseline `aaeadd8`.
Report [BLOCK17_GAUSSIAN_PROPENSITY_JOINT_MEANS.md](BLOCK17_GAUSSIAN_PROPENSITY_JOINT_MEANS.md).
Binary m/oracle propensity and IV r use unchanged B16 adaptive logistic helper;
IV nonlinear shared-U g and Tweedie joint means use new bounded32-row adaptive
product helper. Continuous IV g uses exact base+tau*r identity. Fixed-GH stress
errors removed. `num_quad` now compatibility-only, converts to positiveint;
callbacks deterministic functions of X required. IV callback counts reduced;
observed data/RNG exact only for deterministic callbacks. Derived IV firststage,
reducedform and LATE can change; zero-strength arithmetic unchanged.

Public final57baseline45failed/12passed, focused90passed. Neighbors1449passed
precede final reference tolerance refinement; library bytes final. Probe180exact
frame/schema/calibration/RNGpairs across90configs,52independent jointrefs:
maxbinaryabs1.67e-16/maxgammarel9.82e-11. Estimates not rigorous/rare-relative
certificates. Unresolvable transitions/convergence failures ValueError; failed
binary generation does not roll back RNG/callbacks, including oracleoff path.
Scoped committed correctness integration **2829passed**,0failures/errors/skips,
78warnings,90.21s,exit0; seven sensitivity exclusions unchanged. B16helper/shared
DGP/multi bytes and21other binary/IV methods preserved. No performance guarantee.

Push including pending B16 commits succeeded through permitted escalation.
CI run37647196147 completed/success on exacte2fced5: all6jobs/artifacts
2829passed each; full case sets/all90new cases/actualargv/source/7exclusions
verified. Snapshot UTC2026-10-07T15:53:57.979587+00:00. ActualPython
3.10.21latest/3.10.22legacy,3.11.17,3.12.15,3.13.15,3.14.8. Full dependency
environments in block17_ci_result.json. verify_block17.py confirms5changed
source/testpaths,21unchangedmethods,8committedhashes,allJUnits/CIartifacthashes,
originalprobeprovenance,issues[]. Source/tests frozen aftere2fced5; only audit
changes after. Ordinary final auditpush/live localremote equality+cleanstatus
checked at completion. Historical B16 exact1c91 CI was not separately run.
Do not repeat login/fork/environment setup or old full suites without changes.

Next standalone **B18: learner shape/real/complex and IV assembled-storage
contracts**. Read FIX_PLAN residual priority3, reproduce malformed row/column
and complex predictions with real public fits before fixing; preserve valid
finite behavior and single-class probability mapping. Then extreme finite
score/IF, normalizedcustomATE, duplicate/snapshot/refit/Sphinx backlog; features
repeatedCF→groupCF→externalOOF→DR/R-CATE later. Sensitivity/SC08LOO/selected-U ATT
remain deferred. **Stop at B17; B18 requires next user request/context cleanup.**

## Historical B16 checkpoint

**B16 завершён локально** 7 октября2026; remote/CI verification ожидает network-enabled session. Local checkpoint
`1c91b0d39c8c12ac01d6a61c81d1bcd29c12b658`, baseline `e8459e1`.
Primary report [BLOCK16_BINARY_IV_OUTCOME_ACCURACY.md](BLOCK16_BINARY_IV_OUTCOME_ACCURACY.md).
Новый deterministic Gaussian outcome helper, binary g0/g1 и IV g_d0/g_d1/cate,
nonlinear oracle_nuisance outcome-callables. Independent Gaussian potential
means; clipped exponential target сохранён. num_quad теперь только treatment
GH propensity. Нелинейные IV outcome callbacks вызываются дважды вместо62;
compatibility/RNG evidence только для deterministic functions of X.
Continuous и zero-strength paths сохранены. Multi, binary m, IV shared-U
r/g_by_z, Tweedie и sensitivity sources не менялись.

Focused121passed; identical62publicbaseline37failed/25passed; neighbors
1359passed/2existingwarnings. Probe96exact valid frame/schema/metadata/RNGpairs,
140adaptive references, maxbinaryabs4.44e-16/maxgammarel1.59e-15. Manifests
содержат реальные source/test hashes и original precommit HEAD/time;
committed linkage проверяет verify_block16.py. Local committed correctness integration **2739passed**,0failures/errors/skips,
78warnings,140.70s,exit0. Семь прежних sensitivity exclusions сохранены.
Source/tests frozen после1c91; root validator проверил22unchangedmethods,
7committedsource/test/dependency hashes и actualbaseline/focus/integrationcaseIDs,
issues[]. Итоги в block16_integration_result.json и block16_validation_result.json.

**Исторически в B16 push/CI не подтверждены; B17 subsequently pushed these commits.** git ls-remote и git push получают
`Could not resolve host: github.com` в этой session. Escalation отключена,
обход ограничений не разрешён. Local origin tracking ref — historical cache,
не live remote equality. Не повторять login/fork/env setup. Следующая сессия
с network access должна обычным push отправить local commits в
origin/codex/correctness-roadmap и проверить6CIjobs/artifacts для exact1c91.

Следующий самостоятельный **B17: Gaussian propensity и compound shared-U
means**. Concrete evidence в block16_probe_result.json: IV joint g_by_z
errors≈0.073–0.075; binary m и Tweedie GH21 errors0.0935195 на stressconfiguration.
Сначала target/law, independent joint Gaussian references, bounded-memory
accuracy/failure и callback policy. Joint integrals не заменять product of
marginals. Затем learner shape/real/IVstorage/extremeIF/normalizedATE backlog.
Sensitivity, selected-U ATT, SC08LOO, Sphinx/release остаются отдельно.
**Остановиться на границе B16. B17 начинается новым запросом пользователя.**

## Исторический B15 checkpoint

**B15 завершён** 7 октября2026 (Europe/Moscow). Source/test checkpoint **`9a57e91942a4b90b0401c0f8e3ebe6f5b4d82cdf`**, обычный personal push выполнен; final audit checkpoint — `git log -1`. Baseline **`71f6a619b04e0ab8fab388fb95b7d0f3d6631b96`**. Изменены ровно два library paths: `causalis/dgp/multicausaldata/base.py`, `functional.py`; добавлен `tests/data/test_multicausal_marginal_propensity.py`, 79cases. Root и три существующих CLI агента проверили contract, regressions, compatibility/review и CI.

Новая append-only опция `include_marginal_propensity=False` принимает bool/NumPy bool, требует `include_oracle=True` и добавляет K `m_marginal_<arm>` после всех старых колонок. Старые positional arguments сохранены. Enabled output names и поздние callback mutations проверяются; disabled marginal-like names допустимы. MultiCausalData analysis projection исключает oracles и сохраняет feature policy. Default executable AST обоих library modules после удаления только additive API/branches совпадает с baseline.

Target q_k(X)=E[softmax_k(a(X)+bZ)], Z~N(0,1) independent, a уже содержит прежнюю calibration. Existing m=softmax(a), m_obs=softmax(a+bU) и RNG сохранены. Supplied U не меняет Gaussian reference law. ensure_all q остаётся nominal model quantity, не точной propensity repaired sample. target_d_rate остаётся sample-X/U=0 calibration. Functional wrapper пока имеет zero latent slopes и q=m; нет selected-U ATT API.

Equal slopes дают exact m. Иначе quad_vec интегрирует distinct score rows на[-12,12] с pairwise-crossing neighborhoods, max-norm estimated epsabs1e-10/epsrel0, budget4096, bounded memory O(nK+K²+LK). Omitted Gaussian mass3.553e-33. Nonconvergence/unsupported float geometry/budget дают opt-in ValueError; estimated error не rigorous universal certificate и не rare-probability relative bound. Нет дополнительных RNG draws; failed generation после sampling не откатывает RNG/callbacks.

Final focused **79passed**,0failures/errors/skips/warnings,6.99s. Exact same final file на baseline **74failed/5passed**,0errors/skips/warnings,6.11s. Все74 failures — отсутствие нового API (67unknown-keyword TypeErrors,7missing-field AttributeErrors), не74старых numericalbugs. Initial78pass/1failure — independent reference knots separated by fewULPs; knots coalesced32ULP с прежними integrand/domain/tolerance/error checks, final baseline/focus rerun на одинаковом final SHA.

Independent contract:31private q references,4invariances,8public old/current exact frame/RNG pairs; maxabs3.89e-16. GH32/GH64 agreement показан как ложный convergence certificate в2examples. Frozen full multi/binary/IV graph и actual shared helper closure pinned; wrapper hash в этом probe read-only, wrapper runtime проверен tests/review. Independent review:112default+40additive exact full frame/schema/dtype/metadata/callback/RNG pairs,34adaptive q references до slopes1e6, maxabs2.78e-16;10projectioncases,8failure-policycases. Нет material open findings. Два inherited softmax overflow warnings и inherited large-K pandas fragmentation warnings явно классифицированы.

**Local committed correctness suite:2618passed**,0failures/errors/skips,78warnings,179.77s,exit0. **CI37628255646 completed/success**: все6downloaded artifact sets дают2618passed каждый; source/full case sets/all79new cases/7exclusions/actualargv verified. Snapshot UTC2026-10-07T13:29:16.809213. ActualPython **3.10.21latest /3.10.22legacy,3.11.17,3.12.14,3.13.16,3.14.7**; не копировать предыдущие patchversions. Full dependency environment из `block15_ci_result.json` authoritative. Семь sensitivity modules deferred; full sensitivity/standalone Sphinx/release/performance не validated.

Primary report `BLOCK15_GAUSSIAN_ORACLE.md`, B15_ORACLE_CONTRACT/IMPLEMENTATION/TESTS/REVIEW notes, reproducible probes/runners/manifests. Source hashes c46c1e…/e3b074… и finaltest3e6ade… связаны с9a57,11unique source/test/dependency paths verified; original precommit HEAD/time preserved без broad rerun. `verify_block15.py` проверил scope/defaultAST/actualJUnits/provenance/allCIpayloads/independent CI review с actual artifact hashes;8PythonAST/24relative links,issues[]. English handoff добавляет3immutable links; **110links verified**. Source/tests frozen после9a57; только audit changes до final commit/push. Final live remote/local equality+clean tree проверяются на завершении.

Следующий самостоятельный **B16 — binary/IV marginal outcome numerical accuracy**. B15 подтвердил existing fixed-GH21/GH31 errors: logistic a=-5,s50 reference .4601982453 vs binaryg0 .3666787193 /IVpotentialmean .3898474050; clipped-exp binarya-25,s10relativeerr40.66%, IVa0,s10relativeerr13.81%. Источники неизменны в B15, actual configs в `block15_contract_result.json`. Начальный scope binaryg0/g1 и IV `_potential_outcome_means`: Gaussian target, independent adaptive reference, failure/accuracy policy, observed draws/RNG compatibility. Compound `_g_by_z`, `_r_by_z`, Tweedie joint-latent targets нужно рассмотреть отдельно: product of marginals не заменяет shared-U integral. Existing multi outcome methods измерены и согласуются с reference; не менять без нового finding.

После B16 — learner shape/real/complex/IVstorage, extreme finite score/IF, normalizedcustomATE, duplicate/snapshot/refit/Sphinx gates; затем repeatedCF→groupCF→externalOOF→DR/R-CATE. Sensitivity/SC08LOO и selected-U ATT остаются отдельными задачами. **Остановиться на границе B15; B16 начинается новым запросом пользователя.**

Окружение: `.venv/bin/python`3.12.14macOSarm64; GitHubCLI `/Users/m.lenivkin/.local/bin/gh`, всегда `--repo MaximLenivkin/Causalis`. Existing login/fork/remotes/branch использованы; envreinstall/upstreamsync/PR/release не нужны. Personal branch commits/push authorized earlier; live environment проверить перед новым блоком. Исторические tools/env не являются фактами будущей сессии.

## Исторический B14 checkpoint

**B14 завершён** 7 октября 2026 (Moscow). Source/test checkpoint **`4bdcff7d6388d1d72d5be4a546e8abb2a67a767c`**, ordinary personal push выполнен; final audit checkpoint определяется git log-1. Baseline **`dbded76ecf8a207aad2094903b8f015fed8ae5d6`**. Изменены ровно два library paths: `causalis/scenarios/did/model.py` и `causalis/scenarios/did/refutation/post_inference.py`; 51-case новый public test module и fixture существующих fiveAPItests.

Exact constant control response при actual solver fullrank и unit intercept получает unique analytic OLS β=(c,0,…), без tolerance. Nearconstant/nonconstant/deficient-rank/no-intercept fits прежние. Positive finite SE всегда даёт actual signed ATT/SE, tiny real effects сохраняются. Zero/invalid SE и nonfinite ATT дают NaN; overflow остаётся signed infinity. Все fitted pre cells должны иметь finite t для GREEN, invalid/cached missing-input cells не исчезают. Exact ATT=SE=0 retains legacy p1 convention, но studentization undefined/YELLOW; nonzero zero-SE effects дают NaN p. Fully zero-SE bootstrap keeps NaN simultaneous critical/bands without all-NaN reduction warnings; draws unchanged.

Frozen original six-unit fixture теперь имеет exact preATT/IF/SE0 и **обоснованный YELLOW**, а не rounding-driven huge t. Original GREEN assertion intentionally reproduced as failure на frozen baseline и candidate в отдельном contractprobe; не считать это remaining regression. API successfixture теперь36units/12controls/6cross-cohortclusters/seeded independentnoise, все прежние asserts/thresholds/modelreportargs сохранены, добавлены positive finite preSE assertions. Это numerical/reference policy и correction дизайна теста, а не green-by-threshold workaround.

Final focused: **56passed**,0failures/errors/skips/warnings,5.96s (51new+5existing). Same finalfiles/exactbaseline: **28failed/28passed**,0errors/skips,4oldoverflowwarnings,5.17s; allfive revisedAPI tests passbaseline. Source/class/public/plot bindings, finaltestSHA и exact56collection checked. PrecommitHEAD/time сохранены,4source/test+5dependencies linked exactGitbytes без rerun. Rootcommittedprovenance covers12unique paths.

Independent contract:11OLSrefs,14arithmeticpairs eachversion,7mixedinvalidconfigs andcachedpayload/zero-bootstrap boundaries; actualfive-pathclosure andloadedhashes pinned. Independent review:16configs×2estimatecalls=32old/currentfullreferencepairs (64evaluations), exacttables/dtypes/metadata/diagnostics/reports/RNGstates/next10;27unchangedOLS/7analytic/28studentization/9pvaluecases. Two finalguards have exactinverse-byte link to full-reference hashes plus15mixed-report/fourbootstrap delta proof; originaltimestamps/hashes preserved, broad refs not repeated. No open material findings.

**Local exact4bdc scoped integration:2539passed,0failures/errors/skips,78warnings,80.36s**,exit0. Seven named sensitivity modules remain excluded unchanged. Full sensitivity/release/Sphinx/coverage/benchmark notvalidated. Preliminary151neighbors preceded finaltwo guards and lack instrumentedruntimehashes; finalintegration validatesfinalbytes.

**CI37611862809 completed/success** onexact4bdc; six downloaded selection/result/JUnit sets **2539passed each**,0failures/errors/skips, all56focused caseIDs/source/exclusions verified. SnapshotUTC2026-10-07T11:10:36.429091. **ActualPython3.10.22 latest/legacy,3.11.17,3.12.14,3.13.15,3.14.7**; do not copyB13versions (3.10.21/3.11.16/3.13.16). Per-jobenvironment JSON authoritative. IndependentCIreview separately recorded; audit-onlypush doesnotrerunmatrix.

Primaryreport `BLOCK14_DID_NUMERICAL_ZERO.md`, B14_DID_CONTRACT/IMPLEMENTATION/TESTS/REVIEW notes and reproducible probes/runners/manifests. `verify_block14.py` verifiesexactscope/runtimeAST/retainedassertions/frozenfocusedJUnits/sourcehashes/references/provenance/allCIpayloads. English DOCUMENTATION_HANDOFF addsfour immutablelinks, **107 links verified**, noexternalmessage. Source/tests frozen после4bdc. Final validator прошёл:10PythonAST,20relative links, original baseline/focus/localJUnits, committed provenance, independent CI review и все six downloaded artifacts; issues[]. Final audit commit/ordinary push и live remote/local equality+cleanstatus проверяются на завершении.

Следующий самостоятельный **B15**: Gaussian marginal-oracle numerical accuracy и compatible additive API по B07_DGP_REVIEW.md/FIX_PLAN. Сначала target/law/independent adaptive reference, accuracy/convergence/boundedmemory policy. Existing m/m_obs/RNG semantics сохранить; supplied-U law и latent-selected ATT не подменять treated mean marginal CATE. Затем learner shape/real/IVstorage contracts, extreme finite scores/IF, normalized customATE, duplicate/snapshot/Sphinx gates. Features repeatedCF→groupCF→externalOOF→DR/R-CATE aftercorrectness. **Sensitivity/SC08LOO deferred** untilseparateupstreamsync/review. **Остановиться на границе B14; B15 начинается новым запросом.**

Окружение прежнее: `.venv/bin/python`3.12.14macOSarm64; `/Users/m.lenivkin/.local/bin/gh` with `--repo MaximLenivkin/Causalis`. Login/fork/envreinstall/upstreamsync/PR/release не нужны. Personalbranchcommits/push authorized earlier. Final livegitstate checkmandatory, earlieragents/toolinstallations arenotfactsaboutfutureenvironment.

## Исторический B13 checkpoint

**B13 завершён** 7 октября 2026 (Moscow). Source/tests checkpoint: **`4428be0e39bda8a2a47f1a6f184c92873da10976`**, обычный push в личную ветку выполнен. Изменён один library path `causalis/scenarios/classic_rct/dgp.py`, оба *_26 helpers; новый `tests/data/test_scenario_namespace_contract.py`, 91 cases. Root и три существующих CLI агента независимо проверили baseline contract, regressions, valid reference/RNG и CI artifacts.

Enabled pre-name не может занять scenario outcome или `user_id`, поскольку classic scenario всегда имеет ID даже при ancillary=False. Actual-schema guard перед `y → conversion` защищает позднее переименование. Numeric pre-поля с именами отключённых binary oracles сохраняются features. Gamma pre-name `conversion` валиден; unused pre-name при add_pre=False игнорируется. Public signatures, sampling, calibration, assignment, ID algorithms и numerical formulas сохранены; shared DGP, CUPED/IV, contracts и inference source не менялись. Early check отвечает только за string role collisions; invalid/empty enabled names по-прежнему проверяет underlying B12 wrapper.

Verification: **91 passed**, 0 failures/errors/skips/warnings, 4.37 s; тот же final module на exact baseline9f0 — **28 failed / 63 passed**, 0 errors/skips, 4.79 s. Six public aliases, shared/class bindings, unchanged eight dependency/control modules, exact collection/test SHA и committed-byte linkage verified. Focused был precommit; original process HEAD/time сохранены. Baseline-only contract — 100 records. Review — **116 exact frame/dtype/schema/contract-metadata/all-created-RNG-state/next10 comparisons** (92 classic, 16 CUPED, 8 IV), 13 rejection и 40 allowed/projection probes; runtime warnings0, issues []. Existing frozen IV-docstring SyntaxWarning отдельно. Thirteen referenced source/alias/test files связаны с exact4428 bytes; no repeat broad run ради metadata.

Local Mac integration exact4428: **2487 passed, 1 failed, 0 errors/skips, 78 warnings, 109.60 s**, total2488, exit1. Это не clean local/full suite. Только прежний DiD GREEN/YELLOW numerical-zero failure. Fixture и пятифайловая B10 runtime closure byte-identical; изменённый scenario path вне closure. B13 использует static linkage к прежнему runtime proof, новый cell-value probe не запускался. Assert, thresholds и семь scope exclusions не ослаблены.

CI [37607784481](https://github.com/MaximLenivkin/Causalis/actions/runs/37607784481) **completed/success** на exact4428: все шесть downloaded artifact sets — **2488 passed каждый**, 0 failures/errors/skips; matrix_verified=true, issues []. Snapshot UTC2026-10-07T10:33:36.694587. Actual Python: 3.10.21 latest/legacy, 3.11.16, 3.12.14, **3.13.16**, 3.14.7. Не копировать прежнюю3.13.15 из B12. Семь sensitivity modules deferred; full sensitivity, standalone Sphinx, release и новый benchmark не validated.

Reports: BLOCK13_SCENARIO_NAMESPACE.md, B13_SCENARIO_CONTRACT/IMPLEMENTATION/TESTS/REVIEW.md, reproducible probes/runners/manifests. English handoff содержит готовые migration paragraphs и **103 verified immutable links**; внешние сообщения не отправлялись. `verify_block13.py` проверяет source/test scope/hashes, AST, baseline/focused/JUnit, review, previous DiD closure и все CI payloads. Source/tests frozen после4428, final audit checkpoint определяется git log-1; final ordinary push и remote/local equality + clean tree проверяются на завершении.

Следующий самостоятельный **B14**: mathematical/numerical-zero DiD diagnostic и fixture/reference policy. Existing exact trigger — test_post_inference_report_accepts_panel_and_estimate, truly zero pre-effect/variance, tiny floating residue leads to огромному |t|. Требуется независимый математический/численный reference, без blanket tolerance, clipping, увеличения thresholds или weakening assertion ради green suite. Затем Gaussian oracle numerical accuracy/API и прежний correctness backlog по FIX_PLAN. Sensitivity/SC08LOO deferred. **Остановиться на границе B13; B14 начинается новым запросом пользователя.**

Окружение прежнее: repo-local `.venv/bin/python`3.12.14 macOS arm64; `/Users/m.lenivkin/.local/bin/gh` с `--repo MaximLenivkin/Causalis`. Login, fork setup, env reinstall, upstream sync, PR и release не нужны для продолжения. Branch/remotes прежние; personal branch commits/push ранее разрешены.

## Исторический B12 checkpoint

**B12 завершён** 7 октября 2026 (Moscow). Source/tests checkpoint: **`0b30db33fd2593dc25ea1b823a91795c789e0191`**, обычный push в личную ветку выполнен. Изменены шесть library paths: shared DGP base, binary base/functional/preperiod, IV base/functional. Новый модуль `tests/data/test_wrapper_namespace_contract.py` содержит 162 cases. Root и три существующих CLI субагента независимо проверили контракт, regressions, совместимость и CI.

Guards проверяют только реально включённые pre-period и ancillary поля и отклоняют коллизии без перезаписи. Неиспользуемый pre_name не влияет на ordering. Фактические confounder names и output roles фиксируются immutable tuples до assembly и публикуются после успешной generate. Поздние IV callbacks, включая мутацию внешнего списка имён, не меняют conversion roles. Два private dataclass fields имеют init=False/repr=False/compare=False; constructor signatures сохранены, fields/asdict включают private state. Ordering не повторяет столбцы. Automatic feature selection сохраняет disabled oracle-like names. Роль ID назначается только ancillary-added user_id; low-level user_id feature и IV user_id instrument сохраняют свои роли. Explicit selection и проверки data contracts не ослаблены.

**B12 verification:** 162 новых cases passed, 0 warnings, 4.74 s. Exact baseline eb6dfe: 136 failed / 26 passed, 6.53 s. Проверены шесть module pins, shared bindings, IV inheritance, exact collection и test hash. Focus был precommit; source/test bytes связаны с committed0b30 без rerun и без переписывания original head_at_start. Independent review: 300 wrapper configs + 80 core configs × 2 = **460 exact frame/dtype/schema/contract-metadata/RNG comparisons**; 45 rejects, 34 allowed-name checks, 6 core callback checks, 5 wrapper/helper callback checks, 2 constructor checks; warnings0, issues[]. Full references были precommit, 12 referenced committed file bytes verified. Пять AST runtime bodies сохранены apart from guards/metadata. Исправление ранее misclassified schemas намеренно меняет features и иногда pre/ancillary values/RNG; exact compatibility claim относится к корректно classified schemas.

Local Mac integration на0b30: **2396 passed, 1 failed, 0 errors/skips, 78 warnings, 85.67 s**, exit1, total2397. Это не clean local/full suite. Единственный прежний DiD GREEN/YELLOW failure сохраняется. Fixture и вся пятифайловая package closure из B10 runtime evidence имеют прежние bytes; шесть изменённых DGP paths находятся вне closure. B12 использует static linkage, новый cell-value probe не запускался. Threshold/assert/exclusions unchanged.

CI [37598926037](https://github.com/MaximLenivkin/Causalis/actions/runs/37598926037) **completed/success** на exact0b30: все шесть downloaded job artifacts — **2397 passed каждый**, 0 failures/errors/skips; matrix_verified=true, issues[]. Snapshot UTC2026-10-07T09:15:10.818155. Actual Python: 3.10.21 latest/legacy, 3.11.16, 3.12.14, 3.13.15, 3.14.7. Семь прежних sensitivity modules deferred; full sensitivity, standalone Sphinx, release и новый performance benchmark не validated.

Документация: BLOCK12_WRAPPERS.md, B12_WRAPPER_CONTRACT/IMPLEMENTATION/TESTS/REVIEW.md, воспроизводимые probes/runners/manifests. Portable English handoff дополнен семью source/test links; **101 immutable links verified**. Внешние сообщения автору не отправлялись. Artifact checker verify_block12.py проверяет точные source/test hashes, AST, baseline/focused/JUnit, prior DiD closure, все CI artifacts и локальные report links.

Следующий bounded **B13** candidate: late scenario outcome rename namespace в causalis/scenarios/classic_rct/dgp.py. Confirmed frozen/current trigger: generate_classic_rct_26(add_pre=True, pre_name='conversion', add_ancillary=False, return_causal_data=False). Underlying wrapper создаёт valid y и pre conversion; scenario y→conversion rename возвращает duplicate conversion. Contract rejects duplicates; CUPED26 уже имеет свой reserved-name guard. B12 исправляет шесть DGP paths, не этот поздний scenario rename. Затем отдельная mathematical numerical-zero DiD diagnostic/fixture policy, Gaussian oracle accuracy/API и прежний correctness backlog. Sensitivity/SC08LOO deferred.

Окружение: `.venv/bin/python`3.12.14 macOS arm64; `/Users/m.lenivkin/.local/bin/gh` с явным `--repo MaximLenivkin/Causalis`. Login/fork/remotes повторять не нужно. Source/tests frozen после0b30; final audit checkpoint — git log -1. Обычный final push, remote/local equality и clean tree проверяются на завершении. **На границе B12 работа остановлена; B13 начинается только новым запросом пользователя.**

## Исторический B11 checkpoint

**B11 завершён** 7 октября 2026 (Moscow). Source/tests checkpoint: **`cdc2c9590246c5b049d2184ba3479324217b2b00`**, ordinary personal push выполнен. Два library paths: `causalis/dgp/causaldata/base.py`, `causalis/dgp/causaldata_instrumental/base.py`; новый `tests/data/test_binary_iv_namespace_contract.py`, **163 cases**. Root и три CLI субагента проверили контракт, написали regressions и выполнили независимое review.

Проверяется полный фактически создаваемый core namespace: y, d, IV instrument, expanded confounders и enabled family-specific oracles. ValueError содержит имя и роли; имена сохраняются буквально. Guards работают при construction, на каждом generate, после sampling X и перед DataFrame assembly. Final check ловит callback mutations. Disabled oracles доступны; IV не резервирует binary-only names. Width check сохраняет исторически работавшие zero-confounder list/1D-array inputs без X conversion. Arithmetic, signatures и RNG для valid configs сохранены.

**B11 verification:** 163 новых cases passed, 0 warnings, 4.14 s. Тот же frozen module на baseline4d6b814: 103 failed, 60 passed, 0 errors/skips, 5.81 s. Exact collection/hash, real wrapper bindings и IV parent verified. Focused run был до commit на идентичных committed bytes. Reviewer на actualcdc: 80 valid configs × 2 + 6 family-specific × 2 + 14 k0 containers × 2 = **200 exact frame/dtype/schema/next10RNG comparisons**; 45 reject и 11 mutation probes, issues пуст. Library/test hashes frozen.

Local Mac integration на cdc: **2234 passed, 1 failed, 0 errors/skips, 78 warnings, 84.59 s**, exit1, total2235. Это не clean suite. Единственный failure — прежний DiD GREEN/YELLOW assertion. Fixture и вся package closure из B10 runtime probe имеют прежние bytes/hashes; изменённые DGP paths находятся вне closure. B11 checker использует static linkage с предыдущим runtime evidence, не новый cell-value probe. B09 exact-baseline и B10 runtime proof сохранены. Assert, threshold и exclusions не ослаблялись.

CI [37589241406](https://github.com/MaximLenivkin/Causalis/actions/runs/37589241406) **completed/success** на exactcdc: все шесть Linux jobs и downloaded artifacts — **2235 passed каждый**, 0 failures/errors/skips. `block11_ci_result.json`: matrix_verified=true, issues пуст. Actual Python: 3.10.21 latest / 3.10.22 legacy, 3.11.16, 3.12.15, 3.13.15, 3.14.7. Final artifact checker и **94 immutable handoff links** verified. Report `BLOCK11_NAMESPACE.md`; после cdc менялись только audit files. Ровно семь sensitivity modules deferred; standalone Sphinx, full sensitivity и release не validated.

Окружение: `.venv/bin/python`3.12.14; `/Users/m.lenivkin/.local/bin/gh` с `--repo MaximLenivkin/Causalis`. Credentials/remotes прежние; повторять setup/login/fork не нужно. Итоговый audit checkpoint — `git log -1`; ordinary push, remote/local equality и clean tree проверяются на завершении. На границе B11 работа остановлена; B12 начинается только новым запросом пользователя.

Следующий bounded **B12**: собственный namespace, ordering и projection wrapper layer. Frozen probes подтвердили pre_name='y' overwrite/duplicate projection даже при add_pre=False; ancillary age перезаписывает confounder либо IV instrument; instrument user_id или disabled-oracle m повторяется при IV ordering; automatic conversion исключает disabled-oracle-named confounders. Evidence: `block11_contract_result.json`, `block11_review_probe.json`. B11 core guard не гарантирует полную wrapper safety. Сначала определить actual enabled columns и совместимую conversion feature policy, сохраняющую valid schemas и RNG.

Отдельный **numerical-zero DiD diagnostic/fixture follow-up** сохраняется после wrapper layer: математический и численный reference, без masking failure, blanket tolerance или clipping. Далее Gaussian oracle accuracy, additive marginal propensity / selected ATT, learner/score contracts и features по FIX_PLAN. Sensitivity/SC08LOO deferred.

## Исторический B10 checkpoint

**B10 завершён** 7 октября 2026 (Moscow). Source/tests checkpoint: **`95a8b7599fb129fb2c5973f50e9b4a8018732f6c`**, ordinary personal push выполнен. Один library path `causalis/dgp/base.py`, новый `tests/data/test_copula_categorical_coordinates.py`, 33 cases. Shared categorical inverse CDF использует raw uniforms текущей Gaussian координаты; upper saturation выбирает последний уровень с положительной вероятностью. Numeric clipping, Gaussian draws, PSD repair, schema и API сохранены. Malformed categorical-spec validation не расширена.

**Проверки B10:** 33 новых cases passed, 0 warnings, 3.84 s. Тот же final module на frozen baseline83b6383: 30 failed, 3 passed, 4.29 s. Neighbors: 126 passed, 0 warnings, 3.71 s. Independent review: 18 numeric-helper configs × 2 = 36 exact comparisons; 48 valid public binary/multi/IV configs × 2 = 96 exact frame/schema/RNG comparisons; 9 coordinate references и 7 boundary cases. Source/test hashes совпали. Финальный artifact checker: issues пуст; documentation handoff: 91 immutable links verified. Categorical X/D/Y/oracles могут измениться; полное совпадение downstream RNG для categorical не обещается.

Local Mac integration на committed95a: **2071 passed, 1 failed, 0 errors/skips, 78 warnings, 90.27 s**, exit1, total2072. Это не clean suite. Единственный failure — прежний DiD GREEN/YELLOW numerical-zero assertion. Current provenance на95a показывает те же cell values/flag, неизменные fixture и все пять вызванных package files относительно baseline83b6383. Shared sampler не вызывается. Assert, thresholds и exclusions не менялись. Report `BLOCK10_COPULA.md`; proof `block10_did_provenance.json`; прежнее exact-baseline reproduction — `B09_LOCAL_INTEGRATION_NOTE.md`.

CI [37532909989](https://github.com/MaximLenivkin/Causalis/actions/runs/37532909989) **completed/success** на exact95a. Все шесть Linux jobs и downloaded artifacts: **2072 passed каждый**, без failures/errors/skips. Actual Python3.10.21 latest/legacy,3.11.16,3.12.14,3.13.15,3.14.7. `block10_ci_result.json`: matrix_verified=true, verified jobs6, issues пуст. Ровно семь sensitivity modules deferred; full sensitivity, standalone Sphinx и release не validated. После95a source/tests не менялись; остальные commits только audit artifacts.

Следующий кандидат **B11**: actual namespace guards для binary/IV генераторов. Confounder `d` перезаписывает treatment в raw output: обе семьи при n30,seed731 возвращают 30 nonbinary treatment values. Source этих assignments неизменен; B09 multi-only guard их не покрывает. Evidence `block10_review_namespace_followup.json` и `B10_COPULA_REVIEW.md`. Проверить outcome/treatment/instrument, actual expanded confounders и enabled oracles, без silent rename. Отдельный numerical-zero DiD diagnostic/fixture follow-up сохраняется: нужен независимый математический и численный reference. Не ослаблять assertion и не использовать blanket tolerance/clip ради green status. Затем Gaussian oracle accuracy/additive marginal API, learner contracts/score arithmetic и features по FIX_PLAN. Sensitivity/SC08LOO deferred. **На границе B10 работа остановлена**; следующий блок только новым запросом пользователя.

Git и окружение: `.venv/bin/python`3.12.14; `/Users/m.lenivkin/.local/bin/gh`; явный `--repo MaximLenivkin/Causalis` для CI. Не повторять login/fork setup/upstream sync, не force push. Автору документации внешние сообщения не отправлялись. Final audit checkpoint — `git log -1`; перед новым блоком проверить branch/status/remote equality.

## Исторический B09 checkpoint

**B09 завершён**, начат 6 октября и завершён 7 октября 2026 (Moscow). Source/tests checkpoint: **`1e2b544f7f91a57ad3e049572915a4b3891b084a`**, обычный push в personal fork выполнен. После него меняются только audit artifacts; финальный checkpoint — `git log -1`. Root и три CLI субагента выполнили разбор контракта, независимые regressions и review/CI verification.

Изменены два library paths `multicausaldata/base.py` и `functional.py` (второй — docstring), добавлен `tests/data/test_multicausal_namespace_contract.py`, 123 новых cases. Проверяется полный фактический namespace: outcome, treatment, expanded confounders и enabled oracles. Коллизии отклоняются через ValueError с именем и двумя ролями. Имена не переименовываются и не обрезаются; отключённые oracle и отсутствующий control CATE не резервируются. Tuple, NumPy string-array и непустые whitespace-имена сохранены. Полная проверка выполняется после успешного X sampling и до U/callback/treatment/outcome generation. Повторная generate проверяет изменённые публичные настройки.

**Проверки B09:**

- Новые tests: 123 passed, 0 warnings, 3.65 s; exact baseline: 87 failed, 36 passed. Neighbors: 217 passed, 6.91 s.
- Reference: 64 конфигурации × 2 последовательные генерации = 128 сравнений; frame/dtypes/schema и следующие RNG draws совпали точно. Material patch findings нет.
- Local Mac integration: **2038 passed, 1 failed, 0 errors/skips, 80 warnings, 117.46 s**, exit1, total2039. Это **не чистый local suite**. Failure прежнего DiD assertion GREEN vs YELLOW: preATT1.1102230246251558e-16, SE2.9351198205368013e-31, |t|3.7825e14. Exact pre-B09 source7414566 даёт тот же failure; fixture и весь вызванный code unchanged, изменённые DGP paths не вызываются. Raw baseline/current JUnit и probe retained. Assert не ослаблялся, из scope не исключался.
- CI **37530152376 completed/success**: все шесть Linux jobs и downloaded artifacts — **2039 passed каждый** на exact source1e2b544. Versions/JUnit/selection в `block09_ci_result.json`.
- Ровно семь sensitivity exclusions прежние; full sensitivity, standalone Sphinx и release не проверялись. Handoff: 88 immutable links verified. После verification source/tests не менялись.

**B10 начинается только по новому запросу.** Кандидаты следующего bounded correctness блока: shared categorical copula и отдельная numerical-zero DiD diagnostic/fixture policy. Copula использует `u` предыдущей координаты: первый categorical вызывает UnboundLocalError, а normal→categorical при identity correlation даёт category1 == (normal>0) во всех1000rows, seed731. Sampling fix должен использовать uniforms текущей координаты и independent Gaussian reference через binary/multi callers. Для DiD нельзя просто ослабить assertion или скрыть failure: нужна обоснованная политика при практически нулевых ATT/SE. Затем extreme Gaussian accuracy/additive marginal oracle, learner contracts/score arithmetic и features по FIX_PLAN. Sensitivity и SC08LOO deferred. На границе B09 работа остановлена.

**Git и окружение:** текущий gh `/Users/m.lenivkin/.local/bin/gh`, account MaximLenivkin и personal push проверены живыми запросами. Для CI явно указывать `--repo MaximLenivkin/Causalis`, поскольку default repository может быть upstream. При sandbox DNS нужен разрешённый network запуск; partial clone `git show` иногда подгружает исторические blobs. Не повторять login/fork setup, не push upstream и не force-push. Handoff переносимый, автору не отправлялся. Перед следующим блоком проверить branch/status/remote-local equality; неизменённый B09 suite повторно не запускать.

## Исторический B08 checkpoint

**B08 завершён. Source/tests checkpoint:** `9fb8041300410b560da80a45cabac4b541d1629d`, ordinary push в личную ветку выполнен. Два library paths: multicausaldata/base.py и functional.py;187newcases (112contracts+75assignment). Finite real config/X/U/callback/intermediate/output guards; scalar/singleton-U и callbacks compatibility; targetsumoverflow scaling; defaultensure_all singleton-safe fallback и optiniid single draw. Gaussian-marginal/selectedATT API не реализованы. Source frozen после committed checkpoint; после него толькоauditartifacts; finalauditcheckpointgitlog-1.

**B08 verification:**local1916passed0failures/errors/skips78warnings400.69s,exit0. Один новыйwarning intentionaloverflowtest;77historicalwarnings. CI37420288433completed/success exactsource9fb8041,all6Linuxjobs и downloadedartifacts verified1916passed каждый. Fullversions/JUnit/provenance вblock08_ci_result.json;localrawlog/selection/result вblock08_integration_*. Ровно7named sensitivitymodulesdeferred;fullsuite/Sphinx/release неvalidated. Seeded16referenceconfigs exactframe/schema/RNG verified again наcommittedsource. Handoff85immutablelinksissues0. Source/tests не менять безобоснованныхновыхпроверок.

Finalfocused149passed1intentionaloverflowwarning46.14s и75passed0warnings8.45s;16exact old/currentfiniteconfig comparisons включая RNG. Exactbaselinecontracts100failed12passed, sampling29failed46passed (19coverageparameterizations+10newAPIabsent). Initial/mixed baselines сохраняют отдельные labels; не считать число failingcases числомbugs. B08 notes/probes/rawlogs в audit.

**Следующий кандидат:** ограниченный namespace/schema correctness block. Independent review подтвердил outcome overwrite d_names=['y','arm'], treatment overwrite confounder'd_0', oracle overwrite confounder'g_d_0'. Validate полный namespace с expandedcategorical/enableoracle names, rejectcollisions clearly. Не silentlyrename columns. Затем extremeGaussian boundedintegration/accuracy policy и additiveqoracle. Sensitivity/SC08LOO deferred, upstream не synced; повторная auth не нужна. После B08 остановиться, B09 начинается только по запросу пользователя.

**B07 исторический завершённый блок.** Final source/tests checkpoint **`a2109a6ecd3c8422fbd4e8a7fd8d5d59334e8159`**; после него до B08 менялись только audit artifacts. Commits: 43f0b3e (earliest universal DiD), d3b6709 (DGP factual doc-only), a2109a6 (non-finite nuisance boundaries + fallback guard). Final audit checkpoint — b33922f. Пользователь уже разрешил commits/push в личную ветку; auth повторно не нужна. Sensitivity и SC08LOO deferred.

**Проверки B07:** локально **1729 passed, 0 failures/errors/skips, 77 warnings, 404.84 s**, Windows/Python 3.12.14; 147 новых cases (43 DiD +104 nuisance). CI **37385736343** completed/success на exact source a2109a6: все шесть Linux jobs (Python3.10–3.14 latest-compatible и3.10legacy) и downloaded artifacts проверены, каждый1729passed без failures/errors/skips. Snapshot UTC2026-10-05T23:02:17.8244687Z (6октябряMoscow). Full versions/JUnit — block07_ci_result.json; local raw log/selection/result — block07_integration_*. JUnit в ignored block07_integration_test_temp/junit.xml. Ровно семь named sensitivity modules исключены прежним CI runner; selected_full_suite=false и sensitivity_validated=false. Source/tests не менять после этой verification без обоснованного нового run.

**Nuisance fix:** real numeric NaN/±inf отклоняются до class selection, clipping, normalization и hard-label `np.where`. Binary/multi storage также finite-check. IV получает shared helper для m/g/r, но IV own storage/refit lifecycle не переработан. Finite out-of-range warning/clip/normalization и single-class mappings сохранены. Final focused104new+87neighbors=191passed,1knownwarning,25.75s; earlier222passset94new+128neighbors был до дополнительного fallback guard, counts не складывать. Независимый reviewer обнаружил fallback gap; исправлено до integration. Initial83/81failures включают fixture/message differences; exact previous storage public-fit probe дал10missing infinityguards+5oldNaNmessages без fixture errors; fallback —6missing rejections/4finite mappings. Подробности — B07_NUISANCE_NOTES и B07_METHOD_REVIEW.

**DiD fix:** universal inclpre starts0, varying starts1, post-only unchanged; остальные anticipation/eligibility/complete-pair filters сохранены. Final43newcasespassed28.23s; baseline29missing-cell failures/14passes. Earlier58neighborspassed;12new design-table assertion errors отдельно исправлены (fictitious combinedrun не заявлять). Ручные ATT/nonzeroSE/IF и post inference equality проверены. Cell IDs/event ranges/joint bands/pretests могут измениться; normalizingzero row не добавляется. Earliest B04 follow-up закрыт.

**DGP:** только docstrings в multicausaldata/base.py и scenarios/multi_unconfoundedness/dgp.py. target_d_rate означает sample-X/U=0 calibration; actual latent marginal rates могут систематически отличаться. CopulaToeplitz задаёт latent Corr(Z), не observed Corr(X). Existing m/m_obs, g/cate, RNG/calibration runtime unchanged. Adaptive numeric probe и concrete additive API proposal — B07_DGP_REVIEW.md, block07_dgp_probe*. `m_marginal_<arm>` и latent-selected ATT **не реализованы**. Supplied U не задаёт distribution law автоматически; rare-arm retry/forced assignment policy требует review перед exact oracle claims.

**Artifacts:** portable DOCUMENTATION_HANDOFF дополнен готовыми B07 текстами;81immutable links, verify_handoff issues0. verify_block07.py проверяет source/7exclusions/local+CIJUnit,9library paths,4doc-only AST paths,approved runtime function bodies,Python AST/local links и sensitivity guard. Actual counts — block07_validation_checks.json. Git source читается UTF-8. B06 benchmark не повторяли; B07 нового ускорения не заявляет. Standalone Sphinx/full sensitivity/release/upstream merge не выполнялись. Final audit-only push не перезапускает matrix.

**Historical B07 follow-ups:** contracts/rare-arm sampling выполнены в B08, additive Gaussian-reference propensity API и accuracy policy остаются будущими. Остальные задачи: learner shape/complex/IVstorage contract, extreme finite score arithmetic, normalized custom-ATE near-boundary, duplicate policy/snapshot arrays/Sphinx gate. Features repeatedCF → groupCF → externalOOF → DR/R-CATE после correctness. Перед новым блоком проверить branch/status/local/remote equality; не повторять старые suites без новых изменений.

Ниже — исторические checkpoints B00–B06.

B00 завершён, checkpoint **2c26cee**. B01 завершён: SC-05 Newcombe hybrid formula и SC-10 runtime enum validation. Fix commit **`bd8a2be2dc363400a572c6d369cda887fb17aad9`**. До fix27new casesfailed; после36conversioncasespassed и31соседний RCTcasepassed. Status/commands/ограничения — `BLOCK01_RCT.md`.

B02 завершён: ROOT-01–07, включая grouped ROOT-04/DML-05. Code commits: **817c24c9b00e8896bb578b3568476c178bc024e4**, **add2f36652a7bb7d814975234255f7993f96f240**, **a5a6e3a4887c7ac22aa86b36883398a34bbb5d76**, **c27e74406ffacee460ee6deb7c4be7669d1394e1**. Финальная общая проверка: **606 passed**, 5 existing warnings, 123.61 s; evidence `block02_integration_tests.log`. Это scoped integration run, не полный suite. Полный итог и compatibility notes — `BLOCK02_CONTRACTS_SHARED_DGP.md` и B02_*_NOTES.md.

B03 завершён: **c9259072a24f5325f944cd37c4f203f33c39a5e7**, **e6a92759f3c8844999c53bd065a673e31330d604**, **6084b34d799e9af34228136c0a2e9549063638ac**, **113c693a0dd721c6e77dfe84bc647d2ffb4c7841**. DML-01/02/04/06/09 и independent CATE part DML-03. Общий integration: **1143 passed, 1 known SC-12 failed, 76 warnings, 299.18s**, raw `block03_integration_tests.log`; отдельный selection/result JSON перечисляет 7 исключённых sensitivity test modules. New failures0, не полностью зелёный suite. Focused sets: GATE68, multi63(+final10fixture), binary42+119neighbors, OOS36+50neighbors; counts пересекаются, не суммировать. Independent empirical ratio derivatives и oracle MC600×600 проверены; current CATE остаётся full-sample T-learner.

**B04 завершён**: code commits **87228e267aed3dc71dadd4bbe19b969a95463591**, **57dbba1e2ecc0c1cab413b1da7f40cfdd8b22131**; финальный documentation checkpoint — `git log -1`. SC-01/02/03/04/11: shared control eligibility исключает owncohort и проверяет max(base,target)+anticipation; full normalized traditional MLE/OLS cell IF (ridge/raw likelihood/clipped derivative/designSVD); complete-pair share IF aggregate; >=2cluster guard, bootstrap0или>=2 и согласованная covariance. Cell ATT/policy сохранены вне исправленного precomparison set. Diagnostic output False не отключает share IF. Public comparison_units сохраняет post-only/off-axis API и добавляет optional base_time/anticipation.

B04 integration source checkpoint57dbba1: **1238 passed,1 known SC-12 failed,76warnings,340.04s**, exit1. Newfailures0;7sensitivity modules исключены, exact selection/result JSON. New95cases:cluster10,cell34,alignment32,aggregation19. Focused counts пересекаются, не суммировать с integration. Historical DiD probes теперь дают preATT-2, trend-invariant IPW SE.3752058, DRreferenceSE.03887567, population mixtureSE.49574187. Detailed derivations/limits — BLOCK04_DID иB04_*NOTES/METHOD_REVIEW.

Estimated-nuisance DRMC600×n600 each2DGP coverage.935/.956667; первый имеет finite-nSE gap(meanSE/empSD.9163), universalcoverageimprovement не заявлен. Shares-only oracle coverage.958333. Fixedridge/activeclip могут менять target; missingsamplemixture не fullcohortATT автоматически, fewclustersnonregularrank/clipping/support требуют caveats. ScaleIFsolverchecks не optimizer invariance. Earliest universal pre enumeration index0 пока исключён: отдельный followup, не исправлялся вB04.

**B05 завершён**: repository integration **1376 passed,0failed,77warnings,438.20s**,7sensitivity modules исключены; exit0. Старый SC12 cache assertion сохранён и проходит. Checkpoints **bb31a4b09c20046faafbbd29a541e5acbe50b99d**, **5e0379507bac4b6ec9f561e7978e8835194c2247**, **3c000b10eed1b5366f46cc038870500791b75579**, **1b2477755c9b89bd2f69f260fd094002bdc26fe2**. Последний — tested source checkpoint. SC-06/07/09/12 исправлены: CUPED collision-safe roles/bootstrap, owned designSVD/batch P@Y/HC2-HC3 stable h/reused diagnostics; IV model/result resolver и failed-refit lifecycle. SC-08 только placebo; **LOO sensitivity deferred**. New137cases: names24,stable22,IV60,SCM31. Focused allCUPED127,IV73,SCM67(1known gridwarning), counts пересекаются. Rawlogs/notes — BLOCK05_CUPED_IV_SCM иB05_*NOTES/METHOD_REVIEW.

Small benchmark sequential native1,12000rows/4X/HC2/checksTrue,1/8/32Y: local fit speedups1.73/2.90/2.58, maxATEdiff1.58e-14,maxSE3.47e-18. Constructor/estimate/memory вне timing, не generalrating. Raw-control HC/calibration и variance/rank/drop thresholds сохранены; adapter зависит от small model protocol, compatibility matrix вB06. ASCM old/manual results без13configkeys требуют re-estimation или explicitmissingkwargs; per-result snapshot и partialoverrideinheritance documented. Source/tests больше не редактировались послеcheckpoint1b24777. `run_block05_integration.py` завершён вне7sensitivitymodules; selection/result JSON и raw log сохранены. Final report/portable handoff готовы;58immutable links checked,issues0. verify_block05.py проверяет source/AST/local links/sensitivity guard. Finaldocumentationcheckpoint через git log-1; после push localremote equality иcleanstatus подтверждаются.

**B06 — финальное состояние.** B06: implementation и локальная integration завершены: **1582 passed, 0 failed/skipped, 77 warnings, 400.95s**. 206 новых cases, 7 sensitivity modules явно исключены. Pydantic>=2, full release pytest gate, CI matrix, duplicate screening, linear binary detection, bounded Gaussian KDE и NumPy1.x IV fix. Все шесть clean Linux jobs и artifacts прошли; каждый — 1582 cases без failures/errors/skips. Финальный source09e00de; evidence в BLOCK06_COMPATIBILITY_PERFORMANCE.md. Owned arrays остаются audit-only; полный sensitivity/release/docs build не подтверждался.

Полный source/tests checkpoint `09e00de5a9d3dc915c6d59627f8b0ebc875dd4e9`; после него меняются только audit artifacts. Commits: f31b743 (CI), 5977bb8 (duplicates), 74c0ff0 (binary), d292b3c (KDE), 1be6b67 (audit-only push filter), 50ad33e (benchmark/notes), 09e00de (IV compatibility). Final documentation commit определяется git log-1. Git author/auth/remotes прежние; повторная authorization не нужна.

Реальная legacy CI обнаружила 53 IV failures на NumPy1.26: Unicode array `+` не поддерживался. Installation прошла; canceled status исходного job не скрывает этот pytest failure. Исправлено np.char.add, добавлены13 fold/reference cases; actual fixed legacy source проверяется отдельно. Первоначальные integration1569 и matrix successes сохранены как initial/before_fix evidence; не смешивать их с final1582/09e00de.

Final matrix run **37373828518**, exact source09e00de, snapshot 2026-10-05T21:21:54.6451704Z. Все шесть clean Linux jobs и artifacts прошли; каждый — 1582 cases без failures/errors/skips. Full versions/JUnit/elapsed — block06_ci_result.json. Первые runs37371536543/37372133090 superseded config/fix pushes; prior legacy failure сохранён отдельно. GitHub runner-delay incident3q1yb5m7ltvb объясняет возможную очередь по внешнему статусу. Не делать бессмысленные reruns/смену Ubuntu labels. Final audit-only push не перезапускает матрицу.

Release runner defaultfull и **включает sensitivity**; не заменять на scoped для получения green. Branch correctness имеет ровно7 явных named exclusions; новый sensitivity test требует scope review. Docs extra не подтверждает Sphinx build (current docs test file без collected tests). Локальный env Python3.12.14, Windows, unchanged; нет pip/build/twine. Полный release/tag/PyPI не запускались.

Benchmark отдельно: baselinebf2ea87/currentd292, два последовательных fresh processes, seed731, native1. Constructor speed1.22–2.24×, IRM extraction1.37–4.14×; KDE30k×800 traced peak549.32→8.13MiB, max density difference5.88e-15. Matched IRM20k×8 fit1.24×, same folds/predictions/score/IF/ATE/SE. Tracemalloc не RSS; fit excludesconstruction/estimate. IV split fix не входит в measured operations, benchmark не повторяли. Owned candidate2.23/1.05/1.47× current extraction, audit-only без snapshot/invalidation contract.

**Исторический backlog после B06:** earliest universal DiD pre-cell и finite nuisance outputs впоследствии закрыты B07; DGP marginal/supplied-U/ATT и другие follow-ups остаются в актуальном разделе выше. Feature priorities: repeated cross-fitting → group/cluster-aware cross-fitting → external OOF → DR/R-CATE. Ничего из этого не начиналось в B06. Sensitivity и SC08LOO остаются deferred до upstream sync.

Документация для пересылки готова в `DOCUMENTATION_HANDOFF.md`; дополнена B02–B06 migration и immutable implementation links. GitHub snapshot file/line links проверяются `verify_handoff.py`;70links,issues0,local-only linksнет (`handoff_validation.json`). B04 scripts `verify_block04.py` и `run_block04_integration.py` сохраняют отдельные evidence JSON/log, не переписывая исторический audit/B03 evidence. Финальная B06 artifact validation: 302local links,23PythonAST,9librarypaths,sensitivitypaths0,issues0; JSON хранит actual counts. Git source читается явно вUTF-8, executableAST benchmark paths совпадает. Нет необходимости заново выполнять полный аудит или broad benchmark.

B03 migration: Multi ATTE psi_a matrix(n,K-1), frozen original-row weights изменяются только через refit, OOS t/p fields теперь NaN/NA и отдельно descriptive fold metrics. Старые multi ATTE cached scores могут реконструироваться с `psi_cache_status`, но старые CI требуют re-estimation. Generic scalar/sensitivity refit state и sensitivity diagnostic sigma2 explicitNone annotation issue отложены. Upstream updates не merge/rebase в B03; для новой sensitivity реализации сначала нужна отдельная синхронизация/review.

Новый отдельный DGP follow-up: `m_<arm>` по-прежнему softmax при U=0, не marginal P(D=arm|X) при latent treatment noise. Это явно документировано. Outcome g/cate fix закрыт в рамках Gaussian reference law; arbitrary supplied U и true latent-confounded ATT требуют отдельной интерпретации. Не менять молча propensity API в B03.

## Baseline и ограничения

- Аудит:31grouped findings,11P1+20P2; sensitivity subset отложен. CSV inventory130modules,40notebooks.
- Original suite968cases:964passed/3failed/1error; recheck3passed/1failed. Реальный baseline failure — `tests/statistics/test_cuped_rct.py::test_shared_design_and_input_unchanged` на statsmodels0.15, SC-12. Не считать его регрессией B01/B02/B03; исправлен public batched SVD/cache в B05, исходный assertion сохранён.
- Windows sandbox process pipes/tmp могут вызвать PermissionError; при необходимых tests использовать разрешённый запуск с local basetemp.
- Audit snapshots/copies/runtime caches не включать в commits как whole directory tree. `audit/.gitignore` исключает copied docs build, temp/cache; small evidence logs намеренно разрешены.
- Оригинальные отчёты имеют absolute Windows links для локальной работы. `DOCUMENTATION_HANDOFF.md` переносимый, с GitHub SHA links для отправки автору.

## На завершении любого блока

Записать status, actual commit SHA, tests и оставшиеся ограничения; проверить git status; законченный commit; после доступного remote — push в личный fork. Остановиться и сообщить пользователю результат блока. Не автоматически начинать следующую большую область до его нового запроса.
