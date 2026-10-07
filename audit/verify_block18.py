"""Verify B18 source, reproduction, compatibility and committed CI evidence."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
SOURCE = "df944e0ee814dbe1a631b41ba1b59def9f61ed8b"
BASELINE = "b7cbec9ead7c589fa6d4570c0e8f188d349c95be"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def read(name):
    return json.loads((AUDIT / name).read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def junit(path):
    tree = ET.parse(path).getroot()
    suites = tree.findall(".//testsuite")
    counts = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
              for key in ("tests", "failures", "errors", "skipped")}
    counts["passed"] = counts["tests"] - sum(counts[k] for k in ("failures", "errors", "skipped"))
    cases = {(c.attrib["classname"], c.attrib["name"]) for c in tree.iter("testcase")}
    assert len(cases) == counts["tests"]
    return counts, cases


def main():
    probe = read("block18_probe_result.json")
    baseline = read("block18_baseline_result.json")
    integration = read("block18_integration_result.json")
    selection = read("block18_integration_selection.json")
    ci = read("block18_ci_result.json")
    expected_paths = sorted([
        "causalis/scenarios/_prediction.py", "causalis/scenarios/iv/model.py",
        "causalis/scenarios/unconfoundedness/_utils.py",
        "causalis/scenarios/unconfoundedness/model.py",
        "causalis/scenarios/multi_unconfoundedness/_utils.py",
        "causalis/scenarios/multi_unconfoundedness/model.py",
        "tests/inference/test_learner_output_shapes.py",
    ])
    changed_paths = sorted(git("diff", "--name-only", BASELINE, SOURCE, "--", "causalis", "tests", "scripts").decode().splitlines())
    assert changed_paths == expected_paths and len(changed_paths) == 7
    assert len(probe["sha256"]) == 10
    assert not git("diff", SOURCE, "--name-only", "--", "causalis", "tests", "scripts").strip()
    for path, digest in probe["sha256"].items():
        assert sha((ROOT / path).read_bytes()) == sha(git("show", f"{SOURCE}:{path}")) == digest
    assert probe["baseline"] == probe["process_head"] == BASELINE
    assert probe["exact_fit_pairs"] == 20 and probe["exact_inference_pairs"] == 36
    assert len(probe["unchanged_functions"]) == 125
    for item in probe["unchanged_functions"]:
        path, name = item.split(":")
        def function(source):
            matches = [node for node in ast.walk(ast.parse(source))
                       if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
            assert len(matches) == 1
            return ast.dump(matches[0], include_attributes=False)
        assert function(git("show", f"{BASELINE}:{path}")) == function(git("show", f"{SOURCE}:{path}"))
    assert baseline["baseline"] == BASELINE and baseline["isolated_baseline_import_verified"] is True
    assert baseline["test_sha256"] == probe["sha256"][baseline["test_path"]]
    base_counts, base_cases = junit(AUDIT / "block18_baseline.xml")
    focus_counts, focus_cases = junit(AUDIT / "block18_focus.xml")
    assert base_counts == {k: baseline[k] for k in base_counts}
    assert base_counts == dict(tests=356, failures=267, errors=0, skipped=0, passed=89)
    assert focus_counts == dict(tests=460, failures=0, errors=0, skipped=0, passed=460)
    assert base_cases == {case for case in focus_cases if case[0].endswith("test_learner_output_shapes")}
    integrated_counts, integrated_cases = junit(AUDIT / "block18_integration_test_temp/junit.xml")
    assert integrated_counts == dict(tests=3185, failures=0, errors=0, skipped=0, passed=3185)
    assert integrated_counts == {k: integration[k] for k in integrated_counts}
    assert focus_cases <= integrated_cases
    assert integration["tested_source_checkpoint"] == selection["tested_source_checkpoint"] == SOURCE
    assert integration["exit_code"] == 0 and integration["scoped_suite_clean"] is True
    assert integration["full_suite_clean"] is False
    assert selection["environment"]["commit"] == SOURCE
    assert selection["excluded_modules"] == read("block17_integration_selection.json")["excluded_modules"]
    assert len(selection["excluded_modules"]) == 7
    assert ci["tested_source_checkpoint"] == SOURCE
    assert ci["matrix_verified"] is True and ci["verified_successful_jobs"] == 6 and ci["issues"] == []
    assert ci["expected_tests_per_job"] == 3185 and ci["excluded_modules"] == selection["excluded_modules"]
    for job in ci["jobs"]:
        assert job["conclusion"] == "success" and job["case_sets_verified"] is True
        folder = AUDIT / f"block18_ci_test_temp/run-{ci['run_id']}" / f"correctness-py{job['python_minor']}-{job['stack']}"
        for name, digest in job["artifact_sha256"].items():
            assert sha((folder / name).read_bytes()) == digest
        counts, cases = junit(folder / "junit.xml")
        assert counts == integrated_counts and cases == integrated_cases
    scripts = ["run_block18_baseline.py", "probe_block18.py", "run_block18_integration.py",
               "observe_block18_ci.py", "summarize_block18_ci.py", "verify_block18.py"]
    for name in scripts:
        ast.parse((AUDIT / name).read_text())
    links = re.findall(r"\]\(([^)]+)\)", (AUDIT / "BLOCK18_LEARNER_OUTPUT_CONTRACTS.md").read_text())
    local_links = [link for link in links if not link.startswith("https://")]
    for link in local_links:
        assert (AUDIT / link.split("#")[0]).is_file(), link
    result = dict(tested_source_checkpoint=SOURCE, baseline=BASELINE, changed_source_test_paths=changed_paths,
                  source_hashes_verified=len(probe["sha256"]), unchanged_functions_verified=125,
                  baseline_counts=base_counts, focused_counts=focus_counts, integration_counts=integrated_counts,
                  complete_case_sets_verified=True, successful_ci_jobs=6, audit_scripts_parsed=len(scripts),
                  local_report_links_verified=len(local_links), issues=[])
    (AUDIT / "block18_validation_result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
