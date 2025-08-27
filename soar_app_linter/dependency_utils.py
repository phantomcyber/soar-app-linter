import logging
from pathlib import Path


logger = logging.getLogger(__name__)

# Constants
EGG_FRAGMENT = "#egg="

# Tracks deps that were not installable in the last run (best-effort info)
LAST_UNINSTALLED_DEPS: list[str] = []


def _is_empty_or_irrelevant(file_path: Path) -> bool:
    """Check if a requirements.txt file is empty or doesn't contain any dependencies."""
    if not file_path.exists():
        return True

    # Check if file is empty or only contains comments/whitespace
    with open(file_path) as f:
        return not any(line.strip() and not line.strip().startswith("#") for line in f)


def _ensure_venv_exists(directory: Path) -> tuple[Path, Path]:
    """Ensure virtual environment exists and return venv and python paths."""
    import subprocess
    import sys

    venv_dir = directory / ".venv"
    venv_python = venv_dir / "bin" / "python"

    if not venv_python.exists():
        logger.info(f"Creating virtual environment at {venv_dir}...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "venv", str(venv_dir)],
                cwd=directory,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logger.debug(
                f"[install_dependencies] venv creation stdout: {result.stdout}"
            )
            logger.debug(
                f"[install_dependencies] venv creation stderr: {result.stderr}"
            )
        except Exception as e:
            logger.error(f"Failed to create virtual environment: {e}")
            raise
    else:
        logger.debug(
            f"[install_dependencies] Virtual environment already exists at {venv_dir}"
        )

    return venv_dir, venv_python


def _ensure_uv_installed(venv_python: Path, directory: Path) -> None:
    """Ensure uv is installed in the virtual environment."""
    import subprocess

    try:
        logger.debug("[install_dependencies] Checking for 'uv' installation in venv...")
        subprocess.run(
            [str(venv_python), "-m", "uv", "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
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
                text=True,
            )
            logger.info("'uv' installed in venv.")
        except Exception as e:
            logger.error(f"Failed to install 'uv' in venv: {e}")
            raise


def _install_pylint(venv_python: Path, directory: Path) -> None:
    """Install pylint in the virtual environment."""
    import subprocess

    try:
        result = subprocess.run(
            [str(venv_python), "-m", "pip", "install", "pylint"],
            cwd=directory,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logger.debug(f"[install_dependencies] pylint install stdout: {result.stdout}")
        logger.debug(f"[install_dependencies] pylint install stderr: {result.stderr}")
        logger.info("[install_dependencies] pylint installed in venv.")
    except Exception as e:
        logger.error(f"[install_dependencies] Failed to install pylint in venv: {e}")
        raise


def _install_soar_linter(venv_python: Path, directory: Path, venv_dir: Path) -> None:
    """Install soar-app-linter package in the virtual environment."""
    import subprocess

    linter_src = Path(__file__).parent.parent.resolve()
    # Detect if __file__ is inside a site-packages install (running via pre-commit env)
    is_site_packages = any(part == "site-packages" for part in linter_src.parts)
    has_project_files = (linter_src / "pyproject.toml").exists() or (
        linter_src / "setup.py"
    ).exists()

    if is_site_packages and not has_project_files:
        # Running from an installed distribution, skip attempting to re-install into the app venv
        logger.info(
            "[install_dependencies] Detected installed distribution in site-packages; "
            "skipping editable install of soar-app-linter into app venv"
        )
        return

    logger.info(
        f"[install_dependencies] Installing soar-app-linter from {linter_src} into venv at {venv_dir}"
    )
    try:
        result = subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-e", str(linter_src)],
            cwd=directory,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logger.debug(
            f"[install_dependencies] soar-app-linter install stdout: {result.stdout}"
        )
        logger.debug(
            f"[install_dependencies] soar-app-linter install stderr: {result.stderr}"
        )
        logger.info("[install_dependencies] soar-app-linter installed in venv.")

        # Verify that our plugins are importable in the venv
        logger.debug(
            "[install_dependencies] Verifying soar_app_linter.plugins is importable in venv..."
        )
        try:
            verify_result = subprocess.run(
                [
                    str(venv_python),
                    "-c",
                    "import soar_app_linter.plugins; print('Plugins successfully imported')",
                ],
                cwd=directory,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logger.debug(
                f"[install_dependencies] Plugin verification stdout: {verify_result.stdout.strip()}"
            )
            logger.info("[install_dependencies] Custom plugins are importable in venv.")
        except Exception as plugin_e:
            logger.warning(
                f"[install_dependencies] Plugin verification failed: {plugin_e}"
            )
            # Don't raise here since this is just a verification step

    except Exception as e:
        logger.error(
            f"[install_dependencies] Failed to install soar-app-linter in venv: {e}"
        )
        raise


def _update_pylintrc(directory: Path) -> None:
    """Update .pylintrc to ignore .venv directory."""
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
                    ignores = [
                        x.strip()
                        for x in line[len(ignore_line) :].split(",")
                        if x.strip()
                    ]
                    if venv_entry not in ignores:
                        ignores.append(venv_entry)
                        lines[i] = ignore_line + ", ".join(ignores) + "\n"
                        logger.debug(
                            "[install_dependencies] Added .venv to ignore in .pylintrc"
                        )
            if not found:
                lines.append(f"{ignore_line}{venv_entry}\n")
                logger.debug(
                    "[install_dependencies] Created ignore entry in .pylintrc for .venv"
                )
            with open(pylintrc, "w") as f:
                f.writelines(lines)
        else:
            with open(pylintrc, "w") as f:
                f.write(f"[MASTER]\n{ignore_line}{venv_entry}\n")
                logger.debug(
                    "[install_dependencies] Created .pylintrc with ignore=.venv"
                )
    except Exception as e:
        logger.warning(f"[install_dependencies] Could not update .pylintrc: {e}")


def _get_dependency_files(directory: Path, venv_python: Path) -> list:
    """Get list of dependency files and their installation commands."""
    dependency_files = []
    req_txt = directory / "requirements.txt"
    req_dev_txt = directory / "requirements-dev.txt"
    requirements_dir = directory / "requirements"

    # Check for requirements.txt and requirements-dev.txt
    if req_txt.exists() and not _is_empty_or_irrelevant(req_txt):
        dependency_files.append(
            (
                req_txt,
                [
                    str(venv_python),
                    "-m",
                    "uv",
                    "pip",
                    "install",
                    "-v",
                    "-r",
                    "requirements.txt",
                ],
            )
        )
    if req_dev_txt.exists() and not _is_empty_or_irrelevant(req_dev_txt):
        dependency_files.append(
            (
                req_dev_txt,
                [
                    str(venv_python),
                    "-m",
                    "uv",
                    "pip",
                    "install",
                    "-v",
                    "-r",
                    "requirements-dev.txt",
                ],
            )
        )

    # Add requirements/*.txt files
    logger.debug(
        f"[install_dependencies] Checking for requirements directory at {requirements_dir}"
    )
    if requirements_dir.is_dir():
        logger.debug("[install_dependencies] requirements directory exists.")
        for req_file in requirements_dir.glob("*.txt"):
            logger.debug(f"[install_dependencies] Found requirements file: {req_file}")
            if not _is_empty_or_irrelevant(req_file):
                logger.debug(
                    f"[install_dependencies] {req_file} is not empty or irrelevant. Adding to dependency_files."
                )
                dependency_files.append(
                    (
                        req_file,
                        [
                            str(venv_python),
                            "-m",
                            "uv",
                            "pip",
                            "install",
                            "-v",
                            "-r",
                            str(req_file.relative_to(directory)),
                        ],
                    )
                )
            else:
                logger.debug(
                    f"[install_dependencies] {req_file} is empty or irrelevant. Skipping."
                )
    else:
        logger.debug("[install_dependencies] requirements directory does not exist.")

    return dependency_files


def _extract_package_name(line: str) -> str:
    """Extract the package name from a requirements.txt line."""
    line = line.strip()

    # Remove comments
    if "#" in line:
        line = line.split("#")[0].strip()

    # Handle git+https URLs
    if line.startswith("git+"):
        # Extract from git URL like git+https://github.com/user/repo.git#egg=package_name
        if EGG_FRAGMENT in line:
            return line.split(EGG_FRAGMENT)[1].split("&")[0]
        # Fallback: extract repo name
        repo_part = line.split("/")[-1]
        if repo_part.endswith(".git"):
            repo_part = repo_part[:-4]
        return repo_part

    # Handle -e editable installs
    if line.startswith("-e "):
        line = line[3:].strip()
        if EGG_FRAGMENT in line:
            return line.split(EGG_FRAGMENT)[1].split("&")[0]

    # Handle @ version specifiers (like package@1.0.0 or package.git@tag)
    if "@" in line:
        line = line.split("@")[0]

    # Remove .git suffix from package names
    if line.endswith(".git"):
        line = line[:-4]

    # Handle extras like package[extra1,extra2]
    if "[" in line:
        line = line.split("[")[0]

    # Handle environment markers like package; python_version >= "3.8"
    if ";" in line:
        line = line.split(";")[0]

    # Remove version specifiers
    for separator in ["==", ">=", "<=", ">", "<", "!=", "~=", "==="]:
        if separator in line:
            line = line.split(separator)[0]
            break

    return line.strip()


def _read_dependencies_from_file(dep_file: Path) -> list:
    """Read and parse dependencies from a requirements file."""
    try:
        with open(dep_file, "r") as f:
            lines = f.readlines()
        dependencies = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                # Extract package name using improved logic
                pkg_name = _extract_package_name(line)
                if pkg_name:  # Only add non-empty package names
                    dependencies.append(pkg_name)
        return dependencies
    except Exception as read_e:
        logger.warning(f"Could not read dependencies from {dep_file.name}: {read_e}")
        return []


def _verify_installed_dependencies(
    dependencies: list, dep_file: Path, venv_python: Path, directory: Path
) -> None:
    """Verify that requested dependencies are actually installed."""
    import subprocess

    if not dependencies:
        return

    try:
        list_result = subprocess.run(
            [str(venv_python), "-m", "pip", "list"],
            cwd=directory,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logger.debug(
            f"[install_dependencies] Installed packages:\n{list_result.stdout}"
        )

        # Check which dependencies are missing
        installed_packages = list_result.stdout.lower()
        missing_deps = [
            dep for dep in dependencies if dep.lower() not in installed_packages
        ]

        if missing_deps:
            logger.warning(
                f"Some dependencies from {dep_file.name} may not be installed: {', '.join(missing_deps)}"
            )
        else:
            logger.info(
                f"All dependencies from {dep_file.name} appear to be installed successfully"
            )

    except Exception as list_e:
        logger.warning(f"[install_dependencies] Failed to list packages: {list_e}")


def _is_installation_error_ignorable(stderr: str, dep_file: Path) -> bool:
    """Check if installation error should be ignored (e.g., no dependencies to install)."""
    ignorable_messages = [
        "No dependencies to install",
        "No matching distribution",
        "does not appear to be a Python project",
    ]

    if any(msg in (stderr or "") for msg in ignorable_messages):
        logger.debug(f"No dependencies to install from {dep_file.name}")
        return True
    return False


def _install_and_verify_dependencies(
    dep_file: Path, cmd: list, venv_python: Path, directory: Path, venv_dir: Path
) -> bool:
    """Install dependencies from a file per-package (wheel-only) and verify installation."""
    import subprocess

    # Read and log the dependencies from the file
    dependencies = _read_dependencies_from_file(dep_file)

    if dependencies:
        logger.info(
            f"Dependencies listed in {dep_file.name}: {', '.join(dependencies)}"
        )
    else:
        logger.info(f"No dependencies found in {dep_file.name}")

    logger.info(
        f"Retrieving dependencies for {dep_file.name} (using venv at {venv_dir})..."
    )
    logger.debug(
        f"[install_dependencies] Running command: {' '.join(cmd)} in {directory}"
    )

    try:
        # Prefer wheel-only from caches first to avoid source builds
        import sys as _sys

        wheel_bases = [Path("/wheels"), directory / "wheels"]
        major_minor = f"py{_sys.version_info.major}{_sys.version_info.minor}"
        wheel_subdirs = [major_minor, "py3", "shared"]
        find_links_args: list[str] = []
        for base in wheel_bases:
            for sub in wheel_subdirs:
                candidate = base / sub
                if candidate.is_dir():
                    find_links_args.extend(["--find-links", str(candidate)])

        primary_cmd = (
            [
                str(venv_python),
                "-m",
                "uv",
                "pip",
                "install",
                "-v",
                "-r",
                str(dep_file.relative_to(directory)),
                "--only-binary=:all:",
                *find_links_args,
            ]
            if find_links_args
            else cmd
        )

        result = subprocess.run(
            primary_cmd,
            cwd=directory,
            check=False,  # Don't raise exception on non-zero exit
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        logger.debug(f"[install_dependencies] Command stdout: {result.stdout}")
        logger.debug(f"[install_dependencies] Command stderr: {result.stderr}")
        logger.debug(f"[install_dependencies] Command return code: {result.returncode}")

        # Even if the batch resolver succeeded, continue to verify per-package presence
        if result.returncode == 0:
            logger.info("Dependencies installed successfully in venv (batch)")

        # Per-package wheel-only installs to avoid one bad dep blocking all
        LAST_UNINSTALLED_DEPS.clear()
        for dep in dependencies:
            # Extract clean package name for wheel installation
            package_name = _extract_package_name(dep)
            if not package_name:
                continue

            # Try local wheels
            ok = False
            if find_links_args:
                cmd_local = [
                    str(venv_python),
                    "-m",
                    "uv",
                    "pip",
                    "install",
                    "-v",
                    "--only-binary=:all:",
                    *find_links_args,
                    package_name,
                ]
                r = subprocess.run(
                    cmd_local,
                    cwd=directory,
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                ok = r.returncode == 0
            if not ok:
                # Try index wheels only
                cmd_index = [
                    str(venv_python),
                    "-m",
                    "uv",
                    "pip",
                    "install",
                    "-v",
                    "--only-binary=:all:",
                    package_name,
                ]
                r2 = subprocess.run(
                    cmd_index,
                    cwd=directory,
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                ok = r2.returncode == 0
            if not ok:
                LAST_UNINSTALLED_DEPS.append(dep)

        # Summarize
        if LAST_UNINSTALLED_DEPS:
            logger.info(
                f"Uninstalled dependencies for this run (no compatible wheels found): {', '.join(LAST_UNINSTALLED_DEPS)}"
            )
        return True

    except Exception as e:
        # Non-fatal: proceed with linting even if dependency resolution fails
        logger.warning(
            f"Proceeding without installing dependencies from {dep_file.name}: {e}"
        )
        return True


def install_dependencies(directory: str) -> bool:
    """Install dependencies in a virtual environment for the given directory."""
    from pathlib import Path

    # Convert to Path object and resolve to absolute path
    directory = Path(directory).resolve()

    try:
        # Set up virtual environment and tools
        venv_dir, venv_python = _ensure_venv_exists(directory)
        _ensure_uv_installed(venv_python, directory)
        _install_pylint(venv_python, directory)
        _install_soar_linter(venv_python, directory, venv_dir)
        _update_pylintrc(directory)

        # Install project dependencies
        dependency_files = _get_dependency_files(directory, venv_python)

        # Try each dependency file in order
        for dep_file, cmd in dependency_files:
            logger.debug(f"[install_dependencies] Checking dependency file: {dep_file}")
            if dep_file.exists() and not _is_empty_or_irrelevant(dep_file):
                return _install_and_verify_dependencies(
                    dep_file, cmd, venv_python, directory, venv_dir
                )
            else:
                logger.debug(
                    f"[install_dependencies] {dep_file} does not exist or is empty/irrelevant. Skipping."
                )

        logger.debug(
            "No supported non-empty dependency files found, skipping dependency installation"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False
