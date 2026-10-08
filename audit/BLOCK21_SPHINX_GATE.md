# B21 — standalone Sphinx compatibility gate

Baseline: `2db4802b13d6a312ddb5109fa5d8a9beca30bac8`, personal branch
`codex/correctness-roadmap`. Library and sensitivity sources are unchanged.

## Findings and policy

The real entrypoint is `scripts/generate_api_reference.py`; there is no `docs/`
source tree. The previous generator test module collected no tests. Installing
`.[docs]` and setting `SKIP_DOCS_BUILD=false` therefore did not prove a build.
A disposable copy of the installed tree built 144 HTML pages, exit 0, no warnings.
Evidence: [baseline manifest](block21_baseline_result.json),
[baseline log](block21_baseline_checks.log).

The generated config's over-escaped regex matched only `causalis`. Expanding
`__all__` filtering to every module failed: 14 unresolved lazy-export warnings
and an extension error for a module without `__all__`.
[Probe](block21_parser_probe_checks.log). Keeping root-only `__all__` filtering
and forcing RST parsing instead produced 29 warnings and 25 docutils errors,
including repeated renderings of the same source docstring.
[Probe](block21_rst_probe_checks.log). These are diagnostic occurrences, not
unique defects. Sphinx exited 1; the CLI raised RuntimeError.

B21 makes the actual prior policy explicit: root-only `__all__`, existing MyST
rendering for docstrings. The unused Napoleon extension/settings are removed.
No warning categories are suppressed. A NumPy/RST migration is deferred for a
separate review of the mixed-format corpus; this gate does not certify RST
rendering, role resolution, documentation prose or sensitivity mathematics.

## Changes

- Every generator build uses `-W --keep-going`: warnings prevent publication.
- `--check` builds in owned temporary directories and does not publish HTML.
- Default generation still replaces `notebooks/api` after success;
  `--output-dir` supports separate output. Destinations overlapping package
  sources are rejected. Publication failure restores the previous tree and
  cleans owned staging. This is exception recovery, not crash/concurrent-writer
  durability. No new concurrency guarantee is claimed.
- `scripts/run_docs_check.py` records standalone command, source/environment,
  exit, elapsed time and generator/log hashes. It ignores `SKIP_DOCS_BUILD`.
- All six compatibility jobs and the release workflow require the standalone
  gate and upload evidence. The full release sensitivity scope is unchanged.
- Eight generator regression cases, plus three existing export checks. The
  pytest build tests respect explicit `SKIP_DOCS_BUILD=true` and skip absent
  optional dependencies; the mandatory standalone gate fails without docs deps.

## Evidence

Focused docs: **11 passed**, no warnings, 42.05 seconds.
[Log](block21_focus_tests.log). The identical eight generator cases are run
against the baseline by [probe_block21.py](probe_block21.py), with owned copies
removed afterward. The probe compares exact page sets and Sphinx inventory
records, not HTML byte identity or visual quality. The ignored editable-install
`_version.py` is matched on both sides and its hash recorded; an initial
comparison without that normalization differed only by this generated module.
[Probe result](block21_probe_result.json), [probe log](block21_probe_checks.log),
[baseline regressions](block21_baseline_tests.log).

Source checkpoint: `1780d8c715a15182137d51313e502280d6982dd9`.
The final eight baseline regressions produced **7 failed / 1 passed**, no errors
or skips. Both compared builds have **144 pages / 1296 inventory records**.
Committed correctness: **3367 passed**, zero failures/errors/skips,
91 existing warnings, 115.39 seconds. Docs builds were enabled (`false` skip flag).
[Integration selection](block21_integration_selection.json),
[result](block21_integration_result.json), [log](block21_integration_tests.log).
This remains the scoped correctness suite with seven sensitivity exclusions.
Standalone committed check: exit 0, strict warnings, no publication;
[manifest](block21_docs_result.json), [log](block21_standalone_checks.log).
Handoff: **132 immutable source links**, issues []; [check](block21_handoff_checks.log).

[CI run 37740334131](https://github.com/MaximLenivkin/Causalis/actions/runs/37740334131)
completed successfully on exact `1780d8c`: **all six jobs passed 3367 tests each**
and each separate Sphinx gate exited 0. Downloaded artifacts verified complete
case sets, focused cases, actual normalized arguments, seven sensitivity
exclusions, exact commit, environment, generator and log hashes.
[CI manifest](block21_ci_result.json), [CI check](block21_ci_checks.log).
Snapshot UTC: 2026-10-08T07:00:19.131486+00:00. Actual Python versions: 3.10.21
for both stacks, 3.11.16, 3.12.15, 3.13.15, 3.14.8; exact dependency versions
are preserved in the manifest. Six representative Linux stacks are not all
possible documentation dependency combinations.

[Root verifier](verify_block21.py) checks the six changed non-audit paths,
committed hashes, zero library changes, original comparison provenance and
local/baseline/focus/CI case sets plus standalone evidence.
[Validation](block21_validation_result.json), [log](block21_validation_checks.log):
issues []. Source frozen after `1780d8c`; all later edits are audit-only.
Owned disposable build copies and the recorded integration basetemp are removed;
aggregate JUnit remains for verification. Final checkpoint is `git log -1`.
Ordinary personal push, live local/remote equality and clean state are checked
at completion. No PR was created.

## Limits and next block

No notebook execution, external links check, hosted website build/publish,
release/tag/PyPI or upstream merge. Existing checked-in HTML is not regenerated.
The seven deferred sensitivity test modules and all library bytes are preserved.
MyST accepts some RST-looking text as plain content: zero build warnings is not
a promise of fully interpreted NumPy sections, formulas or RST roles.

Next B22: repeated cross-fitting, starting with an explicit API and split/RNG,
repetition aggregation and inference contract. Group cross-fitting, external
OOF and DR/R-CATE follow. Sensitivity, SC08 LOO and selected-U ATT remain deferred.
Stop after B21; B22 requires the next user request.
