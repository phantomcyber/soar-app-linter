"""A module that imports a removed module to test the linter."""

# This import should be flagged by the linter
import distutils.util  # [import-error]


def use_removed() -> None:
    """Use the removed module."""
    print(distutils.util.strtobool("true"))  # [no-member]
