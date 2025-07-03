import logging
from pathlib import Path


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
    import subprocess
    from pathlib import Path
    # Convert to Path object and resolve to absolute path
    directory = Path(directory).resolve()
    # Always ensure venv exists before installing anything
    venv_dir = directory / ".venv"
    venv_python = venv_dir / "bin" / "python"
    import sys
    if not venv_python.exists():
        logger.info(f"Creating virtual environment at {venv_dir}...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "venv", str(venv_dir)],
                cwd=directory,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.debug(f"[install_dependencies] venv creation stdout: {result.stdout}")
            logger.debug(f"[install_dependencies] venv creation stderr: {result.stderr}")
        except Exception as e:
            logger.error(f"Failed to create virtual environment: {e}")
            return False
    else:
        logger.debug(f"[install_dependencies] Virtual environment already exists at {venv_dir}")
    
    # Check for uv installation in the venv and install if needed
    try:
        logger.debug("[install_dependencies] Checking for 'uv' installation in venv...")
        subprocess.run(
            [str(venv_python), "-m", "uv", "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.debug("[install_dependencies] 'uv' is installed in venv.")
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.info("'uv' not found in venv, installing it...")
        try:
            subprocess.run(
                [str(venv_python), "-m", "pip", "install", "uv"],
                cwd=directory,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info("'uv' installed in venv.")
        except Exception as e:
            logger.error(f"Failed to install 'uv' in venv: {e}")
            return False
    
    # Always ensure pylint is installed in the venv for linting
    try:
        result = subprocess.run(
            [str(venv_python), "-m", "pip", "install", "pylint"],
            cwd=directory,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.debug(f"[install_dependencies] pylint install stdout: {result.stdout}")
        logger.debug(f"[install_dependencies] pylint install stderr: {result.stderr}")
        logger.info("[install_dependencies] pylint installed in venv.")
    except Exception as e:
        logger.error(f"[install_dependencies] Failed to install pylint in venv: {e}")
        return False
    
    # Install the soar-app-linter package itself into the venv so custom plugins are available
    linter_src = Path(__file__).parent.parent.resolve()
    logger.info(f"[install_dependencies] Installing soar-app-linter from {linter_src} into venv at {venv_dir}")
    try:
        result = subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-e", str(linter_src)],
            cwd=directory,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.debug(f"[install_dependencies] soar-app-linter install stdout: {result.stdout}")
        logger.debug(f"[install_dependencies] soar-app-linter install stderr: {result.stderr}")
        logger.info("[install_dependencies] soar-app-linter installed in venv.")
        
        # Verify that our plugins are importable in the venv
        logger.debug("[install_dependencies] Verifying soar_app_linter.plugins is importable in venv...")
        try:
            verify_result = subprocess.run(
                [str(venv_python), "-c", "import soar_app_linter.plugins; print('Plugins successfully imported')"],
                cwd=directory,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.debug(f"[install_dependencies] Plugin verification stdout: {verify_result.stdout.strip()}")
            logger.info("[install_dependencies] Custom plugins are importable in venv.")
        except Exception as plugin_e:
            logger.warning(f"[install_dependencies] Plugin verification failed: {plugin_e}")
            # Don't return False here since this is just a verification step
            
    except Exception as e:
        logger.error(f"[install_dependencies] Failed to install soar-app-linter in venv: {e}")
        return False
    
    # Ensure .venv is ignored by pylint by updating/creating .pylintrc with .venv in the ignore option
    pylintrc = directory / ".pylintrc"
    try:
        ignore_line = "ignore="
        venv_entry = ".venv"
        if pylintrc.exists():
            with open(pylintrc, "r+") as f:
                lines = f.readlines()
            found = False
            for i, line in enumerate(lines):
                if line.strip().startswith(ignore_line):
                    found = True
                    ignores = [x.strip() for x in line[len(ignore_line):].split(",") if x.strip()]
                    if venv_entry not in ignores:
                        ignores.append(venv_entry)
                        lines[i] = ignore_line + ", ".join(ignores) + "\n"
                        logger.debug("[install_dependencies] Added .venv to ignore in .pylintrc")
            if not found:
                lines.append(f"{ignore_line}{venv_entry}\n")
                logger.debug("[install_dependencies] Created ignore entry in .pylintrc for .venv")
            with open(pylintrc, "w") as f:
                f.writelines(lines)
        else:
            with open(pylintrc, "w") as f:
                f.write(f"[MASTER]\n{ignore_line}{venv_entry}\n")
                logger.debug("[install_dependencies] Created .pylintrc with ignore=.venv")
    except Exception as e:
        logger.warning(f"[install_dependencies] Could not update .pylintrc: {e}")

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


    # Build dependency_files list with requirements files first
    dependency_files = []
    req_txt = directory / "requirements.txt"
    req_dev_txt = directory / "requirements-dev.txt"
    requirements_dir = directory / "requirements"

    # Always prioritize requirements.txt and requirements-dev.txt
    if req_txt.exists() and not _is_empty_or_irrelevant(req_txt):
        dependency_files.append((req_txt, [str(venv_python), "-m", "uv", "pip", "install", "-v", "-r", "requirements.txt"]))
    if req_dev_txt.exists() and not _is_empty_or_irrelevant(req_dev_txt):
        dependency_files.append((req_dev_txt, [str(venv_python), "-m", "uv", "pip", "install", "-v", "-r", "requirements-dev.txt"]))

    # Add requirements/*.txt files
    logger.debug(f"[install_dependencies] Checking for requirements directory at {requirements_dir}")
    if requirements_dir.is_dir():
        logger.debug("[install_dependencies] requirements directory exists.")
        for req_file in requirements_dir.glob("*.txt"):
            logger.debug(f"[install_dependencies] Found requirements file: {req_file}")
            if not _is_empty_or_irrelevant(req_file):
                logger.debug(f"[install_dependencies] {req_file} is not empty or irrelevant. Adding to dependency_files.")
                dependency_files.append((
                    req_file,
                    [str(venv_python), "-m", "uv", "pip", "install", "-v", "-r", str(req_file.relative_to(directory))]
                ))
            else:
                logger.debug(f"[install_dependencies] {req_file} is empty or irrelevant. Skipping.")
    else:
        logger.debug("[install_dependencies] requirements directory does not exist.")

    # Add setup.py and setup.cfg
    setup_py = directory / "setup.py"
    setup_cfg = directory / "setup.cfg"
    if setup_py.exists() and not _is_empty_or_irrelevant(setup_py):
        dependency_files.append((setup_py, [str(venv_python), "-m", "uv", "pip", "install", "-v", "-e", "."]))
    if setup_cfg.exists() and not _is_empty_or_irrelevant(setup_cfg):
        dependency_files.append((setup_cfg, [str(venv_python), "-m", "uv", "pip", "install", "-v", "-e", "."]))


    # Only use pyproject.toml if no requirements files are found
    pyproject = directory / "pyproject.toml"
    logger.debug(f"[install_dependencies] Checking for pyproject.toml at {pyproject}")
    if not dependency_files and pyproject.exists() and not _is_empty_or_irrelevant(pyproject):
        logger.debug("[install_dependencies] No requirements files found, using pyproject.toml.")
        dependency_files.append((pyproject, [str(venv_python), "-m", "uv", "pip", "install", "-v", "-e", "."]))
    elif pyproject.exists():
        logger.debug("[install_dependencies] pyproject.toml exists but requirements files take precedence.")
    else:
        logger.debug("[install_dependencies] pyproject.toml does not exist.")

    # Try each dependency file in order
    for dep_file, cmd in dependency_files:
        logger.debug(f"[install_dependencies] Checking dependency file: {dep_file}")
        if dep_file.exists() and not _is_empty_or_irrelevant(dep_file):
            logger.info(f"Retrieving dependencies for {dep_file.name} (using venv at {venv_dir})...")
            logger.debug(f"[install_dependencies] Running command: {' '.join(cmd)} in {directory}")
            try:
                result = subprocess.run(
                    cmd,
                    cwd=directory,
                    check=False,  # Don't raise exception on non-zero exit
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                logger.debug(f"[install_dependencies] Command stdout: {result.stdout}")
                logger.debug(f"[install_dependencies] Command stderr: {result.stderr}")
                logger.debug(f"[install_dependencies] Command return code: {result.returncode}")

                if result.returncode == 0:
                    logger.info("Dependencies installed successfully in venv")
                    
                    # List all installed packages for verification
                    logger.debug("[install_dependencies] Listing installed packages in venv...")
                    try:
                        list_result = subprocess.run(
                            [str(venv_python), "-m", "pip", "list"],
                            cwd=directory,
                            check=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        logger.info(f"[install_dependencies] Installed packages:\n{list_result.stdout}")
                    except Exception as list_e:
                        logger.warning(f"[install_dependencies] Failed to list packages: {list_e}")
                    
                    # Check specific module structure for databricks if it exists
                    logger.debug("[install_dependencies] Checking for databricks module structure...")
                    try:
                        databricks_check = subprocess.run(
                            [str(venv_python), "-c", """
import sys
try:
    import databricks
    print(f"databricks module location: {databricks.__file__}")
    print(f"databricks module dir contents: {dir(databricks)}")
    try:
        import databricks.sdk
        print(f"databricks.sdk module location: {databricks.sdk.__file__}")
        print("databricks.sdk import: SUCCESS")
    except ImportError as e:
        print(f"databricks.sdk import: FAILED - {e}")
except ImportError as e:
    print(f"databricks module: NOT FOUND - {e}")
"""],
                            cwd=directory,
                            check=False,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        logger.info(f"[install_dependencies] Module structure check:\n{databricks_check.stdout}")
                        if databricks_check.stderr:
                            logger.warning(f"[install_dependencies] Module check stderr: {databricks_check.stderr}")
                    except Exception as module_e:
                        logger.warning(f"[install_dependencies] Failed to check module structure: {module_e}")
                    
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
                        f"Failed to install dependencies from {dep_file.name} in venv. "
                        f"Error: {result.stderr.strip() or result.stdout.strip()}"
                    )
                    return False

            except Exception as e:
                logger.error(f"Unexpected error installing dependencies from {dep_file.name} in venv: {e}")
                return False
        else:
            logger.debug(f"[install_dependencies] {dep_file} does not exist or is empty/irrelevant. Skipping.")

    logger.debug("No supported non-empty dependency files found, skipping dependency installation")
    return True
