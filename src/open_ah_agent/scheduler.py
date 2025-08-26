# Copyright 2025, OpenRemote Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import time
from datetime import datetime

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from open_ah_agent.agents.base_agent import AgentError, BaseAgent
from open_ah_agent.common.discord_logger import discord_logger
from open_ah_agent.common.logging import propagate_logs
from open_ah_agent.tasks.agent_task import TaskError

TIME_BETWEEN_RETRIES = 300


class AgentScheduler:
    """Manages the scheduling of agent tasks."""

    def __init__(self) -> None:
        jobstores = {"default": MemoryJobStore()}
        executors = {"default": ThreadPoolExecutor(max_workers=1)}

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            daemon=True,
            coalesce=True,
            max_instances=1,
            job_defaults={"misfire_grace_time": 600},
        )
        propagate_logs()

    def start(self) -> None:
        if self.scheduler.running:
            logger.warning("Agent scheduler already running")
            return

        self.scheduler.start()

    def stop(self) -> None:
        self.scheduler.shutdown()
        logger.info("Agent scheduler stopped")

    def is_running(self) -> bool:
        return bool(self.scheduler.running)

    def add_agent(self, agent: BaseAgent, run_immediately: bool = False) -> None:
        job_id = f"agent_{agent.name}_{int(time.time())}"

        interval_hours = agent.interval_hours
        max_retries = agent.max_retries

        # Schedule the agent to run every interval_hours
        job_kwargs = {
            "func": self._run_agent_with_retries,
            "trigger": "interval",
            "args": [job_id, agent, max_retries],
            "hours": interval_hours,
            "id": job_id,
            "name": f"Agent: {agent.name}",
            "replace_existing": True,
        }

        # Optionally run immediately on first add
        if run_immediately:
            job_kwargs["next_run_time"] = datetime.now()
            logger.info(
                f"Added agent '{agent.name}' to scheduler (every {interval_hours} hour(s), max {max_retries} retries, running immediately)"
            )
        else:
            logger.info(
                f"Added agent '{agent.name}' to scheduler (every {interval_hours} hour(s), max {max_retries} retries)"
            )

        self.scheduler.add_job(**job_kwargs)

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
                    logger.info(f"Retrying agent '{agent.name}' in {TIME_BETWEEN_RETRIES} seconds...")
                    discord_logger.agent_rescheduled(agent.name, TIME_BETWEEN_RETRIES)
                    time.sleep(TIME_BETWEEN_RETRIES)
                else:
                    logger.error(f"Agent '{agent.name}' failed after {max_retries + 1} attempts")
                    discord_logger.agent_error_max_retries(agent.name, str(e), max_retries)
