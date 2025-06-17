"""A module that uses random.sample() to trigger our custom plugin."""
import random

def trigger_random_sample() -> list[int]:
    """Use random.sample() which should trigger our custom plugin.

    Note: This will trigger the 'consider-random-sample-sequence' warning
    from our custom plugin.
    """
    numbers = {1, 2, 3, 4, 5}  # Using a set which will trigger the warning
    return random.sample(numbers, 2)  # This should trigger the warning
