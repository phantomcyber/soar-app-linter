# Python Linter with Custom Rules

A command-line tool for linting Python code with custom pylint rules and automatic `__init__.py` management.

## Features

- Lint Python code using pylint `3.3.6` (same version as SOAR uses)
- Automatic creation of missing `__init__.py` files to avoid pylint skipping over files in subdirectories.
- Emits either 0 or 1 exit code for easy CI integration
- JSON output option
- Currently lints against Python 3.13
- Checks the supplied app json for python 3.13 listing in `python_version`

## Installation

1. Install pyenv (recommended) or your preferred Python version manager
2. Install Python 3.13:
   ```bash
   pyenv install 3.13.0
   ```
3. Create and activate a virtual environment:
   ```bash
   python3.13 -m venv soar_app_linter_venv
   source soar_app_linter_venv/bin/activate
   ```
4. Install the package in development mode:
   ```bash
   # Install uv if not already installed
   pip install uv

   # Install the package in development mode with uv
   uv pip install -e ".[dev]"
   ```

## Usage

Basic usage:
```bash
soar-app-linter /path/to/your/code
```

With JSON output:
```bash
soar-app-linter soar_app_linter /path/to/your/code --json
```

## Command Line Options

- `TARGET_DIR`: Directory containing Python files to lint (required)
- `--json`: Output results in JSON format
- `--no-init`: Disable automatic creation of `__init__.py` files
- `-h, --help`: Show help message and exit
- `--verbose`: Show verbose output
- `--message-level`: Set minimum message level (info, warning, error)
- `--version`: Show version and exit
- `--no-deps`: Disable automatic installation of dependencies specified in app configuration. This also disables import errors from being reported.
- `--disable-app-json-validation`: Disable validation of app.json file. We check that the python versions specified in the app json file are supported by SOAR. 


## Development

To run tests:
```bash
pytest -v
```

## License

Apache License 2.0
