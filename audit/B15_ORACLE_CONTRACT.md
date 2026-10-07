# B15 · Gaussian marginal propensity: независимый контракт

Дата: 2026-10-07. Immutable baseline: `71f6a619b04e0ab8fab388fb95b7d0f3d6631b96`, branch `codex/correctness-roadmap`. Это bounded contract/reference review, не новый аудит всех DGP или causal coverage. Library/tests/git этот агент не менял. Исходная постановка — [B07_DGP_REVIEW.md](B07_DGP_REVIEW.md); historical Windows links внутри B07 относятся к старому checkout.

В B15 разумен additive opt-in для multi-treatment nominal assignment model. Измеренные fixed-GH ошибки старых binary/IV outcome-oracles выделены ниже в следующий numerical block. У существующего multi outcome helper уже другие алгоритмы; менять его или default sampling ради нового propensity API не требуется.

## Target и закон

Для фактически рассчитанного affine score vector `a(x)` и нормализованных latent slopes `b`:

\[
p_k(x,u)=\frac{\exp\{a_k(x)+b_ku\}}{\sum_j\exp\{a_j(x)+b_ju\}},
\qquad q_k(x)=\int_{\mathbb R}p_k(x,u)\phi(u)\,du.
\]

Здесь `a` включает существующие X-score, `propensity_sharpness` и откалиброванный `alpha_d`; latent term масштабируется так же, как в существующем assignment, без дополнительного множителя. Reference law — `U ~ N(0,1)`, независимый от X. Поэтому `q_k` — `P(D=k|X=x)` nominal iid softmax system при этой law. Всегда `0 <= q_k <= 1` и `sum(q)=1`.

Existing `m_<arm>` — `p_k(x,0)`, existing `m_obs_<arm>` — `p_k(x,U_i)`. Эти quantities сохраняют имена и значения. При одинаковых `b_k` общий `bU` сокращается, поэтому `q=m`; это достаточное условие, а не утверждение, что любое случайное равенство требует одинаковых slopes. Scalar `u_strength_d=c` в actual multi API нормализуется в `[0,c,...,c]`, а не одинаковый slope каждого arm. Полный vector из K одинаковых slopes действительно сокращается.

Supplied `U` задаёт реализованные значения, не спецификацию latent distribution. При supplied constant7, иной law или зависимости U от X новые `q` остаются Gaussian-reference quantities. `m_obs` учитывает supplied values; усреднять supplied vector для переопределения oracle нельзя. Если нужна другая latent law, требуется отдельный target/API.

При `assignment_policy="iid"` один multinomial draw на row использует `m_obs`; тогда Gaussian `q` имеет указанную assignment interpretation при Gaussian U. `ensure_all` делает retries и может принудительно вставлять missing arms. Его joint assignment law меняется: neither `m_obs` nor `q` являются точными probabilities conditioning/repair algorithm. Новая колонка описывает nominal structural model; policy не меняется.

`target_d_rate` по-прежнему калибрует empirical-X средние `p(x,0)`. Даже точный `q` не превращает этот режим в Gaussian-marginal calibration или population-X calibration. Frozen no-X пример `b=[0,2,2]`, target `[.2,.3,.5]` имеет `m` равный target, но `q=[.29972870050639017,.2626017373101035,.43766956218350644]`.

Outcome target остаётся `g_k(x)=E_U[mu_k(x,U)]`, CATE=`g_k-g_0`. Gaussian q не даёт latent-selected ATT: для ATT нужен weighted integral `(mu_k-mu_0)*p_k` и соответствующий denominator. Тreated mean marginal CATE не переименовывается в true ATT.

## Минимальный совместимый API

`include_marginal_propensity=False` добавляется после старых public init fields, а в functional signature — последним параметром. Старые positional positions сохраняются. Enabled option требует `include_oracle=True`; новый flag принимает bool/`np.bool_`, остальные типы отклоняются. Строгий type check относится к новому flag и не расширяет legacy truthiness contract других опций.

