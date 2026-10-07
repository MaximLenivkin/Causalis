# B19 — extreme finite score/IF and custom ATE normalization

Baseline: `52cd6e2fbb1934edaa1191856f70424858a59f6f`. Personal branch:
`codex/correctness-roadmap`. Synthetic data only; individual records and arrays
remain in memory. Root agent only, repo-local Python 3.12.14 on macOS.

## Target and failure policy

IRM and MultiTreatmentIRM retain their ATE/ATTE estimating equations; IIVM
retains the reduced-form/first-stage LATE ratio and its population-moment SE.
No denominator derivative, estimand, overlap retention, clipping threshold,
fold assignment, or sensitivity implementation changes in this block.

Custom binary ATE continues to use the retained sample:
`w = weights / mean(weights)`, `w_bar = weights_bar / mean(weights)` and
`psi_b = w*(g1-g0) + w_bar*(h1*(y-g1)-h0*(y-g0))`.
If enabled, Hájek normalization separately divides h1 and h0 by their sample
means. Custom weights and Hájek denominator variability remain treated as fixed
in the existing approximate IF/SE; existing warnings and metadata are preserved.
Weights depending on D/Y still require an appropriate conditional representer;
this block does not establish identification for arbitrary supplied weights.
Signed weights remain permitted with the existing strictly positive retained
mean greater than 1e-12. Both normalized weight vectors must now be finite,
otherwise estimation raises ValueError. There is no arbitrary maximum weight,
new mean floor, automatic truncation or propensity floor.

Finite raw predictions do not guarantee representable float64 intermediates.
The chosen policy is explicit refusal: score/IPW, moment/IF/SE/Wald interval and
relative-effect arithmetic raise RuntimeError on overflow or invalid operations,
or when designated numerical outputs are non-finite. Messages suggest rescaling
outcomes/weights or increasing the estimator's overlap/trimming threshold and
refitting. NumPy error settings are scoped to each calculation and restored on
exit. Python OverflowError is translated too. Underflow retains existing policy.
A mathematically finite final answer can still be rejected when an intermediate
(such as the square of an IF) overflows. No extended-precision or scaled fallback
is promised; no nan_to_num or score clipping is introduced.

Intentional undefined results retain their existing semantics: zero SE can have
NaN t/p, singular moments retain their prior NaN behavior, and unsupported/weak
relative baselines can still give NaN relative effects. Weak-IV guards are
unchanged. IRM publishes its core cache after relative inference succeeds, so
these reproduced arithmetic failures leave a fresh fit without partial core
attributes. General estimate atomicity, externally mutated snapshots and failed
refit lifecycle policies are separate work.

## Implementation and reproductions

Exactly five library paths plus one new regression module change:
shared `_numerics.py`, binary `_score_utils.py`, and the three model modules.
The wrapper enables float64 overflow/invalid/division failure only around score
and inference calculations; diagnostic and sensitivity computation is outside
it. Explicit finite checks handle local intentional NumPy ignore contexts.
IIVM's existing arithmetic is extracted into `_compute_late_inference`; its
formula and operation order are retained.

Public fits with finite constant outcome predictions at ±1e155, 1e307 and
-1e308 reproduce squared-IF or score/reduction overflow. Boundary propensities
0/1 with the smallest positive overlap threshold reproduce reciprocal overflow
and 0*inf. Custom weights_bar=1e308 with accepted means 1.01e-12 and 1e-6
reproduce normalization overflow. Tiny/huge outcome baselines reproduce relative
inference overflow after the absolute calculation. Tests cover binary/multi
ATE/ATTE and IV LATE, requested Hájek on/off, and explicit failure before a new
estimate is published. Counts describe regression cases, not distinct bugs.

Four valid near-boundary custom-ATE cases at m=1e-10 and 1-1e-10 are checked
against an independently assembled fixed-normalization signal, IF and
sample-variance SE. IF comparison uses a scale-aware float64 tolerance for
cancellation; the baseline must pass these cases too. Existing mean-floor cases
and ordinary finite inference remain supported.

Final same-file baseline: 67 cases, 54 failed / 13 passed, no errors/skips.
Final focus: 527 passed, no failures/errors/skips, 13 existing policy warnings,
30.07 seconds (67 new cases + 460 B18 neighbors). The exact compatibility probe
checks 40 public fit pairs and 72 inference pairs, both Hájek settings, binary
and continuous outcomes, n_jobs=1/2 and diagnostics storage modes. Nuisance,
fold, coefficient, SE, p-value, CI and score/IF arrays match baseline exactly;
source frames are unchanged. 129 unmodified functions are AST-checked, and
10 source/test/dependency hashes are recorded. These are bounded synthetic
checks, not universal numerical or causal certificates.
Committed integration and CI linkage will follow in the final audit commit.

## Evidence

- [Exact-baseline runner](run_block19_baseline.py), [result](block19_baseline_result.json), [JUnit](block19_baseline.xml), [log](block19_baseline_tests.log).
- [Focused JUnit](block19_focus.xml), [log](block19_focus_tests.log).
- [Compatibility probe](probe_block19.py), [result](block19_probe_result.json), [log](block19_probe_checks.log).
- [Committed integration runner](run_block19_integration.py).
- [CI observer](observe_block19_ci.py), [artifact verifier](summarize_block19_ci.py).

## Limits and next block

No guarantee of correctness for every finite magnitude, subnormal precision,
conditioning, all dependency combinations, or speed is added. Relative and
core diagnostics/sensitivity are not given a new stable numerical algorithm.
Standalone Sphinx, release and upstream merge are outside this block. Seven
sensitivity exclusions remain unchanged; selected-U ATT and SC08 LOO remain
pending upstream/sensitivity work.

Next B20: establish duplicate numeric/object column and snapshot/refit contracts
from public reproductions, prioritizing concrete failures before changing an
ownership policy. Standalone Sphinx compatibility remains a separate gate.
Features follow correctness: repeated CF → group CF → external OOF → DR/R-CATE.
Stop at this block boundary; B20 requires the next user request.
