"""Verify B16 scope, committed bytes, tests and explicit validation limits."""

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "e8459e1"
SOURCE = "1c91b0d39c8c12ac01d6a61c81d1bcd29c12b658"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def totals(name):
    suites = ET.parse(ROOT / "audit" / name).getroot().findall(".//testsuite")
    result = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
              for key in ("tests", "failures", "errors", "skipped")}
    result["passed"] = result["tests"] - sum(result[key] for key in ("failures", "errors", "skipped"))
    return result


def methods(data):
    tree = ast.parse(data)
    return {node.name: ast.dump(node, include_attributes=False)
            for cls in tree.body if isinstance(cls, ast.ClassDef)
            for node in cls.body if isinstance(node, ast.FunctionDef)}


def cases(name):
    return {(case.attrib["classname"], case.attrib["name"])
            for case in ET.parse(ROOT / "audit" / name).getroot().iter("testcase")}


def main():
    changed = set(git("diff", "--name-only", BASELINE, SOURCE, "--", "causalis", "tests", "scripts").decode().splitlines())
    expected = {"causalis/dgp/_gaussian_outcome.py", "causalis/dgp/causaldata/base.py",
        "causalis/dgp/causaldata_instrumental/base.py", "tests/data/test_binary_iv_marginal_outcomes.py",
        "tests/data/test_gaussian_outcome_accuracy_policy.py"}
    assert changed == expected, changed
    allowed_methods = {"causalis/dgp/causaldata/base.py": {"generate", "oracle_nuisance"},
                       "causalis/dgp/causaldata_instrumental/base.py": {"_potential_outcome_means"}}
    unchanged_methods = 0
    for path, allowed in allowed_methods.items():
        before, after = methods(git("show", f"{BASELINE}:{path}")), methods(git("show", f"{SOURCE}:{path}"))
        assert set(before) == set(after)
        for method in set(before) - allowed:
            assert before[method] == after[method], (path, method)
            unchanged_methods += 1
    probe = json.loads((ROOT / "audit/block16_probe_result.json").read_text())
    for path, digest in probe["source_sha256"].items():
        data = (ROOT / path).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest
        assert data == git("show", f"{SOURCE}:{path}")
    assert probe["issues"] == []
    assert probe["exact_frame_rng_pairs"] == 96
    assert len(probe["independent_references"]) == 140
    baseline = totals("block16_baseline_tests.xml")
    focused = totals("block16_focused_tests.xml")
    neighbors = totals("block16_neighbors_tests.xml")
    integration = totals("block16_integration_test_temp/junit.xml")
    assert baseline == dict(tests=62,failures=37,errors=0,skipped=0,passed=25)
    for result, count in ((focused,121),(neighbors,1359),(integration,2739)):
        assert result == dict(tests=count,failures=0,errors=0,skipped=0,passed=count)
    before_cases = cases("block16_baseline_tests.xml")
    focused_cases = cases("block16_focused_tests.xml")
    assert len(before_cases) == 62 and len(focused_cases) == 121
    public_cases = {case for case in focused_cases if case[0].endswith("test_binary_iv_marginal_outcomes")}
    assert before_cases == public_cases
    assert focused_cases <= cases("block16_neighbors_tests.xml")
    assert focused_cases <= cases("block16_integration_test_temp/junit.xml")
    selection = json.loads((ROOT/"audit/block16_integration_selection.json").read_text())
    result = json.loads((ROOT/"audit/block16_integration_result.json").read_text())
    old_selection = json.loads((ROOT/"audit/block15_integration_selection.json").read_text())
    assert selection["excluded_modules"] == old_selection["excluded_modules"]
    assert len(selection["excluded_modules"]) == 7
    assert selection["tested_source_checkpoint"] == result["tested_source_checkpoint"] == SOURCE
    assert selection["environment"]["commit"] == SOURCE
    assert result["exit_code"] == 0 and result["scoped_suite_clean"] is True
    assert result["full_suite_clean"] is False and result["sensitivity_validated"] is False
    # Retain provenance from the actual precommit probe; do not rerun it only
    # to change HEAD metadata. A separate committed-byte linkage is explicit.
    evidence = dict(baseline=probe["baseline"], source_checkpoint=SOURCE,
        original_probe_process_head=probe["process_head"], original_probe_time=probe["observed_at"],
        committed_paths_verified=len(probe["source_sha256"]), unchanged_methods=unchanged_methods,
        baseline_public_tests=baseline, focused_tests=focused, neighbors=neighbors,
        integration=integration, sensitivity_exclusions=selection["excluded_modules"],
        ci_verified=False, push_verified=False,
        network_failure="git ls-remote and git push: Could not resolve host github.com",
        issues=[])
    (ROOT/"audit/block16_validation_result.json").write_text(json.dumps(evidence,indent=2)+"\n")
    print(json.dumps(evidence,indent=2))


if __name__ == "__main__":
    main()
