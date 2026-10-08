# B27 — inference families

Baseline `750354b51896f0d775b3eb73c1cebaec1b882f17`.
Рабочая ветка `codex/correctness-roadmap`. Final source `72f6918b1eb06b8bfd743397b2bf0bde6a8ef8a0`; implementation commit
`f71863483c59df3d740a4984981998bfcb0da627`, root export correction72f6918.
Final source/local/docs/CI evidence complete; root --require-ci verification ниже.

## Target и assumptions

Фиксированный заранее вектор regular scalar population effects theta. Для
IRM — absolute ATE или ATTE по нескольким outcomes на одинаковых ordered
stable user IDs и treatment. Каждая колонка IF описывает observation-scale
asymptotically linear representation theta_hat-theta = mean(IF)+o_p(n^-1/2).
Колонки совместно относятся к тем же независимым наблюдениям; произвольные
кластеры или повторения не становятся iid от передачи их в generic API.

Нужны joint asymptotic linearity, достаточные moments, nondegenerate variance,
фиксированная до просмотра результатов family; произвольный рост p не
сертифицирован. Causal IRM дополнительно требует consistency, conditional
exchangeability, overlap и подходящие nuisance rates. Active clipping,
estimated nuisance bias и confounding multiplicity correction не исправляет.
Stable IDs проверяют alignment, не independence/leakage/selection history.
Data-adaptive family/contrast selection требует отдельной selection inference
или независимой выборки. Линейные контрасты требуют соизмеримых единиц.

