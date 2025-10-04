import random
import time

from lotkeeper_agent.tasks.agent_task import DEFAULT_DELAY, KEY_DELAY


class SleepUtil:
    """Utility class for managing sleep delays and timing in agent tasks.

    This class provides various static methods for implementing different types of delays
    during task execution, including random delays within ranges and fixed delays.

    Methods:
        sleep_default(): Sleep for a random duration within DEFAULT_DELAY range
        sleep_fixed(delay): Sleep for a specific fixed duration
        sleep_between_range(delay): Sleep for a random duration within a custom range
        sleep_keypress_duration(): Sleep for a random duration within KEY_DELAY range
    """

    @staticmethod
    def sleep_default() -> None:
        """Sleep for a random amount of time between the DEFAULT_DELAY range.

        This provides a natural, randomized delay that helps avoid detection patterns.
        """
        time.sleep(random.uniform(DEFAULT_DELAY[0], DEFAULT_DELAY[1]))

    @staticmethod
    def sleep_fixed(delay: float) -> None:
        """Sleep for a specific, fixed amount of time.

        Args:
            delay: The exact number of seconds to sleep

        Note:
            Use this when you need precise timing control
        """
        time.sleep(delay)

    @staticmethod
    def sleep_between_range(delay: tuple[float, float]) -> None:
        """Sleep for a random amount of time within a custom delay range.

        Args:
            delay: A tuple of (min_seconds, max_seconds) defining the sleep range
        """
        time.sleep(random.uniform(delay[0], delay[1]))

    @staticmethod
    def sleep_keypress_duration() -> None:
        """Sleep for a random amount of time within the KEY_DELAY range.

        This is a shorter delay than sleep_default() and is suitable for simulating human-like keypress timing.
        """
        time.sleep(random.uniform(KEY_DELAY[0], KEY_DELAY[1]))
