"""App validation module for SOAR apps."""

import json
import os
import re
import glob
import tomllib
from typing import Any, Tuple, Union
from packaging.specifiers import SpecifierSet
from packaging.version import Version


class NotFoundError(Exception):
    """Raised when app.json is not found or invalid."""

    pass


# Required fields for app.json
REQUIRED_APP_JSON_FIELDS = (
    "appid",
    "name",
    "description",
    "publisher",
    "package_name",
    "type",
    "main_module",
    "app_version",
    "product_vendor",
    "product_name",
    "product_version_regex",
    "min_phantom_version",
    "logo",
    "configuration",
    "actions",
    "python_version",
)

PYTHON_313_VERSION = Version("3.13")


def load_sdk_project(target_dir: Union[str, os.PathLike]) -> dict[str, Any] | None:
    """Read SDK source metadata without importing app code or generating a manifest."""
    pyproject_path = os.path.join(target_dir, "pyproject.toml")
    if not os.path.isfile(pyproject_path):
        return None

    with open(pyproject_path, "rb") as file:
        project = tomllib.load(file)

    tool = project.get("tool", {})
    if not isinstance(tool, dict):
        return None
    soar = tool.get("soar", {})
    if not isinstance(soar, dict) or not isinstance(soar.get("app"), dict):
        return None
    return project


def validate_app(target_dir: Union[str, os.PathLike]) -> bool:
    """Validate SDK source metadata or a legacy app manifest."""
    try:
        project = load_sdk_project(target_dir)
        if project is None:
            return validate_app_json(target_dir)

        main_module = project["tool"]["soar"]["app"].get("main_module")
        if not isinstance(main_module, str) or not main_module.strip():
            raise ValueError("SDK apps must define tool.soar.app.main_module")

        metadata = project.get("project", {})
        if not isinstance(metadata, dict):
            raise ValueError("SDK project metadata must be a TOML table")
        requires_python = metadata.get("requires-python", "")
        if not isinstance(requires_python, str):
            raise ValueError("project.requires-python must be a string")
        if PYTHON_313_VERSION not in SpecifierSet(requires_python):
            raise ValueError(
                f"SDK app's requires-python ({requires_python}) does not include "
                f"the required version {PYTHON_313_VERSION}"
            )
        return True
    except (OSError, ValueError) as error:
        print(f"Error: {target_dir}/pyproject.toml: {error}")
        return False


def _find_app_json(app_dir: Union[str, os.PathLike]) -> Tuple[str, dict[str, Any]]:
    """
    Locate and return an app's json file.

    Args:
        app_dir: Directory containing the app

    Returns:
        Tuple of (file_path, json_content)

    Raises:
        NotFoundError: If no valid app.json is found
    """
    errors = []
    json_filepaths = glob.glob(os.path.join(app_dir, "*.json"))

    if not json_filepaths:
        raise NotFoundError(f'No JSON files found in directory "{app_dir}"')

    for json_filepath in json_filepaths:
        try:
            with open(json_filepath) as f:
                json_content = json.load(f)
            if not isinstance(json_content, dict):
                errors.append(f"{json_filepath}: Expected a JSON object")
                continue

            missing = [
                field for field in REQUIRED_APP_JSON_FIELDS if field not in json_content
            ]
            if missing:
                errors.append(
                    f"{json_filepath}: Missing required fields: {', '.join(missing)}"
                )
                continue

            return json_filepath, json_content

        except (OSError, ValueError, json.JSONDecodeError) as e:
            errors.append(f"{json_filepath}: {str(e)}")
            continue

    # If we get here, no valid app.json was found
    error_msg = (
        f'No suitable app JSON found in directory "{app_dir}".\n'
        "Encountered the following errors while searching:\n"
    )
    error_msg += "\n".join(f"  - {error}" for error in errors)
    raise NotFoundError(error_msg)


def _app_python_versions(app_json: dict[str, Any]) -> set[Version]:
    """Extract Python versions from app.json."""
    python_versions = app_json.get("python_version")
    if not python_versions:
        raise ValueError("'python_version' must be defined in app json")
    elif isinstance(python_versions, (float, int)):
        python_versions = [python_versions]
    elif isinstance(python_versions, str):
        python_versions = python_versions.split(",")
    elif not isinstance(python_versions, list):
        raise ValueError("'python_version' must be a list, string, float or int")

    out: set[Version] = set()
    for python_version in python_versions:
        if not (python_version := str(python_version).strip()):
            # skip empty strings
            continue

        # only take major(.minor)?
        if match := re.match(r"^\d+(\.\d+)?", python_version):
            python_version = match[0]

        # replace any instances of "3" with "3.9" for clarity
        if python_version == "3":
            python_version = "3.9"

        out.add(Version(python_version))

    return out


def validate_app_json(target_dir: Union[str, os.PathLike]) -> bool:
    """
    Validate that the app's python_version includes Python 3.13.

    Args:
        target_dir: Directory containing the app.json file

    Returns:
        bool: True if validation passes, False otherwise
    """
    try:
        app_json_path, app_json = _find_app_json(target_dir)
        app_versions = _app_python_versions(app_json)

        if PYTHON_313_VERSION not in app_versions:
            app_versions_str = ", ".join(str(v) for v in sorted(app_versions))
            print(
                f"Error: App's Python versions ({app_versions_str}) do not include "
                f"the required version {PYTHON_313_VERSION} in {app_json_path}"
            )
            return False

        return True
    except (NotFoundError, ValueError) as e:
        print(f"Error: {str(e)}")
        return False


def is_app_directory(target_dir: Union[str, os.PathLike]) -> bool:
    """
    Check whether a directory contains SDK source metadata or a legacy app manifest.

    Args:
        target_dir: Directory containing SDK project metadata or an app JSON file

    Returns:
        bool: True if SDK metadata or a valid legacy manifest exists, False otherwise
    """
    try:
        if load_sdk_project(target_dir) is not None:
            return True
        _find_app_json(target_dir)
        return True
    except (OSError, NotFoundError, ValueError):
        return False
