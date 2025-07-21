from astroid import nodes
from pylint.checkers import BaseChecker  # noqa: PH107 avoid pylint imports

from pylint.lint import PyLinter  # noqa: PH107 avoid pylint imports
import astroid

# Currently we're using the library astroid.inference to predict if the while loop
# test condition is always true.
# The node types that are supported for test condition prediction are:
# 1. function call (i.e. function_call())
# 2. name (i.e. variable references)
# 3. unary op (i.e. !)
# 4. binary op (i.e. or, and)
# the astroid.inference library => http://pylint.pycqa.org/projects/astroid/en/latest/_modules/astroid/inference.html
# Note: This implementation only detects infinite while loops


class AvoidInfiniteLoops(BaseChecker):
    __implements__ = BaseChecker

    name = "no-infinite-loops"
    priority = -1
    msgs = {
        "W0002": (
            "No break or return condition was identified for this loop. \
Please check the loop for a valid break or return to avoid an infinite loop.",
            "no-infinite-loops",
            "No break or return condition was identified for this loop. \
Please check the loop for a valid break or return to avoid an infinite loop.",
        ),
    }

    def __init__(self, linter: PyLinter) -> None:
        super().__init__(linter)

    # looks for a break somewhere, and doesn't recurse through nested loops.
    def does_it_break(self, node: nodes.NodeNG) -> bool:
        if isinstance(node, astroid.node_classes.Break):
            return True
        children = node.get_children()
        is_there_break: bool = False

        for child in children:
            if isinstance(child, astroid.node_classes.While) or isinstance(
                child, astroid.node_classes.For
            ):
                continue
            is_there_break = is_there_break or self.does_it_break(child)

        return is_there_break

    # looks for a return statement anywhere. recurses through children
    def does_it_return(self, node: nodes.NodeNG) -> bool:
        if isinstance(node, astroid.node_classes.Return):
            return True
        children = node.get_children()
        is_there_return = False

        for child in children:
            is_there_return = is_there_return or self.does_it_return(child)

        return is_there_return

    # implementing the pylint checker method that visits all while nodes
    def visit_while(self, node: nodes.While) -> None:
        try:
            inferred = next(node.test.infer())
            if hasattr(inferred, "value") and inferred.value:
                if not (self.does_it_return(node) or self.does_it_break(node)):
                    self.add_message("no-infinite-loops", node=node)
        except astroid.exceptions.InferenceError:
            # failed to infer value of the while test condition
            pass
        except StopIteration:
            pass

def register(linter):
    linter.register_checker(AvoidInfiniteLoops(linter))
