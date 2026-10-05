"""Release/scoped-CI policy must be explicit and failures must propagate."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


SPEC = importlib.util.spec_from_file_location(
    "causalis_ci_runner", Path(__file__).resolve().parents[1] / "scripts/run_tests.py",
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_full_selection_includes_sensitivity_and_does_not_ignore_any_module(tmp_path):
    sensitivity = tmp_path / "tests/refutation/test_sensitivity_example.py"
    sensitivity.parent.mkdir(parents=True)
    sensitivity.touch()
    selection = runner.build_selection("full", tmp_path, tmp_path / "output")
    assert selection["selected_full_suite"] is True
    assert selection["excluded_modules"] == []
    assert "tests" in selection["pytest_args"]
    assert "--ignore" not in selection["pytest_args"]


def test_scoped_selection_lists_every_deferred_module(tmp_path):
    for name in runner.DEFERRED_SENSITIVITY_MODULES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    selection = runner.build_selection("correctness", tmp_path, tmp_path / "output")
    assert selection["selected_full_suite"] is False
    assert selection["excluded_modules"] == sorted(runner.DEFERRED_SENSITIVITY_MODULES)
    assert selection["pytest_args"].count("--ignore") == 7


def test_scoped_selection_requires_review_for_new_sensitivity_modules(tmp_path):
    sensitivity = tmp_path / "tests/test_new_sensitivity_method.py"
    sensitivity.parent.mkdir()
    sensitivity.touch()
    with pytest.raises(ValueError, match="explicit CI scope review"):
        runner.build_selection("correctness", tmp_path, tmp_path / "output")


@pytest.mark.parametrize("exit_code", [0, 1, 2, 5])
def test_runner_preserves_pytest_exit_status_and_records_scope(tmp_path, monkeypatch, exit_code):
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)
    monkeypatch.chdir(tmp_path)
    called_args = []
    def fake_pytest_main(args):
        called_args.extend(args)
        return exit_code
    monkeypatch.setattr(pytest, "main", fake_pytest_main)
    status = runner.main(["--output-dir", str(tmp_path / "evidence")])
    assert status == exit_code
    assert "--ignore" not in called_args
    selection = json.loads((tmp_path / "evidence/selection.json").read_text())
    result = json.loads((tmp_path / "evidence/result.json").read_text())
    assert selection["scope"] == result["scope"] == "full"
    assert result["selected_full_suite"] is True
    assert result["exit_code"] == exit_code


def test_runner_rejects_hidden_pytest_addopts(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_ADDOPTS", "--ignore=tests/refutation")
    with pytest.raises(SystemExit) as raised:
        runner.main(["--output-dir", str(tmp_path / "evidence")])
    assert raised.value.code == 2
    assert not (tmp_path / "evidence").exists()


@pytest.mark.parametrize("scope, layout, expected_exit", [
    ("full", "failing_sensitivity_sentinel", 1),
    ("full", "empty", 5),
    ("correctness", "failing_sensitivity_sentinel", 0),
])
def test_cli_gate_runs_real_pytest_and_cannot_pass_a_failing_full_suite(
    tmp_path, scope, layout, expected_exit,
):
    # Synthetic fixtures exercise selection, not the deferred project's formulas.
    project = tmp_path / "project"
    scripts = project / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(SPEC.origin, scripts / "run_tests.py")
    (project / "tests").mkdir()
    if layout != "empty":
        (project / "tests/test_pass.py").write_text("def test_pass():\n    assert True\n")
        sentinel = project / "tests/refutation/test_sensitivity_benchmark.py"
        sentinel.parent.mkdir()
        sentinel.write_text("def test_sentinel():\n    assert False, 'must block full release'\n")
    environment = os.environ.copy()
    environment["PYTEST_ADDOPTS"] = ""
    process = subprocess.run(
        [sys.executable, str(scripts / "run_tests.py"), "--scope", scope],
        cwd=project, env=environment, capture_output=True, text=True,
        timeout=60, check=False,
    )
    assert process.returncode == expected_exit, process.stdout + process.stderr
    result = json.loads((project / "build/ci-tests/result.json").read_text())
    assert result["exit_code"] == expected_exit
    assert result["selected_full_suite"] == (scope == "full")
    assert (project / "build/ci-tests/junit.xml").is_file()
