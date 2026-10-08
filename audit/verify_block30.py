"""Verify B30 source scope, raw local evidence, history, handoff and six CI jobs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

from summarize_block30_ci import EXCLUDED

ROOT = Path(__file__).resolve().parents[1]
BASE = "15f316dc086e658b7cb5567448025f32b7e2f23a"
SOURCE = "d4b8f62a281c37e98b44941f12314de073cad721"
PATHS = {"README.md", "causalis/scenarios/uplift/policy.py",
         "tests/scenarios/uplift/test_policy_cost_capacity.py"}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode().strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((ROOT / "audit" / name).read_text())


def junit(path):
    tree = ET.parse(path).getroot()
    counts = {key: sum(int(s.attrib.get(key, 0)) for s in tree.findall(".//testsuite"))
              for key in ("tests", "failures", "errors", "skipped")}
    cases = [(c.attrib["classname"], c.attrib["name"]) for c in tree.iter("testcase")]
    assert len(cases) == len(set(cases)) == counts["tests"]
    return counts, set(cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-ci", action="store_true")
    args = parser.parse_args()
    assert set(git("diff", "--name-only", BASE, SOURCE).splitlines()) == PATHS
    changed = git("diff", "--name-only", SOURCE).splitlines()
    untracked = git("ls-files", "--others", "--exclude-standard").splitlines()
    assert all(path.startswith("audit/") for path in changed + untracked)
    hashes = {}
    for name in sorted(PATHS):
        committed = subprocess.check_output(["git", "show", SOURCE + ":" + name], cwd=ROOT)
        hashes[name] = hashlib.sha256(committed).hexdigest()
        assert hashes[name] == digest(ROOT / name)

    old_cases = junit(ROOT / "audit/block29_integration_test_temp/junit.xml")[1]
    totals, cases = junit(ROOT / "audit/block30_integration_test_temp/junit.xml")
    focus_totals, focus_cases = junit(ROOT / "audit/block30_focus_test_temp/junit.xml")
    assert len(old_cases) == 4282 and old_cases <= cases
    assert totals == dict(tests=4374, failures=0, errors=0, skipped=0)
    assert focus_totals == dict(tests=380, failures=0, errors=0, skipped=0)
    assert focus_cases <= cases and len(cases - old_cases) == 92
    assert all("test_policy_cost_capacity" in name for name, _ in cases - old_cases)
    focus, result, selection = (read("block30_" + name + ".json") for name in
                                ("focus_result", "integration_result", "integration_selection"))
    assert focus["source_sha256"] == hashes and focus["new_cases"] == 92
    assert focus["junit_sha256"] == digest(ROOT / "audit/block30_focus_test_temp/junit.xml")
    assert focus["observed_head"] == SOURCE and focus["exit_code"] == 0
    for record in (result, selection):
        assert record["tested_source_checkpoint"] == SOURCE
        assert record["scope"] == "correctness" and record["selected_full_suite"] is False
        assert record["sensitivity_validated"] is False
    assert selection["environment"]["commit"] == SOURCE
    assert selection["excluded_modules"] == EXCLUDED
    assert result["exit_code"] == 0 and result["passed"] == 4374
    assert result["scoped_suite_clean"] is True and result["full_suite_clean"] is False
    for name in ("result", "selection"):
        raw = read("block30_integration_test_temp/" + name + ".json")
        recorded = read("block30_integration_" + name + ".json")
        assert all(recorded[key] == value for key, value in raw.items())

    docs = read("block30_docs_result.json")
    assert docs == read("block30_docs_test_temp/result.json")
    assert docs["exit_code"] == 0 and docs["environment"]["commit"] == SOURCE
    assert docs["warnings_are_errors"] is True and docs["publishes_html"] is False
    assert docs["log_sha256"] == digest(ROOT / "audit/block30_docs_test_temp/build.log")
    assert docs["generator_sha256"] == digest(ROOT / "scripts/generate_api_reference.py")

    expected_history = [(51, 0), (77, 5), (77, 0), (143, 1), (143, 1), (143, 0)]
    history = read("block30_development_result.json")
    assert [(entry["tests"], entry["failures"]) for entry in history] == expected_history
    for entry in history:
        raw = ROOT / entry["path"]
        counts = junit(raw)[0]
        assert entry["sha256"] == digest(raw)
        assert all(entry[key] == value for key, value in counts.items())
    cleanup = read("block30_cleanup_result.json")
    assert cleanup["allowed_paths"] == ["audit/block30_focus_test_temp/pytest-temp",
                                         "audit/block30_integration_test_temp/pytest-temp"]
    for entry in cleanup["paths"]:
        assert entry["path"] in cleanup["allowed_paths"] and not (ROOT / entry["path"]).exists()

    subprocess.run([str(ROOT / ".venv/bin/python"), "audit/verify_handoff.py"], cwd=ROOT, check=True)
    handoff = read("handoff_validation.json")
    assert handoff == dict(snapshot_links_checked=171, issues=[])
    ci = None
    if args.require_ci:
        subprocess.run([str(ROOT / ".venv/bin/python"), "audit/summarize_block30_ci.py",
                        "--run-id", "37848086801", "--source", SOURCE,
                        "--expected-tests", "4374"], cwd=ROOT, check=True)
        ci = read("block30_ci_result.json")
        assert ci["matrix_verified"] is True and ci["verified_successful_jobs"] == 6
        assert ci["tested_source_checkpoint"] == SOURCE and ci["issues"] == []

    baseline = git("ls-tree", "-r", "--name-only", BASE).splitlines()
    old_source = [p for p in baseline if p.startswith(("causalis/", "scripts/", ".github/workflows/"))
                  and p.endswith((".py", ".yml", ".yaml")) and p not in PATHS]
    old_tests = [p for p in baseline if p.startswith("tests/") and p.endswith(".py")]
    output = ROOT / ("audit/block30_validation_result.json" if args.require_ci
                     else "audit/block30_local_validation_result.json")
    links = re.findall(r"\]\(([^)]+)\)", (ROOT / "audit/BLOCK30_POLICY_COST_CAPACITY.md").read_text())
    local_links = [link for link in links if not link.startswith("https://")]
    for link in local_links:
        target = (ROOT / "audit" / link.split("#")[0]).resolve()
        assert target == output or target.exists(), link
    payload = dict(source=SOURCE, baseline=BASE, source_sha256=hashes,
                   source_diff=sorted(PATHS), existing_source_paths_unchanged=len(old_source),
                   existing_test_paths_unchanged=len(old_tests), old_cases_retained=len(old_cases),
                   new_cases=92, focus=focus_totals, correctness=totals, docs=docs,
                   handoff_links_checked=171, report_links_checked=len(local_links),
                   history_verified=True, cleanup_verified=True,
                   ci_verified=bool(ci), issues=[])
    output.write_text(json.dumps(payload, indent=2))
    assert all((ROOT / "audit" / link.split("#")[0]).exists() for link in local_links)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
