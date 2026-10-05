# B03 — DML-06: fold stability instead of invalid OOS inference

Status: code complete; focused and neighboring checks pass. Integration and Git checkpoints are maintained by the root agent. Date: 2026-10-05. Severity: **P2** (misleading public diagnostic inference, not a point-estimator change).

## Why the old test was invalid

For ATE, the linear score is `psi_i(theta) = b_i - theta`. With K equally sized folds, let `b_k` be each fold's signal mean and `b_bar` their average. The complement solution and held-out mean are

```text
theta_minus_k = (K * b_bar - b_k) / (K - 1)
r_k = b_k - theta_minus_k = K / (K - 1) * (b_k - b_bar)
sum_k n_k * r_k = 0
```

The last identity holds for arbitrary fold differences. Both old aggregate statistics therefore yield zero and p=1 whenever their denominators are defined. For fold signal means `[0, 100, 200, 300]`, the held-out score means are `[-200, -66.6667, 66.6667, 200]`, yet the old code could flag the aggregate GREEN. Adding within-fold variance does not fix the cancellation.

Unequal fold sizes or ratio scores can break the exact cancellation; this does not calibrate a Gaussian reference distribution. The scores in the complement were already computed using nuisance models whose training sets can include the purported held-out fold. The routine does not refit all nuisances on the complement and evaluate a separate independent validation experiment. Its reused fold residuals are dependent. We therefore retain descriptive comparisons and make the aggregate inference unavailable for **all** fold sizes and scores.

