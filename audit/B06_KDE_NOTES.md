# B06: exact Gaussian KDE with bounded kernel workspace

Baseline: `bf2ea87534e4eaf82266cb61d905b7e876cc2e1d`. Change owned by this subtask: only `_kde_unbounded` in [outcome_plots.py](D:/codex/Causalis/causalis/shared/outcome_plots.py:30), focused [tests](D:/codex/Causalis/tests/statistics/test_outcome_kde_memory.py:1), and this evidence. Sensitivity and other estimators were not changed.

## Defect and implementation

The previous ordinary KDE materialized an `n_group × n_grid` standardized-difference matrix and a second kernel matrix, with further expression temporaries. At `n_group=1,000,000`, `n_grid=800`, each float64 matrix alone is 6.4 GB; the two named matrices alone are 12.8 GB. These figures are shape calculations, not an executed out-of-memory experiment.

The new helper evaluates **every observation/grid pair exactly once**, using one reusable float64 block. Subtraction, division by bandwidth, squaring, multiplication, exponentiation and Gaussian normalization use `out=` to reuse that block. A partial-sum vector is accumulated into the output density and divided by the original total observation count. Both observations and grid coordinates are blocked, so a very wide grid also stays within the explicit kernel-work-array budget. This is the same Gaussian estimator, without sampling, FFT, grid approximation or bandwidth changes.

The original three positional parameters still work. A private keyword-only `max_work_bytes`, default `8*1024*1024`, permits a different scratch budget and tests; it accepts integer/NumPy integer values of at least 16 bytes, rejecting booleans, fractional/string/None values. There is no new public plot option.

## Memory bound and limits

For ordinary data, let `B=floor(max_work_bytes/8)`, `g=min(n_grid,floor(B/2))`, and `b=min(n_group,floor(B/g)-1)`. The two explicitly allocated work arrays total `8*g*(b+1)` bytes, which is at most `max_work_bytes`. With the existing 800-point grid and the default 8 MiB budget, `b=1309`, the kernel matrix is 8,377,600 bytes and the partial vector 6,400 bytes: **8,384,000 bytes together**. They are reused across all blocks, including short final blocks.

The single/nearly-constant bump branch also blocks grid coordinates and reuses one float64 vector within the budget. The empty-input result still uses the original `zeros_like(xs)` semantics.

This is a **kernel workspace bound**, not a total-memory or process-RSS guarantee. The existing float conversion can copy the input; NumPy's unchanged `std` calculation may allocate O(n) work; the grid and returned density cost O(n_grid); NumPy iterator/reduction buffers and Python object overhead are outside the explicit-array budget. The caller's existing DataFrame selections, finite filtering, quantile calculations and bandwidth calculation also use memory. Overall input/output processing remains linear in input/grid size, while the n×grid matrices are eliminated.

## Preserved semantics and numeric validation

- `_silverman_bandwidth`, including its quantiles, ddof and floors, is untouched. All plot treatment/group selection, finite filtering, 800-point grid, clipping, histogram behavior, color/labels and density-to-count scaling are untouched.
- Empty, single, constant and standard deviation below `1e-12` use the original choices. The bump retains `h0=max(h,1e-3)` and matches the dense formula bit for bit in the tested cases.
- Ordinary density agrees with an independent copy of the original dense formula at `rtol=2e-14, atol=2e-15` on normal/skewed/separated inputs, budgets from 16 bytes through 8 MiB, and after row permutations. Blocking changes the grouping of float64 additions, so bitwise identity for ordinary density is not promised.
- An independent SciPy `gaussian_kde` oracle uses `bw_method=h/std(x,ddof=1)` to match the **same absolute bandwidth**, and agrees at `rtol=2e-13, atol=2e-15`. SciPy's default bandwidth is deliberately not substituted.
- Huge/infinite grid tails retain zero densities; NaN grid coordinates retain NaN output. Existing warning and nonfinite-input policies were not redesigned. Public plotting still removes nonfinite group observations before KDE, as checked through the actual plotted lines.
- A structural test observes exactly two ordinary work-array allocations, checks their combined bytes against a 512-byte budget, forces blocking along both axes and verifies that the sum of evaluated pair counts is exactly `n_group*n_grid`.
- A traced-allocation check with 20,000 observations × 801 grid points and 128 KiB private budget passes an upper bound of 566,032 traced bytes (allowing linear std scratch, output, iterator/reduction buffers and overhead). One original dense matrix alone would be 128,160,000 bytes. This test does not measure process RSS or claim tracemalloc sees every native allocation.

## Final focused check

Command, from `D:\codex\Causalis`:

```powershell
$env:MPLBACKEND='Agg'
$env:MPLCONFIGDIR='D:\codex\Causalis\audit\mplconfig'
.\.venv\Scripts\python.exe -m pytest tests/statistics/test_outcome_kde_memory.py tests/statistics/test_outcome_plots.py -p no:cacheprovider --basetemp=audit/block06_kde_test_temp
```

**40 passed, 0 failed, 0 warnings, 12.67 s**, including 37 new KDE tests and three existing plot tests. This rerun covers the final constant-bump block implementation. Log: [block06_kde_tests.log](D:/codex/Causalis/audit/block06_kde_tests.log); machine-readable focused result: [block06_kde_result.json](D:/codex/Causalis/audit/block06_kde_result.json).

Root's final sequential benchmark uses [benchmark_block06.py](D:/codex/Causalis/audit/benchmark_block06.py) for before/after timing and traced memory, alongside the other B06 paths. No speed claim is made from focused pytest runtime; the purpose of this change is removing the n×grid memory requirement. There is no separate concurrent KDE benchmark worker.

No statistical specification changed, so no new causal coverage claim is made. Arbitrary numerical inputs, underflow/overflow and summation order remain limited by float64 arithmetic. The test tolerances above are verified regression tolerances for the stated fixtures, not a uniform relative-error theorem for every sample/grid/bandwidth.
