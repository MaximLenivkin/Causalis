# B10 independent categorical copula review

Baseline: exactly `83b63836dbd0c4793c24dd95ff7dc18c443792ad`. The initial scope was the working-tree change to `causalis/dgp/base.py` relative to HEAD, and the separately inspected new `tests/data/test_copula_categorical_coordinates.py`. Final frozen-source verification reviewed the exact commit-to-commit diff from that baseline to `95a8b7599fb129fb2c5973f50e9b4a8018732f6c` and reran the independent probes on the committed source with valid reference names. The already-read `code-review` skill was applied. The reviewer read the binary, multi-treatment, inherited IV and numeric-only scenario callers; no library, test or git mutations were performed. Reviewed source/test byte hashes and the exact reviewed HEAD are recorded in `block10_review_result.json`.

## Result

No open material correctness findings in the patch. Categorical inversion now uses its own raw Gaussian-CDF coordinate `U[:, j]`. The existing numeric inverse-CDF clip remains restricted to numeric marginals. PSD repair, jitter, Gaussian draw shape, scalar numeric marginals, probability normalization, drop-first expansion, names and single-level schema remain unchanged.

The corrected categorical branch resolves both first-coordinate UnboundLocalError and the previous-coordinate reuse. It preserves the existing right-sided interval convention: equality at a cumulative threshold belongs to the next nonzero interval, while zero-width leading and internal intervals are skipped. Using raw categorical uniforms also preserves legitimate probabilities below the numeric 1e-12 clipping boundary.

## Boundary discovered and resolved before source checkpoint

A coordinate-only candidate would introduce a valid-probability boundary error: a latent +10 gives Gaussian CDF exactly one; categories `[0, 1, 2]` with probabilities `[.5, .5, 0]` would hit the old upper fallback and select category 2 despite its zero probability. Previously, the reused numeric uniform was clipped below one. This was proved using a controlled Gaussian draw, with baseline and candidate comparisons explicitly labelled in-memory in `block10_review_boundary_candidate.json`.

The actual patch conditionally maps an out-of-range upper draw to the final positive-probability level. This closes the boundary without clipping valid rare categories, modifying probability validation, introducing random draws or reserving a nonexistent category. It also handles all mass on the omitted base level with trailing zero levels. Leading zero probability at a saturated lower CDF and internal zero probability at an exact .5 threshold remain correct under the original right-sided search.

## Independent verification

The standalone reviewer probe loads the shared helper directly from the pinned baseline git revision. The final successful evidence is `block10_review_probe.py`, `block10_review_probe.log` and `block10_review_result.json`; these are independent comparisons rather than pytest case counts.

- Eighteen numeric-only helper configurations, each with two consecutive calls: thirty-six exact comparisons of arrays, names and the next ten RNG draws. The cases include all eight supported scalar marginals (normal, uniform, Bernoulli, lognormal, gamma, beta, Poisson and negative binomial), scalar clipping, identity/Toeplitz/singular-repaired correlations, three seeds and n=1/30.
- Forty-eight numeric-only public generator configurations, each with two consecutive generations: ninety-six exact full-DataFrame/dtype/schema comparisons and next-ten-RNG comparisons. These cover binary, multi-treatment and inherited IV generators, four outcome families, oracle on/off and two seeds. The baseline helper is temporarily substituted into the unchanged caller modules within this isolated reviewer process; the current helper is restored before every current-side call.
- Nine independent coordinate references compare corrected category indicators to Gaussian quantile partitions of their own reference latent columns. The patterns include categorical first, all-consecutive categorical, and numeric/categorical interleaving; correlation configurations include zero, positive and negative/repaired dependence. Each pattern matches all 1000 rows and retains exactly equal next-ten-RNG draws to the Gaussian reference. For mixed layouts that returned under the baseline, their numeric columns remain exactly equal.
- Seven controlled boundary cases cover upper saturation with positive/zero tails, lower saturation with zero leading intervals, an exact .5 threshold with an internal zero interval, and a rare valid lower interval. All match their explicit expected dummy values and make exactly one Gaussian draw.

An initial reviewer harness error attempted to inspect a multi-generator-only attribute on the binary generator. The harness was corrected; it was not a library failure. Its scalar fixture names were then changed from a through h to `numeric_a` through `numeric_h`, avoiding the reserved treatment name d in binary/IV callers. Only the final successful comparisons with these valid names are counted above.

## Separate existing binary/IV namespace follow-up

The fixture-name review confirmed that a built-in confounder named d overwrites the treatment in raw binary and IV outputs. Trigger: either `CausalDatasetGenerator` or `InstrumentalGenerator` with `confounder_specs=[{'name':'d','dist':'normal'}]`, `use_copula=True`, `include_oracle=False`, n=30 and seed=731. Both return a frame whose d has thirty nonbinary values. The binary overwrite occurs at `causalis/dgp/causaldata/base.py:668`; the IV overwrite occurs at `causalis/dgp/causaldata_instrumental/base.py:356`, after treatment insertion. Evidence is `block10_review_namespace_followup.json`.

This is a bounded P2 schema-corruption follow-up for the two caller families. Their column-assignment source is unchanged by B10, and numeric-only old/current compatibility was separately established. B09's multi-treatment namespace validator does not cover these classes. A future fix should validate their complete actually generated namespaces without renaming columns; no library or regression changes were added here.

## Test review

The new test module builds low-dimensional latent Gaussian references using explicit analytic triangular projections, independent of the production PSD correction and copula helper. It checks first/mixed/consecutive categorical positions, normalized/default/unnormalized probabilities, single levels, exact-threshold/tail/rare probabilities, no additional RNG use, numeric compatibility and public binary/multi/IV callers.

Its statistical reference `Corr(Z0, 1{Z1 >= 0}) = rho * sqrt(2/pi)` correctly distinguishes latent Gaussian correlation from observed one-hot Pearson correlation. The finite-sample tolerances are appropriate to the fixed n=20000 probes. No sensitivity or DiD assertion was altered to obtain a pass.

## Limits

This review ran independent probes through `.venv/bin/python`, not the general pytest suite or CI. Invalid probability/category specification contracts are not expanded or certified. Corrected categorical X can change downstream D, Y, oracles and branching draw consumption; the helper's unchanged Gaussian draw contract does not imply identical full-frame/RNG results for previously incorrect categorical datasets. General integration, compatibility CI, Sphinx and release validation belong to the block's separate root-agent evidence. Sensitivity and the known numerical-zero DiD diagnostic follow-up remain outside B10's library patch.
