from pylint.checkers import BaseChecker  # noqa: PH107 avoid pylint imports


from .banned_functions import BannedFunctions


class AvoidShellAccess(BannedFunctions):
    __implements__ = BaseChecker

    name = "avoid-shell-access"

    BANNED_FUNCTIONS_MAP = {
        "subprocess": {
            "run",
            "call",
            "check_call",
            "check_output",
        },
        "subprocess.Popen": set(),
        "os": {
            "system",
            "popen",
            "posix_spawn",
            "posix_spawnp",
            "spawnl",
            "spawnle",
            "spawnlp",
            "spawnlpe",
            "spawnv",
            "spawnve",
            "spawnvp",
            "spawnvpe",
            "startfile",
        },
        "phantom_common.phproc": {
            "run",
        },
        "phantom_common.phproc.Process": set(),
    }

    priority = -1
    msgs = {
        "W0007": (
            "Shell access is not recommended.",
            "no-shell-access",
            "Shell access is not recommended.",
        ),
    }

    MESSAGE = "no-shell-access"

def register(linter):
    linter.register_checker(AvoidShellAccess(linter))
