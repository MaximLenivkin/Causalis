# Ревью Unconfoundedness, MultiTreatmentIRM, GATE/GATET и Uplift

Дата: 5 октября 2026. Commit: `ffe2c356c115f335b74b2f10117e19fe15585d46`.

Рабочая копия: `D:/codex/Causalis`. Исходный код не изменён. Проверки выполнялись через репозиторный `.venv/Scripts/python.exe` (Python 3.12.14; numpy 2.5.3, pandas 3.0.6, sklearn 1.9.1). Прочитан `AGENTS.md`; его macOS-путь к Python не соответствует этому Windows checkout, поэтому использован согласованный локальный `.venv`.

## Результат и границы проверки

Базовый **невзвешенный binary IRM ATE/ATTE** реализован узнаваемыми ортогональными scores. Cross-fitting клонирует learners и предсказывает на held-out folds; постоянный binary outcome в одном treatment arm обрабатывается без утечки. Canonical subgroup ATT реализован отдельно от ordinary GATE. Policy learning использует DR signals, требует независимые client IDs при evaluation и честно документирует greedy optimization. Эти части не следует объявлять методологически неверными целиком.

При этом подтверждены ошибки inference и lifecycle, а также диагностики, которые могут создавать ложное ощущение корректности модели. Самые важные: неправильная influence function для multi-arm ATTE, ошибочная калибровка multi-arm sensitivity benchmarks, превращение отрицательной `nu2` в нулевой confounding bound и использование результатов предыдущего fit.

**Доказательства:** [repro_dml_core.py](D:/codex/Causalis/audit/repro_dml_core.py) и [repro_dml_core.log](D:/codex/Causalis/audit/repro_dml_core.log). Скрипт содержит 12 самостоятельных проверок. Основной прогон занял около 9 секунд. Дополнительная lifecycle-проверка выполнена отдельно и дописана в лог. Полный suite в рамках этого направления не запускался; зависимости не устанавливались этим агентом. Репозиторный полный baseline и общий performance audit ведутся в других направлениях.

Повторить из `D:/codex/Causalis`:

```powershell
$env:MPLCONFIGDIR = 'D:\codex\Causalis\.matplotlib'
.\.venv\Scripts\python.exe -m audit.repro_dml_core
```

Критичность: P1 — исправить до опоры на соответствующий результат для принятия решений; P2 — существенный дефект отдельной опции/диагностики; P3 — точность документации или ограничение API. Confidence у приведённых ниже воспроизведений высокий; перенос вывода на все возможные DGP не предполагается.

## Покрытие

| Область | Что просмотрено | Что проверено исполнением | Ограничения |
|---|---|---|---|
| `unconfoundedness/model.py`, `_utils.py`, `_score_utils.py`, `_diagnostic_utils.py` | Scores, cross-fitting, sample snapshot/fingerprint, overlap/drop, weight normalization, relative effects, sensitivity elements, estimator state | ATTE relative inference, repeated fit, drop+weights, invalid propensity sensitivity | Не проводилась большая Monte Carlo coverage study для каждого learner |
| `unconfoundedness/refutation/unconfoundedness/*` | Balance, sensitivity bounds/RV/RVa, benchmarks, protocol/calibration, love plot | Infinite SMD, negative nu2, RVa threshold, ATT nuisance derivative | Полный sensitivity protocol не запускался повторно |
| `unconfoundedness/refutation/score/*`, `refutation/_shared.py` | Score reconstruction, finite-basis derivatives, OOS moments, tail diagnostics, residual/influence plot inputs and alignment | Тождественно нулевой OOS statistic | Визуальный render каждого plot не выполнялся |
| `unconfoundedness/refutation/overlap/*` | Raw/postprocessed propensity, common support, ESS/tails, calibration/reliability/native importance | Семантический просмотр; числовые edge cases входят в общий аудит | Calibration ECE/slope — эвристики, не доказательство ignorability |
| `multi_unconfoundedness/model.py`, `_utils.py` | Arm scores, class support, generalized propensity alignment, simplex processing, ATE/ATTE relative inference, sensitivity | Noiseless ATTE IF, multi-arm benchmark | Совместная covariance между active-arm contrasts в публичном API не реализована |
| `multi_unconfoundedness/refutation/*` | Pairwise overlap/balance/score reconstruction, sensitivity bounds/benchmarks, plot input handling | Infinite SMD, OOS p-values, strong-confounder benchmark | Latent-U oracle генераторов отдельно проверяет общий DGP audit |
| `gate/model.py`, `gate_plot.py`, `_orthogonal.py` | ID/group alignment, strict partitions, GATE/GATET signals, HC0–HC3, pointwise covariance and contrasts | Численная cancellation GATE SSE | Группы должны быть pre-treatment и заранее фиксированными; API не может проверить происхождение группы |
| `uplift/model.py`, `policy.py` | Lazy T-learner cache, scoring schema, greedy objective/splits, disjoint evaluation, policy-vs-none/all paired signals | CATE после refit, estimator state | Exact global tree optimization, cost/capacity constraints отсутствуют и это документировано |
| Scenario `dgp.py` и `__init__.py` в обоих unconfoundedness пакетах | Wrapper configuration, scales/logit links, treatment encodings, oracle descriptions, exports | Математическая проверка copula correlation claim | Core DGP engine находится вне этой узкой области и покрыт отдельно |

