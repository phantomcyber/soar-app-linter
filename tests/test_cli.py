"""Tests for the soar-app-linter CLI."""
import json
import subprocess
from pathlib import Path
from collections.abc import Callable

import pytest

from soar_app_linter.cli import MessageLevel


def test_good_app(run_linter: Callable[..., tuple[int, str]], good_app_dir: Path) -> None:
    """Test that a good app passes all linting checks."""
    # Run the linter on our good app
    exit_code, output = run_linter(str(good_app_dir), output_format="json")

    # Parse the JSON output
    results = json.loads(output)

    # There should be no errors or warnings
    if exit_code != 0:
        pytest.fail(f"Expected exit code 0, got {exit_code}. Output: {output}")
    if results:
        pytest.fail(f"Expected no issues, but got: {results}")


def test_bad_import(run_linter: Callable[..., tuple[int, str]], bad_import_dir: Path) -> None:
    """Test that importing a removed module in python 3.13 fails."""
    # Run the linter on the bad import test
    exit_code, output = run_linter(
        str(bad_import_dir),
        output_format="json",
        message_level=MessageLevel.ERROR
    )

    # We expect import errors
    if exit_code != 1:
        pytest.fail(f"Expected exit code 1 for import error, got {exit_code}")

    # Parse the JSON output
    results = json.loads(output)

    # Check that we have the expected import error
    if not any(
        "Unable to import 'distutils.util'" in result.get("message", "")
        for result in results
    ):
        pytest.fail(f"Expected import error for distutils.util, but got: {results}")


def test_custom_plugin(run_linter: Callable[..., tuple[int, str]], custom_plugin_dir: Path) -> None:
    """Test that our custom plugin detects the random.sample() issue."""
    # First run with INFO level to see all messages
    _, output = run_linter(
        str(custom_plugin_dir),
        output_format="json",
        message_level=MessageLevel.INFO
    )

    # Parse the JSON output
    results = json.loads(output)

    # We should find our custom warning
    if not any(
        'consider-random-sample-sequence' in result.get("symbol", "")
        for result in results
    ):
        pytest.fail(f"Expected 'consider-random-sample-sequence' warning, but got: {results}")

    # Now run with ERROR level only - should not show the warning
    exit_code_error_only, output_error_only = run_linter(
        str(custom_plugin_dir),
        output_format="json",
        message_level=MessageLevel.ERROR
    )

    # Should be no errors (just warnings), so exit code should be 0
    if exit_code_error_only != 0:
        pytest.fail(
            f"Expected exit code 0 with ERROR level, got {exit_code_error_only}"
        )

    # Should be no results at ERROR level
    results_error_only = json.loads(output_error_only)
    if results_error_only:
        pytest.fail(
            f"Expected no results at ERROR level, got: {results_error_only}"
        )


def test_imports(run_linter: Callable[..., tuple[int, str]], import_test_dir: Path) -> None:
    """Test that imports between files in the same package work."""
    exit_code, output = run_linter(
        str(import_test_dir),
        output_format="json"
    )

    # Should pass with no errors
    if exit_code != 0:
        pytest.fail(f"Expected exit code 0, got {exit_code}. Output: {output}")

    # Parse the JSON output
    results = json.loads(output)

    # There should be no import errors
    if any(
        result.get("type") == "error" and "import" in result.get("message", "").lower()
        for result in results
    ):
        pytest.fail(f"Unexpected import errors: {results}")


def test_third_party_import(
    run_linter: Callable[..., tuple[int, str]],
    tmp_path: Path
) -> None:
    """Test that third-party imports work when dependencies are installed."""
    # Use a unique module name for this test run
    import uuid
    module_name = f"test_six_{uuid.uuid4().hex[:8]}"

    # Create a temporary test directory
    test_dir = tmp_path / "test_pkg"
    test_dir.mkdir()

    # Create a simple test file that uses six
    test_file = test_dir / f"{module_name}.py"
    test_file.write_text(
        'import six\n'
        'def test():\n'
        '    return isinstance("test", six.string_types)\n'
    )

    # Create a requirements file
    (test_dir / "requirements.txt").write_text("six==1.16.0\n")

    # Run with auto-install enabled
    exit_code, output = run_linter(
        str(test_dir),
        output_format="json",
        message_level=MessageLevel.ERROR,
        no_deps=False  # Enable auto-install
    )

    # Should pass with no errors
    if exit_code != 0:
        pytest.fail(
            f"Expected exit code 0 after installing deps, got {exit_code}. "
            f"Output: {output}"
        )

    # Verify the code actually works by importing and running it in a clean environment
    result = subprocess.run(
        ["python", "-c", f"import {module_name}; print({module_name}.test())"],
        cwd=str(test_dir),
        capture_output=True,
        text=True,
        check=False
    )

    # Check if the test passed
    if result.returncode != 0:
        pytest.fail(f"Test failed with error: {result.stderr}")
    if result.stdout.strip() != "True":
        pytest.fail(f"Expected True, got {result.stdout}")


def test_message_level_filtering(
    run_linter: Callable[..., tuple[int, str]],
    custom_plugin_dir: Path
) -> None:
    """Test that message level filtering works as expected."""
    # First get all messages at INFO level
    _, info_output = run_linter(
        str(custom_plugin_dir),
        output_format="json",
        message_level=MessageLevel.INFO
    )
    info_results = json.loads(info_output)

    # Should have at least one info message
    if not info_results:
        pytest.fail("Expected at least one message at INFO level")

    # Now run with ERROR level - should have fewer or no messages
    _, error_output = run_linter(
        str(custom_plugin_dir),
        output_format="json",
        message_level=MessageLevel.ERROR
    )
    error_results = json.loads(error_output)

    # Should have no messages at ERROR level (since our custom check is a warning)
    if error_results:
        pytest.fail(
            f"Expected no messages at ERROR level, got: {error_results}"
        )


def test_no_deps_disables_import_errors(
    run_linter: Callable[..., tuple[int, str]],
    tmp_path: Path
) -> None:
    """Test that import errors are disabled when --no-deps is used."""
    # Create a test file with an import that will fail
    test_file = tmp_path / "test_import.py"
    test_file.write_text(
        'import this_module_does_not_exist\n'
        'def test():\n'
        '    return True\n'
    )

    # First run without --no-deps - should fail with import error
    exit_code, output = run_linter(
        str(test_file),
        output_format="json",
        message_level=MessageLevel.ERROR,
        no_deps=False
    )

    # Should fail because of import error
    if exit_code != 1:
        pytest.fail("Expected failure without --no-deps")

    # Verify the output contains the import error
    results = json.loads(output)
    if not any(
        "Unable to import 'this_module_does_not_exist'" in result.get("message", "")
        for result in results
    ):
        pytest.fail(
            f"Expected import error for 'this_module_does_not_exist', got: {results}"
        )

    # Now run with --no-deps - should pass (import errors disabled)
    exit_code, output = run_linter(
        str(test_file),
        output_format="json",
        message_level=MessageLevel.ERROR,
        no_deps=True
    )

    # Should pass because import errors are disabled
    if exit_code != 0:
        pytest.fail(
            f"Expected success with --no-deps, got {exit_code}. Output: {output}"
        )
