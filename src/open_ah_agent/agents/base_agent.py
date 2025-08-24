import os
import subprocess
import time
from abc import ABC, abstractmethod

from loguru import logger

from open_ah_agent.common.discord_logger import discord_logger
from open_ah_agent.tasks.agent_task import AgentTask, TaskError, TimeUtils


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

    def __init__(self, name: str) -> None:
        self.name = name
        self.display = os.environ.get("DISPLAY", ":99")
        self.time_between_tasks = 10.0
        self._tasks: list[AgentTask] = []
        self.window_process: subprocess.Popen[bytes] | None = None

    def add_task(self, task: AgentTask) -> None:
        self._tasks.append(task)

    def add_tasks(self, tasks: list[AgentTask]) -> None:
        for task in tasks:
            self.add_task(task)

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
            logger.error(f"A task error occurred while running tasks: {e}")
            discord_logger.agent_task_failed(self.name, e.task_name, str(e))
        except Exception as e:
            logger.error(f"An unexpected error occurred while running tasks: {e}")
            discord_logger.agent_error(self.name, str(e))
        finally:
            self.teardown()

    def _run(self) -> None:
        task_names = [task.name for task in self._tasks]
        joined_tasks = ", ".join(task_names)

        logger.info(f"Agent {self.name} will execute tasks: {joined_tasks}")
        discord_logger.agent_running_tasks(self.name, task_names)

        # Run all configured tasks
        agent_start_time = time.time()  # Agent start time
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

        # Time the agent
        agent_end_time = time.time()
        agent_duration = round(agent_end_time - agent_start_time, 2)
        logger.info(f"Agent {self.name} completed all tasks in {agent_duration} seconds")

        # Notify discord once all tasks are completed
        discord_logger.agent_all_tasks_completed(self.name, agent_duration)
