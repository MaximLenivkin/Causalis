# B08: independent review of multi-arm assignment sampling

Reviewed 2026-10-06 at the B07 checkpoint. Source: `causalis/dgp/multicausaldata/base.py`, `_draw_multinomial`; public `generate`, `to_multicausal_data`, and `functional.generate_multitreatment`. Sensitivity code untouched.

## Confirmed findings

**P2: the assignment sampler does not follow the advertised independent softmax law.** It samples the entire assignment vector again up to ten times until every arm occurs. Accepted early samples are conditioned on complete coverage. If retries fail, random observations receive missing-arm labels irrespective of their individual probabilities. Thus `m_obs_<arm>` records nominal softmax probabilities, generally not the actual row assignment probability under this procedure. This differs from Gaussian marginalization discussed in B07: the sampling distortion exists with U=0 and constant X.

For two observations, two arms, and constant nominal probabilities [0.9, 0.1], every final vector contains one observation of each arm. Exchangeability therefore gives actual row probabilities [0.5, 0.5]. A local probe over seeds 0 through 999 produced total counts [1000, 1000], rather than preserving the nominal law. This is a finite-sample design property, not evidence of Monte Carlo bias of a particular estimator.

**P2: fallback can fail its own all-arms guarantee.** Missing arms are inserted at uniformly selected row indices without protecting the last observation of an existing arm. For n=3, constant probabilities [0.8, 0.199999999, 0.000000001], seed=4, direct `_draw_multinomial` returned [2, 0, 0], with counts [2, 0, 1]. Arm 1 remains missing.

Public reproduction: `MultiCausalDatasetGenerator(k=0, alpha_d=[0., 0., -1000.], seed=3).generate(3, U=np.zeros(3))` returned treatment counts [0, 2, 1]. `m_obs_d_2` was identically zero: the method forced an arm with zero numerical probability, while removing all control observations.

Direct zero-support reproduction: with n=3 and probabilities [1, 0, 0] at every row, seed=19 returned labels [0, 2, 1]. This shows that forced insertion intentionally changes support; it cannot be called an exact draw from the supplied probabilities.

Existing semantic and latent-oracle tests use comparatively large samples and check outcome means, additive effects, or latent propensity variation. They do not independently check retry conditioning, zero-support insertion, preservation of existing singleton arms, or single-draw RNG behavior.

## Bounded recommendation

Add an explicit trailing public parameter, e.g. `assignment_policy="ensure_all"`, to the generator and functional wrapper. Keep the historical compatibility policy as the default; add `"iid"` for one categorical draw per row without coverage conditioning or forced insertion. The iid option can permit positive n smaller than K for a raw DataFrame. Do not silently switch the default, alter existing columns, or attach a new meaning to `m_obs` without documenting the policy.

For `ensure_all`, retain the existing ten-attempt behavior, then repair coverage by overwriting only rows belonging to classes with count > 1. Update donor counts after every insertion. Since n >= K, enough surplus observations always exist: if r classes are represented, total surplus is n-r >= K-r. The repair intentionally changes the nominal assignment law, even when it protects coverage.

For reproducibility, preserve the existing proposed random indices whenever they all come from donor classes with sufficient surplus; choose replacements only where a proposed index would eliminate an arm. This narrows default-output changes to previously defective fallbacks. Do not promise exact legacy RNG identity on corrected defective paths; it is possible to preserve identity when the first draw covers all arms and on valid historical repairs.

Document `m` and `m_obs` as nominal assignment-model probabilities under `ensure_all`; exact row-conditional assignment probabilities apply to `iid` (with the existing U=0 versus realized-U distinction). Keeping outcome g/cate oracles unchanged is appropriate because the structural potential outcomes remain unchanged. No claim that the nominal probabilities identify the repaired finite-sample assignment law is appropriate.

Missing-arm outputs can be valid raw one-hot DataFrames. `MultiCausalData` currently accepts constant treatment columns but rejects duplicate stored columns; two absent arms can therefore fail its separate duplicate-value contract. Do not relax that data contract incidentally. Explain this difference for `return_causal_data=True`, or raise a clear wrapper-specific error when necessary. Fitted nuisance models may independently require each arm to be observed.