Primary method reference: [DoubleML official simultaneous-inference guide](https://docs.doubleml.org/stable/guide/se_confint.html).
Общий multiplier принцип сверён с первичным implementation guide; finite-n
normalization, finite-draw p/quantile и invariants выведены и протестированы
отдельно. API/numerical identity с DoubleML или theorem certification нет.

## Sequential alternatives и выбранный seam

1. Изменить estimate() каждого estimator, добавить joint-family mutable state:
   увеличивает scope, включает алгоритмы, не имеющие общего inference contract,
   и рискует смешать median repetitions / cluster / CATE с iid IF.
2. Отдельный owned InferenceFamily с generic iid representation и ограниченным
   pure IRM adapter. Совместная зависимость скрыта за компактным infer/contrast
   API; существующие одиночные алгоритмы и результаты остаются неизменными.

Выбран второй вариант. Новой сторонней зависимости нет; используются NumPy,
SciPy normal tails и имеющиеся raw real/finite arithmetic guards. Production
imports не содержат imports из tests. Source не вызывает внешних сервисов.

## Public caller contract

```python
from causalis.inference import InferenceFamily
family = InferenceFamily.from_irm({"a": fitted_irm_a, "b": fitted_irm_b}, score="ATE")
result = family.infer(method="max-t", n_boot=1999, random_state=42)
result.summary()
contrast = family.contrast([[1, -1]], names=["a_minus_b"])
contrast.infer(method="bonferroni").summary()
```

Generic constructor принимает values(p,), influence(n,p), names(p), n>=2,
p>=1; inputs копируются, IF центрируются. Positive variance mandatory;
perfect dependence/singular joint covariance допускается. Overflow, invalid
values и diagonal underflow отклоняются явно, silent zero uncertainty нет.
Covariance property возвращает owned aggregate copy; contrast одновременно
преобразует effects и IF. Result frozen dataclass с immutable scalar tuples;
summary возвращает fresh table; individual observations/IF/draws не возвращаются.
Private Python attributes остаются изменяемыми; thread safety и скрытые callback
side effects не гарантируются. Собственные inputs/results не алиасируют caller.

IRM adapter требует actual internal R1 iid unweighted clip fit, current
normalize_ipw=False; ATE/ATTE только. Проверяет current roles/raw-real sample/
fit fingerprint и unique nonmissing stable IDs, IDs совпадают с fit snapshot.
Все модели имеют одинаковые ordered IDs и treatment role/vector. Нельзя
сопоставлять модели лишь по одинаковому RangeIndex. Outcomes/features/folds
могут различаться. External OOF, cluster, repetitions, drop, custom weights,
Hájek-normalized inference и CATE/GATE rejected. Adapter не fit/predict,
не обновляет scalar caches/score/config, не строит diagnostics, не потребляет RNG.
Он использует существующие pure score/moment вычисления IRM на копиях массивов;
нормализация/weights и fit guards в существующем IRM не изменены.

## Formula и finite-draw convention

I = IF - column means; Sigma = I.T @ I / [n(n-1)]. SE = sqrt(diag Sigma).
Сначала используются column scales для безопасного вычисления нормы; полностью
нулевой/непредставимый float64 SE/covariance reject. Standardized influence
columns U = I / sqrt(sum_i I_ij^2) имеют unit norm; Gaussian multipliers xi_b
на одних и тех же rows дают t*_b = xi_b @ U с conditional covariance correlation
matrix Sigma. Общий draw сохраняет зависимости между outcomes/контрастами.

Bonferroni: marginal p=2*normal.sf(abs((value-null)/SE)), adjusted_j=min(1,m*p_j),
critical=normal.isf(alpha/(2*m)), bands=value±critical*SE. Здесь m — число hypotheses, p_j — marginal probability.
Max-t: M_b=max_j abs(t*_bj), adjusted_j=(1+count(M_b>=abs(t_j)))/(B+1).
Critical — order ceil((1-alpha)*(B+1)), one-based. Alpha>=1/(B+1), B>=99.
Ties включены, rejection adjusted<=alpha; endpoint comparisons при ties могут
различаться. Это Monte Carlo approximation Gaussian limit, не exact
randomization test. Null scalar/vector меняет tests, не centered bands.
Bonferroni n_boot=0/seedNone, no random draws; его bootstrap args не используются.

Max-t использует fresh local Generator, None либо uint32 integer seed, batches
не более256*n multipliers; memory дополнительно O(B+256*n+256*p+p*p+n*p),
compute O(B*n*p). Тот же seed воспроизводит same-environment draws; нет exact
cross-platform/version RNG guarantee. Perturbation не refit whole pipeline.
Finite B tail accuracy остаётся caller choice; минимальный B не quality promise.

Нет Holm/Romano-Wolf stepdown, clusters/few-cluster guarantees, repeated-split
median joint covariance, generic estimator adapter certification, weak-IV,
relative effects или pointwise CATE CI. Иные методы — отдельные blocks.

## Verification evidence

Development run:97cases,5failed/92passed/8warnings/23.17s. Все5 fixture mistakes:
четыре source-ownership теста обращались к y1, который CausalData убрал в model
с outcome y2; один null1e308 фактически не переполнял statistic. Исправлены
actual outcome name и null1.7e308; runtime algorithm для этих failures не менялся.
[Raw development log](block27_development_tests.log).

Первый focus после fixture corrections:790passed/72warnings/32.87s,104new.
[Initial focus](block27_initial_focus_result.json),
[raw log](block27_initial_focus_tests.log). После numerical review добавлен
explicit covariance-diagonal-underflow guard и две независимые проверки:
underflow fail и orthogonal IF Gaussian maximum closed-form critical value.
Поэтому требуется final focus и committed local/CI gate на последних bytes.

Все fixtures synthetic; клиентские строки/IDs/attributes не запрашивались и
не скачивались. Code-test JUnit/logs/metadata сохраняются, exact owned pytest
temporary directories удаляются после проверки.

Следующий блок B28 — weak-IV LATE; не начинать автоматически. Sensitivity,
SC08LOO, selected-U ATT, multi-IV grouping/repetitions, few/multiway clusters и
NumPy/RST documentation debt остаются отдельными/deferred.

Final algorithm focus before root export correction:792passed/72warnings/32.63s,
106new. Initial committed source f71863483c59df3d740a4984981998bfcb0da627.
Initial strict Sphinx failed exit1/16.306s: new causalis.inference package omitted
from root __all__ produced toc.not_included warning. This is a real documentation
integration failure, not a fixture issue. Correction adds the package to root
lazy exports; final source must pass fresh source/local/docs/CI gates. Initial
result/log retained separately: [initial docs](block27_initial_docs_result.json).

Initial committed integration on f718634:1failed/3979passed/157warnings/131.17s.
The same strict Sphinx toc.not_included failure occurred in the existing docs
integration test. [Initial integration](block27_initial_integration_result.json),
[raw log](block27_initial_integration_tests.log). Initial gates are superseded,
not reported as final successful evidence. Root lazy export correction also
adds a fresh-process lazy-import regression case; final new case count107.

Final focused gate on committed72f6918:793passed/72warnings/39.36s,107new,
0failures/errors/skips. [Focus result](block27_focus_result.json),
[raw focus](block27_focus_tests.log), [runner](run_block27_focus.py).
107cases include independent sample-mean covariance/Bonferroni reference,
12 Gaussian-draw/order-statistic oracles (B99/256/257/999; alpha.05/.2/.5),
perfect ±correlation, singular covariance, weighted contrasts, column permutation,
owned snapshots/results/covariance and global RNG, centering/scales1e-100..1e100,
shape/name/raw-complex/nonfinite/context guards, null/seed/draw resolution,
overflow/underflow and closed-form independent Gaussian max law with100000draws.
Real production IRM ATE/ATTE×diagnosticflags match scalar estimates/SEs/joint
covariance; source attrs/caches unchanged, post-snapshot mutations harmless.
Fit/predict/estimate callback bombs, fresh-refit ID/order/treatment misalignment,
stale sample/role/objectcomplex, actual external/repeated/cluster/drop/weight/
Hájek fits, bad fitted propensity and fresh-process lazy import are checked.
IID Gaussian two-mean Bonferroni FWER smoke uses2000×n80, seed71 and broad
.025..085 gate; one oracle regime only, not DML nuisance/coverage certification.

Final standalone strict Sphinx on72f6918:exit0/18.183s, warnings are errors,
no publication. [Docs result](block27_docs_result.json),
[standalone log](block27_standalone_checks.log). Root functions are AST-identical
and154existing library/scripts/workflowfiles byte-identical baseline→final;
existing root module changes only the new package's export/config/type imports.
Five non-audit changed paths, no dependency/workflow/old scalar/DR/R/T/policy/
repeated/cluster/external/sensitivity algorithm changes.
Handoff now158immutable links checked: [validation](handoff_validation.json),
[handoff](DOCUMENTATION_HANDOFF.md), [log](block27_handoff_checks.log).

Final committed correctness on72f6918:3981passed/157warnings/132.77s,
0failures/errors/skips; runner elapsed132.958s.
[Selection](block27_integration_selection.json), [result](block27_integration_result.json),
[raw integration](block27_integration_tests.log), [runner](run_block27_integration.py).
All3874previous B26 case IDs retained;107newcase IDs are the exact difference.
Seven named sensitivity exclusions unchanged; this is not full sensitivity or
release gate. Native threads1, local actualPython3.12.14, existing .venv.
No dependency installation, environment/login/fork setup, subagents, notebook
execution, website publication, PR, release or upstream merge/push.

Exact owned focus/integration pytest-temp directories removed after inspection;
JUnits, synthetic code-test logs, source/environment/development/initial/docs
metadata retained. [Cleanup manifest](block27_cleanup_result.json). No prefix
cleanup or other blocks' evidence removed.

Local root validation before CI:exit0,issues[],154existing files unchanged,
793focus/107new/3981integration,3874previous case IDs retained,158handoff links,
19report links checked. [Local validation](block27_local_validation_result.json),
[local checks](block27_local_validation_checks.log), [root verifier](verify_block27.py).
Ordinary source push750354b..72f6918 succeeded under persistent explicit user
«Разрешаю пуш в нашу ветку» grant. No automatic review rejection/new permission.
CI run37809518217 completed/success on exact finalsource; final artifacts verified.

## Final CI and completion gates

[CI37809518217](https://github.com/MaximLenivkin/Causalis/actions/runs/37809518217) completed/success, exact finalsource72f6918;
one actual B27 CI run, no reruns. All6jobs3981passed each,0failures/errors/skips,
strictSphinx exit0 each. ActualPython3.10.22legacy/latest,3.11.17,3.12.15,
3.13.16,3.14.8. SnapshotUTC2026-10-08T16:37:07.010575+00:00.
[CI manifest](block27_ci_result.json), [CI observer log](block27_ci_checks.log),
[artifact verifier](summarize_block27_ci.py).
Full local/CI3874old+107new case sets,793focus, exactsource/normalizedargv/
7exclusions/environments/docs generator+buildlog and5hashes per job verified.
Six representative Linux dependency configurations, not all possible stacks.

[Final root manifest](block27_validation_result.json),
[root checks](block27_validation_checks.log), [root verifier](verify_block27.py)
verify source isolation and original root-function AST, final+initial raw local
JUnit evidence, old case-set inclusion, focus hashes, strict docs failure/fix,
exact cleanup, local/report links and deterministic raw CI resummarization.
Final audit checkpoint via gitlog-1 avoids recursive metadata SHA recording;
ordinary final audit push/live local-remote identity/clean tree at completion.
Source/tests frozen after72f6918; subsequent changes audit-only. No automatic
approval rejection; persistent user push permission applies to this branch.

Final root --require-ci exit0/issues[],28reportlocal links checked. B27 complete;
final audit checkpoint via gitlog-1. Stop at B27 for
context cleanup; B28weak-IVLATE requires a new user request. Deferred areas above
remain separate. No PR/release/upstream/main/forcepush/publication/messages.