This is a code-specific algebraic result. It does not invalidate DML estimator inference under its required assumptions. Orthogonal scores and cross-fitting form part of the estimator construction described by [Chernozhukov et al., Double/Debiased Machine Learning for Treatment and Causal Parameters](https://arxiv.org/abs/1608.00060), checked 2026-10-05; that result does not supply a null distribution for the old extra diagnostic.

## Implementation and public behavior

Sources:

- [Binary score diagnostics](D:/codex/Causalis/causalis/scenarios/unconfoundedness/refutation/score/score_validation.py).
- [Multi-treatment score diagnostics](D:/codex/Causalis/causalis/scenarios/multi_unconfoundedness/refutation/score/score_validation.py).
- [Multi diagnostic payload contract](D:/codex/Causalis/causalis/data_contracts/causal_diagnostic_data.py): one optional `psi_a` field added; sensitivity fields unchanged.

The historical `oos_moment_test` name remains for compatibility. It now reports `available=False`, `inference_status='unavailable'`, an explicit reason, and NaN for legacy `oos_tstat_fold`, `oos_tstat_strict`, `p_value_fold` and `p_value_strict`. The binary `oos_max_abs_t` summary row and the multi legacy t-statistic rows remain as NaN. The corresponding `oos_moment` flag is NA and contributes no GREEN/PASS evidence to the overall flag. Other score diagnostics retain their existing policies.

New ungraded values describe fold differences:

| Field | Meaning |
| --- | --- |
| `fold_diagnostics_available` | At least two nonempty folds, with all reported fold and complement solutions and held-out means finite. |
| `fold_diagnostics_reason` | Missing scores/folds, fewer than two folds, or undefined solutions due to nonfinite scores / zero Jacobian. Stored per comparison for multi reports. |
| `fold_score_mean_rms` | `sqrt(sum_k n_k * r_k^2 / sum_k n_k)`, scaled before squaring to avoid overflow. |
| `fold_score_mean_max_abs` | Largest absolute held-out score mean. |
| `fold_theta_range` | Largest minus smallest within-fold solution, on the effect scale. |
| `fold_theta_gap_max_abs` | Largest absolute difference between a fold solution and its complement solution. |

`fold_table` retains `fold`, `n`, `theta_minus_k`, `psi_mean`, `psi_var`, and adds `theta_fold` and `theta_gap`. Multi tables also retain `comparison`; scalar fields appear in `by_comparison`. Existing sample variances remain descriptive. Singleton folds can have undefined sample variance while their score mean and effect solution are defined. Complete summaries do not require a finite variance because no variance-based test is computed. Undefined fold solutions remain in the table and make the complete summary unavailable; they are not silently discarded. The existing near-zero Jacobian cutoff (`1e-12`) is retained.

For `[0, 100, 200, 300]` above, the new effect range is 300, maximum held-out mean/gap is 200, and RMS is approximately 149.0712. For identical constant folds all four metrics are zero, with **no p=1 or OOS GREEN flag**. These are scale-dependent descriptive values; no universal thresholds or significance claims are supplied.

The multi private wrapper reuses the binary private linear-score helper per contrast to keep the algebra consistent. This is an internal dependency, not a newly exported cross-scenario API.

## ATTE coordination and old caches

The multi estimator fix DML-01 changes the ratio score Jacobian to `psi_a = -d_k / p_k`. This diagnostic change reconstructs ATTE residuals as `psi_b + psi_a * theta`, rather than incorrectly subtracting the effect from every row.

New multi payloads can preserve `psi_a`: an `(n,)` ATE vector or an `(n, K-1)` array. For ATTE, missing or incompatible shapes (including an old constant `(n,)` vector) fall back to `-d_k / p_k`; valid provided arrays are honored. ATE vectors broadcast across contrasts. Cached Jacobian rows take part in the existing finite-row filter. `meta.used_estimator_psi_a` identifies the source.

Legacy ATTE caches can contain `psi_b - theta` even when the new Jacobian is reconstructed. If a cached residual array disagrees with `psi_b + resolved_psi_a * theta` (`rtol=1e-10`, `atol=1e-12`, matching NaNs), diagnostics reconstruct it and record `meta.used_estimator_psi=False`, `meta.psi_cache_status='inconsistent_atte_score'`. Compatible arrays retain provenance `used`; missing and incompatible shape caches have corresponding statuses. This policy fixes the diagnostic representation. It **does not repair confidence intervals or standard errors already stored in an estimate produced by the older estimator**; re-fit/re-estimate using the corrected model for estimator inference.

## Verification

Commands use the repo-local `.venv\Scripts\python.exe`, `MPLBACKEND=Agg`, a task-owned basetemp and `-p no:cacheprovider`.

| Stage | Result | Evidence |
| --- | --- | --- |
| Initial 17 new cases against old implementation | 17 failed in 12.51s | [before log](D:/codex/Causalis/audit/block03_oos_before_tests.log) |
| First corrected helper/reconstruction run | 17 passed in 10.63s | [after log](D:/codex/Causalis/audit/block03_oos_after_tests.log) |
| 14-file diagnostic/orthogonality neighborhood | 50 passed, 24 warnings in 25.93s | [neighbor log](D:/codex/Causalis/audit/block03_oos_neighbors_tests.log) |
| Final focused files including cache/shape cases | 36 passed in 12.49s | [final log](D:/codex/Causalis/audit/block03_oos_final_tests.log) |

The final files are [fold regressions](D:/codex/Causalis/tests/refutation/test_oos_fold_diagnostics.py) (19 cases), [multi public tests](D:/codex/Causalis/tests/refutation/test_multi_score_diagnostics.py) (13 cases) and [binary public alignment tests](D:/codex/Causalis/tests/refutation/test_refutation_score_alignment.py) (4 cases). The before failures include deliberately missing new API fields and are not 17 independent bugs. Regression properties cover binary/multi equal and unequal folds, zero within-fold variance, single-fold/undefined solutions, nonfinite inputs, ratio fold solutions, missing/misaligned fold assignments, corrected no-noise ATTE residuals, legacy cached scores, provenance, and finite-row alignment. The existing test that asserted p=1 was rewritten to check the independently known fold range and unavailable inference. Neighborhood warnings concern the existing relative-effect baseline guards; no OOS `All-NaN slice` warning remains.

No sensitivity test, formula, module or field was changed. This scoped run is not a full-suite result or a calibrated coverage experiment.

## Ready documentation text

> Score diagnostics report descriptive fold stability, including fold effect estimates, leave-fold gaps and weighted RMS held-out score means. They reuse cached cross-fit score arrays and do not refit nuisances for an independent validation experiment. Accordingly, `oos_moment_test.available` is false, legacy OOS t-statistics and p-values are NaN, and the OOS flag is NA. Use `fold_diagnostics_available`, the effect-scale ranges/gaps and the fold table to inspect differences; these quantities have no calibrated significance thresholds and do not certify causal identification. ATTE comparisons use the treated-share ratio Jacobian. Re-estimate older ATTE results with the corrected model to obtain updated uncertainty intervals.

Deferred feature: a separate validation dataset/split with nuisance and parameter training provenance, an explicit null hypothesis and a justified calibration procedure. Unequal folds, repeated cross-fitting or a different arbitrary aggregate do not by themselves supply such a procedure.
