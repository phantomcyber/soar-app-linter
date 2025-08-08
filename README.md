# SOAR App Linter

Lint Splunk SOAR apps with pylint and SOAR-specific rules. Simple CLI, CI-friendly output.

## Features

- Pylint 3.3.6 (matches SOAR platform)
- SOAR-specific pylint plugins
- Auto-create missing `__init__.py` files
- Text or JSON output; exit code 0/1 for CI
- Python 3.13 compatible and app.json validation

## Installation

1. Use Python 3.13
1. Create a venv and install:
   ```bash
   python3.13 -m venv .venv && source .venv/bin/activate
   pip install uv  # if not already installed
   uv pip install -e ".[dev]"
   ```

## Quick start

### Single repository (common)

- Errors only (CI-friendly):

```bash
soar-app-linter --single-repo ./googlepeople --message-level error
```

- JSON output:

```bash
soar-app-linter --single-repo /path/to/app --output-format json
```

### Multiple repositories (optional)

```bash
soar-app-linter /path/to/apps
```

## CLI options (most used)

- `target` (positional): directory to app or apps to lint (default: `.`)
- `--single-repo`: treat target as one app repo
- `--message-level {info,error}`: minimum messages to show (default: info)
- `--output-format {text,json}`: output format (default: text)
- `--no-deps`: skip dependency install and ignore import errors (disables E0401)
- `-v, --verbose`: verbose logs

Advanced:

- `--only-import-errors`: show only import errors (E0401)
- `--json-failures`: JSON with repos and their error messages
- `--disable-app-json-validation`: skip app.json validation

## Development

Run tests:

```bash
pytest -v
```

## Pre-commit hook

Can use this tool with `pre-commit`:

1. Add to your project's `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/splunk/soar-app-linter
    rev: v1.0.0 # Or whatever the current tag is
    hooks:
      - id: soar-app-linter
        args: ["--single-repo", "--message-level", "error"]
```

## License

Apache License 2.0
