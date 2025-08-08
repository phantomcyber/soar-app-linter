"""Tests for app.json validation."""

import json
from pathlib import Path
from typing import Any

from soar_app_linter.app_validation import validate_app_json


def create_app_json(
    tmp_path: Path, python_version: Any, publisher: str = "Splunk"
) -> Path:
    """Create an app.json file with the given python_version.

    Default publisher is set to "Splunk" to align with validation behavior.
    """
    app_dir = tmp_path / "test_app"
    app_dir.mkdir()

    app_json = {
        "appid": "test-app",
        "name": "Test App",
        "description": "Test app for validation",
        "publisher": publisher,
        "package_name": "test_app",
        "type": "python3",
        "main_module": "test_app.py",
        "app_version": "1.0.0",
        "product_vendor": "Test",
        "product_name": "Test App",
        "product_version_regex": ".*",
        "min_phantom_version": "5.0.0",
        "logo": "test.png",
        "configuration": {},
        "actions": [],
        "python_version": python_version,
    }

    app_json_path = app_dir / "app.json"
    app_json_path.write_text(json.dumps(app_json))
    return app_dir


def test_valid_app_json_string(tmp_path):
    """Test app.json with python_version as string "3.13"."""
    app_dir = create_app_json(tmp_path, "3.13")
    assert validate_app_json(app_dir) is True


def test_valid_app_json_comma_string(tmp_path):
    """Test app.json with python_version as comma-separated string."""
    app_dir = create_app_json(tmp_path, "3.12, 3.13")
    assert validate_app_json(app_dir) is True


def test_valid_app_json_list(tmp_path):
    """Test app.json with python_version as list."""
    app_dir = create_app_json(tmp_path, [3.12, "3.13"])
    assert validate_app_json(app_dir) is True


def test_missing_python_version(tmp_path):
    """Test app.json with missing python_version."""
    app_dir = tmp_path / "test_app"
    app_dir.mkdir()

    # Create app.json without python_version
    app_json = {
        "appid": "test-app",
        "name": "Test App",
        "description": "Test app for validation",
    }

    (app_dir / "app.json").write_text(json.dumps(app_json))

    # This should return False because python_version is missing
    assert validate_app_json(app_dir) is False


def test_unsupported_python_version(tmp_path):
    """Test app.json with unsupported python_version."""
    app_dir = create_app_json(tmp_path, "2.7")  # Unsupported version
    assert validate_app_json(app_dir) is False


def test_app_json_not_found(tmp_path):
    """Test when app.json is not found."""
    # Create a directory without app.json
    app_dir = tmp_path / "test_app"
    app_dir.mkdir()

    # This should return False because no app.json exists
    assert validate_app_json(app_dir) is False