## Десять основных проблем по приоритету

| № | ID | Уровень | Проблема | Статус |
|---:|---|---|---|---|
| 1 | DML-01 | P1 | MultiTreatmentIRM ATTE: неправильная IF и SE | Детерминированное воспроизведение + ratio derivation |
| 2 | DML-10 | P1 | Multi-arm sensitivity benchmark оценивает объяснимость residuals полного модели вместо confounder gain | Воспроизведение сильного confounder |
| 3 | DML-07 | P1 | Отрицательная nu2 превращается в нулевой confounding bound | Public API воспроизведение |
| 4 | DML-03 | P1 | Повторный fit сохраняет CATE cache и старые scalar estimates/sensitivity state | Public API воспроизведение |
| 5 | DML-02 | P2 | Binary ATTE relative CI пропускает denominator IF baseline | Детерминированное воспроизведение + ratio derivation |
| 6 | DML-11 | P2 | ATTE sensitivity `m_alpha` теряет ортогональность | Численная nuisance derivative + functional derivation |
| 7 | DML-05 | P2 | Infinite SMD исключается из failure summary; получается PASS | Binary и multi воспроизведения; объединить с общим balance defect |
| 8 | DML-06 | P2 | OOS moment p-values равны 1 по конструкции на equal ATE folds | Точное алгебраическое тождество |
| 9 | DML-08 | P2 | RVa не является порогом собственного bias-aware CI | Числовое воспроизведение |
| 10 | DML-04 | P2 | `overlap_policy='drop'` не согласует custom weights с retained sample | Public API ValueError |

### DML-01. Multi-arm ATTE: знаменатель sample treatment share пропущен в IF

Места: [model.py:754](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/model.py:754), [model.py:755](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/model.py:755), [model.py:775](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/model.py:775). Та же reconstruction повторяется в [score_validation.py:172](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/refutation/score/score_validation.py:172).

Для arm k обозначим `A_i = d_k*(Y-g0) - d0*(m_k/m0)*(Y-g0)`, `p_k=E[d_k]`. Point estimate `mean(A)/mean(d_k)` верен при нужных assumptions. Но это ratio estimator. Для iid population ATT правильная IF:

```text
IF_k = (A_i - theta_k*d_ki)/p_k
     = psi_b_ki - theta_k*d_ki/p_k.
```

Код использует `psi_a=-1`, соответственно `IF=psi_b-theta`. Эмпирические roots совпадают, influence functions различаются. Разница `theta*(d_k/p_k-1)` не исчезает относительно масштаба SE при росте n. Направление ошибки variance не фиксировано: добавленный компонент может как увеличивать, так и уменьшать variance через covariance.

Репродукция: n=300, 3 arms поровну, Y(0)=10, Y(1)=12, Y(2)=14, outcome nuisances — constants без ошибки. ATT [2,4] точно идентифицируются по каждому sample с support. Correct IF и SE [0,0]. Фактически SE `[0.1635721640, 0.3271443280]`. Это не обычная конечновыборочная поправка `ddof`.

