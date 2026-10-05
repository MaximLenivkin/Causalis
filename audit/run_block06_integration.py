"""Use the CI's explicit non-sensitivity selection and preserve B06 evidence."""
import importlib.util
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "09e00de5a9d3dc915c6d59627f8b0ebc875dd4e9"


if __name__ == "__main__":
    os.chdir(ROOT)
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["MPLCONFIGDIR"] = str(ROOT / "audit/mplconfig")
    os.environ["SKIP_DOCS_BUILD"] = "true"
    for name in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
        os.environ[name] = "1"
    spec = importlib.util.spec_from_file_location("block06_ci_runner", ROOT / "scripts/run_tests.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    output = ROOT / "audit/block06_integration_test_temp"
    status = runner.main(["--scope", "correctness", "--output-dir", str(output)])
    for name in ["selection", "result"]:
        payload = json.loads((output / f"{name}.json").read_text(encoding="utf-8"))
        payload["tested_source_checkpoint"] = SOURCE
        payload["sensitivity_validated"] = False
        (ROOT / f"audit/block06_integration_{name}.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8")
    shutil.copyfile(output / "junit.xml", ROOT / "audit/block06_integration_test_temp/final-junit.xml")
    raise SystemExit(status)
