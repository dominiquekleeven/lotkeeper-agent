import random
import time
from abc import ABC, abstractmethod
from enum import Enum

from loguru import logger

# Sensible defaults
TYPING_DELAY: tuple[float, float] = (0.05, 0.15)
KEY_DELAY: tuple[float, float] = (0.3, 0.5)
DEFAULT_DELAY: tuple[float, float] = (2, 4)


class TaskError(Exception):
    pass


class TaskErrorText(Enum):
    COULD_NOT_FIND_WINDOW = "Unable to find the WoW window"
    COULD_NOT_FOCUS_WINDOW = "Unable to focus the WoW window"
    COULD_NOT_START = "Unable to start the task"
    COULD_NOT_DETECT_TEXT = "Unable to detect text"
    PRECHECK_FAILURE = "Pre-check failed, not all requirements were met"
    UNEXPECTED_ERROR = "An unexpected error occurred"
    TASK_FAILED = "Task failed"


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
        logger.info(f"Executing task: {self.name}")
        try:
            result = self.run()
            logger.info(f"Completed task: {self.name}, success: {result}")
            return result
        except Exception as e:
            logger.error(f"Error occurred in task: {self.name}: {e}")
            return False
