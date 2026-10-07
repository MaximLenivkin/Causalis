# B11 independent binary/IV namespace review

Frozen baseline: `4d6b8143db7a93c1a7eba371fcd144878d80c896`. Final source/test checkpoint: `cdc2c9590246c5b049d2184ba3479324217b2b00`. Applied the already-read `code-review` skill. Initially reviewed the two library working-tree changes relative to HEAD and inspected the separately untracked regression module. Final verification used the exact baseline-to-source comparison and reran the independent probe on the committed source. Source/test byte hashes, pinned revision and final reviewed HEAD are recorded in `block11_review_probe.json`.

## Result and namespace contract

No open material findings in the bounded core-generator patch. Binary generation emits y, d, actual sampled/expanded confounders, and six enabled oracles: m, m_obs, tau_link, g0, g1 and cate. IV emits y, d, the literal instrument name, actual confounders, and fourteen enabled IV oracles: m, r_obs, r_z0, r_z1, g_z0, g_z1, iv_first_stage, iv_reduced_form, late_x, late, tau_link, g_d0, g_d1 and cate.

The inherited validator dispatches to the IV-specific role list rather than reserving the binary oracle list. This is necessary: m_obs/g0/g1 are legitimate IV confounder names, and m_obs is a legitimate IV instrument name even when IV oracles are enabled. Conversely, r_obs/g_d0 are legitimate binary confounder names. Disabled oracle names remain available in both families. Literal strings, NumPy string scalars, whitespace-only nonzero-length names, actual categorical expansion and sampler-specific default fallbacks are preserved.

Fixed-role validation occurs at construction and on every generation call, including mutated instrument names and enabled-oracle settings. After successful sampling, the full validator checks actual names before U, callbacks, calibration and assignment. The count check matches actual X width without converting X or adding general shape/finite validation; accepted legacy zero-confounder one-dimensional/nested-list containers remain accepted.

## Guard gap found and resolved

The initial patch checked schemas only before and immediately after X sampling. Three ordinary callback closures could subsequently invalidate the emitted schema:

- Binary g_y enables oracles while an initially valid oracle-off confounder is named m; the old unchecked assembly overwrites X with propensity .5.
- IV g_z produces the same oracle-enable/confounder collision.
- IV g_z changes instrument_name from z to y; the DataFrame dictionary replaces the outcome with the instrument.

These were reproduced with n=30, seed=731. Both generators now repeat the full actual-name check immediately before DataFrame construction. All three cases raise contextual ValueError before schema corruption. The IV oracle evaluations after frame construction insert only fixed names already reserved by that enabled block; they do not create a previously unreserved dynamic name in the assembled core frame.

## Independent evidence

`block11_review_probe.py`, `.json` and `.log` contain the final successful reviewer evidence. The baseline binary class is loaded directly from its pinned source, and the baseline IV source is loaded against that frozen binary parent, not against the patched parent. All generated records are synthetic; the retained JSON records settings/statuses and counts rather than rows.

- Eighty valid configurations, each with two consecutive generations: 160 exact complete-frame/dtype/schema comparisons and next-ten-RNG comparisons. These cover binary continuous/binary/Poisson/gamma and both Tweedie positive families, all four IV outcome families, default/independent/categorical-copula/custom-X paths, oracle on/off, calibrated treatment rates, latent strengths, heterogeneous effects and pure callbacks. Fixtures use legitimate names and verify binary treatment/instrument values.
- Six additional family-specific allowed-name configurations, each with two generations, preserve complete frames and next RNG draws exactly. These include IV-only versus binary-only names, disabled-oracle overlaps, m_obs as an IV instrument, and literal whitespace names.
- Fourteen previously valid zero-confounder container configurations, each with two generations, preserve complete frames/schema/next RNG exactly, including n=0 and n=30, one-dimensional arrays and applicable nested lists. Previously failing IV oracle/list combinations are not claimed as valid references.
- Forty-five distinct baseline configurations return raw overwritten/reduced schemas; the patch rejects all with contextual ValueError naming the actual conflicting column. Cases cover core roles, all enabled family oracles, duplicate confounders, all enabled-oracle instrument collisions, categorical expansion and default X/instrument collisions.
- Eleven mutation probes reject invalid schemas, including the three callback mutations, invalid/colliding instrument settings on reuse, and enabling oracles between calls.

These comparisons are separate from pytest counts and must not be added to integration counts. The new `tests/data/test_binary_iv_namespace_contract.py` was read in full, including wrappers with optional augmentation disabled, literal/fallback names, actual expansion, oracle family distinctions, mutation/fail-fast checks, count mismatches and valid zero-feature container cases.

## Confirmed separate wrapper residual

Optional ancillary augmentation is outside the two core-generator paths. A still-valid core instrument name can collide later with that augmentation. Reproduction: `generate_iv_data(n=30, random_state=731, k=1, instrument_name='age', include_oracle=False, add_ancillary=True, deterministic_ids=True)` returns an age column with thirty nonbinary values. The core instrument was binary before `_add_ancillary_info` overwrote age at `causalis/dgp/base.py:138`, called by `causalis/dgp/causaldata_instrumental/functional.py:150`. The compact result is retained under `wrapper_residuals` in the reviewer JSON.

This is a separate P2 wrapper schema-corruption follow-up. B11 does not modify ancillary/preperiod augmentation or claim complete namespaces for their added columns. A future bounded wrapper fix should account for enabled added columns, instrument/outcome/treatment roles and preperiod names before assigning them, while preserving valid requested schemas. No wrapper library or test edits were made here.

## Verification limits

The reviewer ran independent probes through `.venv/bin/python` and inspected source/callers/tests; the root agent owns general local integration evidence. The delegated CI observation additionally verified run `37589241406` at exact source `cdc2c9590246c5b049d2184ba3479324217b2b00`, completed/success, observed `2026-10-07T07:48:19.487537+00:00`. All six artifacts were downloaded and checked: every Linux stack has 2235 passed, zero failures/errors/skips, the exact source marker and the same seven sensitivity exclusions. `block11_ci_result.json` records `matrix_verified=true` and `issues=[]`.

This is the scoped correctness selection, not a full sensitivity suite. No sensitivity, numerical-zero DiD policy, Sphinx or release validation is claimed. Malformed numeric-X contracts and output-setting mutations after IV frame construction that affect conversion metadata remain separate from this core namespace check. No source, test, git or GitHub mutations were performed by the reviewer.
