# Покрытие ревью и карта доказательств

Commit `ffe2c356c115f335b74b2f10117e19fe15585d46`, 2026-10-05. Основной итог — [REPORT.md](D:/codex/Causalis/audit/REPORT.md).

## Все модульные области

[MODULE_INVENTORY.csv](D:/codex/Causalis/audit/MODULE_INVENTORY.csv) содержит **каждый из 130** source Python modules: path, lines, направление ревью, число AST functions, наличие module docstring и успешность parse. Generated `_version.py` исключён из ручной source инвентаризации; с ним API inventory содержит131 модуль. Это inventory/parse evidence, не 100% branch coverage.

Группы ниже исчерпывают инвентаризацию. Число строк — физические строки файлов, включая комментарии/пустые строки, не количество statements. Все группы просмотрены статически, но глубина различается: maximum в score/inference/contracts, меньше в plotting/rendering и convenience wrappers. Владелец в CSV — первоначальное распределение; пересечения, особенно DGP, проверялись несколькими направлениями.

| Группа | Модулей / строк | Основная проверка и executed evidence | Где детали |
|---|---:|---|---|
| Package root | 1 / 80 | Exports/version surface; actual imports | Contracts/docs |
| data_contracts | 17 / 5255 | Causal/Multi/Rct/IV/PanelDID/PanelSCM, estimate/diagnostic containers; finite/complex/roles/ownership/IDs; constructor benchmark | CONTRACTS_SHARED_DGP + PERFORMANCE |
| dgp | 19 / 6550 | Binary/multi/IV/panel/preperiod engines, natural-scale oracles, RNG/ID uniqueness; nonlinear latent multi and UUID probes | CONTRACTS_SHARED_DGP |
| scenarios root / `_orthogonal` | 2 / 65 | Shared orthogonal API/export; используется GATE/policy paths | DML_REVIEW |
| classic_rct | 7 / 1108 | DiffInMeans, t/z/permutation inference, DGP; Newcombe/enum/Inf probes | SCENARIOS_REVIEW |
| cuped | 7 / 2898 | Design/names/multioutcome regression, HC covariance/relative inference/diagnostics/DGP; collision/leverage; suite cache failure | SCENARIOS_REVIEW |
| did | 8 / 4891 | Cohort/base/control/anticipation, IPW/DR, cell IF/aggregation/bootstrap/diagnostics/DGP; six numerical defects | SCENARIOS_REVIEW |
| gate | 3 / 1581 | GATE/GATET fixed partitions, scores/covariance/contrasts, plot input; cancellation probe | DML_REVIEW |
| iv | 6 / 1926 | IIVM nuisance/ratio LATE/diagnostics/assumptions/DGP; model-vs-estimate diagnostics probe | SCENARIOS_REVIEW + DOCS_RESEARCH |
| multi_unconfoundedness | 14 / 6247 | Multiarm assignment/classes/simplex, ATE/ATT, sensitivity/overlap/balance/score/plots/DGP wrappers; ATTE IF/benchmark/infinite SMD/OOS probes | DML_REVIEW |
| synthetic_control | 11 / 4181 | ASCM constraints/ridge/inference/placebo/LOO/donor diagnostics/plots/DGP; refutation config probe | SCENARIOS_REVIEW |
| unconfoundedness | 21 / 10046 | Cross-fit cloning/heldout predictions, ATE/ATT/relative effects/drop/weights/sensitivity/refit; diagnostics; matched DoubleML ATE/SE/predictions | DML_REVIEW + PERFORMANCE |
| uplift | 3 / 967 | T-learner lifecycle, policy objective/greedy splits/provenance/disjoint evaluation; refit cache probe | DML_REVIEW |
| shared | 11 / 2399 | Balance/clustering/outliers/outcome plots/stats/SRM/SUTVA/design/MDE/power/assignment; separation/duplicate-index/NaN probes; static KDE memory estimate | CONTRACTS_SHARED_DGP + PERFORMANCE |
| **Всего** | **130 / 48194** | AST parse всех; selective deep review и executions | CSV и тематические отчёты |

## Не только исходники

