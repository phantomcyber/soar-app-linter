from pylint.checkers import BaseChecker  # noqa: PH107 avoid pylint imports


from .banned_functions import BannedFunctions


class AvoidFilesystemAccess(BannedFunctions):
    __implements__ = BaseChecker

    name = "avoid-filesystem-access"

    BANNED_FUNCTIONS_MAP = {
        "open": set(),  # this is a little jank, but it's for the raw open() function
        "os": {
            "access",
            "chdir",
            "chflags",
            "chmod",
            "chown",
            "chroot",
            "fchdir",
            "fwalk",
            "get_exec_path",
            "getcwd",
            "getcwdb",
            "lchflags",
            "lchmod",
            "lchown",
            "link",
            "listdir",
            "lstat",
            "major",
            "makedirs",
            "minor",
            "mkdev",
            "mkdir",
            "mkfifo",
            "mknod",
            "open",
            "pathconf",
            "readlink",
            "remove",
            "rename",
            "renames",
            "replace",
            "rmdir",
            "scandir",
            "stat",
            "statvfs",
            "symlink",
            "sync",
            "unlink",
            "utime",
            "walk",
        },
        "pathlib.Path": {
            "absolute",
            "chmod",
            "cwd",
            "exists",
            "expanduser",
            "glob",
            "group",
            "hardlink_to",
            "home",
            "is_block_device",
            "is_char_device",
            "is_dir",
            "is_fifo",
            "is_file",
            "is_mount",
            "is_socket",
            "is_symlink",
            "iterdir",
            "lchmod",
            "lstat",
            "mkdir",
            "open",
            "owner",
            "read_bytes",
            "read_text",
            "readlink",
            "rename",
            "replace",
            "resolve",
            "rglob",
            "rmdir",
            "samefile",
            "stat",
            "symlink_to",
            "touch",
            "unlink",
            "walk",
            "write_bytes",
            "write_text",
        },
        "shutil": {
            "chown",
            "copy",
            "copy2",
            "copyfile",
            "copyfileobj",
            "copymode",
            "copystat",
            "copytree",
            "diskusage",
            "make_archive",
            "move",
            "rmtree",
            "unpack_archive",
            "which",
        },
        "tempfile": {
            "NamedTemporaryFile",
            "SpooledTemporaryFile",
            "TemporaryDirectory",
            "TemporaryFile",
            "gettempdir",
            "gettempdirb",
            "gettempprefix",
            "gettempprefixb",
            "mkdtemp",
            "mkstemp",
        },
    }

    priority = -1
    msgs = {
        "W0006": (
            "Accessing the filesystem is not recommended.",
            "no-filesystem-access",
            "Accessing the filesystem is not recommended.",
        ),
    }

    MESSAGE = "no-filesystem-access"

def register(linter):
    linter.register_checker(AvoidFilesystemAccess(linter))