Enabled output добавляет только `m_marginal_<literal arm>` после существующих oracles. Имена не strip/coerce; role namespace резервирует их только когда действительно включены. Повторная проверка flags/actual expanded names нужна при mutable settings и callbacks. Отключённое marginal имя остаётся допустимым actual confounder; включённое конфликтующее имя даёт ValueError. Новые колонки не становятся X features при default contract projection. Старые learners и nuisance-column selection не переключаются на них автоматически.

Functional [generate_multitreatment](../causalis/dgp/multicausaldata/functional.py) не exposes latent-strength arguments, поэтому при его нынешних default latent slopes `q=m`. Нетривиальный Gaussian integral доступен через low-level [MultiCausalDatasetGenerator](../causalis/dgp/multicausaldata/base.py). Добавление новых latent knobs в wrapper не является необходимой частью B15.

Successful valid opt-in generation должна сохранять Y/D/X, все existing oracle values, calibration, callback behavior и RNG draws. Integration не использует RNG. При explicit opt-in numerical failure ValueError допустим; это не гарантия transactional RNG rollback после уже выполненного sampling.

## Numerical policy и независимый reference

Candidate интегрирует каждый distinct score row через vector adaptive `quad_vec` на `[-12,12]`, absolute max-norm target `1e-10`, `epsrel=0`, budget4096 subintervals. Common intercept/slope shifts центрируются до affine evaluation; одинаковые slopes возвращают exact existing m без integration. Pairwise crossings вместе с local width points `crossing ± {1,4,16,40}/abs(b_i-b_j)` показывают integrator узкие transitions и intermediate-arm regions. Все crossings здесь partition hints, а не предположение, что каждый arm действительно dominant.

Проверяются solver success/status, finite estimated error <= tolerance, finite nonnegative probability vector и near-unit mass. Normalization допускается после этих checks для rounding mass error, а не для скрытия плохого integration. Unsupported floating geometry, domain envelope или point/subdivision budget дают explicit opt-in ValueError. Default path не запускает эту интеграцию и сохраняет прежние numerical contracts.

Working storage candidate `O(nK + K² + LK)`, `L` bounded by subdivision budget, без `n × K × nodes` tensor. Distinct-row deduplication помогает constant scores, но varying X может потребовать отдельный integral на почти каждую row. Public speed/large-K performance guarantee не проверялась.

Analytic omitted Gaussian mass:

\[
2\Phi(-12)=3.552964224155308\times10^{-33}.
\]

Каждый propensity bounded by1, поэтому столько же ограничивает truncation error. Это аналитический tail bound. Adaptive returned error — numerical estimate, не строгая probability certificate для любых finite coefficients. `1e-10` — integration target и acceptance policy, не доказанная uniform guarantee на весь возможный API domain. Very small probabilities не имеют обещанного relative accuracy.

Независимый [block15_contract_probe.py](block15_contract_probe.py) использует scalar `scipy.integrate.quad` отдельно для каждого arm и `scipy.special.softmax`, не candidate softmax/integration helper как reference. Его transition offsets `.5,2,8,32,64` отличаются от candidate; `epsabs=epsrel=2e-13`, domain тот же с явным tail bound, warnings/error estimates сохраняются. Shared affine-Gaussian geometry выведена из target; backend и evaluation независимы. Это numerical cross-check, не formal proof of QUADPACK accuracy.

## Выполненные проверки и происхождение

Aggregate-only evidence: [block15_contract_result.json](block15_contract_result.json). Frozen baseline modules выполняются под отдельными именами, candidate берётся как предварительно captured source snapshot; package modules не заменяются. Frozen IV import единожды перенаправлен на frozen binary class, identity assert проверяет наследование. Original-source и фактически compiled IV hashes записаны раздельно. Его function bodies совпадают с frozen Git source; отличается только class import binding.

Runtime profile фиксирует фактически вызванные snapshot paths и actual shared helper. Closure: frozen multi, frozen binary, frozen IV; candidate multi; actual shared [dgp/base.py](../causalis/dgp/base.py), SHA256 `f5cd516bd4a2b071470fe6ee6a3a1da073432b551117375f6d74aabcc452c849`, byte-identical baseline. Candidate functional file hash captured, но этот probe не выполнял wrapper: его runtime validation относится к отдельным B15 tests/review.

