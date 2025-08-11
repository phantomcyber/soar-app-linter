from astroid import nodes
from .avoid_deprecation_base import AvoidDeprecationBase


class Avoid313RandomDeprecationsOnAll(AvoidDeprecationBase):
    name = "no-313-random-deprecations-on-all"
    priority = -1
    msgs = {
        "I9900": (
            'The "population" parameter of "random.sample()" must be a sequence (e.g. a list) on Python 3.13. On Python 3.9, non-sequences (e.g. a set) were automatically converted to a list, but on Python 3.13 will raise a TypeError. Please confirm your inputs are correct on migration to Python 3.13.',
            "consider-random-sample-sequence",
            "Warns about potential issues with random.sample() usage.",
        ),
        "I9901": (
            'Arguments to "random.randrange()" must be ints on Python 3.13. On Python 3.9, non-integers (e.g floats) were automatically converted an int, but on Python 3.13 will raise a TypeError. Please confirm your inputs are correct on migration to Python 3.13.',
            "consider-random-randrange-integer-args",
            "Warns about potential issues with random.randrange() usage.",
        ),
        "W9902": (
            'Stop using the parameter "random" of "random.shuffle()" to aid in migration to Python 3.13 where it is removed.',
            "no-random-shuffle-random-param",
            "Warns about issues with random.shuffle() usage.",
        ),
    }

    def visit_call(self, node: nodes.Call) -> None:
        module_name = self._resolve_full_name(node)
        if module_name.startswith("random."):
            method_name = module_name.split(".")[-1]
            if method_name == "sample":
                self.add_message("consider-random-sample-sequence", node=node)
            elif method_name == "randrange":
                self.add_message("consider-random-randrange-integer-args", node=node)
            elif method_name == "shuffle":
                self._check_random_shuffle(node)

    def _check_random_shuffle(self, node: nodes.Call):
        # Check for the second positional argument
        if len(node.args) > 1:
            self.add_message("no-random-shuffle-random-param", node=node)

        # Check for the 'random' keyword argument
        if any(kw.arg == "random" for kw in node.keywords):
            self.add_message("no-random-shuffle-random-param", node=node)


def register(linter):
    linter.register_checker(Avoid313RandomDeprecationsOnAll(linter))
