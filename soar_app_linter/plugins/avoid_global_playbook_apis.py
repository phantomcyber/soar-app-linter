import astroid
from astroid import nodes
from pylint.checkers import BaseChecker  # noqa: PH107 avoid pylint imports

from pylint.lint import PyLinter  # noqa: PH107 avoid pylint imports
from typing import Optional


class AvoidGlobalPlaybookAPIs(BaseChecker):
    """Checker to avoid usage of Playbook APIs in global scope."""

    __implements__ = BaseChecker
    priority = -1

    name = "no-global-playbook-apis"
    msgs = {
        "E0007": (
            'Usage of playbook API "%s" in global scope is not allowed, as it leads to undefined behavior within playbook runs.',
            "no-global-playbook-apis",
            "Used when a playbook API is called within global scope since it leads to undefined behavior within playbook runs",
        ),
    }

    PHANTOM_MODULE = "phantom"
    PLAYBOOK_API_SUBMODULE = "rules"
    PH_ENGINE_API_SUBMODULE = "ph_engine"
    # Playbook APIs that are 1) not REST based and 2) not calling ph_engine APIs under the hood
    ALLOWLIST_APIS = [
        "address_in_network",
        "build_phantom_rest_url",
        "concatenate",
        "get_base_url",
        "get_default_rest_headers",
        "get_phantom_home",
        "get_rest_base_url",
        "parse_errors",
        "parse_results",
        "parse_success",
        "print_errors",
        "render_template",
        "valid_ip",
        "valid_net",
    ]

    @property
    def playbook_api_module_full_path(self) -> str:
        return f"{self.PHANTOM_MODULE}.{self.PLAYBOOK_API_SUBMODULE}"

    @property
    def ph_engine_api_module_full_path(self) -> str:
        return f"{self.PHANTOM_MODULE}.{self.PH_ENGINE_API_SUBMODULE}"

    def __init__(self, linter: PyLinter) -> None:
        # To track aliases
        self.playbook_api_aliases: set[Optional[str]] = set()
        self.playbook_apis_forbidden_modules: set[str] = {
            f"{self.PHANTOM_MODULE}.{self.PLAYBOOK_API_SUBMODULE}"
        }

        self.ph_engine_api_aliases: set[Optional[str]] = set()
        self.ph_engine_forbidden_modules: set[str] = {
            f"{self.PHANTOM_MODULE}.{self.PH_ENGINE_API_SUBMODULE}"
        }
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

    def visit_import(self, node: nodes.Import) -> None:
        """Parse aliases of phantom module, playbook api submodule and ph_engine submodule from import statements."""
        for module_name, alias in node.names:
            # e.g import phantom as alias_phantom
            if module_name == self.PHANTOM_MODULE and alias:
                self.ph_engine_forbidden_modules.add(
                    f"{alias}.{self.PH_ENGINE_API_SUBMODULE}"
                )
                self.playbook_apis_forbidden_modules.add(
                    f"{alias}.{self.PLAYBOOK_API_SUBMODULE}"
                )

            # e.g import phantom.rules as phantom
            if module_name == self.playbook_api_module_full_path:
                if alias:
                    self.playbook_api_aliases.add(alias)
            if module_name == self.ph_engine_api_module_full_path:
                if alias:
                    self.ph_engine_api_aliases.add(alias)

    def visit_importfrom(self, node: nodes.ImportFrom) -> None:
        """Track playbook api and ph_engine submodule and their aliases from import-from statements."""
        module_name = node.modname
        if module_name != self.PHANTOM_MODULE:
            return

        submodules = node.names
        for submodule_name, alias in submodules:
            if submodule_name == self.PLAYBOOK_API_SUBMODULE:
                self.playbook_api_aliases.add(alias or submodule_name)

            if submodule_name == self.PH_ENGINE_API_SUBMODULE:
                self.ph_engine_api_aliases.add(alias or submodule_name)

    def visit_call(self, node: nodes.Call) -> None:
        """Check for any method calls from phantom library and its submodules at module level"""
        if not self._is_module_level(node):
            return

        try:
            func = node.func
            if func.attrname:
                module = func.expr.as_string()

                # Check if the module is forbidden
                if (
                    module in self.ph_engine_forbidden_modules
                    or module in self.ph_engine_api_aliases
                ):
                    self.add_message(
                        "no-global-playbook-apis",
                        node=node,
                        args=(func.as_string(),),
                    )

                if (
                    module in self.playbook_apis_forbidden_modules
                    or module in self.playbook_api_aliases
                ):
                    if func.attrname not in self.ALLOWLIST_APIS:
                        self.add_message(
                            "no-global-playbook-apis",
                            node=node,
                            args=(func.as_string(),),
                        )

        except AttributeError:
            # Skip the nodes that do not have expected attributes
            pass


def register(linter):
    linter.register_checker(AvoidGlobalPlaybookAPIs(linter))
