from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _generator():
    spec = importlib.util.spec_from_file_location(
        'api_generator', REPO_ROOT / 'scripts/generate_api_reference.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _require_docs_dependencies():
    if os.environ.get('SKIP_DOCS_BUILD', '').lower() == 'true':
        pytest.skip('Documentation builds explicitly disabled by SKIP_DOCS_BUILD=true')
    pytest.importorskip('sphinx')
    pytest.importorskip('myst_parser')
    pytest.importorskip('autodoc2')


def _copy_repo(tmp_path, *, full=False, broken=False):
    repo = tmp_path / 'repo'
    repo.mkdir()
    shutil.copytree(REPO_ROOT / 'scripts', repo / 'scripts',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    if full:
        shutil.copytree(REPO_ROOT / 'causalis', repo / 'causalis',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    else:
        package = repo / 'causalis'
        package.mkdir()
        doc = '```{unknown-directive}\n```' if broken else 'A tiny API package.'
        (package / '__init__.py').write_text(
            f'"""{doc}"""\n__all__ = ["answer"]\n'
            'def answer():\n    """Return the answer."""\n    return 42\n'
        )
    output = repo / 'notebooks/api'
    output.mkdir(parents=True)
    (output / 'sentinel.txt').write_text('old published reference')
    return repo


def _run(repo, *args):
    return subprocess.run(
        [sys.executable, 'scripts/generate_api_reference.py', *args],
        cwd=repo, capture_output=True, text=True, check=False,
    )


def _tree_hashes(path):
    return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob('*') if p.is_file()}


def test_check_builds_full_package_without_publishing(tmp_path):
    _require_docs_dependencies()
    repo = _copy_repo(tmp_path, full=True)
    before = _tree_hashes(repo)
    run = _run(repo, '--check')
    assert run.returncode == 0, run.stdout + run.stderr
    assert 'check passed' in run.stdout
    assert _tree_hashes(repo) == before


def test_default_publish_replaces_output_and_cleans_staging(tmp_path):
    _require_docs_dependencies()
    repo = _copy_repo(tmp_path)
    run = _run(repo)
    assert run.returncode == 0, run.stdout + run.stderr
    output = repo / 'notebooks/api'
    assert not (output / 'sentinel.txt').exists()
    page = (output / 'html/apidocs/causalis/causalis.html').read_text()
    assert 'causalis.answer' in page and 'Return the answer.' in page
    assert (output / 'html/objects.inv').is_file()
    assert sorted(p.name for p in output.parent.iterdir()) == ['api']


def test_custom_output_preserves_default_reference(tmp_path):
    _require_docs_dependencies()
    repo = _copy_repo(tmp_path)
    output = tmp_path / 'custom'
    run = _run(repo, '--output-dir', str(output))
    assert run.returncode == 0, run.stdout + run.stderr
    assert (output / 'html/reference.html').is_file()
    assert (repo / 'notebooks/api/sentinel.txt').read_text() == 'old published reference'


def test_warning_fails_without_replacing_published_reference(tmp_path):
    _require_docs_dependencies()
    repo = _copy_repo(tmp_path, broken=True)
    before = _tree_hashes(repo)
    run = _run(repo)
    assert run.returncode != 0
    assert 'unknown-directive' in run.stderr
    assert _tree_hashes(repo) == before
    assert sorted(p.name for p in (repo / 'notebooks').iterdir()) == ['api']


def test_publication_failure_restores_previous_output(tmp_path, monkeypatch):
    module = _generator()
    package = tmp_path / 'causalis'
    package.mkdir()
    output = tmp_path / 'api'
    output.mkdir()
    (output / 'sentinel').write_text('previous')
    staging = tmp_path / '.api.staged-owned'
    staging.mkdir()
    (staging / 'new').write_text('new')
    monkeypatch.setattr(module, 'PACKAGE_DIR', package)
    monkeypatch.setattr(module, 'OUTPUT_DIR', output)
    monkeypatch.setattr(module, '_build_staged_output', lambda destination: staging)
    replace = os.replace

    def failing_replace(source, destination):
        if source == staging:
            raise OSError('publication failed')
        return replace(source, destination)

    monkeypatch.setattr(module.os, 'replace', failing_replace)
    with pytest.raises(OSError, match='publication failed'):
        module.generate_api_reference()
    assert (output / 'sentinel').read_text() == 'previous'
    assert not staging.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ['api', 'causalis']


@pytest.mark.parametrize('relative', ['.', 'causalis', 'causalis/subdir'])
def test_output_cannot_replace_package_source(tmp_path, monkeypatch, relative):
    module = _generator()
    package = tmp_path / 'causalis'
    package.mkdir()
    (package / '__init__.py').write_text('source')
    monkeypatch.setattr(module, 'PACKAGE_DIR', package)
    with pytest.raises(ValueError, match='package source'):
        module.generate_api_reference(tmp_path / relative)
    assert (package / '__init__.py').read_text() == 'source'
