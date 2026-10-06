"""Check B08 source scope, committed test evidence and artifact syntax."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

from summarize_block08_ci import EXCLUDED

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
START = "b33922f1c0db8885ae9e8e071c45fc46de5205b6"
LIBRARY = {"causalis/dgp/multicausaldata/base.py",
           "causalis/dgp/multicausaldata/functional.py"}
TESTS = {"tests/data/test_multicausal_generator_contracts.py",
         "tests/data/test_multicausal_assignment_policy.py"}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True,
                                   encoding="utf-8").strip()


def main():
    result = json.loads((AUDIT / "block08_integration_result.json").read_text(encoding="utf-8"))
    selection = json.loads((AUDIT / "block08_integration_selection.json").read_text(encoding="utf-8"))
    ci = json.loads((AUDIT / "block08_ci_result.json").read_text(encoding="utf-8"))
    reference = json.loads((AUDIT / "block08_finite_reference_result.json").read_text(encoding="utf-8"))
    paths = set(git("diff", START, "--name-only").splitlines())
    paths.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    issues = []
    def check(condition, message):
        if not condition:
            issues.append(message)
    source = result["tested_source_checkpoint"]
    check(not git("diff", source, "--name-only", "--", "causalis", "tests", "scripts"),
          "Source drift after integration")
    check(not git("ls-files", "--others", "--exclude-standard", "--", "causalis", "tests", "scripts"),
          "Untracked source/tests")
    check({p for p in paths if p.startswith("causalis/")} == LIBRARY, "Unexpected library paths")
    check({p for p in paths if p.startswith("tests/")} == TESTS, "Unexpected test paths")
    check(not any("sensitivity" in p.lower() for p in paths), "Deferred sensitivity paths changed")
    check(selection["excluded_modules"] == EXCLUDED, "Wrong exclusions")
    check(selection["tested_source_checkpoint"] == selection["environment"]["commit"] == source,
          "Local provenance mismatch")
    check(result["scoped_suite_clean"] and not result["full_suite_clean"] and not result["sensitivity_validated"],
          "Incorrect scope/result claim")
    suites = ET.parse(AUDIT / "block08_integration_test_temp/junit.xml").getroot().findall(".//testsuite")
    cases = [case for suite in suites for case in suite.findall("testcase")]
    check(len(cases) == result["passed"] == result["tests"], "Local JUnit count mismatch")
    check(not any(case.find(tag) is not None for case in cases for tag in ("failure", "error", "skipped")),
          "Local failures/errors/skips")
    new_cases = [case for case in cases if any(Path(p).stem in case.attrib.get("classname", "") for p in TESTS)]
    check(result["tests"] == 1729 + len(new_cases), "Previous/new case total mismatch")
    check(ci["matrix_verified"] and ci["verified_successful_jobs"] == 6 and not ci["issues"],
          "CI matrix not verified")
    check(ci["tested_source_checkpoint"] == source, "CI/local source mismatch")
    check(reference["tested_source_checkpoint"] == source and reference["verified"] == 16
          and not reference["issues"], "Finite reference provenance/count mismatch")
    check(all(row["schema_equal"] and row["values_exact"] and row["next_rng_draws_exact"]
              for row in reference["configurations"]), "Finite reference mismatch")
    python_paths = sorted(p for p in paths if p.endswith(".py"))
    for path in python_paths:
        try:
            ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=path)
        except (OSError, SyntaxError) as error:
            issues.append(f"{path}: {error}")
    links = 0
    for path in sorted(p for p in paths if p.endswith(".md")):
        for target in re.findall(r"\]\((D:/codex/Causalis/[^)]+)\)",
                                 (ROOT / path).read_text(encoding="utf-8")):
            links += 1
            check(Path(target).is_file(), f"Missing local link: {target}")
    payload = {"source_checkpoint": source, "new_cases": len(new_cases),
               "local_passed": result["passed"], "ci_verified_jobs": ci["verified_successful_jobs"],
               "library_paths": sorted(LIBRARY), "test_paths": sorted(TESTS),
               "python_files_checked": len(python_paths), "local_links_checked": links,
               "finite_reference_configurations": reference["verified"],
               "sensitivity_paths": [], "issues": issues}
    (AUDIT / "block08_validation_checks.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return bool(issues)


if __name__ == "__main__":
    raise SystemExit(main())