Run UTC `2026-10-07T13:19:40.628099+00:00`–`13:19:46.562352+00:00`; actual process HEAD71f6 baseline, Python3.12.14, NumPy2.5.3, SciPy1.18.1, pandas3.0.6, native threads1. Exact versions в result JSON authoritative.

| Snapshot | SHA256 |
|---|---|
| Baseline multi base | `2977f5ee3fe7ae2ce10a19d39d898e048f448c2b15d1b93a48f04094db00a859` |
| Candidate multi base | `c46c1e090b0e033b59a6aa4eb65ba7cb9a1fdbb5aba4cde05132b19f903ea982` |
| Candidate functional, read only | `e3b074a2ff2cd57de9756cd81b4f01bdbbaa8fd728b87de5517d692b37723d43` |
| Baseline binary base | `794fd4f5d7a9f23cec06987ffbbb5615e75ae57b0ba87e6520ea05db14b356e6` |
| Baseline IV base | `4ec2a4b77b5974f4db103b2c8aa157b7b1f8347fbb90f4137e2139b904aa1daa` |

31 **private mathematical q-reference cases**: K2/K3/K5, slopes0/.1/1/2/5/10/50/1000, additional1e6 narrow-middle, shifted narrow-middle, near-tail crossing, equal nonzero slopes and repeated slope groups. Max candidate/reference absolute difference `3.885780586188048e-16`, finite bounds/mass checks прошли, reference/candidate warnings0. Four invariance checks: U-sign reversal, common intercept shift, common slope shift, arm permutation; max discrepancy below1e-12.

Отдельно **8 public generate baseline/candidate frame comparisons**: iid/ensure_all × drawn Gaussian/supplied constant7 × calibrated/uncalibrated, K3/n64/noX/gamma. All existing columns/dtypes/schema exact equal; full RNG state и subsequent10 draws exact equal. Each enabled frame adds only3 marginal columns; их aggregate means совпадают с независимым Gaussian q до1e-10. Это bounded compatibility evidence, не broad causal coverage и не проверка всех x_sampler/callback families. Recorded40 actual `quad_vec` calls включают private/reference and public cases, не являются числом public generation cases.

При одинаковых intercepts и slopes `[0,1,1]` q=`[.3601605153366524,.3199197423316738,.3199197423316738]`, хотя m=`[1/3,1/3,1/3]`. Supplied constant7 изменяет m_obs и observations при прочих равных, но Gaussian q не меняет своего reference target.

## Почему одинаковые fixed-GH orders недостаточны

В двух независимых examples GH32 и GH64 совпадают до `2.220446049250313e-16`; это не convergence certificate.

| Structural a,b | Adaptive q | GH32/GH64 | Maximum error |
|---|---|---|---:|
| `a=[0,1], b=[0,1000]` | `[.49960105844232044,.5003989415576799]` | approximately `[.5,.5]` | `.00039894155768005` |
| `a=[0,5,0], b=[-1000,0,1000]` | `[.4980051371618147,.0039897256763704895,.4980051371618148]` | approximately `[.5,0,.5]` | `.0039897256763704895` |

GH81 errors на тех же configurations `.031678457387901315` и `.13299231279779106`: central node overweight не заменяет разрешение узкой области. Reference error estimates около1e-15/1e-16, warnings0. Поэтому B15 использует geometry-aware adaptive reference, не условие «два соседних GH orders похожи».

## Следующий bounded numerical block: binary/IV outcome means

Эти findings относятся к **existing baseline**, а не к new marginal propensity API. B15 оставляет прежние defaults. 31 outcome configurations:11 logistic and20 clipped-log; each independent scalar adaptive reference сравнивается с unchanged multi baseline/candidate helper, binary public generate и IV potential-outcome helper. Individual rows не сохраняются. Gamma links representative также для идентичного Poisson mean formula; Poisson public sampling здесь не выполнялся. IV reduced-form/treatment propensity compound integrals и Tweedie не measured в этих31 cases.

