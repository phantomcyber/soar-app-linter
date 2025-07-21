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
        avoid_global_playbook_apis as global_apis,
        avoid_global_variables as global_variables,
        avoid_filesystem_access as filesystem_access,
        avoid_infinite_loops as infinite_loops,
        avoid_libraries as libraries,
        avoid_lxml_library as lxml_library,
        avoid_shell_access as shell_access,
        avoid_sleeping as sleeping,
    )

    # Register each checker
    random_deprecations.register(linter)
    removals.register(linter)
    chained_classmethod.register(linter)
    base.register(linter)
    global_apis.register(linter)
    global_variables.register(linter)
    filesystem_access.register(linter)
    infinite_loops.register(linter)
    libraries.register(linter)
    lxml_library.register(linter)
    shell_access.register(linter)
    sleeping.register(linter)

# This makes the package a valid PyLint plugin
__all__ = ["register"]
