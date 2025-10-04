from abc import ABC, abstractmethod

# Sensible defaults
KEY_DELAY: tuple[float, float] = (0.5, 1.1)
DEFAULT_DELAY: tuple[float, float] = (2, 4)


class TaskError(Exception):
    """Exception raised when a task fails"""

    def __init__(self, task_name: str, message: str) -> None:
        self.task_name = task_name
        self.message = message

    def __str__(self) -> str:
        return f"{self.task_name}: {self.message}"


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
