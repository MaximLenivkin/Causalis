"""Check B06 compatibility/release configuration without publishing anything."""
import ast
import importlib.util
import json
from pathlib import Path
import tomllib

from packaging.requirements import Requirement
import yaml


ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requirement = next(Requirement(s) for s in metadata["project"]["dependencies"]
                       if Requirement(s).name == "pydantic")
    assert not requirement.specifier.contains("1.10.22")
    assert requirement.specifier.contains("2.0.0")
    assert requirement.specifier.contains("2.13.5")
    ci = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    release = yaml.load((ROOT / ".github/workflows/release.yml").read_text(), Loader=yaml.BaseLoader)
    matrix = ci["jobs"]["correctness"]["strategy"]["matrix"]["include"]
    assert sorted(row["python"] for row in matrix if row["stack"] == "latest") == [
        "3.10", "3.11", "3.12", "3.13", "3.14"]
    assert [row for row in matrix if row["stack"] == "legacy"] == [
        {"python": "3.10", "stack": "legacy"}]
    assert ci["jobs"]["correctness"]["strategy"]["fail-fast"] == "false"
    assert ci["on"]["push"]["branches"] == ["main", "codex/**"]
    assert "pull_request" in ci["on"] and "workflow_dispatch" in ci["on"]
    assert release["on"]["push"]["tags"] == ["v*.*.*"]
    jobs = release["jobs"]
    steps = jobs["build-and-check"]["steps"]
    full_index = next(i for i, step in enumerate(steps)
                      if step.get("run") == ".venv/bin/python scripts/run_tests.py --scope full")
    build_index = next(i for i, step in enumerate(steps)
                       if step.get("run") == ".venv/bin/python -m build")
    assert full_index < build_index
    assert "if" not in steps[full_index] and "continue-on-error" not in steps[full_index]
    assert jobs["pypi"]["needs"] == "build-and-check"
    assert jobs["github-release"]["needs"] == "pypi"
    tag_guard = next(step["run"] for step in steps if step["name"] == "Verify release tag")
    assert 'tag_type != "tag"' in tag_guard
    assert '"--is-ancestor", tagged_commit, "origin/main"' in tag_guard
    assert "version != expected" in tag_guard
    for job in (ci["jobs"]["correctness"], jobs["build-and-check"]):
        for step in job["steps"]:
            run = step.get("run", "")
            assert "--scope full" not in run or "--ignore" not in run
            for line in run.splitlines():
                if line.strip().startswith("python "):
                    assert line == "python -m venv .venv", line
    parsed = []
    for name in ("scripts/run_tests.py", "tests/test_compatibility_ci_runner.py"):
        ast.parse((ROOT / name).read_text(encoding="utf-8"), filename=name)
        parsed.append(name)
    spec = importlib.util.spec_from_file_location("ci_runner_validation", ROOT / "scripts/run_tests.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    selection = runner.build_selection("correctness", ROOT, ROOT / "build/ci-tests")
    assert selection["excluded_modules"] == sorted(runner.DEFERRED_SENSITIVITY_MODULES)
    result = {
        "pydantic_requirement": str(requirement),
        "pydantic_v1_rejected": True,
        "matrix": matrix,
        "release_full_pytest_before_build": True,
        "release_publish_dependencies_preserved": True,
        "annotated_tag_main_and_version_guards_preserved": True,
        "correctness_excluded_modules": selection["excluded_modules"],
        "python_ast_checked": parsed,
        "issues": [],
        "actual_matrix_runs": "not claimed by this static check",
    }
    (ROOT / "audit/block06_compat_checks.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
