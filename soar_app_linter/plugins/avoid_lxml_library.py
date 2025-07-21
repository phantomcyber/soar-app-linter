from astroid import nodes
from pylint.checkers import BaseChecker  # noqa: PH107 avoid pylint imports

import astroid
from pylint.lint import PyLinter  # noqa: PH107 avoid pylint imports


class AvoidLxml(BaseChecker):
    __implements__ = BaseChecker

    name = "no-lxml"
    msgs = {
        "W0005": (
            "Using the lxml library with BeautifulSoup may cause problems in playbooks. \
Where possible, use another library, such as html5lib or html.parser instead.",
            "no-lxml",
            "Using the lxml library with BeautifulSoup may cause problems in playbooks. \
Where possible, use another library, such as html5lib or html.parser instead.",
        )
    }

    def __init__(self, linter: PyLinter) -> None:
        super().__init__(linter)

        # the aliases are sets because in python its valid to import a library more than once
        self.bs4_aliases: set[str] = set()
        self.soup_aliases: set[str] = set()
        self.lxml_lib = set(["lxml", "lxml-xml", "xml"])
        # constants
        self.BS4 = "bs4"
        self.BEAUTIFUL_SOUP = "BeautifulSoup"
        self.PARSER_ARG_KEYWORD = "features"

    # implementing the pylint checker method that visits all import nodes
    def visit_import(self, node: nodes.Import) -> None:
        for name in node.names:
            # import name[0] as name[1]
            if name[0] == self.BS4:
                # add 'bs4' to the alias set if the alias doesn't exist, otherwise add the alias
                self.bs4_aliases.add(name[1] or name[0])

    # implementing the pylint checker method that visits all importfrom nodes
    def visit_importfrom(self, node: nodes.ImportFrom) -> None:
        if node.modname == self.BS4:
            for name in node.names:
                # from bs4 import name[0] as name[1]
                if name[0] == self.BEAUTIFUL_SOUP:
                    # add 'BeautifulSoup' to the alias set if the alias doesn't exist, otherwise add the alias
                    self.soup_aliases.add(name[1] or name[0])

    def is_beautiful_soup_call(self, node: nodes.Call) -> bool:
        # check if the function call is foo.bar()
        if isinstance(node.func, astroid.node_classes.Attribute) and isinstance(
            node.func.expr, astroid.node_classes.Name
        ):
            # check if the function call is bs4.BeautifulSoup()
            if (
                node.func.attrname == self.BEAUTIFUL_SOUP
                and node.func.expr.name in self.bs4_aliases
            ):
                return True

        elif isinstance(node.func, astroid.node_classes.Name):
            # check if the function call is BeautifulSoup()
            if node.func.name in self.soup_aliases:
                return True

        return False

    def check_literal_value(self, node: nodes.NodeNG) -> None:
        # if the node is a literal, check its direct value
        if isinstance(node, astroid.node_classes.Const) and node.value in self.lxml_lib:
            self.add_message("no-lxml", node=node)
        else:
            # the node isn't a literal, try to infer its value
            try:
                inferred = next(node.infer())
                if isinstance(inferred, astroid.node_classes.Const) and inferred.value is not None:
                    if inferred.value in self.lxml_lib:
                        self.add_message("no-lxml", node=node)
            except astroid.exceptions.InferenceError:
                # failed to infer value of the variable passed
                pass
            except StopIteration:
                pass

    # implementing the pylint checker method that visits all function call nodes
    def visit_call(self, node: nodes.Call) -> None:
        if self.is_beautiful_soup_call(node):
            # check the named arguments
            if node.keywords:
                # look for the keyword for the parser argument
                for k in node.keywords:
                    if k.arg.lower() == self.PARSER_ARG_KEYWORD:
                        # pass the rhs to check for literal value and look for lxml usage
                        self.check_literal_value(k.value)
                        return

            # check if the parser was passed as a positional argument
            # the parser is the second argument
            if len(node.args) >= 2:
                # pass the second argument to check for literal value and look for lxml usage
                self.check_literal_value(node.args[1])
            else:
                # no parser was passed explicitly; default parser(lxml) was used
                self.add_message("no-lxml", node=node)

def register(linter):
    linter.register_checker(AvoidLxml(linter))
