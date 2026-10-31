"""Path handling at the runner boundary and in filesystem helpers."""

from pathlib import Path

import pytest

from soar_app_linter.pylint_runner import (
    MessageLevel,
    _detect_namespace_conflict,
    _ensure_init_files,
    _find_python_files,
    run_pylint,
)


@pytest.mark.parametrize("path_type", [str, Path])
@pytest.mark.parametrize("single_file", [False, True])
@pytest.mark.parametrize("has_error", [False, True])
def test_runner_accepts_relative_strings_and_paths(
    tmp_path, monkeypatch, path_type, single_file, has_error
):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "example.py").write_text(
        "VALUE = missing_name\n" if has_error else "VALUE = 1\n"
    )
    monkeypatch.chdir(tmp_path)
    target = path_type("app/example.py" if single_file else "app")

    exit_code, output = run_pylint(
        target, no_deps=True, message_level=MessageLevel.ERROR
    )

    assert exit_code == int(has_error), output
    assert ("E0602" in output) is has_error


def test_find_python_files_returns_paths_and_excludes_venv_and_hidden_files(tmp_path):
    (tmp_path / "module.py").write_text("VALUE = 1\n")
    (tmp_path / ".hidden.py").write_text("VALUE = 1\n")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested/child.py").write_text("VALUE = 1\n")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv/dependency.py").write_text("VALUE = 1\n")

    assert set(_find_python_files(tmp_path)) == {
        tmp_path / "module.py",
        tmp_path / "nested/child.py",
    }
    assert set(_find_python_files(tmp_path, use_relative_paths=True)) == {
        Path("module.py"),
        Path("nested/child.py"),
    }


def test_ensure_init_files_walks_paths_and_preserves_existing_packages(
    tmp_path, monkeypatch
):
    (tmp_path / "module.py").write_text("VALUE = 1\n")
    for name in ("existing", "new_package", ".hidden", ".venv", "__pycache__"):
        package = tmp_path / name
        package.mkdir()
        (package / "module.py").write_text("VALUE = 1\n")
    (tmp_path / "existing/__init__.py").write_text("# Preserve this package\n")
    (tmp_path / "data").mkdir()
    monkeypatch.chdir(tmp_path)

    _ensure_init_files(Path("."))

    assert (tmp_path / "__init__.py").is_file()
    assert (tmp_path / "new_package/__init__.py").is_file()
    assert (
        tmp_path / "existing/__init__.py"
    ).read_text() == "# Preserve this package\n"
    for name in (".hidden", ".venv", "__pycache__", "data"):
        assert not (tmp_path / name / "__init__.py").exists()


def test_namespace_detection_accepts_a_path(tmp_path):
    (tmp_path / "requests.py").write_text("import requests\n")

    assert _detect_namespace_conflict(tmp_path) == {"requests"}
