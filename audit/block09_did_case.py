"""Reproduce one unchanged DiD assertion under current or pre-B09 source."""

import argparse
import contextlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile


BASELINE = "74145665127f8fa5a0bf038d769697ab880854b8"
NODE = "tests/scenarios/did/refutation/test_did_post_inference_diagnostics.py::test_post_inference_report_accepts_panel_and_estimate"
TARGETS = ("causalis/dgp/multicausaldata/base.py", "causalis/dgp/multicausaldata/functional.py")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("baseline", "current"), required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = "1"
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["MPLCONFIGDIR"] = str(root / ".venv" / "matplotlib")
    os.environ["SKIP_DOCS_BUILD"] = "true"
    changed = subprocess.check_output(["git", "diff", "--name-only", BASELINE, "--", "causalis"], text=True).splitlines()
    assert not (set(changed) - set(TARGETS)), changed
    assert (root / NODE.split("::")[0]).read_bytes() == subprocess.check_output(["git", "show", BASELINE + ":" + NODE.split("::")[0]])
    import pytest
    with contextlib.ExitStack() as cleanup:
        if args.mode == "baseline":
            temporary = Path(cleanup.enter_context(tempfile.TemporaryDirectory(prefix="b09-did-case-", dir=root / ".venv")))
            import causalis.dgp.multicausaldata as package
            for source_path in TARGETS:
                snapshot = temporary / Path(source_path).name
                snapshot.write_bytes(subprocess.check_output(["git", "show", BASELINE + ":" + source_path]))
                name = "causalis.dgp.multicausaldata." + snapshot.stem
                spec = importlib.util.spec_from_file_location(name, snapshot)
                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                spec.loader.exec_module(module)
                setattr(package, snapshot.stem, module)
        stem = root / ("audit/block09_did_" + args.mode + "_case")
        with stem.with_suffix(".log").open("w", encoding="utf-8") as output:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                exit_code = int(pytest.main([
                    "-q", "-p", "no:cacheprovider",
                    "--basetemp=" + str(root / ".venv" / ("block09-did-" + args.mode + "-case-temp")),
                    "--junitxml=" + str(stem.with_suffix(".xml")), NODE,
                ]))
        print("mode=" + args.mode + ", pytest_exit_code=" + str(exit_code))
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
