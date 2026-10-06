# B09 independent generated-namespace contract review

Review date: 2026-10-06. Source baseline: `9fb8041300410b560da80a45cabac4b541d1629d`; the handoff commit `74145665127f8fa5a0bf038d769697ab880854b8` only updates audit artifacts. This reviewer made no library or test edits. Scope: multi-treatment generator, functional/scenario wrappers, shared covariate-name generation, and the MultiCausalData conversion boundary.

## Complete generated schema

The generator inserts columns in this exact order:

1. Outcome `y`.
2. Each treatment name, in the supplied control-first order.
3. Each actual sampled covariate name, in sampled-X order.
4. When oracles are enabled, `m_<arm>`, `m_obs_<arm>`, and `tau_link_<arm>` for each arm, with these three columns adjacent.
5. When oracles are enabled, `g_<arm>` for every arm.
6. When oracles are enabled, `cate_<arm>` for each non-control arm only.

For K arms and k expanded covariates, this is `1 + K + k` columns without oracles and `6*K + k` with oracles. No user ID, raw categorical column, latent U column, marginal propensity, or control-arm CATE column is generated. MultiCausalData validation is a subsequent, distinct contract; it cannot recover columns overwritten before conversion, and raw DataFrame returns bypass it entirely.

Every actual generated name must be a nonempty string and unique across the complete generated schema. Here nonempty means a string with at least one character: an otherwise unique whitespace-only name remains accepted, preserving the established raw DataFrame schema. Accepted strings retain their exact spelling. Avoid automatic stripping, coercion, suffixing, reordering, or global prefix reservation: these would change valid requested schemas or reserve columns that are never produced. MultiCausalData retains its separate normalization and validation at conversion.

## Covariate names differ by sampling path

- Without specs, the names are `x1` through `xk`, including custom samplers.
- A custom sampler with specs uses `spec.get('name', f'x{i+1}')` and produces one name per spec. It does not one-hot-expand categorical specs; its X shape contract remains `(n, len(specs))`. Explicit None or empty names currently survive this name lookup and should be rejected as invalid actual generated names.
- Independent built-in sampling uses `spec.get('name') or f'x{len(names)+1}'`. The fallback index depends on the number of already expanded columns, which can exceed the number of prior specs.
- Copula sampling uses `spec.get('name') or f'x{j+1}'`, where j is the spec index. Preserve this existing distinction.
- Both built-in categorical paths omit the first category and produce `f'{base}_{category}'` for every remaining category, using the category's string representation. A single-level categorical produces `f'{base}__onlylevel'` as a zero column.

Consequently the validator should consume actual `_sample_X` names rather than reconstructing the naming algorithm. Numeric categorical labels are supported; distinct labels with the same string representation can nevertheless collide. An actual-name validator does not need to tighten all raw spec or category type contracts in this block.

## Confirmed corruption probes and regression cases

Baseline public-API probes used n=30, seed=1, K=2. In addition to the three B08 handoff collisions, the baseline returns silently reduced schemas for:

- Repeated treatment names `['arm', 'arm']`.
- Treatment names `['arm', 'm_arm']`: an enabled oracle replaces a treatment.
- Treatment names `['arm', 'obs_arm']`: `m_obs_arm` and `m_` plus `obs_arm` collide, even though neither base treatment name is repeated.
- Categorical spec `{'name': 'd', 'dist': 'categorical', 'categories': [0, 1, 2]}`: `d_1` replaces the default treatment column.
- Categorical categories `[0, 1, '1']`: both remaining categories generate `cat_1`.
- A categorical `cat` with categories `[0, 1]` followed by scalar confounder `cat_1`: the latter replaces the expanded covariate.

The baseline also accepts integer treatment names and a scalar string `d_names='ab'`, which silently becomes two character arm names. The documented input is a collection of string names; rejecting the scalar-string container and non-string members gives a clear error. Preserve previously usable ordered tuple or array containers where practical rather than imposing an unrelated strict-list requirement.

Useful positive cases are equally important:

- With `include_oracle=False`, a confounder named `g_d_0` remains a legitimate requested column.
- `cate_d_0` remains available because no control CATE column is generated, even with oracles enabled.
- Prefixes in names are allowed when the actual complete schema stays unique.
- Repeated raw categorical base names can still be valid if their expanded names are disjoint.
- Missing/None/empty spec-name fallback in built-in sampling remains compatible; custom sampler naming retains its own established lookup rule.

## Minimal fix recommendation

Use one generator-local validation helper for generated-name entries, carrying role labels in errors. Validate the outcome/treatment/enabled-oracle subset at construction and again at generation, so mutated public fields cannot bypass validation. After `_sample_X` and numeric X shape validation, validate the same subset plus actual sampled names, before drawing U or calling score/outcome callbacks or constructing DataFrame columns. Check that the number of names matches the actual X width. Do not modify the shared copula helper merely to enforce this generator's schema.

This catches corruption before column assignment and preserves values, column order, and RNG consumption on valid configurations. Exact seeded comparisons against the frozen baseline should include custom samplers, categorical expansions, copula numeric marginals, oracle on/off, renamed arms, and both assignment policies. The early subset check should fail before invoking custom samplers for treatment/oracle-only collisions. The complete post-sampling check should fail before any score or outcome callback for sampled-name collisions.

## Separate residual: categorical copula draws

The shared `_gaussian_copula` categorical branch uses `u` before setting it to the current column's uniforms. A first categorical spec reproducibly raises `UnboundLocalError`; later categorical specs reuse the preceding non-categorical column's uniforms. This is a pre-existing sampling defect, not an additional generated-name collision. It should be tracked separately rather than broadening B09's implementation into distribution changes.

Independent helper probe: seed=731, n=1000, specs consisting of one standard normal followed by categorical `[0, 1]`, and identity latent correlation. Every generated `category_1` equals the indicator that the preceding normal exceeds zero (`np.array_equal` returned True). The intended identity-correlation copula would use a separate independent latent coordinate.

A first-categorical collision configuration may therefore fail during covariate generation before a post-sampling namespace guard. That path already fails rather than returning corrupted data. Duplicating all name generation into a schema preflight solely to change this earlier exception is not required for the bounded namespace fix.

## Verification boundary

The probes load the frozen baseline generator from git and use repository-local Python. The categorical copula defect was also reproduced against the shared helper. This reviewer did not run the general integration suite, CI, documentation builds, or deferred sensitivity tests. Final implementation review and block verification remain separate root-agent responsibilities.
