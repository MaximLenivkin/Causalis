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

Committed-source integration, standalone check, remote matrix, handoff and
final validation will be recorded below before completion.

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
