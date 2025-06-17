"""A simple module that should pass all linting checks."""

def add(a: int, b: int) -> int:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        The sum of a and b
    """
    return a + b


if __name__ == "__main__":
    print(add(2, 3))  # Should print 5
