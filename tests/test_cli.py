"""Tests for the soar-app-linter CLI."""

import json
import subprocess
import sys
from unittest.mock import Mock
from pathlib import Path
from collections.abc import Callable

import pytest

from soar_app_linter.pylint_runner import MessageLevel
from soar_app_linter import cli


CLI = str(Path(sys.executable).with_name("soar-app-linter"))


@pytest.mark.parametrize("publisher", ["Splunk", "Splunk Community", "Mandiant", ""])
@pytest.mark.parametrize("single_repo", [True, False])
def test_cli_checks_python_compatibility_for_all_publishers(
    create_app_json, publisher, single_repo
):
    app_dir = create_app_json("3.13", publisher=publisher)
    (app_dir / "test_app.py").write_text(
        "class Example:\n"
        "    @classmethod\n"
        "    @property\n"
        "    def value(cls):\n"
        "        return 1\n"
    )
    command = [CLI, "--no-deps", "--message-level", "error"]
    if single_repo:
        command.extend(["--single-repo", str(app_dir)])
    else:
        command.append(str(app_dir.parent))

    result = subprocess.run(command, capture_output=True, text=True)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "E9903" in result.stdout


@pytest.mark.parametrize("single_repo", [True, False])
def test_cli_rejects_vendor_app_without_python_313(create_app_json, single_repo):
    app_dir = create_app_json("3.9", publisher="Mandiant")
    (app_dir / "test_app.py").write_text("VALUE = 1\n")
    command = [CLI, "--no-deps"]
    command.extend(
        ["--single-repo", str(app_dir)] if single_repo else [str(app_dir.parent)]
    )

    result = subprocess.run(command, capture_output=True, text=True)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "do not include the required version 3.13" in result.stdout


