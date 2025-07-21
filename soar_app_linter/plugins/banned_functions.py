from astroid import nodes

from pylint.lint import PyLinter  # noqa: PH107 avoid pylint imports

from .avoid_deprecation_base import AvoidDeprecationBase


class BannedFunctions(AvoidDeprecationBase):
    # This is meant to be overridden by children. The key is the module, the value is a set of banned
    # functions in that module
    BANNED_FUNCTIONS_MAP: dict[str, set] = {}
    MESSAGE = ""
    msgs = {}
    name = ""

    def __init__(self, linter: PyLinter) -> None:
        super().__init__(linter)

        self.banned_functions: set[str] = set()

        for k, v in self.BANNED_FUNCTIONS_MAP.items():
            for v1 in v:
                self.banned_functions.add(f"{k}.{v1}")

            if not v:
                self.banned_functions.add(k)

    # implementing the pylint checker method that visits all function call nodes
    def visit_call(self, node: nodes.Call) -> None:
        full_name = self._resolve_full_name(node)
        if full_name in self.banned_functions:
            self.add_message(self.MESSAGE, node=node)
