import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _is_empty_or_irrelevant(file_path: Path) -> bool:
    """Check if a file is empty or doesn't contain any dependencies."""
    if not file_path.exists():
        return True

    if file_path.suffix == '.toml':
        try:
            import tomli
            with open(file_path, 'rb') as f:
                data = tomli.load(f)
            # Check if project.dependencies exists and is not empty
            has_deps = bool(data.get('project', {}).get('dependencies'))
            has_build_system = 'build-system' in data
            # If it has a build system but no deps, it's a package that needs installation
            return not has_deps and not has_build_system
        except Exception:
            # If we can't parse the file, assume it's not empty
            return False
    elif file_path.suffix == '.txt':
        # Check if file is empty or only contains comments/whitespace
        with open(file_path) as f:
            return not any(line.strip() and not line.strip().startswith('#')
                            for line in f)
    return False


def install_dependencies(directory: str) -> bool:
    """Install dependencies using uv if a dependency file is found.

    Supported files (in order of precedence):
        - pyproject.toml (installs in development mode only if it has dependencies)
        - requirements.txt
        - requirements-dev.txt
        - setup.py (installs in development mode)
        - setup.cfg (installs in development mode)

    Args:
        directory: Directory containing the dependency files

    Returns:
        bool: True if installation was successful, no installation was needed,
            or if the file exists but has no dependencies to install.
            False if installation failed for other reasons.
    """
    import subprocess
    from pathlib import Path

    # Convert to Path object and resolve to absolute path
    directory = Path(directory).resolve()

    # Check for uv installation
    try:
        subprocess.run(
            ["uv", "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning(
            "uv is not installed. Please install it with 'pip install uv' "
            "for faster dependency resolution.")
        return False

    # Define supported dependency files in order of precedence
    # For pyproject.toml, we'll handle it specially to check for deps first
    dependency_files = [
        (directory / "requirements.txt", ["uv", "pip", "install", "-r", "requirements.txt"]),
        (directory / "requirements-dev.txt", ["uv", "pip", "install", "-r", "requirements-dev.txt"]),
        (directory / "setup.py", ["uv", "pip", "install", "-e", "."]),
        (directory / "setup.cfg", ["uv", "pip", "install", "-e", "."]),
    ]

    # Check pyproject.toml first if it exists
    pyproject = directory / "pyproject.toml"
    if pyproject.exists():
        if not _is_empty_or_irrelevant(pyproject):
            # If it has dependencies, add it to the front of the list
            dependency_files.insert(0, (pyproject, ["uv", "pip", "install", "-e", "."]))

    # Check for requirements/*.txt files
    requirements_dir = directory / "requirements"
    if requirements_dir.is_dir():
        for req_file in requirements_dir.glob("*.txt"):
            if not _is_empty_or_irrelevant(req_file):
                dependency_files.insert(1, (
                    req_file,
                    ["uv", "pip", "install", "-r", str(req_file.relative_to(directory))]
                ))

    # Try each dependency file in order
    for dep_file, cmd in dependency_files:
        if dep_file.exists() and not _is_empty_or_irrelevant(dep_file):
            logger.info(f"Retrieving dependencies for {dep_file.name}...")
            try:
                result = subprocess.run(
                    cmd,
                    cwd=directory,
                    check=False,  # Don't raise exception on non-zero exit
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                if result.returncode == 0:
                    logger.info("Dependencies installed successfully")
                    return True
                else:
                    # Check if the error is due to no dependencies to install
                    if any(msg in (result.stderr or "") for msg in
                        ["No dependencies to install",
                        "No matching distribution",
                        "does not appear to be a Python project"]):
                        logger.debug(f"No dependencies to install from {dep_file.name}")
                        return True

                    logger.error(
                        f"Failed to install dependencies from {dep_file.name}. "
                        f"Error: {result.stderr.strip() or result.stdout.strip()}"
                    )
                    return False

            except Exception as e:
                logger.error(f"Unexpected error installing dependencies from {dep_file.name}: {e}")
                return False

    logger.debug("No supported non-empty dependency files found, skipping dependency installation")
    return True
