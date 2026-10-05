# B04: normalized cell influence and traditional MLE/OLS inference

Scope: SC-01 and SC-03; source `causalis/scenarios/did/model.py`. Base code for the reproduction: B03 `f57f2d32d232e5ab0b358153f6ac564e615d19c3`. Sensitivity modules are excluded. The point estimator remains the existing traditional logistic MLE / control OLS estimator, rather than switching to IPT / weighted least squares.

## Derivation for the implemented empirical estimator

Let a cell contain `n` complete units, design `X` including an unpenalized intercept, treatment-cohort membership `D`, outcome change `ΔY`, and `r=ΔY-Xβ` in DR/AIPW (`r=ΔY` in IPW). Write `p0=expit(Xγ)` and the weight probability `p=clip(p0,c,1-c)`. Define `wt=D/mean(D)` and `wc=((1-D)p/(1-p))/mean((1-D)p/(1-p))`. The estimator is `θ=ηt-ηc`, where `ηt=mean(wt r)` and `ηc=mean(wc r)`.

The normalized direct influence is

`IF_direct = wt(r-ηt)-wc(r-ηc)`.

The previous `(wt-wc)r-wtθ` omits the control normalization. This makes IPW variance change when the same arbitrary time trend is added to every unit, although the DID effect is unchanged.

For OLS on controls,

`IFβ_i = [mean((1-D)XX')]^-1 (1-D_i)X_i r_i`.

The implementation evaluates this representation through the SVD pseudoinverse of the control design, avoiding a squared condition number from forming its normal equations. Numerically center the empirical influence rows; least-squares equations imply zero mean at a full-rank exact solution. The derivative of the estimator in the β direction is `-mean((wt-wc)X)`.

For the actual penalized MLE objective `mean(logaddexp(0,Xγ)-D Xγ)+λγ'Rγ/2`, with `R=diag(0,1,...)`,

`Hγ = mean(p0(1-p0)XX') + λR`,

`IFγ_i = Hγ^-1 {X_i(D_i-p0_i)-mean[X(D-p0)]}`.

Centering is required with nonzero fixed ridge: the penalty stays fixed when the empirical distribution is contaminated. At an exact optimum the subtracted score mean equals `λRγ`. The likelihood Hessian uses the raw fitted probability `p0`, not clipped weights `p`.

The Hessian inverse map is computed from the augmented weighted design `A=[sqrt(p0(1-p0)/n)X; sqrt(λ)R]`, through `pinv(A) pinv(A)'`, since `A'A=Hγ`. This avoids forming a Gram-matrix pseudoinverse, which squares the condition number and can discard valid directions after rescaling a covariate. The parameter penalty uses the current coefficient scale: rescaling covariates with a fixed positive isotropic slope ridge changes the estimator, so invariance is only asserted at ridge zero.

Let `A_i=1{c<p0_i<1-c}`. Away from clipping boundaries, the derivative of normalized control odds in the γ direction gives `-mean(wc A (r-ηc)X)`. Thus

`IF = IF_direct - IFβ·mean((wt-wc)X) - IFγ·mean(wc A (r-ηc)X)`.

IPW has no β term. For an intercept-only design, both nuisance contributions are identically zero; the normalized control odds are a constant within controls. This remains a difference of sample means even when the sample treatment share is clipped.

The cell influence embeds into the original panel-unit population as `IF_full = 1{unit in cell} IF_cell * n_total/n_cell`. Units lacking either outcome period receive zero cell influence. This targets the selected complete-case functional; it does not identify full-population effects under arbitrary missingness.

## Primary reference and scope of agreement

