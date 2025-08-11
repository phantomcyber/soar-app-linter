"""Pytest configuration and fixtures."""

from pathlib import Path
from typing import Callable

import pytest

from soar_app_linter.pylint_runner import run_pylint, MessageLevel


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return the path to the test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def good_app_dir(test_data_dir: Path) -> Path:
    """Return the path to the good app test directory."""
    return test_data_dir / "good_app"


@pytest.fixture(scope="session")
def bad_import_dir(test_data_dir: Path) -> Path:
    """Return the path to the bad import test directory."""
    return test_data_dir / "bad_import"


@pytest.fixture(scope="session")
def custom_plugin_dir(test_data_dir: Path) -> Path:
    """Return the path to the custom plugin test directory."""
    return test_data_dir / "custom_plugin"


@pytest.fixture(scope="session")
def import_test_dir(test_data_dir: Path) -> Path:
    """Return the path to the import test directory."""
    return test_data_dir / "import_test"


@pytest.fixture()
def run_linter() -> Callable[..., tuple[int, str]]:
    """Fixture to run the linter with the given arguments."""

    def _run_linter(
        target: str,
        output_format: str = "text",
        message_level: MessageLevel | None = None,
        no_deps: bool = False,
    ) -> tuple[int, str]:
        """Run the linter with the given arguments."""
        if message_level is None:
            message_level = MessageLevel.INFO

        return run_pylint(
            target=target,
            output_format=output_format,
            message_level=message_level,
            no_deps=no_deps,
        )

    return _run_linter
