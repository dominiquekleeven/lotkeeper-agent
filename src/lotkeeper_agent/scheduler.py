import os
import time
from datetime import datetime

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from lotkeeper_agent.agents.base_agent import AgentError, BaseAgent
from lotkeeper_agent.common.discord_logger import discord_logger
from lotkeeper_agent.common.logging import propagate_logs
from lotkeeper_agent.tasks.agent_task import TaskError


class AgentScheduler:
    """Manages the scheduling of agent tasks."""

    def __init__(self, time_between_retries: int = 300) -> None:
        """
        Args:
            time_between_retries: Time to wait between retries in seconds
        """
        self.time_between_retries = time_between_retries
        jobstores = {"default": MemoryJobStore()}
        executors = {"default": ThreadPoolExecutor(max_workers=1)}

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            daemon=True,
            coalesce=True,
            max_instances=1,
            job_defaults={"misfire_grace_time": 3600},
        )
        propagate_logs()

    def start(self) -> None:
        if self.scheduler.running:
            logger.warning("Agent scheduler already running")
            return

        self.scheduler.start()

        # Log jobs after starting
        for job in self.scheduler.get_jobs():
            logger.info(f"Job: {job.name} (next run: {job.next_run_time or 'None'})")
            discord_logger.agent_scheduled(job.name, job.next_run_time or None)

    def stop(self) -> None:
        self.scheduler.shutdown()
        logger.info("Agent scheduler stopped")

    def is_running(self) -> bool:
        return bool(self.scheduler.running)

    def add_agent(self, agent: BaseAgent) -> None:
        job_id = f"agent_{agent.name}"
        cron_expr = agent.cron_expression.value
        max_retries = agent.max_retries

        # create job trigger from cron expression
        trigger = CronTrigger.from_crontab(cron_expr)

        self.scheduler.add_job(
            func=self._run_agent_with_retries,
            trigger=trigger,
            args=[job_id, agent, max_retries],
            id=job_id,
            name=f"Agent: {agent.name}",
            replace_existing=True,
            jitter=120,
        )

        logger.info(f"Added agent '{agent.name}' to scheduler ({cron_expr}, max {max_retries} retries)")

    def get_job_next_run_time(self, job_id: str) -> datetime | None:
        job = self.scheduler.get_job(job_id)
        return job.next_run_time if job else None

    def _run_agent_with_retries(self, job_id: str, agent: BaseAgent, max_retries: int) -> None:
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Running agent '{agent.name}' (attempt {attempt + 1}/{max_retries + 1})")
                discord_logger.agent_running(agent.name, agent.get_task_names())

                # Set display to allow agents to interact with X11
                if "DISPLAY" not in os.environ:
                    os.environ["DISPLAY"] = ":99"

                # track agent time
                agent_start_time = time.time()
                agent.start()

                # log completion and send to discord
                logger.info(f"Agent '{agent.name}' completed successfully")
                agent_duration = round(time.time() - agent_start_time, 2)
                next_run_time = self.get_job_next_run_time(job_id)
                discord_logger.agent_all_tasks_completed(agent.name, agent_duration, next_run_time)
                return

            except (TaskError, AgentError, Exception) as e:
                logger.exception(f"Agent '{agent.name}' failed on attempt {attempt + 1}: {e}")

                # Log specific error types to Discord
                if isinstance(e, TaskError):
                    discord_logger.agent_task_error(agent.name, e.task_name, str(e))
                elif isinstance(e, AgentError) or isinstance(e, Exception):
                    discord_logger.agent_error(agent.name, str(e))

                if attempt < max_retries:
                    logger.info(f"Retrying agent '{agent.name}' in {self.time_between_retries} seconds...")
                    discord_logger.agent_rescheduled(agent.name, self.time_between_retries)
                    time.sleep(self.time_between_retries)
                else:
                    logger.error(f"Agent '{agent.name}' failed after {max_retries + 1} attempts")
                    discord_logger.agent_error_max_retries(agent.name, str(e), max_retries)
