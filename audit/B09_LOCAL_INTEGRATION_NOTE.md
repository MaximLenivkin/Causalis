# B09 local DiD diagnostic failure: unchanged numerical-zero fragility

Date: 2026-10-07, Europe/Moscow. B09 source commit: `1e2b544f7f91a57ad3e049572915a4b3891b084a`. Pre-B09 checkpoint: `74145665127f8fa5a0bf038d769697ab880854b8`.

The root local scoped integration reported **2038 passed, 1 failed, 80 warnings** in 117.46 seconds. The failure was:

`tests/scenarios/did/refutation/test_did_post_inference_diagnostics.py::test_post_inference_report_accepts_panel_and_estimate`

The unchanged assertion expects `GREEN`; this machine returns `YELLOW`. Read-only probes reproduce the **same one-case failure on current and pre-B09 source**, with identical report rows and fitted aggregate cell rows. This is a pre-existing numerical-zero fragility on the current macOS stack, not a B09 source regression. These probes do not establish that the behavior is unique to macOS or isolate operating system, BLAS, and dependency effects.

## Observed reason

The only non-green detail row is `fitted_pre_period_placebo`, with a maximum absolute t-statistic of **378254753641406.06** against the relaxed threshold 10. All other detail report rows are green.

The responsible pre-period cell, `cell_id=0`, has:

| Quantity | Value |
| --- | ---: |
| ATT | 1.1102230246251558e-16 |
| SE | 2.9351198205368013e-31 |
| Absolute t-statistic | 378254753641406.06 |
| Control design rank / parameters | 2 / 2 |
| Control design condition number | 13.626614198845914 |
| Control effective sample size | 1.1939990074156166 |

Across all fitted cells, condition numbers are between 13.626614198845914 and 13.997558972175948, every control design is full rank, and every fitted cell diagnostic status is green. The failure is therefore not a new support, rank, or conditioning warning.

The synthetic fixture has exactly common deterministic linear pre-treatment trends, with treatment effects added only after adoption. Its mathematical pre-period ATT and variance are zero. The two-control, two-parameter outcome regression is saturated; floating-point residuals around that exact-zero calculation can yield a tiny nonzero ATT and a much smaller positive SE. The existing `_safe_t_stat` divides whenever SE is positive; its special zero-SE branch applies only when SE is exactly zero. This yields the extreme standardized ratio observed above despite the absolute ATT being at machine precision.

No production inference policy, diagnostic threshold, test assertion, or fixture was changed. A later bounded review should define the diagnostic policy for numerical-zero / zero-variance cells and consider a nondegenerate fixture for this public API test. Blanket tolerance changes are not justified by this single example.

## Exact-source evidence

Only the two multi-treatment DGP source files differ between the frozen checkpoint and B09; the new namespace test is the only added test. The failing DiD fixture is byte-identical to the frozen checkpoint. Both probes check that all other tracked package paths are unchanged.

The baseline probe reconstructs the two changed DGP files from Git objects and loads them under their original module names; it also reconstructs the original fixture. Runtime profiling of fit, estimate, report, and influence-table calls finds **five package source paths**, all byte-identical to the frozen checkpoint. Neither changed DGP path is called. Current and baseline report rows, aggregate cell rows, and isolated failure messages are identical.

Evidence files:

- `block09_did_probe_result.json`: exact node, source SHAs, source-closure checks, matching counts/messages, numerical reason, and conditioning summary.
- `block09_did_current_probe.json` and `block09_did_baseline_probe.json`: aggregate report and cell outputs, called-source hashes, dependency/platform details.
- `block09_did_current_case.xml` and `block09_did_baseline_case.xml`: isolated raw JUnit; each has tests=1, failures=1, errors=0, skipped=0, passed=0.
- `block09_did_current_case.log` and `block09_did_baseline_case.log`: isolated pytest outputs. Both exit with code 1 and `AssertionError: assert 'YELLOW' == 'GREEN'`.

The reproducible probes are:

```bash
.venv/bin/python audit/block09_did_probe.py --mode current
.venv/bin/python audit/block09_did_probe.py --mode baseline
.venv/bin/python audit/block09_did_case.py --mode current
.venv/bin/python audit/block09_did_case.py --mode baseline
```

The final two commands intentionally reproduce the assertion failure and return exit code 1. All runners set native thread counts to one, use Agg and `.venv/matplotlib`, and skip documentation builds. Temporary baseline snapshots are deleted. Only aggregate/scalar synthetic diagnostic outputs were saved; no individual rows were saved.

This probe task did not rerun integration or CI. Root owns the full scoped integration and CI conclusions. The local scoped suite remains non-clean with this documented baseline failure; no full-suite, sensitivity, or release validation is claimed.
