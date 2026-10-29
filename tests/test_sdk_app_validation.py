"""SDK metadata replaces generated app JSON during source linting."""

import json

import pytest

from soar_app_linter.app_validation import is_app_directory, validate_app


@pytest.mark.parametrize("requires_python", [">=3.13,<3.15", ">=3.9", "==3.13.*", None])
def test_sdk_python_support_uses_project_constraints(create_sdk_app, requires_python):
    app_dir = create_sdk_app(requires_python)

    assert is_app_directory(app_dir)
    assert validate_app(app_dir)


@pytest.mark.parametrize(
    "requires_python", [">=3.14", "<3.13", "!=3.13.*", "invalid", 313]
)
def test_sdk_rejects_incompatible_or_invalid_python_constraints(
    create_sdk_app, requires_python, capsys
):
    app_dir = create_sdk_app(requires_python)

    assert not validate_app(app_dir)
    assert "Error:" in capsys.readouterr().out


@pytest.mark.parametrize("main_module", [None, "", 123])
def test_sdk_requires_an_entry_point(create_sdk_app, main_module, capsys):
    app_dir = create_sdk_app()
    project_path = app_dir / "pyproject.toml"
    replacement = (
        f"main_module = {json.dumps(main_module)}" if main_module is not None else ""
    )
    project_path.write_text(
        project_path.read_text().replace('main_module = "app:app"', replacement)
    )

    assert not validate_app(app_dir)
    assert "tool.soar.app.main_module" in capsys.readouterr().out


def test_unrelated_python_project_is_not_an_sdk_app(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "ordinary-python-package"\n'
    )

    assert not is_app_directory(tmp_path)
    assert not validate_app(tmp_path)


def test_invalid_toml_fails_with_a_diagnostic(create_sdk_app, capsys):
    app_dir = create_sdk_app()
    (app_dir / "pyproject.toml").write_text("[tool.soar.app\n")

    assert not is_app_directory(app_dir)
    assert not validate_app(app_dir)
    assert "pyproject.toml" in capsys.readouterr().out
