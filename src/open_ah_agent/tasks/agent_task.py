import random
import time
from abc import ABC, abstractmethod

# Sensible defaults
TYPING_DELAY: tuple[float, float] = (0.05, 0.15)
KEY_DELAY: tuple[float, float] = (0.3, 0.5)
DEFAULT_DELAY: tuple[float, float] = (2, 4)


class TaskError(Exception):
    """Exception raised when a task fails"""

    def __init__(self, task_name: str, message: str) -> None:
        self.task_name = task_name
        self.message = message

    def __str__(self) -> str:
        return f"{self.task_name}: {self.message}"


class TimeUtils:
    @staticmethod
    def delay() -> None:
        """Sleep for a random amount of time between the DEFAULT_DELAY"""
        time.sleep(random.uniform(DEFAULT_DELAY[0], DEFAULT_DELAY[1]))

    @staticmethod
    def fixed_delay(delay: float) -> None:
        """Sleep for a specific amount of time"""
        time.sleep(delay)

    @staticmethod
    def range_delay(delay: tuple[float, float]) -> None:
        """Sleep for a random amount of time between the custom delay range"""
        time.sleep(random.uniform(delay[0], delay[1]))

    @staticmethod
    def key_delay() -> None:
        """Sleep for a random amount of time between the KEY_DELAY"""
        time.sleep(random.uniform(KEY_DELAY[0], KEY_DELAY[1]))

    @staticmethod
    def type_delay() -> None:
        """Sleep for a random amount of time between the TYPING_DELAY"""
        time.sleep(random.uniform(TYPING_DELAY[0], TYPING_DELAY[1]))


class AgentTask(ABC):
    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    @abstractmethod
    def run(self) -> bool:
        """Method to be implemented by the subclass to run the task"""
        pass

    def execute(self) -> bool:
        """Execute the task"""
        result = self.run()
        return result
