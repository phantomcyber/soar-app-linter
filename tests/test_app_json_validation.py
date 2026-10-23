"""Tests for app.json validation."""

import json

import pytest

from soar_app_linter.app_validation import validate_app_json


@pytest.mark.parametrize("publisher", ["Splunk", "Splunk Community", "Mandiant", ""])
def test_valid_app_json_string(create_app_json, publisher):
    """Test app.json with python_version as string "3.13"."""
    app_dir = create_app_json("3.13", publisher=publisher)
    assert validate_app_json(app_dir) is True


def test_valid_app_json_comma_string(create_app_json):
    """Test app.json with python_version as comma-separated string."""
    app_dir = create_app_json("3.12, 3.13")
    assert validate_app_json(app_dir) is True


def test_valid_app_json_list(create_app_json):
    """Test app.json with python_version as list."""
    app_dir = create_app_json([3.12, "3.13"])
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


@pytest.mark.parametrize("publisher", ["Splunk", "Splunk Community", "Mandiant", ""])
@pytest.mark.parametrize("python_version", ["2.7", "3", "3.9"])
def test_unsupported_python_version(create_app_json, publisher, python_version):
    """Test app.json with unsupported python_version."""
    app_dir = create_app_json(python_version, publisher=publisher)
    assert validate_app_json(app_dir) is False


def test_app_json_not_found(tmp_path):
    """Test when app.json is not found."""
    # Create a directory without app.json
    app_dir = tmp_path / "test_app"
    app_dir.mkdir()

    # This should return False because no app.json exists
    assert validate_app_json(app_dir) is False