Исправление: отдельный Jacobian/score derivative на каждый contrast, `psi_a_k=-d_k/p_k`, либо непосредственно корректная ratio IF и covariance. Согласовать model, score diagnostics, tests и документацию. Текущий `tests/inference/test_multi_treatment_irm.py:317` прямо фиксирует неправильный `psi_a=-ones`; его нельзя использовать как независимое доказательство корректности.

Сравнение: binary IRM этой библиотеки использует `psi_a=-w` для ATTE правильно. Аналогичный принцип есть в [официальном score DoubleMLIRM](https://raw.githubusercontent.com/DoubleML/doubleml-for-py/main/doubleml/irm/irm.py). Это стандартная ratio derivative, а не требование скопировать API другой библиотеки.

### DML-10. Multi-arm benchmarking: сильный известный confounder получает strength почти ноль

Места: [sensitivity.py:1101](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/refutation/unconfoundedness/sensitivity.py:1101), [sensitivity.py:1105](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/refutation/unconfoundedness/sensitivity.py:1105), [sensitivity.py:1154](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/refutation/unconfoundedness/sensitivity.py:1154), [sensitivity.py:1158](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/refutation/unconfoundedness/sensitivity.py:1158).

Short model действительно refit, однако его predictions/elements не участвуют в `r2_y`, `r2_d`, `rho`: код регрессирует residuals **полного** модели на covariate, который уже вошёл в полный модели. При oracle nuisances `E[Y-g(D,X)|D,X]=0` и `E[D-m(X)|X]=0`; значит эти regressions имеют population R² ноль для любого included X. Чем качественнее nuisances, тем ближе benchmark к нулю независимо от истинной силы confounder. Для multi-IRM treatment strength дополнительно нельзя в общем заменить обычным residual R² pairwise treatment contrasts: нужен соответствующий Riesz representer.

Репродукция: 4000 observations, z∈{-1,1}; baseline/treatment proportions `.8/.1` и `.1/.8` при двух z; Y=10+5z+arm_effect+noise, второй covariate независим. После удаления z получены effect shifts `[-7.7852446,-3.9324498]`, но `r2_y=9.06e-9`, `r2_d≈[4.99e-7,1.61e-9]`.

Практический риск: пользователь переносит почти нулевую силу наблюдаемого confounder на hidden-confounding сценарий и получает искусственную устойчивость. Если эти показатели предназначены исключительно для проверки residual misspecification, это допустимая другая задача, но их нельзя называть sensitivity benchmark силы исключённого confounder.

Исправление: калибровать outcome/Riesz gains по sensitivity elements long/short, actual theta shift и совпадающим folds. Binary benchmark уже идёт по этому пути. Принцип long/short decomposition дан в [Chernozhukov et al., Long Story Short](https://arxiv.org/abs/2112.13398); рабочая реализация — [gain_statistics DoubleML](https://raw.githubusercontent.com/DoubleML/doubleml-for-py/main/doubleml/utils/gain_statistics.py).

### DML-07. Невалидная variance representer превращается в отсутствие bias

Места: [binary sensitivity.py:601](D:/codex/Causalis/causalis/scenarios/unconfoundedness/refutation/unconfoundedness/sensitivity.py:601), [multi sensitivity.py:651](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/refutation/unconfoundedness/sensitivity.py:651). Аналогичный clamp есть в низкоуровневых bias helpers.

Ортогональная оценка `nu2=mean(2*m_alpha-rr²)` может стать отрицательной при плохой propensity nuisance. Отрицательное значение не означает, что истинная variance равна нулю. Код считает `sqrt(max(sigma2*nu2,0))` и возвращает нулевой bound без предупреждения/invalid status.

Репродукция через IRM.fit/estimate: treatment balanced, `DummyClassifier(constant=0)` + clipping .01, Y содержит noise. `nu2=-4798.4899500`; sensitivity strengths `.5/.5` дают `bound_width=0` и CI, равный обычному sampling CI.

Исправление: reject/invalid result с причиной и learner diagnostics; либо явно выбранная положительная estimator/fallback с отдельным статусом. Не заменять неудачную оценку на утверждение о robustness. [DoubleMLFramework](https://raw.githubusercontent.com/DoubleML/doubleml-for-py/main/doubleml/double_ml_framework.py) проверяет отрицательные variance elements и связывает ошибку с quality of learners.

Смежная проблема: отсутствие sensitivity elements также молча даёт bound=0. Например estimate с `store_diagnostics=False`, переданный без model reference, не содержит информации для расчёта bound. Корректный API должен различать «данных нет» и «доказанный нулевой bound».

### DML-03. Повторный fit не инвалидирует связанные результаты

Места: [uplift/model.py:86](D:/codex/Causalis/causalis/scenarios/uplift/model.py:86), [IRM.fit:1129](D:/codex/Causalis/causalis/scenarios/unconfoundedness/model.py:1129), [MultiTreatmentIRM.fit:672](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/model.py:672).

Lazy CATE models кешируются при первом predict. После `fit(new_data)` проверка `hasattr(_uplift_g0_model_,_uplift_g1_model_)` сразу возвращает старые models. Изменение nuisance learner или schema даёт тот же риск. Scalar attributes `coef_`, `se_`, `psi_`, summaries и sensitivity state также не очищаются в обоих fit methods.

Два public API воспроизведения:

1. Training tau=2; predict_cate=2; повторный fit на tau=7; predict_cate всё ещё 2. Свежий IRM даёт 7.
2. IRM estimate tau=2; fit на tau=7; sensitivity_analysis вызывается до нового estimate и принимает stale `coef_` как fitted result: sensitivity theta=2, тогда как estimate на новой выборке даёт 7.

Исправление: единая функция очистки всех производных estimate/scoring artifacts при успешном новом fit; cache version tied to fit fingerprint/schema/learner configuration. После нового fit coefficient inference должен требовать новый estimate. Для исключения partially fitted state предпочтителен commit нового fit state после успешной cross-fit стадии.

### DML-02. Relative ATT: baseline IF должен учитывать treated denominator

Место: [model.py:1306](D:/codex/Causalis/causalis/scenarios/unconfoundedness/model.py:1306).

Пусть `w=D/p`, `odds=m/(1-m)` и

```text
Z0_i = D_i*g0(X_i) + (1-D_i)*odds_i*(Y_i-g0(X_i));
mu0_ATT = E[Z0]/p;
psi_mu = Z0_i/p;
IF_mu = psi_mu - w_i*mu0_ATT.
```

Binary absolute ATT IF уже корректно учитывает `w*theta`. Но baseline код центрирует как `IF_mu=psi_mu-mu0`; он пропускает `-mu0*(w-1)`. Для relative effect `r=100*theta/mu0` нужно `IF_r=100*(IF_theta/mu0-theta*IF_mu/mu0²)`. Вставка неправильного baseline IF оставляет лишний treated-share component.

Репродукция Y(0)=10,Y(1)=12,n=120: relative ATT точно 20% при любом достаточном sample; correct SE=0. Absolute ATT SE в библиотеке 0, но relative SE=1.8333969941 процентных пункта. Аналогичная ошибка может влиять на baseline-low-signal guard.

Исправление: score-aware baseline ratio IF и covariance. Для normalized custom-weight ATE также derivation должен быть ratio-aware; там текущая approximate inference заранее отмечена warning/model_options. Это не устраняет неправильную асимптотическую IF, но снижает риск молчаливого заблуждения. У multi-arm relative ATT оба текущих centered components теряют один и тот же treatment denominator, который сокращается в relative ratio; **эта binary ошибка не переносится автоматически на multi relative formula**.

### DML-11. ATT sensitivity nu2 score не ортогонален propensity nuisance

Место: [sensitivity.py:173](D:/codex/Causalis/causalis/scenarios/unconfoundedness/refutation/unconfoundedness/sensitivity.py:173).

Для функционала `E[w*(g1-g0)]` representer `rr=w_bar*(D/m-(1-D)/(1-m))`, а `m(W,rr)=w*w_bar*(1/m+1/(1-m))`. Код подставляет `w_bar²` вместо `w*w_bar`. При обычных X-only weights они совпадают; при ATT `w=D/p`, `w_bar=m/p` — нет. Population means при истинных nuisances совпадают после conditioning, но заменить observed functional его условным ожиданием внутри orthogonal score нельзя без дополнительной augmentation.

Чистая проверка orthogonality: exact design p=m0=.2, fixed population p, perturb m на ±1e-5. Производная ожидаемого `nu2` текущего score по m =62.4999999978; canonical functional derivative ≈-1.21e-8. Значит slow ML nuisance error может входить первым порядком в sensitivity statistic. Ссылка на DoubleML-style элементы не делает эту замену корректной; [официальная IRM реализация](https://raw.githubusercontent.com/DoubleML/doubleml-for-py/main/doubleml/irm/irm.py) использует observed weight times representer weight.

Исправление: вывести весь ATT sensitivity score, включая estimator normalization, и реализовать его целиком. Для sample denominator `p=mean(D)` ratio derivative `nu2` дополнительно содержит `-2*nu2*(D/p-1)`; часть этого вклада при **constant** m может случайно совпасть с текущей заменой w→w_bar, что не является доказательством корректности при variable m. Общая `sigma2=E[(Y-g(D,X))²]` не является treated-normalized quantity: отдельную denominator correction к её score добавлять без derivation не надо.

### DML-05. SMD=∞ исключается из failure aggregation

Места: [binary balance:205](D:/codex/Causalis/causalis/scenarios/unconfoundedness/refutation/unconfoundedness/unconfoundedness_validation.py:205), [multi balance:267](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/refutation/unconfoundedness/unconfoundedness_validation.py:267), [multi balance:309](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/refutation/unconfoundedness/unconfoundedness_validation.py:309).

При X=D признак внутри каждого arm константен, уровни различаются; pooled variance=0 и SMD=∞. Это максимальная separation. Код корректно получает ∞, затем `isfinite` убирает его из summary. Если других finite SMD нет, `pass=True`, violation fraction=0. При наличии finite balanced features infinite feature всё равно игнорируется.

Репродукция binary/multi: SMD `[Infinity]`, PASS true. Объединить в общем отчёте с родственными defects `shared/confounders_balance.py`; не считать разные реализации независимыми научными проблемами.

Исправление: inf считать нарушением с RED; NaN — unavailable/invalid, а не PASS. В denominator fraction использовать число применимых признаков, явно учитывая separation.

### DML-06. OOS aggregate tests вырождаются в тождество

Места: [binary score:290](D:/codex/Causalis/causalis/scenarios/unconfoundedness/refutation/score/score_validation.py:290), [binary score:323](D:/codex/Causalis/causalis/scenarios/unconfoundedness/refutation/score/score_validation.py:323), [multi score:447](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/refutation/score/score_validation.py:447), [multi score:476](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/refutation/score/score_validation.py:476).

ATE psi_a=-1. При K одинаковых folds размером q, средних b_k, код берёт `theta_minus_k=sum_{j≠k}b_j/(K-1)` и агрегирует fold score means. Но

```text
sum_k q*(b_k - theta_minus_k) = 0
```

для **любых** b_k. Значит обе t-statistics нулевые, p-values=1 даже при громадных различиях между folds. Unequal fold sizes нарушают точное тождество, но тогда statistic в основном зависит от небольших различий размеров и не получает автоматически valid null distribution. В дополнение scores training complement построены nuisance models, обученными в том числе на test fold; это не действительно независимое refit/evaluation split.

Репродукция fold scores с means около 0,100,200,300: leave-fold residual means `[-200,-66.6667,66.6667,200]`, binary и multi p=1.

Классификация: если задумка лишь descriptive fold stability, это ограничение дизайна и неверное наименование `test/p_value/GREEN`, а не estimator bug. Однако публичный диагностический output действительно выставляет GREEN на вырожденном тесте. Исправление: отдельная held-out проверка параметра и nuisances с provenance, либо корректный heterogeneity/overidentification test; до этого сохранить fold table как descriptive и убрать pretend p-values.

### DML-08. RVa использует fixed original SE, хотя собственный CI меняет SE при bias

Места: [binary sensitivity:617](D:/codex/Causalis/causalis/scenarios/unconfoundedness/refutation/unconfoundedness/sensitivity.py:617), [multi sensitivity:665](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/refutation/unconfoundedness/sensitivity.py:665).

RVa рассчитывается closed form из `abs(theta-H0)-z*original_se`. Затем bias-aware CI строится с `var(psi ± correction(strength))`, поэтому `se_lower/upper` зависят от того же strength. RVa не инвертирует фактически публикуемый CI.

Репродукция на корректно центрированных synthetic sensitivity elements: reported RVa .4453738155; подставляем equal strengths r2_y=r2_d=RVa и получаем lower CI=.1581811778, H0=0 всё ещё вне CI. Направление расхождения меняется с covariance between psi and bias correction.

Исправление: численно решать crossing соответствующей confidence bound с H0, учитывая IF covariance; либо явно назвать показатель fixed-SE approximation. Дополнительно binary RV означает equal r2_y/r2_d, а multi RV — minimum r2_d при фиксированном cf_y; одинаковое имя в summaries требует явного различия. [Официальный DoubleML sensitivity guide](https://docs.doubleml.org/stable/guide/sensitivity.html) определяет RVa через interval crossing.

### DML-04. Drop sample поддерживается, но custom weights остаются full-length

Места: [model.py:912](D:/codex/Causalis/causalis/scenarios/unconfoundedness/model.py:912), [model.py:1043](D:/codex/Causalis/causalis/scenarios/unconfoundedness/model.py:1043).

Overlap mask подрезает Y,D,X,nuisances и IDs. Переданный `self.weights` не подрезается. `estimate` ожидает length retained n и получает исходное n. Результат — fit успешно, estimate падает.

Репродукция weights=ones(120), propensity зависит от x и 60 rows retained: `weights must have shape (n,) with n=60, got shape (120,)`. Это также затрагивает weights dictionaries и sensitivity benchmark short refits.

Исправление: зафиксировать immutable full-sample weights на fit, применять ту же mask к weights/weights_bar, нормировать после retention; проверить совпадение initial lengths до дорогого fitting. Если сочетание не поддерживается по дизайну, отвергать его до fit и документировать.

## Дополнительный подтверждённый численный дефект

**DML-09, P2:** [gate/model.py:609](D:/codex/Causalis/causalis/scenarios/gate/model.py:609) считает within-group SSE как `sum(phi²)-sum(phi)²/n`, что теряет precision для большого среднего и небольшого разброса. На phi=1e8±1,n=100 HC0 SE должен быть .1, фактически 0. В другом порядке сложения возможен negative SSE и RuntimeError. Это условный numerical bug для больших signal levels; он не означает, что обычные GATE на масштабе 0–10 некорректны. GATET uses аналогичную formula для descriptive `std_phi`, но inference там считает sum of squared centered moment residuals, поэтому нельзя автоматически приписать его SE тот же defect. Исправление GATE — centered two-pass bincount или stable online group variance; скорость O(n+groups) сохраняется.

## Фактические неточности в документации исходников

| Уровень | Место | Неточность | Как исправить |
|---|---|---|---|
| P2 | `unconfoundedness/refutation/unconfoundedness/sensitivity.py:5–13`, `:1647–1651` | Для nonlinear IRM treatment lever объясняется обычным partial R² treatment residual, как в линейной regression sensitivity. В общем случае lever относится к Riesz representer variation | Дать IRM-specific parameter definition, отдельно PLR simplification; сослаться на [Long Story Short](https://arxiv.org/abs/2112.13398) |
| P2 | `sensitivity.py:1637–1643`, model.sensitivity_analysis docstrings | r2_y описан как доля объяснённой residual outcome variance, но code использует odds r2_y/(1-r2_y) там, где стандартный cf_y означает непосредственно эту долю | Либо изменить formula/API, либо явно определить нестандартный параметр и conversion to cf_y; ordinary r2=.5 сейчас даёт cf_y=1 вместо .5 |
| P2 | `multi_unconfoundedness/model.py:183–188` | ATTE psi_a=-1 заявлен как orthogonal inference score | Переписать после DML-01; point estimate root не обосновывает IF |
| P2 | Описания `RVa`/faithful CI | Fixed-SE critical strength назван robustness value для одновременно изменяющегося CI | Реализовать crossing либо явно пометить approximation |
| P3 | `multi_unconfoundedness/dgp.py:313–315`, `:484–488` | Corr(X_i,X_j)=.3^distance названа correlation смешанных observed covariates | Это latent Gaussian copula correlation, а не их observed Pearson correlation. Например для Bernoulli(.5) marginals при latent rho=.3 observed corr=(2/pi)*asin(.3)≈.194 |
| P3 | `unconfoundedness/model.py:73` | n_folds default5 в prose | Binary constructor actual default4; синхронизировать generated reference. MultiTreatmentIRM default5 описан правильно |
| P3 | `gate/model.py:436–438` | Docstring говорит averaging z over treated units. Implementation correctly sums z over all group observations then divides by treated count | Сказать `sum(z_i*1{G=g})/sum(D_i*1{G=g})`; controls входят в numerator correction |
| P3 | `uplift/model.py` / scenario overview | Lazy T-learner может восприниматься как DML/DR CATE | Текст самого метода честно называет T-learner. В overview и examples сохранять это название; scalar DML fit не превращает его CATE scorer в orthogonal learner |

## Соответствие современным практикам и ten feature priorities

Базовые AIPW/ATT scores и sample splitting соответствуют established DML framework [Chernozhukov et al.](https://arxiv.org/abs/1608.00060). Отсутствие новой статьи/модной модели само по себе не defect. Ранжирование ниже ориентировано на прикладную пользу и проверяемые assumptions, а не на обещание «самой современной библиотеки».

| Приоритет | Дополнение | Почему полезно | Научная/инженерная опора |
|---:|---|---|---|
| 1 | Общий score/IF contract и independent oracle/coverage tests | Предотвращает повтор DML-01/02/11 между model, diagnostics и sensitivity | Functional ratio derivatives, established orthogonal estimation |
| 2 | Повторное cross-fitting `n_rep>1`, public fixed folds/external predictions | Сейчас n_rep>1 явно отвергается; partition variability не учитывается. Повторение + правильная aggregation делает результаты устойчивее | [DML paper](https://arxiv.org/abs/1608.00060) |
| 3 | DR-learner для CATE поверх cross-fitted pseudo-outcomes | Current lazy T-learner — хорошая простая baseline, но не robust CATE learner | [Kennedy, DR CATE](https://arxiv.org/abs/2004.14497) |
| 4 | R-learner как альтернативный heterogeneous-effect estimator | Orthogonal residual loss может использовать structure CATE, learner tuning и flexible regularization | [Nie & Wager](https://arxiv.org/abs/1712.04912) |
| 5 | Cluster-aware splits и standard errors | `user_id` как уникальный identifier не заменяет cluster handling; row-wise CV нарушает independence для household/company/panel data | [Chiang et al.](https://arxiv.org/abs/1909.03489) |
| 6 | Совместная IF covariance / multiplier bootstrap для multi contrasts и GATE | Shared baseline создаёт correlated contrasts; нужны formal arm-vs-arm tests, simultaneous CI и согласованная multiplicity policy | DML inference framework; уже есть useful `GateEstimate.contrast` |
| 7 | Версионированная sensitivity API с корректной gain calibration и numeric RVa | Binary и multi semantics сейчас различаются; ошибочный benchmark особенно рискован | [Long Story Short](https://arxiv.org/abs/2112.13398) |
| 8 | Cost/capacity policy и exact shallow-tree option | Greedy sign-benefit policy не учитывает price/capacity; can miss interaction requiring zero-gain first split, что уже честно документировано | [Athey & Wager](https://arxiv.org/abs/1702.02896) |
| 9 | Honest subgroup discovery workflow | Пользователь может построить groups по outcome/same-sample CATE и получить selection bias; current pre-specified GATE API assumption разумна, но процесс можно поддержать | Независимые discovery/evaluation splits; policy module уже задаёт хороший pattern |
| 10 | Propensity processing/config с raw/post metadata и choice of overlap estimand | Clipping, dropping, calibration и overlap-weighting решают разные задачи; не надо подавать clip/drop как interchangeable estimation detail | Current DoubleML PS processor; явный target population contract |

Эти предложения не требуют реализовывать все research methods сразу. Сначала устранить подтверждённые score/sensitivity/lifecycle errors, затем добавлять API и сравнивать независимые empirical coverage/accuracy baselines. Отдельное направление общего аудита проверяет более новые работы 2024–2026 и дополняет этот established-method shortlist.

## Производительность без изменения статистического качества

В этих модулях core scores уже NumPy-vectorized; после fit `estimate` берёт retained target snapshots и не переобучает nuisances. Поэтому утверждение «главное замедление — pandas» нельзя принять без измерений. Основной fit обычно делает 3×fold learner fits (multi — (K+1)×fold); CatBoost/feature importance/diagnostics могут доминировать. Общее направление performance audit измеряет это отдельно.

Локальные кандидаты, не меняющие scores:

1. Общий read-only fit array bundle `(X,y,d,IDs)` с единственным schema validation: нынешний `get_df`/DataFrame-to-array path и full fingerprint создают дополнительный O(np) проход/copy.
2. Сохранить lightweight diagnostics option; не копировать X без необходимости. Указать реальные memory costs, поскольку model всё равно удерживает `self.data` DataFrame.
3. Хранить plot caches как views/shared immutable arrays и делать copy только при пользовательской mutation. Сейчас кеши преимущественно views, но downstream payloads/snapshot могут удваивать arrays; измерить peak RSS.
4. Stable centered group SSE посредством двух `bincount` passes: исправляет DML-09 с O(n+g), не требует O(n×g) dummy matrix.
5. Для `UpliftPolicyTree` можно pre-sort feature order и переиспользовать sorting между depths вместо repeated argsort на каждой node; benchmark shallow depths и correctness одинаковых ties/thresholds.
6. Single fold scheduling budget: parallel across folds + learner threads=1 versus serial folds + learner parallelism. Current defaults снижают oversubscription для default CatBoost при n_jobs≠1 правильно.
7. Single-class outcome arms уже избегают needless model.fit; распространить constant-valued regression arm fast path только при корректном learner contract и изменении desired behavior.
8. Persist explicit out-of-fold prediction artifacts/fold assignments для sensitivity short refits и comparing learners; нельзя «оптимизировать» benchmark reuse prediction полного модели вместо необходимого short refit.
9. Native numeric input adapter для columnar/sparse matrices, если learners поддерживают их, с минимальным materialization. CatBoost categorical feature support требует отдельного schema path: float coercion сейчас ограничивает возможности, а не просто скорость.
10. Benchmark end-to-end fit, estimate, diagnostics, scoring separately на n,p,K; фиксировать learners, folds, seed, parallelism, memory и statistical error. Repeated estimate ускорение бесполезно выдавать за fit speedup; сравнение с аналогами должно совпадать по target/overlap/splits.

Недопустимые shortcuts: in-sample nuisance predictions, разные folds при сравнении long/short, применение full-model residuals как omission strength, отключение uncertainty correction, float32 для sensitive score divisions без error budget.

## Что не подтверждено как отдельный bug

- Hájek и normalized weighted ATE denominator variability игнорируются в current SE, но это отмечено explicit warnings/model_options. Нужна exact ratio inference feature; не представлять это как скрытое обещание exact inference.
- Multiclass lower clipping + simplex renormalization может опустить final probabilities чуть ниже threshold, но docstring прямо говорит threshold **до** renormalization. Это не доказанная implementation error; при необходимости предложить lower-bounded simplex projection с новым контрактом.
- CATE T-learner недостаточно robust по сравнению с DR/R learners, но метод честно описан и не имеет scalar causal CI. Это feature gap, а не автоматически неправильные prediction values.
- GATE covariance diagonal корректна для fixed mutually exclusive exhaustive partition и iid sampling; overlapping groups/learned groups/cluster sampling требуют другого контракта. Нельзя объявить matrix diagonal неверной без этих дополнительных условий.
- Policy tree greedy optimization не global optimum; это явно documented limitation.
- Отсутствие classifier для ml_m binary допускает regression probabilities с warning/clipping. Полезнее stricter validation/config, но сама возможность не является доказанным defect.
- Core latent-U oracle errors в DGP находятся в отдельном общем направлении; в этот список они не продублированы.
