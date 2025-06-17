import sys
from astroid import nodes
from pylint.lint import PyLinter  # avoid pylint imports
from .avoid_deprecation_base import AvoidDeprecationBase

REMOVED_MODULES: set[str] = {
    "distutils",
    "formatter",
    "parser",
    "binhex",
    "imp",
    "asynchat",
    "asyncore",
    "mailcap",
}

REMOVED_CLASSES: dict[str, set[str]] = {
    "pkgutil": {"ImpLoader", "ImpImporter"},
    "importlib.abc": {"Finder"},
    "asyncio.coroutines": {"CoroWrapper"},
    "configparser": {"SafeConfigParser", "LegacyInterpolation"},
}

REMOVED_METHODS: dict[str, set[str]] = {
    "importlib.util": {"set_package", "module_for_loader", "set_loader"},
    "re": {"template"},
    "configparser.RawConfigParser": {"readfp"},
    "pathlib.PurePath": {"__class_getitem__"},
    "pathlib.Path": {"link_to"},
    "ssl": {"RAND_pseudo_bytes", "RAND_egd", "wrap_socket", "match_hostname"},
}

REMOVED_ATTRIBUTES: dict[str, set[str]] = {
    "re": {"TEMPLATE", "T"},
    "typing": {"io", "re"},
    "configparser.ParsingError": {"filename"},
}

REMOVED_DECORATORS: dict[str, set[str]] = {
    "asyncio": {"coroutine"},
}


class Avoid313RemovalsOn39(AvoidDeprecationBase):
    name = "no-313-removals-on-39"
    priority = -1
    msgs = {
        "W9904": (
            'Stop using method "%s" from library "%s" to aid in migration to Python 3.13 where it is removed.',
            "no-313-removed-method",
            "Used when a Python 3.13 unsupported method is detected.",
        ),
        "W9905": (
            'Stop using module "%s" to aid in migration to Python 3.13 where it is removed.',
            "no-313-removed-module",
            "Used when a Python 3.13 removed module is detected in the imports.",
        ),
        "W9906": (
            'Stop using attribute "%s" from module "%s" to aid in migration to Python 3.13 where it is removed.',
            "no-313-removed-attribute",
            "Used when a Python 3.13 removed attribute is detected.",
        ),
        "W9907": (
            'Stop using class "%s" from module "%s" to aid in migration to Python 3.13 where it is removed.',
            "no-313-removed-class",
            "Used when a Python 3.13 removed class is detected.",
        ),
        "W9908": (
            'Stop using decorator "%s" from module "%s" to aid in migration to Python 3.13 where it is removed.',
            "no-313-removed-decorator",
            "Used when a Python 3.13 removed decorator is detected.",
        ),
    }

    def __init__(self, linter: PyLinter) -> None:
        super().__init__(linter)
        self.enabled = sys.version_info[:2] == (3, 9)

    def visit_import(self, node: nodes.Import) -> None:
        if not self.enabled:
            return

        super().visit_import(node)

        for name, _ in node.names:
            if name in REMOVED_MODULES:
                self.add_message("no-313-removed-module", node=node, args=(name,))

    def visit_importfrom(self, node: nodes.ImportFrom) -> None:
        if not self.enabled:
            return

        super().visit_importfrom(node)

        module_name = node.modname
        if module_name in REMOVED_MODULES:
            self.add_message("no-313-removed-module", node=node, args=(module_name,))

        for name, _ in node.names:
            full_name = f"{module_name}.{name}"

            if full_name in REMOVED_MODULES:
                self.add_message("no-313-removed-module", node=node, args=(full_name,))

            if module_name in REMOVED_ATTRIBUTES and name in REMOVED_ATTRIBUTES[module_name]:
                self.add_message("no-313-removed-attribute", node=node, args=(name, module_name))

            if module_name in REMOVED_METHODS and name in REMOVED_METHODS[module_name]:
                self.add_message("no-313-removed-method", node=node, args=(name, module_name))

            if module_name in REMOVED_CLASSES and name in REMOVED_CLASSES[module_name]:
                self.add_message("no-313-removed-class", node=node, args=(name, module_name))

    def visit_call(self, node: nodes.Call) -> None:
        if not self.enabled:
            return

        self._check_method(node)
        self._check_class(node)

    def visit_attribute(self, node: nodes.Attribute) -> None:
        if not self.enabled:
            return

        self._check_attribute(node)

    def visit_classdef(self, node: nodes.ClassDef) -> None:
        if not self.enabled:
            return

        if node.bases:
            for base_node in node.bases:
                self._check_class(base_node)

    def visit_functiondef(self, node: nodes.FunctionDef) -> None:
        if not self.enabled:
            return

        if node.decorators:
            for decorator_node in node.decorators.nodes:
                self._check_decorator(decorator_node)

    def _check_method(self, node) -> None:
        module_name = self._resolve_full_name(node)
        method_name = module_name.split(".")[-1]
        for library, methods in REMOVED_METHODS.items():
            if module_name.startswith(library) and method_name in methods:
                self.add_message("no-313-removed-method", node=node, args=(method_name, library))

    def _check_attribute(self, node) -> None:
        module_name = self._resolve_full_name(node)
        attr_name = module_name.split(".")[-1]
        for module, attributes in REMOVED_ATTRIBUTES.items():
            if module_name.startswith(module) and attr_name in attributes:
                self.add_message("no-313-removed-attribute", node=node, args=(attr_name, module))

    def _check_class(self, node) -> None:
        module_name = self._resolve_full_name(node)
        class_name = module_name.split(".")[-1]
        for module, classes in REMOVED_CLASSES.items():
            if module_name.startswith(module) and class_name in classes:
                self.add_message("no-313-removed-class", node=node, args=(class_name, module))

    def _check_decorator(self, node) -> None:
        module_name = self._resolve_full_name(node)
        decorator_name = module_name.split(".")[-1]
        for module, decorators in REMOVED_DECORATORS.items():
            if module_name.startswith(module) and decorator_name in decorators:
                self.add_message(
                    "no-313-removed-decorator", node=node, args=(decorator_name, module)
                )

def register(linter):
    linter.register_checker(Avoid313RemovalsOn39(linter))
