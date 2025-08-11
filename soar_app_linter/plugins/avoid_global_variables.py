import astroid
from astroid import nodes
from pylint.checkers import BaseChecker  # noqa: PH107 avoid pylint imports

from pylint.lint import PyLinter  # noqa: PH107 avoid pylint imports


class AvoidGlobalVars(BaseChecker):
    """Checker to avoid global variables updates in non-module scope."""

    __implements__ = BaseChecker
    priority = -1

    name = "no-globals"
    msgs = {
        "E0006": (
            'Updating global variable "%s" once created is not allowed, as it leads to undefined behavior within playbook runs.',
            "no-global-updates",
            "Used when a global variable is updated other than the initial creation since it leads to undefined behavior within playbook runs",
        ),
    }
    MUTABLE_TYPES = (astroid.List, astroid.Dict, astroid.Set)
    MUTATE_METHODS = {
        "append",
        "extend",
        "insert",
        "remove",
        "pop",
        "clear",
        "sort",
        "reverse",
        "add",
        "discard",
        "update",
        "intersection_update",
        "difference_update",
        "symmetric_difference_update",
        "__setitem__",
        "setdefault",
        "popitem",
    }

    def __init__(self, linter: PyLinter) -> None:
        self.mutable_globals: set[str] = set()
        self.current_globals: set[str] = set()
        super().__init__(linter)

    def _is_module_level(self, node: nodes.NodeNG) -> bool:
        """Traverse up the tree to determine if the node is at module level"""
        parent = node.parent
        if isinstance(parent, astroid.scoped_nodes.Module):
            return True
        elif isinstance(
            parent, (astroid.scoped_nodes.ClassDef, astroid.scoped_nodes.FunctionDef)
        ):
            return False
        # Otherwise, follow parent(parent could be an if condition, for loop,..etc)
        return self._is_module_level(parent)

    def _is_nonstatic_condition(self, condition_node: nodes.NodeNG) -> bool:
        """Traverse up the tree to determine if the condition contains function call"""
        if not condition_node:
            return False

        if isinstance(condition_node, astroid.Call):
            return True

        for operand in condition_node.get_children():
            if self._is_nonstatic_condition(operand):
                return True

        return False

    def _is_within_non_static_condition_if_while(self, node: nodes.NodeNG) -> bool:
        """Traverse up the tree to determine if the node is within if or while statement with non-static condition"""
        current = node
        while current:
            if isinstance(current, (astroid.If, astroid.While)):
                if self._is_nonstatic_condition(current.test):
                    return True
            current = current.parent
        return False

    def _check_valid_update(self, node: nodes.NodeNG, node_name: str) -> None:
        if self._is_module_level(node):
            if self._is_within_non_static_condition_if_while(node):
                self.add_message("no-global-updates", node=node, args=node_name)
        else:
            if node_name in self.current_globals or node_name in self.mutable_globals:
                self.add_message("no-global-updates", node=node, args=node_name)

    def visit_assign(self, node: nodes.Assign) -> None:
        """Check for reassignments of globals once created"""
        if self._is_module_level(node):
            for target in node.targets:
                if isinstance(target, astroid.AssignName):
                    if self._is_within_non_static_condition_if_while(target):
                        # To prevent unpredictable update at module level
                        self.add_message(
                            "no-global-updates", node=node, args=target.name
                        )
                    else:
                        if isinstance(node.value, self.MUTABLE_TYPES):
                            self.mutable_globals.add(target.name)
        else:
            for target in node.targets:
                if isinstance(target, astroid.AssignName) and (
                    target.name in self.mutable_globals
                    or target.name in self.current_globals
                ):
                    # Update at non-module level is not valid when
                    # 1) The variable is mutable and defined in global scope
                    # 2) The variable is immutable and the global keyword is used to modify the global variable
                    self.add_message("no-global-updates", node=node, args=target.name)

    def visit_call(self, node: nodes.Call) -> None:
        """Check for any method calls are made on global variables(e.g., dict.update)"""
        if isinstance(node.func, astroid.Attribute):
            if (
                isinstance(node.func.expr, astroid.Name)
                and node.func.attrname in self.MUTATE_METHODS
            ):
                self._check_valid_update(node.func, node.func.expr.name)

    def visit_augassign(self, node: nodes.AugAssign) -> None:
        """Check for augmented assignments (e.g., +=, -=, etc.) to global variables"""
        if isinstance(node.target, astroid.AssignName):
            self._check_valid_update(node, node.target.name)

    def visit_subscript(self, node: nodes.Subscript) -> None:
        """Check for subscript assignments (e.g., dict["key"] = value, list[index] = value) on global variables"""
        if isinstance(node.value, astroid.Name) and str(node.ctx) == "Context.Store":
            self._check_valid_update(node, node.value.name)

    def visit_global(self, node: nodes.Global) -> None:
        """Track the global declarations in the current scope"""
        self.current_globals.update(node.names)

    def visit_functiondef(self, node: nodes.FunctionDef) -> None:
        """Reset the current globals for each function scope"""
        self.current_globals = set()


def register(linter):
    linter.register_checker(AvoidGlobalVars(linter))
