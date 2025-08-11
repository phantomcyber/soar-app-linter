"""Main module that imports from utils to test imports."""

from . import utils


def main() -> None:
    """Main function that uses the imported module."""
    print(f"Constant value: {utils.CONSTANT_VALUE}")
    print(utils.helper_function())


if __name__ == "__main__":
    main()