The functional wrapper also currently describes `target_d_rate` as "Target marginal class probabilities", whereas the base class already correctly documents U=0 sample calibration. Correct this wording when touching its parameter documentation.

## Independent test targets

1. Deterministic RNG stub: ten draws containing [0, 0, 1], proposed overwrite of singleton arm 1; repaired result must contain all three arms.
2. More than one missing arm, n=K and n>K; donor counts never fall below one.
3. Reproductions above with real seeds; keep public coverage regression and zero-support iid regression distinct.
4. Iid exact comparison against an independent inverse-CDF reference using a separately seeded RNG; verify next RNG value to prove one draw and no hidden retries.
5. Iid n=1, K=3 is a valid raw one-hot DataFrame; ensure_all rejects n<K with a policy-specific explanation.
6. Zero-support iid probabilities never assign zero-support arms. No stochastic frequency threshold is needed.
7. Unknown policy fails before generating observations; wrapper forwards the policy.
8. Default equals explicit ensure_all; first-success seeded output and downstream outcome draws match the B07 baseline.
9. Policy changes assignment draws and therefore potentially observed y/RNG progression; oracle schema, structural g/cate, and propensity formulas retain their specified meanings.
10. Independent deterministic enumeration for K=2, n=2 illustrates conditioning exactly; avoid a slow probabilistic CI assertion merely reproducing the implementation.

All initial probes used `.venv\\Scripts\\python.exe` from the repository. The initial review made no source, test, Git, or sensitivity mutations.

## Implemented and verified

Implemented `assignment_policy` after the existing `seed` field in the dataclass and after the existing final parameter in the functional wrapper, preserving old positional argument mappings. Initialization and `generate` validate the policy, including post-initialization mutation. The iid branch makes exactly one vector uniform draw and sets the terminal CDF to one. The compatibility branch retains its original ten retries and initial `choice(n, ...)` proposals; only singleton-erasing proposals draw a replacement from surplus donors. Counts update after each insertion, so later proposals cannot erase an earlier repaired singleton. No automatic warning or schema change was introduced.

Added `tests/data/test_multicausal_assignment_policy.py`: **75 cases**. Coverage spans 60 seed/configuration combinations, the public failure, iid independent inverse-CDF labels and exact next RNG state, zero-support iid behavior, n<K raw generation, policy validation, wrapper forwarding, first-success public X/D/Y and RNG identity, a safe historical fallback with exact labels/RNG, and a deterministic ten-draw singleton-overwrite script.

Baseline log `block08_sampling_before_tests.log` records **29 failed / 44 passed**, 10.40 s. This run preceded the policy implementation but overlapped the independent contracts work: it is not an untouched full-B07-source baseline. Eighteen failures were actual coverage regressions (one public reproduction and seventeen seed/configuration cases); ten exercised the absent new policy API; one was a test error expecting a different existing rejection message. The old `n<K` behavior was already correct for the compatibility policy. Its test regex was corrected to accept `n must`, rather than counting a diagnostic wording mismatch as a defect.

After implementation, `block08_sampling_after_tests.log` records **103 passed**, 44.53 s: the then-current 73 policy cases plus 30 existing semantic/latent-oracle neighbors. The two final independent fallback tests were added afterward. `block08_sampling_final_tests.log` records **75 passed**, 8.45 s, for the final policy test file. No test failures or warnings occurred in either successful run. Counts overlap and must not be added.

The compatibility claim is deliberately bounded: first-success draws and already-safe legacy fallbacks preserve labels and RNG state; formerly invalid repairs can change both. The new policy allows exact nominal assignment draws but does not resolve Gaussian-marginal propensity integration or selected-treatment ATT oracles. Those features remain separate work.

Root subsequently replayed the final 75 tests against both exact B07 generator and wrapper source via `probe_block08_sampling_baseline.py`. `block08_sampling_exact_before_tests.log`: **29 failed, 46 passed, 2.33 s**. Here nineteen failures reproduce missing coverage (public case, seventeen seed/configuration cases, and the deterministic singleton script); ten exercise the new API absent from B07. There is no diagnostic-regex fixture failure in this exact replay. This is the final baseline evidence; the earlier mixed-state run remains historical evidence.