Для binary natural mean target `E[expit(a+sU)]`. Actual [binary generate](../causalis/dgp/causaldata/base.py) uses fixed GH21 при ненулевом outcome latent strength; [IV _potential_outcome_means](../causalis/dgp/causaldata_instrumental/base.py) uses `_u_quadrature()` GH31. При `a=-5,s=50`:

| Quantity | Value | Absolute difference |
|---|---:|---:|
| Independent adaptive Gaussian reference | `.46019824525940106` | — |
| Binary public `g0`, GH21 | `.3666787193329233` | `.09351952592647778` |
| IV potential-outcome mean, GH31 | `.3898474049920017` | `.07035084026739935` |

Synthetic reproduction: binary `CausalDatasetGenerator(k=0,alpha_y=-5,theta=0,u_strength_y=50,outcome_type="binary",seed=731).generate(8,U=zeros(8))`; IV same inherited config, `_potential_outcome_means(zeros((8,0)),zeros(8))`. Supplied U0 affects draws, но oracle calculation retains Gaussian law; поэтому пример не является empirical averaging mismatch.

Для gamma/Poisson natural mean target `E[exp(clip(a+sU,-20,20))]`. Boundary kinks при U=`(-20-a)/s,(20-a)/s` важны; unbounded `exp(a+s²/2)` не тот target. Независимый reference split именно в этих kinks.

| Configuration/quantity | Adaptive reference | Existing value | Relative difference |
|---|---:|---:|---:|
| `a=-25,s=10`, binary GH21 | `3015.774279316849` | `1789.522799117206` | `.4066124870848825` |
| `a=0,s=10`, IV GH31 | `14262957.080491794` | `12293569.226898238` | `.13807710718608224` |

Крупные absolute errors также есть на upper-clipped means; они не равны tiny clipping tolerances. Эти observed defects оправдывают следующий bounded block для binary/IV marginal outcome accuracy с explicit compatibility/RNG policy. Начальный scope — binary g0/g1 и IV `_potential_outcome_means`, затем отдельно решить reuse в `_g_by_z`, поскольку последний интегрирует `(1-p_d(U))*mu0(U)+p_d(U)*mu1(U)` с общим U; нельзя заменить его product of independent marginal means. `_r_by_z` — ещё другой propensity integral. Tweedie `E[p_positive(U)*mu_positive(U)]` требует сохранения общей latent law и отдельного решения scope.

Multi не противоречит findings: actual `_marginal_natural_scale_from_link` уже использует GH81 только при abs(s)<=2, logistic-normal convolution/GL256 при s>2, analytic clipped-exponential CDF expression для gamma/Poisson. На измеренных11 logistic cases max observed absolute difference1.7802426199864385e-12; на20 clipped-log cases max observed relative difference1.2157238483134129e-14. Последнее ниже relative adaptive reference error estimate порядка2e-13; это согласие reference, не universal rigorous accuracy certificate. Baseline/candidate multi outcome values exact equal во всех31 configs.

Mean tail bound для clipped log reference `exp(20)*2Phi(-12)=1.723774582096304e-24`; quadrature error estimates для large-scale means выражаются в outcome units, поэтому могут быть около1e-5 при relative tolerance2e-13. Эти estimates намного меньше выявленных GH defects. Все outcome reference warnings0. Arbitrarily extreme finite link/strength values, IV compound nuisances, binary Tweedie, performance и causal-estimator coverage здесь не подтверждались.

## Воспроизведение и ограничения

```bash
.venv/bin/python audit/block15_contract_probe.py
```

Probe требует process HEAD baseline71f6; candidate bytes captures отдельно. После source commit baseline остаётся доступен через Git, но исходный result нельзя выдавать за новый committed runtime без exact-byte linkage. Root может добавить такую linkage metadata отдельно, сохранив actual run timestamps/hashes. Local/CI tests, final source freeze и другие agents' evidence не включаются в этот независимый run count.
