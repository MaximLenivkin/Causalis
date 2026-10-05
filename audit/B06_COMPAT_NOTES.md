# B06 compatibility and release gates

Implementation starts from `bf2ea87534e4eaf82266cb61d905b7e876cc2e1d`; the root agent owns commits and GitHub execution evidence. No release/tag/PyPI publication was triggered by this work.

## ROOT-08: Pydantic requirement

`pyproject.toml` now declares **`pydantic>=2`**. Contracts import `model_validator`, `field_validator`, `ConfigDict` and `AliasChoices`, so an installed 1.x cannot satisfy the package requirement any more. The versioned [Pydantic 2.0 migration guide](https://docs.pydantic.dev/2.0/migration/) documents the v2 validator/config APIs; the [2.0 field guide](https://docs.pydantic.dev/2.0/usage/fields/) documents AliasChoices and separate validation/serialization aliases. This fixes the resolver/import boundary; it does not assert that every possible 2.x patch has been executed.

The legacy CI job exercises Pydantic 2.0.3, a representative patch from the first v2 minor release. The local environment remains Pydantic 2.13.5 and was not changed. Other runtime dependencies retain their existing public bounds; the legacy constraints are explicitly a CI fixture, not inferred minimum support for all packages.

## ROOT-09: release pytest gate

Previously `release.yml` called its build job “Test and build distributions”, but did not run pytest. The job now creates `.venv`, installs `.[dev,docs]` plus release tooling, checks dependency consistency, verifies the existing release tag rules, runs **`scripts/run_tests.py --scope full`**, then builds and validates distributions. Ordinary step failure blocks both build and the downstream PyPI job. GitHub Release still depends on PyPI. The existing annotated tag, semver, package-version and ancestry-to-origin/main constraints are retained.

The full gate has no sensitivity exclusions, no `continue-on-error`, and no `SKIP_DOCS_BUILD=true`. An actual sensitivity failure will block a future release until upstream repairs it. We did **not** run or change the project's sensitivity modules/tests during B06. Installing the docs extra avoids missing-package skips, but pytest alone does not demonstrate a production Sphinx site build: the current `tests/docs/test_generate_api_reference.py` contains helper functions and no collected tests. A dedicated documentation build gate remains a separate improvement.

`scripts/run_tests.py` defaults to full selection and preserves pytest's real exit status, including failed tests (1), collection/interruption errors (2), and no tests collected (5). It records environment, commit, exact args/exclusions, elapsed time and result alongside JUnit output. Hidden `PYTEST_ADDOPTS` is rejected to keep the selection explicit. Existing pytest test-level skip policies are not overridden; a full selection means all repository test modules are submitted to pytest, not that every test has necessarily passed or executed.

## Development compatibility matrix

`.github/workflows/ci.yml` runs on main/codex branch pushes, pull requests and manual dispatch. All six jobs have `fail-fast: false` and execute the complete **non-sensitivity** repository suite, including the CUPED public statsmodels adapter reference/reuse tests. Job names and manifests explicitly say sensitivity is deferred; this workflow is not a replacement for the full release gate.

Branch pushes that modify only `audit/**` are ignored, so a final evidence/report checkpoint does not cancel or restart the matrix for unchanged library/test source. Any push with a change outside that directory still runs the workflow. Pull-request and manual-dispatch triggers retain their existing behavior; no broader Markdown filter is applied.

| Python | Stack | Scope |
|---|---|---|
| 3.10 | Latest versions compatible with that interpreter | Scoped correctness |
| 3.11 | Latest versions compatible with that interpreter | Scoped correctness |
| 3.12 | Latest versions compatible with that interpreter | Scoped correctness |
| 3.13 | Latest versions compatible with that interpreter | Scoped correctness |
| 3.14 | Latest versions compatible with that interpreter | Scoped correctness |
| 3.10 | Representative older stack below | Scoped correctness |

Legacy constraints: NumPy 1.26.4, pandas 1.5.3, SciPy 1.11.4, statsmodels 0.14.0, scikit-learn 1.3.2, Pydantic 2.0.3, CatBoost 1.2.8. NumPy/SciPy are constrained with pandas/statsmodels to avoid introducing an ABI mismatch or removed SciPy API into this particular compatibility fixture. Current/latest package versions are resolved in clean job-local environments and reported by the runner; they are not assumed to equal the local environment. Python patch versions are selected by [setup-python](https://github.com/actions/setup-python/blob/main/docs/advanced-usage.md). The [GitHub matrix syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idstrategymatrix) documents the explicit include matrix and fail-fast policy.

Only these seven existing modules are deferred in the development correctness scope:

- `tests/refutation/test_multi_sensitivity_benchmark.py`
- `tests/refutation/test_sensitivity_benchmark.py`
- `tests/refutation/test_sensitivity_combination.py`
- `tests/refutation/test_sensitivity_integration_irm.py`
- `tests/refutation/test_sensitivity_protocol.py`
- `tests/refutation/test_sensitivity_rv_signed_rr.py`
- `tests/refutation/test_trim_sensitivity_ate.py`

Discovery of a new sensitivity-named test module raises an error that requires explicit scope review; it is never automatically ignored. Removing an old deferred module removes it from the actual ignore list. No sensitivity source or test path is edited here. Existing ordinary DML tests may construct legacy sensitivity payloads as part of model behavior; those tests are not sensitivity formula validation.

## Local evidence and reproducible commands

Focused CI policy tests: **11 passed in 6.30s**, no warnings, exit 0. These include three real subprocess pytest fixtures: full synthetic failing sensitivity sentinel exits 1; full empty fixture exits 5; scoped synthetic sentinel is excluded while a passing ordinary test executes. They exercise gate selection/exit semantics, not any deferred sensitivity formula.

```powershell
$env:MPLBACKEND='Agg'
$env:MPLCONFIGDIR='D:\codex\Causalis\audit\mplconfig'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=audit/block06_compat_test_temp tests/test_compatibility_ci_runner.py
.\.venv\Scripts\python.exe audit/block06_compat_checks.py
```

`block06_compat_tests.log` retains the exact focused result. `block06_compat_checks.py` parses TOML/YAML and checks Pydantic v1 rejection, six matrix entries, supported Python minors, branch triggers, fail-fast policy, full pytest ordering before build, preserved publish graph/tag rules, local Python entrypoint policy, AST syntax, and exact deferred module list. Its JSON/log report issues 0. This is a static check, not actionlint validation, installation, a GitHub workflow result, or a six-interpreter test result.

The local `.venv` has no pip/build/twine module. No install, dependency replacement or interpreter replacement was performed locally. Actual GitHub job results must be attached by the root agent after pushing a checkpoint; **no matrix success is claimed in these notes before that evidence exists**. Matrix is Linux only; local B06 verification uses Windows/Python 3.12.14. This is representative coverage, not every dependency cross product, Mac support validation or full release validation.

## Compatibility defect actually found by clean CI

The initial legacy job on `d292b3c2f83ec94ef75652a17f3e34436c71902f` installed successfully and passed `pip check`, then returned pytest exit 1: **1516 passed, 53 failed**. Although its overall run/job was subsequently cancelled by a newer push, its pytest step had already failed. All 53 failures had one source cause: IIVM's joint strata used `z.astype(str) + "_" + d.astype(str)`, while NumPy 1.26.4's addition ufunc has no Unicode string loop. This was an actual compatibility defect, not evidence of a Pydantic/schema or CUPED adapter failure. The separately preserved `block06_ci_prior_legacy_result.json` records versions, failure grouping, counts and source checkpoint.

The root agent replaced that expression with nested `np.char.add`, preserving the exact joint labels rather than re-encoding them, and added 13 independent fold/legacy-behavior regressions. The [NumPy 1.26 API](https://numpy.org/doc/1.26/reference/generated/numpy.char.add.html) supports elementwise string concatenation. Corrected-source [run 37373828518](https://github.com/MaximLenivkin/Causalis/actions/runs/37373828518) uses **`09e00de5a9d3dc915c6d59627f8b0ebc875dd4e9`**; its legacy job has actually passed **1582 tests, zero failures/errors/skips**, on NumPy 1.26.4, pandas 1.5.3, statsmodels 0.14.0 and Pydantic 2.0.3. Final six-job status and every installed dependency version are recorded in `block06_ci_result.json`; `matrix_verified` becomes true only after all six jobs conclude success and all six artifacts are checked against the exact source and expected 1582 tests. Earlier partial successes are retained in `block06_ci_before_fix_result.json` and are never mixed into the corrected-source matrix.

**Final observation: 2026-10-05 21:21:54 UTC. The corrected-source run completed successfully; all six job artifacts were independently checked. Each job ran 1582 tests with zero failures, errors or skips.** `matrix_verified=true`, verified successful jobs 6, artifact verification issues 0. The seven explicitly deferred sensitivity modules remain excluded; this is six clean scoped correctness runs, not full sensitivity/release validation.

| Actual Python | Stack | NumPy | pandas | statsmodels | Pydantic |
|---|---|---|---|---|---|
| 3.10.21 | latest compatible | 2.2.6 | 2.3.3 | 0.15.0 | 2.13.5 |
| 3.10.21 | legacy | 1.26.4 | 1.5.3 | 0.14.0 | 2.0.3 |
| 3.11.16 | latest compatible | 2.4.6 | 3.0.6 | 0.15.0 | 2.13.5 |
| 3.12.14 | latest compatible | 2.5.3 | 3.0.6 | 0.15.0 | 2.13.5 |
| 3.13.15 | latest compatible | 2.5.3 | 3.0.6 | 0.15.0 | 2.13.5 |
| 3.14.7 | latest compatible | 2.5.3 | 3.0.6 | 0.15.0 | 2.13.5 |

The compact JSON also records exact SciPy/scikit-learn/CatBoost, plotting/docs/test dependency versions, per-job timings, source and scope. Timings are CI test durations, not a library performance comparison. No further monitoring or source/configuration changes were performed after this final snapshot.

The initial queue coincided with the [GitHub Actions hosted-runner incident](https://www.githubstatus.com/incidents/3q1yb5m7ltvb). That external report supports the queue interpretation but does not prove the cause of an individual delayed job. No rerun, cancellation, library change or publication was performed by the compatibility-monitoring subagent; the root agent owns the actual source fix, commits and pushes.

Artifact verification is reproducible with:

```powershell
.\.venv\Scripts\python.exe audit/summarize_block06_ci.py --run-id 37373828518 --source 09e00de5a9d3dc915c6d59627f8b0ebc875dd4e9 --expected-tests 1582
```

The raw timestamped GitHub snapshot and downloaded artifacts belong to `audit/block06_ci_test_temp/run-37373828518/` (ignored); the compact result JSON is the committed evidence. A final audit-only checkpoint does not restart this validated-source workflow.

## Ready documentation text

> Causalis requires Python 3.10–3.14 and Pydantic 2 or later. Pydantic 1 is incompatible with the data-contract validation APIs and is rejected by package metadata. Compatibility CI tests latest compatible dependencies for each supported Python minor and a representative older dependency stack. Consult the workflow artifacts for the exact installed versions and test results. During the upstream sensitivity-analysis rewrite, development CI explicitly defers seven sensitivity test modules; release CI selects the complete test suite and a failing test prevents publication.

Do not say “all supported versions passed” unless the corresponding six jobs actually pass. Do not say the documentation build was validated by this change. Release rules and the publication configuration otherwise retain their existing behavior.
