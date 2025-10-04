import datetime
import io
import time
from enum import Enum
from http import HTTPStatus
from typing import ClassVar

import cv2
import numpy
from discord_webhook import DiscordEmbed, DiscordWebhook
from loguru import logger

from lotkeeper_agent.common.app_info import get_app_info
from lotkeeper_agent.config import ENV


class DiscordLevel(Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    AGENT = "agent"
    TASK = "task"
    GAME = "game"


class DiscordLogger:
    COLORS: ClassVar[dict[DiscordLevel, int]] = {
        DiscordLevel.SUCCESS: 0x00D26A,  # Discord green
        DiscordLevel.ERROR: 0xF23F42,  # Discord red
        DiscordLevel.WARNING: 0xFEE75C,  # Discord yellow
        DiscordLevel.INFO: 0x5865F2,  # Discord blurple
        DiscordLevel.AGENT: 0x7289DA,  # Discord blue
        DiscordLevel.TASK: 0x9B59B6,  # Purple
        DiscordLevel.GAME: 0xE67E22,  # Orange
    }

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or ENV.DISCORD_WEBHOOK_URL
        if not self.webhook_url:
            logger.warning("Discord webhook URL not configured. Logging will be disabled.")

    def _is_enabled(self) -> bool:
        return bool(self.webhook_url)

    def _format_embed(self, level: DiscordLevel, message: str, title: str | None = None) -> DiscordEmbed:
        color = self.COLORS.get(level)

        if not title:
            title = f"{level.value.upper()}"

        embed = DiscordEmbed(title=title, description=message, color=color)

        embed.set_footer(text=f"Lotkeeper Agent v{get_app_info().version}")
        embed.set_timestamp()

        if level in [DiscordLevel.SUCCESS, DiscordLevel.ERROR]:
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/916750808889917440.png")  # Robot emoji

        return embed

    def _send_log(self, level: DiscordLevel, message: str, title: str | None = None) -> bool:
        if not self._is_enabled():
            logger.debug(f"Discord logging disabled. Would send: [{level.value.upper()}] {message}")
            return False

        try:
            webhook = DiscordWebhook(url=self.webhook_url, username=ENV.AGENT_NAME, avatar_url=ENV.AGENT_IMAGE_URL)
            embed = self._format_embed(level, message, title)
            webhook.add_embed(embed)
            response = webhook.execute()

            if response.status_code == HTTPStatus.OK:
                return True
            else:
                return False

        except Exception:
            return False

    def success(self, message: str, title: str | None = None) -> bool:
        return self._send_log(DiscordLevel.SUCCESS, message, title)

    def error(self, message: str, title: str | None = None) -> bool:
        return self._send_log(DiscordLevel.ERROR, message, title)

    def warning(self, message: str, title: str | None = None) -> bool:
        return self._send_log(DiscordLevel.WARNING, message, title)

    def info(self, message: str, title: str | None = None) -> bool:
        return self._send_log(DiscordLevel.INFO, message, title)

    # When an agent starts running
    def agent_running(self, agent_name: str, tasks: list[str]) -> bool:
        title = f"{agent_name} Started"
        tasks_str = ", ".join(f"`{task}`" for task in tasks)
        enhanced_message = f"**Agent is now running and will execute its tasks**\n\n**Tasks:** {tasks_str}"
        return self._send_log(DiscordLevel.INFO, enhanced_message, title)

    # When an agent error occurs
    def agent_error(self, agent_name: str, error_details: str = "") -> bool:
        title = f"{agent_name} Error"
        enhanced_message = "Agent encountered an error, attempting to reschedule."
        if error_details:
            enhanced_message += f"\n\n**Details:** `{error_details}`"
        return self._send_log(DiscordLevel.ERROR, enhanced_message, title)

    # When an agent task fails
    def agent_task_error(self, agent_name: str, task_name: str, error_details: str = "") -> bool:
        title = f"{agent_name} Task Failed"
        enhanced_message = f"**Task:** `{task_name}` failed, attempting to reschedule."
        if error_details:
            enhanced_message += f"\n\n**Error:** `{error_details}`"
        return self._send_log(DiscordLevel.ERROR, enhanced_message, title)

    # When an agent fails to complete tasks after max retries
    def agent_error_max_retries(
        self,
        agent_name: str,
        error_details: str = "",
        max_retries: int = 3,
        next_run_time: datetime.datetime | None = None,
    ) -> bool:
        title = f"{agent_name} Max Retries Exceeded"
        enhanced_message = f"Failed after {max_retries} attempts."
        if error_details:
            enhanced_message += f"\n\n**Final Error:** `{error_details}`"
        if next_run_time:
            discord_timestamp_str = f"<t:{int(next_run_time.timestamp())}:F>"
            enhanced_message += f"\n\n**Next run is scheduled for:** {discord_timestamp_str}"
        return self._send_log(DiscordLevel.ERROR, enhanced_message, title)

    # When an agent is rescheduled
    def agent_rescheduled(self, agent_name: str, time_between_retries: int) -> bool:
        title = f"{agent_name} Rescheduled"
        future_run_time = time.time() + time_between_retries
        enhanced_message = f"Retrying at <t:{int(future_run_time)}:F>"
        return self._send_log(DiscordLevel.INFO, enhanced_message, title)

    # When an agent is scheduled
    def agent_scheduled(self, agent_name: str, next_run_time: datetime.datetime | None) -> bool:
        title = f"{agent_name} Scheduled"

        if next_run_time:
            discord_timestamp_str = f"<t:{int(next_run_time.timestamp())}:F>"
            enhanced_message = f"Run scheduled for {discord_timestamp_str}"
        else:
            enhanced_message = "Run scheduled for unknown time (exact time pending)"

        return self._send_log(DiscordLevel.INFO, enhanced_message, title)

    # When an agent task starts
    def agent_task_started(self, agent_name: str, task_name: str) -> bool:
        title = f"{agent_name} Task Started"
        enhanced_message = f"**Task:** `{task_name}`"
        return self._send_log(DiscordLevel.INFO, enhanced_message, title)

    # When an agent task completes
    def agent_task_completed(self, agent_name: str, task_name: str, duration: float) -> bool:
        title = f"{agent_name} Task Complete"
        enhanced_message = f"**Task:** `{task_name}` completed in {duration:.1f} seconds"
        return self._send_log(DiscordLevel.SUCCESS, enhanced_message, title)

    # When an agent completes all tasks
    def agent_all_tasks_completed(
        self, agent_name: str, duration: float, next_run_time: datetime.datetime | None
    ) -> bool:
        title = f"{agent_name} All Tasks Complete"
        enhanced_message = f"**All tasks completed in** {duration:.1f} seconds"
        if next_run_time:
            discord_timestamp_str = f"<t:{int(next_run_time.timestamp())}:F>"
            enhanced_message += f"\n\n**Next run is scheduled for:** {discord_timestamp_str}"
        return self._send_log(DiscordLevel.SUCCESS, enhanced_message, title)

    # When OCR detection succeeds
    def ocr_success(self, snapshot: numpy.ndarray, keywords: list[str], duration: float) -> bool:
        title = "🔍 OCR Success"
        keywords_str = ", ".join(f"`{kw}`" for kw in keywords)
        enhanced_message = f"**Successfully detected:** {keywords_str} in {duration:.2f} seconds"
        return self.send_snapshot(DiscordLevel.SUCCESS, snapshot, enhanced_message, title)

    # When OCR detection times out
    def ocr_timeout(self, snapshot: numpy.ndarray, keywords: list[str], timeout_duration: float) -> bool:
        title = "⏱️ OCR Timeout"
        keywords_str = ", ".join(f"`{kw}`" for kw in keywords)
        enhanced_message = f"**Search timed out after** {timeout_duration} seconds while looking for {keywords_str}"
        return self.send_snapshot(DiscordLevel.ERROR, snapshot, enhanced_message, title)

    def send_snapshot(
        self, level: DiscordLevel, snapshot: numpy.ndarray, message: str | None = None, title: str | None = None
    ) -> bool:
        if not self._is_enabled():
            logger.debug(f"Discord logging disabled. Would send: {message}")
            return False

        try:
            webhook = DiscordWebhook(url=self.webhook_url, username=ENV.AGENT_NAME, avatar_url=ENV.AGENT_IMAGE_URL)

            rgb_image = cv2.cvtColor(snapshot, cv2.COLOR_BGR2RGB)

            is_success, buffer = cv2.imencode(".png", cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR))
            if not is_success:
                logger.error("Failed to encode screenshot as PNG")
                return False

            image_bytes = io.BytesIO(buffer.tobytes())
            image_bytes.name = "snapshot.png"

            webhook.add_file(file=image_bytes.getvalue(), filename="snapshot.png")

            if message or title:
                color = self.COLORS.get(level)

                embed_title = title or "Snapshot"
                embed = DiscordEmbed(title=embed_title, description=message or "", color=color)
                embed.set_image(url="attachment://snapshot.png")
                embed.set_footer(text=f"Lotkeeper Agent v{get_app_info().version}")
                embed.set_timestamp()

                webhook.add_embed(embed)

            response = webhook.execute()

            if response.status_code == HTTPStatus.OK:
                logger.debug("Discord snapshot sent")
                return True
            else:
                logger.error(f"Failed to send Discord snapshot. Status: {response.status_code}")
                return False

        except Exception as e:
            logger.exception(f"Error sending Discord snapshot: {e}")
            return False


# Create a module-level instance for direct usage
discord_logger = DiscordLogger()
