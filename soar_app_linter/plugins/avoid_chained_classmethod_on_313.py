import sys
from astroid import nodes
from pylint.lint import PyLinter  # avoid pylint imports
from .avoid_deprecation_base import AvoidDeprecationBase


# List of common descriptor names to check
DESCRIPTOR_NAMES = {"property", "staticmethod", "cached_property", "abstractmethod"}


class AvoidChainedClassmethodOn313(AvoidDeprecationBase):
    name = "no-chained-classmethod-after-313"
    priority = -1
    msgs = {
        "E9903": (
            "Chaining classmethod descriptors are deprecated."
            'Consider using __wrapped__ instead of chaining "%s".',
            "no-chained-classmethod",
            "Used when chained classmethod descriptors are detected.",
        ),
    }

    def __init__(self, linter: PyLinter) -> None:
        super().__init__(linter)
        # Only run on 3.13 and greater - the __wrapped__ alternative doesn't exist until 3.10
        self.enabled = sys.version_info[:2] >= (3, 13)

    def _check_decorator(self, attribute) -> None:
        if isinstance(attribute, nodes.FunctionDef) and attribute.decorators:
            decorator_nodes = attribute.decorators.nodes
            if len(decorator_nodes) > 1 and any(
                d.as_string() == "classmethod" for d in decorator_nodes
            ):
                for decorator_node in decorator_nodes:
                    if decorator_node.as_string() in DESCRIPTOR_NAMES:
                        self.add_message(
                            "no-chained-classmethod",
                            node=decorator_node,
                            args=(decorator_node.as_string(),),
                        )

    def visit_classdef(self, node: nodes.ClassDef) -> None:
        """Visit class definitions to find chained classmethod descriptors."""
        if self.enabled:
            for attribute in node.body:
                self._check_decorator(attribute)


def register(linter):
    linter.register_checker(AvoidChainedClassmethodOn313(linter))
