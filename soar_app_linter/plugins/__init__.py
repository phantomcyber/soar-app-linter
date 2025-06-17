"""Pylint custom rules plugin package."""

def register(linter):
    """Register all checkers with the linter.

    This function avoids circular imports by importing the checkers only when needed.
    """
    # Import checkers here to avoid circular imports
    from . import (
        avoid_313_random_deprecations_on_all as random_deprecations,
        avoid_313_removals_on_39 as removals,
        avoid_chained_classmethod_on_313 as chained_classmethod,
        avoid_deprecation_base as base,
    )

    # Register each checker
    random_deprecations.register(linter)
    removals.register(linter)
    chained_classmethod.register(linter)
    base.register(linter)

# This makes the package a valid PyLint plugin
__all__ = ["register"]
