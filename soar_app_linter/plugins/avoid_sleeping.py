from astroid import nodes
from pylint.checkers import BaseChecker  # noqa: PH107 avoid pylint imports

import astroid
from pylint.lint import PyLinter  # noqa: PH107 avoid pylint imports


class AvoidSleeping(BaseChecker):
    __implements__ = BaseChecker

    name = "no-sleeps"
    priority = -1
    msgs = {
        "W0001": (
            "Using the sleep function is not recommended.",
            "no-sleeps",
            "Using the sleep function is not recommended.",
        ),
    }

    def __init__(self, linter: PyLinter) -> None:
        super().__init__(linter)
        # the aliases are sets because in python its valid to import a library more than once
        self.time_aliases: set[str] = set()
        self.sleep_aliases: set[str] = set()
        # constants
        self.TIME = "time"
        self.SLEEP = "sleep"

    # implementing the pylint checker method that visits all import nodes
    def visit_import(self, node: nodes.Import) -> None:
        for name in node.names:
            # import name[0] as name[1]
            if name[0] == self.TIME:
                # add 'time' to the alias set if the alias doesn't exist, otherwise add the alias
                self.time_aliases.add(name[1] or name[0])

    # implementing the pylint checker method that visits all importfrom nodes
    def visit_importfrom(self, node: nodes.ImportFrom) -> None:
        if node.modname == self.TIME:
            for name in node.names:
                # from time import name[0] as name[1]
                if name[0] == self.SLEEP:
                    # add 'sleep' to the alias set if the alias doesn't exist, otherwise add the alias
                    self.sleep_aliases.add(name[1] or name[0])

    # implementing the pylint checker method that visits all function call nodes
    def visit_call(self, node: nodes.Call) -> None:
        # check if the function call is foo.bar()
        if isinstance(node.func, astroid.node_classes.Attribute) and isinstance(
            node.func.expr, astroid.node_classes.Name
        ):
            # check if the function call is time.sleep()
            if (
                node.func.attrname == self.SLEEP
                and node.func.expr.name in self.time_aliases
            ):
                self.add_message("no-sleeps", node=node)

        elif isinstance(node.func, astroid.node_classes.Name):
            # check if the function call is sleep()
            if node.func.name in self.sleep_aliases:
                self.add_message("no-sleeps", node=node)


def register(linter):
    linter.register_checker(AvoidSleeping(linter))
