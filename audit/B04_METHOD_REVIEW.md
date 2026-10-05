# B04: независимая методологическая проверка DiD

Дата: 2026-10-05. Исходная ветка блока: `codex/correctness-roadmap`, checkpoint `f57f2d3`. Проверка выполнена независимо от реализации aggregation и cell IF. Sensitivity analysis не рассматривался. Все Python checks запускались через `.venv\Scripts\python.exe`.

## Выбор метода и первичные источники

В B04 сохраняется фактический traditional estimator: logistic MLE с существующим ridge, обычный control OLS и отдельно нормированные treated/control means. Inference должен включать производные всех этих шагов. Это согласуется с структурой [официального DRDID traditional panel estimator](https://github.com/pedrohcgs/DRDID/blob/85807cfbddbd64cc6f3f8ba37f52d07c6c3acc65/R/drdid_panel.R#L140), который отдельно учитывает OLS, logit и нормировки. [Normalized IPW source](https://github.com/pedrohcgs/DRDID/blob/85807cfbddbd64cc6f3f8ba37f52d07c6c3acc65/R/std_ipw_did_panel.R#L114) также содержит вклад оценивания propensity.

[Sant'Anna–Zhao, Appendix A.1](https://arxiv.org/html/1812.01723) обосновывает необходимость всех nuisance-estimation corrections для generic parametric first steps. Отдельный improved estimator использует IPT propensity и propensity-weighted WLS; его inference не требует этих first-step corrections при соответствующих условиях. Поэтому смена только формулы score не превращает traditional MLE/OLS в improved DRDID. [Официальное описание improved estimator](https://psantanna.com/DRDID/reference/drdid_imp_panel.html).

[Официальный did aggregation source](https://github.com/bcallaway11/did/blob/74b88eb07f1faa644df1271055a0f77848f6550c/R/compute.aggte.R#L693) добавляет влияние оценивания cohort probabilities в simple, dynamic и calendar aggregations. Там используются full-cohort probabilities. Ниже независимо выведено обобщение для уже существующих **complete-pair counts** Causalis; это сохраняет point-estimate policy при неполном panel.

SHA public `master` branches получены через read-only GitHub API (`gh api .../commits/master --jq .sha`). Immutable DRDID `drdid_panel.R` и did `compute.aggte.R` дополнительно открыты через web; source/formula checks относятся к этим snapshot, а не к будущему состоянию веток.

## SC-01/03: независимый вывод IF фактического cell estimator

Здесь `E_n` — среднее внутри фактически используемой complete-pair treated+control cell, `X` включает intercept, `D` — индикатор target cohort. Определим:

\[
p_i^0=\operatorname{expit}(X_i^\top\hat\gamma),\qquad
p_i=\operatorname{clip}(p_i^0,c,1-c),\qquad
w_{ti}=D_i/E_n[D],\quad
w_{ci}=\frac{(1-D_i)p_i/(1-p_i)}{E_n[(1-D)p/(1-p)]}.
\]

Для DR/AIPW `r_i=\Delta Y_i-X_i^\top\hat\beta`; для IPW `r_i=\Delta Y_i`, без `beta` contribution. `eta_t=E_n[w_t r]`, `eta_c=E_n[w_c r]`, `theta=eta_t-eta_c`. Прямое влияние наблюдения при фиксированных nuisance:

\[
\phi_i^{direct}=w_{ti}(r_i-\eta_t)-w_{ci}(r_i-\eta_c).
\]

Это IF двух ratio means. Выражение `(w_t-w_c)r-w_t theta` совпадает с ним только при `eta_c=0`; normalized IPW этого не гарантирует. При добавлении общего тренда к `delta_y` обе mean centers сдвигаются вместе, а эта IF сохраняется.

Пусть `R=diag(0,1,...,1)`, ridge `lambda` фиксирован как часть estimator. Propensity first-order equation:

\[
E_n[X(D-p^0)]-\lambda R\hat\gamma=0,\qquad
H_\gamma=E_n[p^0(1-p^0)XX^\top]+\lambda R.
\]

При загрязнении эмпирической меры penalty не получает observation weight. Поэтому:

\[
IF_{\gamma,i}=H_\gamma^{-1}\{X_i(D_i-p_i^0)-E_n[X(D-p^0)]\}.
\]

Centering необходимо при fixed nonzero ridge; raw logit score в среднем не равен нулю. В Hessian и nuisance score нужна **raw** logistic probability, поскольку оптимизируется unclipped logistic loss. В производной control odds нужна производная **clipped** probability:

\[
a_i=1\{c<p_i^0<1-c\},\qquad
B_\gamma=-E_n[w_c(r-\eta_c)aX].
\]

Saturated propensity имеет нулевую производную clipped odds. Формула предполагает отсутствие observation ровно на clipping kink; она не создаёт обычной гладкой асимптотики на самой границе.

Для control OLS:

\[
H_\beta=E_n[(1-D)XX^\top],\qquad
IF_{\beta,i}=H_\beta^{-1}(1-D_i)X_i r_i,\qquad
B_\beta=-E_n[(w_t-w_c)X].
\]

При full-rank design корректнее численно применять SVD исходной control design, чем инвертировать Gram matrix. При structural rank deficiency pseudoinverse описывает выбранный minimum-norm функционал только при стабильном rank; он не устраняет identification problem, отмеченную existing diagnostics.

Полная cell IF:

\[
\phi_i=\phi_i^{direct}+B_\gamma^\top IF_{\gamma,i}
       +B_\beta^\top IF_{\beta,i},
\]

где последний член отсутствует для IPW. Для embedding в общий panel из `N` units cell IF умножается на `N/n_cell`, а для units вне cell равна нулю. Это обеспечивает `N^{-1} sum_i phi_i` для того же estimator; не нужно дополнительного влияние вероятности попадания в cell, потому что локальная IF уже центрирована.

Статически проверена реализованная `_cell_influence_scores`: знаки обоих nuisance contributions, `n_cell * pinv(X_control)` OLS map, centered penalized-logit score, raw probability Hessian, strict-interior clipping derivative и intercept-only cancellation согласуются с этим независимым выводом. New `test_cell_if_matches_refitted_empirical_contamination` использует отдельный `scipy.optimize.root` и weighted least squares, заново оценивая nuisance для каждой perturbation, а не повторяя IF formula. Root/implementing agent сохраняет execution/Monte Carlo evidence отдельно.

После дополнительного numeric review likelihood solver усилен через augmented weighted design:

\[
A=\begin{bmatrix}
\operatorname{diag}(\sqrt{p^0(1-p^0)/n_{cell}})X\\
\operatorname{diag}(\sqrt{\lambda(0,1,\ldots,1)})
\end{bmatrix},\qquad A^\top A=H_\gamma,
\qquad H_\gamma^+B_\gamma=A^+(A^{+\top}B_\gamma).
\]

При `lambda=0` penalty rows можно не создавать. SVD исходной `A` сохраняет направления, которые pseudoinverse Gram Hessian мог бы преждевременно потерять после возведения condition number в квадрат. Статически проверены augmented rows, transpose/dimensions и равенство inverse map; новая реализация согласуется с derivative выше. Шесть regression cases (DR/AIPW/IPW × covariate scales `1e6/1e7`) по сообщению implementing agent сначала провалились на Gram-pinv, затем вошли в **34 passing focused cases** на SVD map. Они преобразуют `gamma` аналитически при `ridge=0`, поэтому проверяют **IF solver**, а не масштабную инвариантность optimizer/full fit. При ненулевом fixed ridge смена масштаба covariates также меняет сам penalty functional; универсальной scale invariance не заявлено. Machine precision, rank threshold и separation остаются ограничениями.

Fixed ridge и active clipping могут менять probability limit. Полный sandwich оценивает uncertainty фактически заданного plug-in функционала. Causal ATT дополнительно требует parallel trends, подходящих comparison units, overlap и корректности хотя бы нужной nuisance specification. При опоре только на propensity model нужны условия, при которых ridge bias исчезает и clipping не меняет нужные true odds. Правильная outcome model может сохранять DR point consistency; исправленный IF сам по себе не исправляет неверные causal assumptions.

## SC-04: complete-pair population mixture

Для выбранного набора cells `J` определим индикатор на общей unit axis:

\[
T_{ij}=1\{i\text{ принадлежит treated cohort cell }j
\text{ и имеет оба outcome: base и target}\},\quad
q_j=E_N[T_j]=n_{treated,j}/N,\quad S=\sum_{j\in J}q_j.
\]

Simple/calendar/event estimator уже использует

\[
w_j=q_j/S,\qquad \alpha=\sum_j w_j\theta_j.
\]

По quotient rule его population IF:

\[
IF_{\alpha,i}=\sum_jw_j IF_{\theta_j,i}
 +\frac{1}{S}\sum_j(T_{ij}-q_j)(\theta_j-\alpha)
=\sum_jw_j IF_{\theta_j,i}
 +\frac{1}{S}\sum_jT_{ij}(\theta_j-\alpha).
\]

Последнее равенство использует `sum_j q_j(theta_j-alpha)=0`. Один unit может участвовать в нескольких cells: вклады суммируются на той же unit axis, поэтому между-cell covariance и повторение cohort indicators сохраняются автоматически. Controls дают вклад через cell IF, но не через treated mixture counts.

**Нельзя** заменять `T_ij` полным cohort indicator при сохранении `n_treated` complete-pair denominator. При missing outcomes `q_j` действительно меняется между cells одного cohort. Cohort aggregation сейчас — равное среднее доступных post cells; эти веса фиксированы, поэтому отдельного cohort-share term в этом конкретном aggregate нет.

Это mixture cell effects среди complete-pair treated subpopulations. Она не становится full-cohort ATT автоматически при информативной missingness. Если требуется full-cohort estimand, нужна отдельная missingness policy/identification strategy; незаметная смена весов в bugfix была бы сменой point estimator.

Статически проверены итоговая `_aggregate_scores` и извлечение unit positions в `.estimate()`: scale `N/sum(n_treated)` соответствует `1/S`; позиции взяты из actual complete-pair treated rows; повторные вклады разных cells суммируются; equal-weight cohort aggregate не получает ошибочного share term. Fit сохраняет membership независимо от `diagnostic_data` output option. New public `test_aggregate_scores_and_public_se_match_unit_contamination_refits` независимо пересчитывает weighted cell means и mixture counts, покрывая все четыре aggregate families, missing pairs и ненулевые cell scores; это дополнение к audit-only probe ниже.

### Независимая проверка производных

[block04_aggregate_review_probe.py](block04_aggregate_review_probe.py) **не импортирует библиотечный aggregation helper**. Он возмущает всю эмпирическую probability measure в направлении каждого unit, заново вычисляет counts и ratio. Проверены balanced/unbalanced masks и отдельно фиксированные/меняющиеся cell functionals (4 cases, по 11 directions). Последние добавляют ненулевые cell IF и проверяют product/ratio derivative целиком.

Команда:

```powershell
.\.venv\Scripts\python.exe audit\block04_aggregate_review_probe.py
```

Все 4 cases прошли. Max absolute derivative discrepancy **7.25e-10** при central step `1e-6`; mean IF меньше `6e-16`. Balanced counts `[3,3,3,4,4]`, unbalanced `[3,2,2,3,2]`. Намеренная подмена complete-pair indicator whole-cohort indicator дала unbalanced error **5.875**, подтверждая существенность выбора derivative. Это derivative verification, не Monte Carlo coverage и не проверка всей nuisance pipeline. [Raw evidence](block04_aggregate_review_checks.log).

## SC-11: bootstrap covariance и граница применимости

Existing analytic convention для cluster sums `U_c=sum_{i in c} phi_i`, `C` clusters:

\[
\widehat V=\frac{C}{C-1}\frac{1}{N^2}
\sum_c(U_c-\bar U)(U_c-\bar U)^\top.
\]

Для согласованного multiplier bootstrap можно генерировать iid Rademacher `v_c`, затем использовать `z_c=sqrt(C/(C-1))*(v_c-mean_c v_c)` и общую across-cell матрицу этих unit-mapped draws. Тогда `E_v[(N^{-1} sum_c z_c U_c)(...)^T]` точно равно этой analytic covariance. Centering работает и для неполностью zero-sum numeric IF; factor выбран для **existing Causalis convention**, а не заимствован как универсальное official did finite-sample правило.

Нужны `C>=2` до вычисления любой inference и `bootstrap_replications=0` либо `>=2`, чтобы sample SD не была undefined. Одинаковые cluster draws должны использоваться для cells и aggregates, сохраняя joint covariance. При unequal cluster sizes суммируются unit IF, а не средние внутри cluster.

Эта алгебраическая согласованность не доказывает finite-cluster coverage. При двух clusters support centered Rademacher draws дискретен, часть draws нулевая. Simultaneous normal/studentized bands при few clusters могут быть ненадёжны даже после guard/factor. [Callaway–Sant'Anna, Remark 10](https://arxiv.org/html/1803.09015) обосновывает cluster-specific multipliers при большом числе независимых clusters и отдельно указывает ограничение малого числа clusters. [Official did multiplier source](https://github.com/bcallaway11/did/blob/74b88eb07f1faa644df1271055a0f77848f6550c/R/mboot.R#L103) использует cluster sums и общие draws; это reference структуры, не обещание точного совпадения bootstrap distribution Causalis с R-пакетом.

Root regression test `test_cluster_multiplier_exact_covariance_matches_analytic_finite_cluster_formula` независимо перечисляет все 8 sign patterns для трёх неравных clusters, включая score columns с ненулевой суммой. Статическое review его ожидаемой covariance и helper center/scale согласуется с формулами выше. Проверку test execution и public integration ведёт root block report.

## Дополнительные ограничения scope

Selection доступных cells, complete pairs, support thresholds и диагностических flags считается стабильным локально. Производные не учитывают discontinuous reselection прямо на support/condition/ESS thresholds. Обычная parametric asymptotics требует regular nuisance solution и конечных моментов; полная IF не обещает достоверный CI при separation, ill conditioning или экстремальных весах. Cross-fitting, improved IPT/WLS и few-cluster alternative inference — самостоятельные методы, не добавлены в B04.
