import os

from loguru import logger

from open_ah_agent.common.discord_logger import discord_logger
from open_ah_agent.tasks.agent_task import AgentTask, TaskError, TaskErrorText, TimeUtils


class BaseAgent:
    """Base class for all agents"""

    def __init__(self, name: str) -> None:
        self.name = name
        self.display = os.environ.get("DISPLAY", ":99")
        self.time_between_tasks = 10.0
        self.tasks: list[AgentTask] = []

    def run(self) -> bool:
        """Run the agent tasks"""
        task_names = [task.name for task in self.tasks]
        joined_tasks = ", ".join(task_names)

        logger.info(f"Agent {self.name} will execute tasks: {joined_tasks}")

        # Notify Discord
        discord_logger.agent_running_tasks(self.name, task_names)

        # Run all configured tasks
        for task in self.tasks:
            logger.info(f"Executing task: {task.name} in {self.time_between_tasks} seconds")
            TimeUtils.fixed_delay(self.time_between_tasks)
            success = task.execute()
            if not success:
                # Notify Discord
                discord_logger.agent_task_failed(self.name, task.name)
                raise TaskError(TaskErrorText.TASK_FAILED)

        # Notify Discord
        logger.info("All tasks completed")
        discord_logger.agent_all_tasks_completed(self.name)
        return True

    def add_task(self, task: AgentTask) -> None:
        self.tasks.append(task)

    def add_tasks(self, tasks: list[AgentTask]) -> None:
        for task in tasks:
            self.add_task(task)
