# B16 — Gaussian marginal potential-outcome accuracy

Baseline: `e8459e1` (`codex/correctness-roadmap`). Дата: 2026-10-07.
Source checkpoint и итог integration дополняются после коммита и проверки.

## Контракт и исправление

Target — E[Y(d)|X] по независимому U ~ N(0,1), а не E[Y|D=d,X]
при latent confounding. Supplied U меняет наблюдаемые outcomes, но не reference
law. Для Poisson/Gamma target включает фактический exp(clip(link,-20,20)).
Фиксированные GH21/GH31 ошибались при сильном latent outcome effect:
logistic link=-5,strength=50 даёт reference 0.4601982452594012 вместо
binary 0.36667871933292406 / IV 0.3898474050. Это numerical bias oracle,
не ошибка наблюдаемого stochastic DGP.

Три library paths: новый `causalis/dgp/_gaussian_outcome.py`, binary base и IV
base. Binary `g0/g1`, IV `g_d0/g_d1`, `cate` и nonlinear outcome-callables
используют общий deterministic helper. Binary при strength<1 интегрирует
Gaussian на [-12,12], иначе использует independent logistic CDF identity
E[sigmoid(a+sZ)] = E[Phi((a-L)/s)] на L∈[-40,40]. Обе формы сохраняют smooth
integrand даже при strength 1e308. Adaptive max-norm estimated epsabs 1e-11,
epsrel=0, limit256, cache1MiB, batch1024. Gaussian omitted mass<3.6e-33,
logistic omitted mass<8.5e-18. Nonconvergence/nonfinite backend errors/results
дают ValueError; это estimated absolute accuracy, не rigorous uniform или
rare-probability relative certificate. Вероятности за пределами machine
roundoff range отклоняются; допустимая rounding correction ограничена 4eps.

Clipped exponential — два Gaussian tail terms плюс truncated exponential
moment. При strength≤8 используются log-CDF differences и expm1; при strength>8
middle интегрируется на [-20,20] с per-value peak normalization. Это исключает
катастрофическую компенсацию O(strength²) log terms и overflow square для
enormous finite strengths. Tail saturation за 12sigma имеет relative bound
exp(40)*Phi(-12)<4.2e-16. Finite real inputs обязательны; unsupported analytic
geometry/nonconvergence отвергаются. Working storage O(n) плюс bounded batches;
helper не создаёт RNG draws.

## Совместимость и границы

Signatures/schema/dtypes/column ordering сохранены. Zero-strength branches
используют прежнюю arithmetic, continuous IV сохраняет старую GH31 path.
Binary callback call counts сохранены. IV nonlinear potential means теперь
оценивают две base locations вместо 62 node-specific evaluations; математический
контракт предполагает deterministic functions of X. Stateful/random callbacks
не имеют обещания old/current эквивалентности: их call counts и дальнейший RNG
могут измениться. Наблюдаемые draws до oracle evaluation сохраняются.

`oracle_nuisance(num_quad=...)` сохраняет параметр и прежний GH propensity;
только outcome-callables больше не зависят от num_quad. Existing DML
identification guard сохранён. Failed generation не откатывает RNG/callbacks.
Binary по-прежнему вычисляет скрытые oracle means даже при include_oracle=False;
новая failure policy может проявиться и в этом существующем compute path.

Multi outcomes/source, binary propensity m, IV `_r_by_z`/joint `_g_by_z`,
Tweedie joint-latent means не изменены. Joint targets нельзя заменить products
of separately integrated marginals. Sensitivity и selected-U ATT вне scope.

## Проверка

- Один и тот же public 62-case module: baseline **37 failed/25 passed**,
  final candidate все62passed; failures включают numerical accuracy и
  num_quad-dependent exact callable disagreement, не37 distinct defects.
  [Baseline JUnit](block16_baseline_tests.xml),
  [log](block16_baseline_tests.log).
- Final focused: **121 passed**,0failures/errors/skips/warnings,5.17s
  (62 public +59 helper boundary/failure/batching cases).
  [JUnit](block16_focused_tests.xml), [log](block16_focused_tests.log).
- `tests/data`: **1359 passed**,0failures/errors/skips,2existing warnings,14.11s.
  [JUnit](block16_neighbors_tests.xml), [log](block16_neighbors_tests.log).
- [Frozen-baseline probe](probe_block16.py), [aggregate evidence](block16_probe_result.json):
  48 configurations×2 generations = **96 exact frame/schema/dtype/metadata/
  calibration/full-RNG-state/next10 pairs** outside corrected oracle columns.
  Four families, binary/IV classes, strength0/0.5/10, oracle enabled/disabled,
  deterministic nonlinear callback and heterogeneous tau. Public signatures
  равны; shared sampling и multi modules byte-identical baseline.
- **140 independent scalar adaptive references**: max binary absolute error
  4.440892098500626e-16, max Gamma relative error 1.5843718726530021e-15.
  Это evidence на выбранной grid, не универсальная гарантия.
- Root выполнил review и все проверки в этом блоке. Независимые субагенты не
  запускались; independent references означают другой численный reference,
  а не отдельного reviewer.

Первый focused run:60passed/2failed. Нормализованный exponential middle при
link=-100,strength10 потребовал realistic epsabs1e-11 вместо1e-12 из-за
roundoff/error estimator. Последующие range probes обнаружили harmless
probability overshoot нескольких ULP при smallstrength; добавлен4eps guard.
Окончательные focused/probe/neighbors проверяют final source hashes в manifest.

Backend semantics: [SciPy quad_vec](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.quad_vec.html)
возвращает estimated error и convergence status; [log_ndtr](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.log_ndtr.html)
сохраняет точность log-CDF в хвостах. Target identities выведены из Gaussian
density и independent logistic latent representation, reference не использует
production helper.

## Следующий самостоятельный блок

B17 — Gaussian propensity accuracy и shared-U compound means. Probe сохраняет
четыре concrete residuals: IV joint g_by_z errors≈0.073–0.075; binary m и Tweedie
GH21 errors0.0935195 при logistic link=-5,strength50. Начать с общего target,
independent joint adaptive references и callback/accuracy policy; не менять
assignment/calibration/observed RNG и не подменять joint integrals marginals.
Затем прежний learner shape/real/IVstorage backlog.

GitHub live-read сейчас ограничен DNS/network sandbox: `git ls-remote origin`
получил `Could not resolve host: github.com`. Push/CI не подтверждены.
На границе B16 остановиться; следующий блок после очистки контекста и нового
запроса пользователя.
