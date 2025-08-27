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


class BaseAgent(ABC):
    """
    Base Agent, provides a base class for all agents.
    """

    def __init__(self, name: str, interval_hours: int = 1, max_retries: int = 3) -> None:
        self.name = name
        self.display = os.environ.get("DISPLAY", ":99")
        self.interval_hours = interval_hours
        self.max_retries = max_retries
        self.time_between_tasks = 10.0
        self._tasks: list[AgentTask] = []
        self.window_process: subprocess.Popen[bytes] | None = None

    def add_task(self, task: AgentTask) -> None:
        self._tasks.append(task)

    def add_tasks(self, tasks: list[AgentTask]) -> None:
        for task in tasks:
            self.add_task(task)

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
            # Ensure display is set for the current thread context
            self.display = os.environ.get("DISPLAY", ":99")
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