def test_cli_accepts_clean_apps_and_skips_non_app_directory(create_app_json, tmp_path):
    for publisher, name in (("Mandiant", "vendor"), ("Splunk Community", "community")):
        app_dir = create_app_json("3.13", publisher=publisher, name=name)
        (app_dir / "test_app.py").write_text("VALUE = 1\n")
    (tmp_path / "not_an_app").mkdir()

    result = subprocess.run(
        [CLI, "--no-deps", "--message-level", "error", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Processing repository:" in result.stderr
    assert "Processed 2 apps, skipped 1 non-app directories" in result.stderr


def test_cli_rejects_invalid_explicit_app(tmp_path):
    (tmp_path / "test_app.py").write_text("VALUE = 1\n")

    result = subprocess.run(
        [CLI, "--single-repo", "--no-deps", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "No JSON files found" in result.stdout


@pytest.mark.parametrize("layout", ["single", "collection", "root"])
@pytest.mark.parametrize("has_error", [False, True])
def test_cli_lints_sdk_source_without_a_generated_manifest(
    create_sdk_app, layout, has_error
):
    app_dir = create_sdk_app()
    if has_error:
        (app_dir / "app.py").write_text(
            "class Example:\n"
            "    @classmethod\n"
            "    @property\n"
            "    def value(cls):\n"
            "        return 1\n"
        )
    # SDK source trees have subdirectories even before dependencies are installed.
    (app_dir / "src").mkdir()
    command = [CLI, "--no-deps", "--message-level", "error"]
    if layout == "single":
        command.extend(["--single-repo", str(app_dir)])
    else:
        command.append(str(app_dir.parent if layout == "collection" else app_dir))

    result = subprocess.run(command, capture_output=True, text=True)

    assert result.returncode == int(has_error), result.stdout + result.stderr
    assert ("E9903" in result.stdout) is has_error
    assert f"Processing repository: {app_dir}" in result.stderr
    assert not list(app_dir.glob("*.json"))


def test_cli_does_not_import_sdk_entry_point(create_sdk_app):
    app_dir = create_sdk_app()
    (app_dir / "app.py").write_text(
        'raise RuntimeError("The linter must not import the app")\n'
    )

    result = subprocess.run(
        [CLI, "--single-repo", "--no-deps", "--message-level", "error", str(app_dir)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_dependency_installation_failure_stops_linting(create_sdk_app, monkeypatch):
    app_dir = create_sdk_app()
    monkeypatch.setattr(cli, "install_dependencies", Mock(return_value=False))
    run_pylint = Mock()
    monkeypatch.setattr(cli, "run_pylint", run_pylint)
    args = cli.parse_args(["--single-repo", str(app_dir)])

    exit_code, _, _ = cli.process_single_repo(str(app_dir), args)

    assert exit_code == 1
    run_pylint.assert_not_called()


@pytest.mark.parametrize("locked", [False, True])
def test_cli_installs_sdk_runtime_and_test_dependencies_without_legacy_conflicts(
    create_sdk_app, locked
):
    app_dir = create_sdk_app()
    project_path = app_dir / "pyproject.toml"
    project_path.write_text(
        project_path.read_text().replace(
            "dependencies = []", 'dependencies = ["pydantic>=2,<3"]'
        )
        + '\n[dependency-groups]\ndev = ["pytest"]\n'
    )
    (app_dir / "app.py").write_text("import pydantic\nimport pytest\n")
    lock_path = app_dir / "uv.lock"
    lock_contents = None
    if locked:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uv",
                "lock",
                "--project",
                str(app_dir),
                "--python",
                sys.executable,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        lock_contents = lock_path.read_bytes()

    result = subprocess.run(
        [CLI, "--single-repo", "--message-level", "error", str(app_dir)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    subprocess.run(
        [
            str(app_dir / ".venv/bin/python"),
            "-c",
            'import pydantic, pytest; assert pydantic.__version__.startswith("2.")',
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    if locked:
        assert lock_path.read_bytes() == lock_contents
    assert not list(app_dir.glob("*.json"))


def test_good_app(
    run_linter: Callable[..., tuple[int, str]], good_app_dir: Path
) -> None:
    """Test that a good app passes all linting checks."""
    exit_code, output = run_linter(str(good_app_dir), output_format="json")

    # Parse the JSON output
    try:
        results = json.loads(output)
    except json.JSONDecodeError:
        pytest.fail(f"Failed to parse JSON output: {output}")

    # There should be no errors
    assert exit_code == 0, f"Expected exit code 0, got {exit_code}. Output: {output}"
    assert not any(result.get("type") == "error" for result in results), (
        f"Found errors in output: {output}"
    )


def test_bad_import(
    run_linter: Callable[..., tuple[int, str]], bad_import_dir: Path
) -> None:
    """Test that importing a removed module in python 3.13 fails."""
    # First test without --no-deps to ensure import errors are caught
    exit_code, output = run_linter(
        str(bad_import_dir), output_format="json", message_level=MessageLevel.ERROR
    )

    # Should fail with import error
    assert exit_code != 0, "Expected non-zero exit code for import error"

    # Now test with --no-deps to ensure import errors are ignored
    exit_code, _ = run_linter(
        str(bad_import_dir),
        output_format="json",
        message_level=MessageLevel.ERROR,
        no_deps=True,
    )

    # Should pass when import errors are ignored
    assert exit_code == 0, "Expected zero exit code with --no-deps"


def test_custom_plugin(
    run_linter: Callable[..., tuple[int, str]], custom_plugin_dir: Path
) -> None:
    """Test that our custom plugin detects the random.sample() issue."""
    # Run with INFO level to see all messages
    exit_code, output = run_linter(
        str(custom_plugin_dir), output_format="json", message_level=MessageLevel.INFO
    )

    # Parse the JSON output
    try:
        results = json.loads(output)
    except json.JSONDecodeError:
        pytest.fail(f"Failed to parse JSON output: {output}")

    # We should find our custom warning
    assert any(
        "consider-random-sample-sequence" in result.get("symbol", "")
        for result in results
    ), f"Expected 'consider-random-sample-sequence' warning, but got: {results}"


def test_message_level_filtering(
    run_linter: Callable[..., tuple[int, str]], custom_plugin_dir: Path
) -> None:
    """Test that message level filtering works as expected."""
    # First get all messages at INFO level
    exit_code, output = run_linter(
        str(custom_plugin_dir), output_format="json", message_level=MessageLevel.INFO
    )

    # Parse the JSON output
    try:
        info_results = json.loads(output)
    except json.JSONDecodeError:
        pytest.fail(f"Failed to parse JSON output: {output}")

    # Should have at least one message at INFO level
    assert len(info_results) > 0, "Expected at least one message at INFO level"

    # Now run with ERROR level - should have fewer or no messages
    exit_code, output = run_linter(
        str(custom_plugin_dir), output_format="json", message_level=MessageLevel.ERROR
    )

    # Parse the JSON output
    try:
        error_results = json.loads(output)
    except json.JSONDecodeError:
        pytest.fail(f"Failed to parse JSON output: {output}")

    # Should have fewer or no messages at ERROR level
    assert len(error_results) <= len(info_results), (
        f"Expected fewer or equal messages at ERROR level, got {len(error_results)} vs {len(info_results)}"
    )


def test_no_deps_disables_import_errors(
    run_linter: Callable[..., tuple[int, str]], bad_import_dir: Path
) -> None:
    """Test that --no-deps disables import errors."""
    # First test without --no-deps to ensure it fails
    exit_code, _ = run_linter(
        str(bad_import_dir), output_format="json", message_level=MessageLevel.ERROR
    )

    # Should fail with import error
    assert exit_code != 0, "Expected failure without --no-deps"

    # Now test with --no-deps to ensure it passes
    exit_code, _ = run_linter(
        str(bad_import_dir),
        output_format="json",
        message_level=MessageLevel.ERROR,
        no_deps=True,
    )

    # Should pass when import errors are ignored
    assert exit_code == 0, "Expected success with --no-deps"
