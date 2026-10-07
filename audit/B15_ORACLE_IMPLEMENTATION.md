# B15 · Additive Gaussian marginal propensity

Baseline: `71f6a619b04e0ab8fab388fb95b7d0f3d6631b96`. Source checkpoint is recorded in the final block report. Runtime scope: `causalis/dgp/multicausaldata/base.py` and `functional.py`.

The appended constructor/functional option `include_marginal_propensity=False` preserves all existing positional arguments. Only the new flag requires bool/NumPy bool; the old `include_oracle` contract is unchanged. Enabled marginal propensities require enabled oracles. Validation runs at construction, before sampling, and after structural callbacks before assembly. Only enabled new column names are reserved. Late failures do not roll back callbacks or random draws.

The new K columns are appended after all existing columns. For already calibrated affine scores a(X), the target is q_k(X)=E[softmax_k(a(X)+bZ)], independent Z~N(0,1). Supplied realized U does not define another latent law; ensure_all conditions/repairs the nominal law, so q is a reference model probability. U=0 calibration, m/m_obs, outcomes, CATE and latent-selected ATT semantics retain their separate meaning.

Equal slopes return the existing m exactly. Otherwise distinct score rows are integrated once with vector adaptive Gauss-Kronrod quadrature. Pairwise score crossings and local offsets 1/4/16/40 divided by the slope difference expose steep transitions and narrow intermediate-arm regions. The domain is [-12,12], estimated max-norm absolute error target 1e-10, relative target zero, and subinterval limit4096. Omitted normal probability mass is below4e-33. Error/status/finite/bounds/unit-mass checks precede rounding normalization; no m fallback or fixed-order convergence claim is made.

Common score/slope shifts are removed before affine evaluation. Opt-in floating-point geometries that cannot remain finite throughout the domain, excessive initial breakpoints and nonconvergence raise ValueError. This is an explicit unsupported numerical-domain policy, not a guarantee for arbitrary finite coefficients. Allocation is O(n*K + K**2 + L*K), L<=4096; no n*K*nodes tensor, and memoization is bounded to262144bytes. Time can be substantial for varying X; no performance improvement is claimed.

The existing outcome integration bodies, sampling, calibration and assignment algorithms are unchanged. No quadrature work is done with the option disabled. Independent contract, same-file baseline/focused regressions, reference review, committed integration and six actual CI artifact sets are linked in the final report.
