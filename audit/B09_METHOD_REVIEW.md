# B09 independent implementation review

Review date: 2026-10-06. Baseline is exactly `74145665127f8fa5a0bf038d769697ab880854b8`, whose generator source equals the preceding tested B08 source `9fb8041300410b560da80a45cabac4b541d1629d`. Reviewed the two generator library paths as current working-tree changes relative to HEAD, and separately inspected the new untracked `tests/data/test_multicausal_namespace_contract.py`. The baseline module was loaded directly from the pinned git revision; source and tests were not edited by this reviewer. The `code-review` skill was used for patch scope, caller inspection, reproduction and verification limits.

## Result

No material correctness findings in the bounded namespace patch. The validator reserves actual emitted columns, identifies both conflicting roles, rejects malformed actual names before dictionary membership, and does not rename or strip requested strings. Disabled oracles are not reserved; no control-arm CATE is reserved. The initial subset check catches treatment/oracle collisions before X sampling, and the complete check consumes actual `_sample_X` names after successful sampling, before U draws, structural callbacks, treatment draws or outcome draws.

The actual-name design preserves existing naming differences among independent, copula and custom-X paths. In particular, a custom sampler does not expand categorical specs. Construction checks alone would not cover mutable public fields: the generation-time subset and complete checks correctly reject changes to arm names, arm count, enabled-oracle policy, and sampled confounder names between calls.

## Independent evidence

`block09_review_probe.py`, `block09_review_baseline.json`, `block09_review_patched.json` and `block09_review_checks.json` retain compact evidence, without storing generated rows. The reviewed library diff's SHA-256 is recorded in the checks JSON. These are independent probes, not pytest case counts:

- Eighteen baseline configurations return silently corrupted/reduced schemas; the patch rejects all eighteen with contextual ValueError. They include outcome/treatment, confounder/treatment, confounder/outcome, duplicate treatment/confounder, treatment/oracle and oracle/oracle collisions, categorical expansions, single-level naming, fallback-after-expansion naming, copula names and custom-X names.
- Three additional acceptance probes remain successful: disabled-oracle overlap, a treatment named after the ungenerated control CATE, and categorical specs with custom X and actual unexpanded names.
- Eleven distinct valid configurations, each exercised by two consecutive generations, give twenty-two exact frame/schema comparisons against the pinned baseline. After each generation the next ten RNG draws are also exactly equal. Cases include ordinary, tuple, NumPy-string-array, Unicode/punctuation, whitespace-only nonzero-length names, disabled-oracle overlaps, unused control CATE, expanded categorical/default fallback, single-level categorical, numeric copula and custom-X categorical paths.
- Five mutation probes reject the resulting invalid schema: enabling oracles, renaming an arm to y, changing K, appending an arm name, and changing a confounder name to y.
- Nine malformed-name probes reject empty, None, numeric, list and dict treatment members, a scalar-string treatment container, a list-valued actual confounder, and empty/None actual names from custom X. Tuple and NumPy-string-array containers remain accepted.

The new regression test module covers both functional return modes, reused generator/conversion methods, enabled and disabled oracles, categorical expansion, custom-X naming, rejection before callbacks, and valid name/value/order/RNG preservation. Its copula categorical comparison is a compatibility check against the previous output; it does not establish categorical sampling accuracy.

## Confirmed separate residual

`causalis/dgp/base.py:307` uses `u` in the categorical copula branch before assigning it to the current coordinate's uniforms. A categorical first coordinate raises UnboundLocalError in both baseline and patched generator. After a normal first coordinate, the categorical branch reuses that previous coordinate. An independent n=1000, seed=731 identity-correlation probe produces `c_1 == (z > 0)` in every row. This changes the intended copula sampling law and needs its own bounded correctness block.

This is pre-existing shared-helper behavior, not a regression introduced by B09. A categorical-first invalid namespace can fail in sampling before the complete post-sampling check; this path already fails before any DataFrame schema corruption. The B09 contract is validation of actual sampled names before assignment, not a new guarantee that namespace errors precede every sampler error. No shared-helper distribution change was added to this patch.

## Limits

This reviewer ran the independent probes through repository-local `.venv/bin/python` and inspected source, callers and the new tests. The general integration suite, compatibility CI, documentation builds, sensitivity analysis and oracle numeric accuracy were not run or claimed here; their evidence belongs to the root agent's block verification. Counts above must not be summed with integration or regression pytest counts.
