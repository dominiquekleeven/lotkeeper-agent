import os
import subprocess
import time
from abc import ABC, abstractmethod

from loguru import logger

from openah_agent.common.discord_logger import discord_logger
from openah_agent.tasks.agent_task import AgentTask, TaskError, TimeUtils


class AgentError(Exception):
    """Exception raised when an agent fails"""

    def __init__(self, agent_name: str, message: str) -> None:
        self.agent_name = agent_name
        self.message = message

    def __str__(self) -> str:
        return f"{self.agent_name}: {self.message}"


INTERVAL_HOURS = 1  # TODO: Use cron for interval
MAX_RETRIES = 1
TIME_BETWEEN_TASKS = 10.0

class BaseAgent(ABC):
    """
    Base Agent, provides a base class for all agents.

    Args:
        name: The name of the agent

    Use settings() for configuration
    """

    def __init__(self, name: str) -> None:
        # Agent settings
        self.name = name
        self.display = os.environ.get("DISPLAY", ":99")
        self._tasks: list[AgentTask] = []
        self.window_process: subprocess.Popen[bytes] | None = None

        # Schedule and retry settings
        self.interval_hours = INTERVAL_HOURS
        self.max_retries = MAX_RETRIES
        self.time_between_tasks = TIME_BETWEEN_TASKS

    def with_interval_hours(self, interval_hours: int) -> "BaseAgent":
        """
        Set the interval between agent runs in hours
        
        Args:
            interval_hours: Interval between agent runs in hours (must be positive)
            
        Returns:
            self for method chaining
        """
        if interval_hours <= 0:
            raise ValueError("interval_hours must be positive")
        self.interval_hours = interval_hours
        return self

    def with_max_retries(self, max_retries: int) -> "BaseAgent":
        """
        Set the maximum number of retries for failed operations
        
        Args:
            max_retries: Maximum number of retries (must be non-negative)
            
        Returns:
            self for method chaining
        """
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        self.max_retries = max_retries
        return self

    def with_time_between_tasks(self, time_between_tasks: float) -> "BaseAgent":
        """
        Set the time to wait between tasks in seconds
        
        Args:
            time_between_tasks: Time to wait between tasks (must be non-negative)
            
        Returns:
            self for method chaining
        """
        if time_between_tasks < 0:
            raise ValueError("time_between_tasks must be non-negative")
        self.time_between_tasks = time_between_tasks
        return self

    def add_task(self, task: AgentTask) -> "BaseAgent":
        """
        Add a single task to the agent
        
        Args:
            task: The task to add
            
        Returns:
            self for method chaining
        """
        self._tasks.append(task)
        return self

    def add_tasks(self, tasks: list[AgentTask]) -> "BaseAgent":
        """
        Add multiple tasks to the agent
        
        Args:
            tasks: List of tasks to add
            
        Returns:
            self for method chaining
        """
        for task in tasks:
            self._tasks.append(task)
        return self

    def get_task_names(self) -> list[str]:
        return [task.name for task in self._tasks]

    @abstractmethod
    def setup(self) -> None:
        """Setup the agent"""

    @abstractmethod
    def teardown(self) -> None:
        """Teardown the agent"""

    def start(self) -> None:
        """Start the agent"""
        try:
            self.setup()
            self._run()
        except TaskError as e:
            raise e
        except Exception as e:
            raise e
        finally:
            self.teardown()

    def _run(self) -> None:
        for task in self._tasks:
            logger.info(f"Executing task: {task.name} in {self.time_between_tasks} seconds")

            # Wait between tasks to give the agent a chance to settle
            TimeUtils.fixed_delay(self.time_between_tasks)

            # Notify discord that the task has started
            discord_logger.agent_task_started(self.name, task.name)

            # Execute the task
            task_start_time = time.time()  # Task start time
            task.execute()

            # Time the task
            task_end_time = time.time()  # Task end time
            task_duration = round(task_end_time - task_start_time, 2)
            logger.info(f"Task {task.name} completed in {task_duration} seconds")

            # Notify discord that the task has completed
            discord_logger.agent_task_completed(self.name, task.name, task_duration)
