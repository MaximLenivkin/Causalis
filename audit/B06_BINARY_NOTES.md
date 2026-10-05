# B06: numeric binary detection

Numeric `bool/int/uint/float/complex` arrays use exact comparisons with 0/1 instead of unique/sort. Complex helper behavior is preserved for compatibility; public contracts still reject complex analysis data. Object/string/datetime and other dtype arrays retain the former fallback, including its exceptions.

Binary-treatment IRM and IV require both 0 and 1; multi-treatment IRM treats constant zero/one outcomes as binary. Empty input returns False for both. No tolerances, missing-value filtering, integer truncation or learner-selection changes were introduced. Inputs can be noncontiguous, multidimensional or read-only; no mutation occurs. Other np.unique calls, including fold/class enumeration, are retained.

New 74 cases: 66 reference cases (33 arrays × two helpers), two no-sort/readonly checks, six full-estimator comparisons (binary/multi/IV × continuous/binary Y). Each comparison uses repeated DataFrame indices and checks identical folds, nuisance predictions, scores/IF, effects, p-values and confidence intervals against the legacy helper. No sensitivity-targeted execution.

Before optimization: **2 failed, 72 passed**, 13.64s; the failures demonstrate numeric sorting, not wrong statistical results. After: **111 passed**, one existing low-signal relative-baseline warning, 18.86s including 37 neighboring cases. Raw logs: `block06_binary_before_tests.log`, `block06_binary_after_tests.log`.

Owned extraction remains an audit-only benchmark candidate. There is no caching or changed pandas ownership/mutation contract in this patch.
