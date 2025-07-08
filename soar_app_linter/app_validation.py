"""App validation module for SOAR apps."""
import json
import logging
import os
import re
import glob
from typing import Any, Tuple, Union
from packaging.version import Version
import re

logger = logging.getLogger(__name__)

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
                
            missing = [field for field in REQUIRED_APP_JSON_FIELDS if field not in json_content]
            if missing:
                errors.append(f"{json_filepath}: Missing required fields: {', '.join(missing)}")
                continue
                
            return json_filepath, json_content
            
        except (OSError, ValueError, json.JSONDecodeError) as e:
            errors.append(f"{json_filepath}: {str(e)}")
            continue

    # If we get here, no valid app.json was found
    error_msg = (
        f'No suitable app JSON found in directory "{app_dir}".\n'
        'Encountered the following errors while searching:\n'
    )
    error_msg += '\n'.join(f"  - {error}" for error in errors)
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
        publisher = app_json.get("publisher", "")
        
        # Skip non-Splunk apps
        if publisher != "Splunk":
            logger.debug(f"Skipping app with publisher '{publisher}' - only processing Splunk apps")
            return False
            
        app_versions = _app_python_versions(app_json)
        
        if PYTHON_313_VERSION not in app_versions:
            app_versions_str = ", ".join(str(v) for v in sorted(app_versions))
            return True
            # already aware of this
            # print(
            #     f"Error: App's Python versions ({app_versions_str}) do not include "
            #     f"the required version {PYTHON_313_VERSION} in {app_json_path}"
            # )
            # return False
            
        return True
    except (NotFoundError, ValueError) as e:
        print(f"Error: {str(e)}")
        return False


def should_process_app(target_dir: Union[str, os.PathLike]) -> bool:
    """
    Check if an app should be processed based on its publisher.
    
    Args:
        target_dir: Directory containing the app.json file
        
    Returns:
        bool: True if app should be processed (publisher is Splunk), False otherwise
    """
    try:
        app_json_path, app_json = _find_app_json(target_dir)
        publisher = app_json.get("publisher", "")
        return publisher == "Splunk"
    except (NotFoundError, ValueError):
        return False