The official [DRDID traditional panel implementation](https://github.com/pedrohcgs/DRDID/blob/85807cfbddbd64cc6f3f8ba37f52d07c6c3acc65/R/drdid_panel.R#L140), nuisance and normalization influence at lines 140–190 (retrieved 2026-10-05), provides the no-ridge, no-active-trimming specialization. This review uses a separate Python translation of that specialization, not an executed R-package comparison. Causalis retains its own symmetric clipping policy; the derivative above follows its actual policy rather than copying the reference package's trimming rule.

Traditional MLE/OLS with full nuisance influence is distinct from the improved IPT/WLS procedure. With two correct nuisance models and regular overlap the nuisance correction vanishes asymptotically; with misspecified nuisance components it generally does not vanish.

Fixed nonzero ridge and active clipping can change the population nuisance probability. The computed influence describes the implemented penalized/clipped functional, and does not restore double-robust causal consistency when only the original propensity model is correctly specified. Clipping at an exact boundary is nonregular; derivative tests stay away from such boundaries. Rank-deficient or ill-conditioned designs continue to require diagnostic attention; a fixed-rank pseudoinverse does not establish causal identification or conventional asymptotic coverage at a changing rank.

## Independent tests and reproduction

`tests/scenarios/did/test_did_cell_influence.py` contains 34 cases:

- 12 parameter combinations: DR/AIPW/IPW × ridge `0/.07` × clip `1e-6/.25`. For each combination, all 96 empirical contamination directions are evaluated by independently refitting weighted logistic estimating equations with an analytic Jacobian and weighted least squares. The implementation's BFGS fitting and influence helper are not used in this reference. Central perturbations `±2e-5` preserve positive empirical masses.
- 12 common-trend / complete-case embedding cases across the three estimators, with and without covariates and with balanced/unbalanced panels. A common trend of 1000 is added; ATT, SE, p-value and unit influence must agree. Omitted rows exclude five treated and five control units from the complete cell without excluding them from the original population.
- Three intercept-only cases where the treated share `8/90` is below clip `.2`; influence must equal the independently centered difference-of-means representation.
- One explicit traditional DRDID no-ridge matrix reference with 240 units, using separately computed OLS and MLE Hessians.
- Six nuisance-influence scale cases: DR/AIPW/IPW × covariate multipliers `1e6/1e7`, with zero ridge. The raw likelihood and fitted weight probabilities are held exactly the same by transforming the logistic coefficient. This isolates the linear-algebra influence map from optimizer convergence on differently scaled input.

Before patch: **18 failed, 10 passed, 20.84 s**. All 12 independent derivative cases fail, four IPW common-trend cases fail, the IPW clipped-share case fails, and the traditional DRDID reference fails. Raw evidence: `block04_cell_before_tests.log`. This counts failing test cases, not independent defects.

First post-patch: **28 passed, 22.09 s**, `block04_cell_after_tests.log`. New numeric scale cases then failed **6/6**, `block04_cell_scale_before_tests.log`, with the initial Gram-based propensity-Hessian pseudoinverse. After replacing this with augmented-design SVD: **34 passed, 23.09 s**, `block04_cell_final_tests.log`. These intermediate failures belong to the newly introduced solver during this block, rather than additional original-audit findings.

Existing targeted DiD model, refutation, data-contract and DGP neighbors: **45 passed, 19.01 s**, `block04_cell_neighbor_tests.log`. This run preceded the final equivalent numeric solver refinement; the root agent runs the integration suite after all B04 changes.

## Estimated-nuisance coverage probe

`audit/block04_cell_coverage.py` fits the actual logistic MLE and control OLS for each replication and uses the final cell influence helper. It generates two one-dimensional covariate designs with true constant ATT `2`, Gaussian outcome noise and independent units. There are 600 replications of `n=600` each, seed `48129`, ridge zero and no active clipping. This is an estimated-nuisance cell experiment, rather than oracle prediction injection or a validation of staggered panel support and population aggregation.

| DGP | Mean ATT | Empirical SD | Mean corrected SE | Corrected SE / empirical SD | Corrected 95% coverage (MCSE) | Previous raw-score coverage |
|---|---:|---:|---:|---:|---:|---:|
| Correct logistic propensity `expit(-.15+.8X)`, misspecified linear OR for `exp(.6X)` | 2.004463 | .122363 | .112119 | .916274 | .935000 (.010064) | .941667 |
| Misspecified linear-logit propensity for `expit(-.15+.6X+.45X²)`, correct OR `1+.7X` | 1.999753 | .086321 | .088849 | 1.029285 | .956667 (.008312) | .943333 |

Evidence: `block04_cell_coverage.json` and `block04_cell_coverage.log`. Root-mean-square reported SE in the first DGP is `.115236`, below empirical SD `.122363`. The first DGP therefore retains a finite-sample SE discrepancy; coverage is 1.5 percentage points below nominal, about 1.5 Monte Carlo standard errors. These numbers do not demonstrate uniformly better finite-sample coverage than the old incorrect formula. The independent empirical derivatives establish correspondence to the actual estimator; coverage is a separate, limited check. Larger sample sizes, weak overlap, heavy-tailed changes, varying designs and few-cluster refinements remain subjects for dedicated validation.

The simulation script was rerun against the final augmented-SVD source with local `MPLCONFIGDIR`; the saved final log has no sandbox font-cache error. It writes a separate JSON result and does not alter historical audit files.

## Migration paragraph for public documentation

> Cell inference uses the full influence function of the implemented normalized logistic MLE/control OLS estimator, including the estimated nuisance coefficients and both weight normalizations. AIPW is an alias for the traditional DR estimator. Fixed ridge and active propensity clipping can change the probability limit; the corrected variance does not remove that bias. The local derivative requires stable design rank and clipping regions. On an incomplete panel, each cell targets the units observed at both comparison dates.

The root agent incorporates this explanation into the public model docstring and documentation handoff. No claim of switching to improved IPT/WLS estimation is made.