| Область | Что сделано | Где evidence |
|---|---|---|
| 123 test files / 968 cases | Полный baseline; recheck четырёх failures; distinguished sandbox vs real cache regression | pytest_full.log/xml, pytest_recheck.log |
| 40 notebooks /1062cells | Inventory, извлечён весь markdown, просмотр ключевых code/output и methodology claims | docs_inventory.json, docs_notebook_markdown.txt |
| Imports examples | 27 suspicious AST flags проверены runtime, actual errors0 | docs_verify_exports.py, docs_inventory.json |
| Generated API | Current source131 vs checked-in HTML126; missing5 public modules/stale1; isolated successful build131HTML | docs_inventory.json, docs_build.log/summary |
| README/CONTRIBUTING/pyproject/workflow | Claims/assumptions/dependency requirements/release test gate | DOCS_RESEARCH + CONTRACTS_SHARED_DGP |
| Опубликованный сайт | Homepage и ключевые RCT/CUPED/IRM/IV/GATE/Uplift/SCM статьи; сопоставление с current source | DOCS_RESEARCH primary links |
| Литература | Foundational/official implementations и актуальные author versions вплоть до Sep2026 | DOCS_RESEARCH + REPORT method roadmap |
| Производительность | Constructor/extraction100k–1m rows, matched IRM20k, traced allocation peaks/cProfile; clean run без параллельных fits | benchmark_data_path.json/log, profile_*.txt |

## Как связаны finding и проверка

| Семейство findings | Исполняемый артефакт | Output |
|---|---|---|
| DML-01–11 (включая additional GATE DML-09) | [repro_dml_core.py](D:/codex/Causalis/audit/repro_dml_core.py) | [repro_dml_core.log](D:/codex/Causalis/audit/repro_dml_core.log) |
| SC-01–11 (SC-12 отдельно suite) | [repro_scenarios.py](D:/codex/Causalis/audit/repro_scenarios.py) | [repro_scenarios.log](D:/codex/Causalis/audit/repro_scenarios.log); отдельные paths объединены в 10 probes |
| SC-12 cache | Existing `test_shared_design_and_input_unchanged` и installed statsmodels source | [pytest_recheck.log](D:/codex/Causalis/audit/pytest_recheck.log) |
| ROOT data/shared | [repro_contracts_shared.py](D:/codex/Causalis/audit/repro_contracts_shared.py) | [results_contracts_shared.json](D:/codex/Causalis/audit/results_contracts_shared.json), log |
| ROOT-01/05 DGP | [repro_dgp.py](D:/codex/Causalis/audit/repro_dgp.py) | [results_dgp.json](D:/codex/Causalis/audit/results_dgp.json), log |
| ROOT-08/09 | Static metadata/API imports/workflow checks; no v1 env/publish experiment | CONTRACTS_SHARED_DGP exact references |
| Docs Newcombe D05=SC05 | [docs_newcombe_check.py](D:/codex/Causalis/audit/docs_newcombe_check.py) | [docs_newcombe_result.json](D:/codex/Causalis/audit/docs_newcombe_result.json) |
| Docs drift/build | [docs_inventory.py](D:/codex/Causalis/audit/docs_inventory.py), [verify_docs_build.py](D:/codex/Causalis/audit/verify_docs_build.py) | docs_inventory.json, docs_build.log |

## Что не установлено этим аудитом

- Coverage probability каждого estimator/learner/DGP в большой Monte Carlo study. Counterexamples и formula mismatches достаточны для выявления дефекта, но не оценивают его частоту на произвольных данных.
- Полная execution воспроизводимость всех40 notebook; сохранённый output отдельно отмечается как snapshot.
- Visual QA каждого diagnostic plot, accessibility/site rendering, exhaustive HTTP link crawl. Web extractor error не равно broken URL.
- Original R package execution для всех reference checks; DID reference IF переведён из official source в Python probe, это явно подписано.
- Всё множество параметров/версий/OS/parallel configurations, production CatBoost/XGBoost и complete large-data comparison с EconML/другими библиотеками.
- Formal security/supply-chain audit, лицензирование всего dependency tree, exhaustive review каждого exception path.
- Исчерпывающий systematic literature review или theorem-to-code proof всех новых статей; часть research horizon — проверенные abstracts и направления.

Отсутствие найденного дефекта в конкретном module не означает гарантии его отсутствия. Рекомендации и ограничения scope не включены в число подтверждённых bugs.
