from astroid import nodes
from pylint.checkers import BaseChecker  # avoid pylint imports
from pylint.lint import PyLinter  # avoid pylint imports


class AvoidDeprecationBase(BaseChecker):
    __implements__ = BaseChecker

    def __init__(self, linter: PyLinter) -> None:
        super().__init__(linter)
        # the aliases are sets because in python its valid to import a library more than once
        self.alias_map: dict[str, str] = {}
        self.enabled = True

    def visit_import(self, node: nodes.Import) -> None:
        if not self.enabled:
            return

        # build alias map
        for name, alias in node.names:
            self.alias_map[alias or name] = name

    def visit_importfrom(self, node: nodes.ImportFrom) -> None:
        if not self.enabled:
            return

        # build alias map
        module_name = node.modname
        for name, alias in node.names:
            full_name = f"{module_name}.{name}"
            self.alias_map[alias or name] = full_name

    def visit_assign(self, node: nodes.Assign) -> None:
        for target_node in node.targets:
            node_value = self._resolve_full_name(node.value)

            if isinstance(target_node, nodes.AssignName):
                self.alias_map[target_node.name] = node_value if node_value else target_node.name
            elif isinstance(target_node, nodes.AssignAttr):
                self.alias_map[target_node.as_string()] = node_value

    def _resolve_full_name(self, node) -> str:
        """Resolve the full module path for a node."""
        if isinstance(node, nodes.Name):
            return self.alias_map.get(node.name, node.name)
        elif isinstance(node, nodes.Attribute):
            # Recursively resolve the full name for chained attributes
            base_name = self._resolve_full_name(node.expr)

            return f"{base_name}.{node.attrname}" if base_name else node.attrname
        elif isinstance(node, nodes.Call):
            # Handle the case where the node is a call to a class to create an instance
            return self._resolve_full_name(node.func)
        return ""

def register(linter):
    linter.register_checker(AvoidDeprecationBase(linter))
