from astroid import nodes
from pylint.checkers import BaseChecker  # noqa: PH107 avoid pylint imports

from pylint.lint import PyLinter  # noqa: PH107 avoid pylint imports

# TODO: Can our pylint processes import from phantom_common?

PRODUCT_NAME = "Splunk SOAR"  # noqa: PH110 use get_product_name()


class AvoidLibraries(BaseChecker):
    __implements__ = BaseChecker

    name = "not-recommended-libraries"

    @staticmethod
    def get_message_id(library: str) -> str:
        return f"not-recommended-libraries-{library}"

    priority = -1
    msgs = {
        "W0003": (
            "Using the requests library is not recommended. "
            f"Where possible, use the {PRODUCT_NAME} HTTP app instead.",
            "not-recommended-libraries-requests",
            "Using the requests library is not recommended. "
            f"Where possible, use the {PRODUCT_NAME} HTTP app instead.",
        ),
        "W0004": (
            "Using the lxml library is not recommended. Where possible, use another library, \
such as html5lib or html.parser instead.",
            "not-recommended-libraries-lxml",
            "Using the lxml library is not recommended. Where possible, use another library, \
such as html5lib or html.parser instead.",
        ),
        # the number skips a bunch because of other existing lints
        "W0008": (
            "Using the psycopg2 library is not recommended. Where possible, use the SOAR API instead.",
            "not-recommended-libraries-psycopg2",
            "Using the psycopg2 library is not recommended. Where possible, use the SOAR API instead.",
        ),
    }
    # add more libraries that aren't recommended in playbooks to this set
    libraries_to_avoid = set(["requests", "lxml", "psycopg2"])

    def __init__(self, linter: PyLinter) -> None:
        super().__init__(linter)

    # implementing the pylint checker method that visits all import nodes
    def visit_import(self, node: nodes.Import) -> None:
        # check if any of the unrecommended libraries are imported
        imported_libraries = {name[0] for name in node.names}
        for library in imported_libraries & self.libraries_to_avoid:
            self.add_message(AvoidLibraries.get_message_id(library), node=node)

    # implementing the pylint checker method that visits all importfrom nodes
    def visit_importfrom(self, node: nodes.ImportFrom) -> None:
        if node.modname in self.libraries_to_avoid:
            self.add_message(AvoidLibraries.get_message_id(node.modname), node=node)

def register(linter):
    linter.register_checker(AvoidLibraries(linter))
