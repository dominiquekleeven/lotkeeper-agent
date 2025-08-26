import datetime
import io
from http import HTTPStatus

import cv2
import numpy
from discord_webhook import DiscordEmbed, DiscordWebhook
from loguru import logger

from open_ah_agent.common.app_info import get_app_info
from open_ah_agent.config import ENV


class DiscordLogger:
    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or ENV.DISCORD_WEBHOOK_URL
        if not self.webhook_url:
            logger.warning("Discord webhook URL not configured. Logging will be disabled.")

    def _is_enabled(self) -> bool:
        return bool(self.webhook_url)

    def _get_enhanced_colors(self) -> dict[str, int]:
        return {
            "success": 0x00D26A,  # Discord green
            "error": 0xF23F42,  # Discord red
            "warning": 0xFEE75C,  # Discord yellow
            "info": 0x5865F2,  # Discord blurple
            "agent": 0x7289DA,  # Discord blue
            "task": 0x9B59B6,  # Purple
            "game": 0xE67E22,  # Orange
        }

    def _format_embed(self, message: str, level: str, title: str | None = None) -> DiscordEmbed:
        colors = self._get_enhanced_colors()
        color = colors.get(level.lower(), colors["info"])

        if not title:
            title = f"{level.upper()}"

        embed = DiscordEmbed(title=title, description=message, color=color)

        embed.set_footer(text=f"OpenAH Agent v{get_app_info().version}")
        embed.set_timestamp()

        if level.lower() in ["success", "error"]:
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/916750808889917440.png")  # Robot emoji

        return embed

    def send_log(self, message: str, level: str = "info", title: str | None = None) -> bool:
        if not self._is_enabled():
            logger.debug(f"Discord logging disabled. Would send: [{level.upper()}] {message}")
            return False

        try:
            webhook = DiscordWebhook(url=self.webhook_url, username=ENV.AGENT_NAME, avatar_url=ENV.AGENT_IMAGE_URL)
            embed = self._format_embed(message, level, title)
            webhook.add_embed(embed)
            response = webhook.execute()

            if response.status_code == HTTPStatus.OK:
                return True
            else:
                return False

        except Exception:
            return False

    def success(self, message: str, title: str | None = None) -> bool:
        return self.send_log(message, "success", title)

    def error(self, message: str, title: str | None = None) -> bool:
        return self.send_log(message, "error", title)

    def warning(self, message: str, title: str | None = None) -> bool:
        return self.send_log(message, "warning", title)

    def info(self, message: str, title: str | None = None) -> bool:
        return self.send_log(message, "info", title)

    # When an agent starts running
    def agent_running(self, agent_name: str, tasks: list[str]) -> bool:
        title = f"{agent_name} Started"
        tasks_str = ", ".join(f"`{task}`" for task in tasks)
        enhanced_message = f"Agent is now running and will execute its tasks \n\n **Tasks:** {tasks_str}"
        return self.send_log(enhanced_message, "info", title)

    # When an agent error occurs
    def agent_error(self, agent_name: str, error_details: str = "") -> bool:
        title = f"{agent_name} Error"
        enhanced_message = "Agent encountered an error, attempting to reschedule."
        if error_details:
            enhanced_message += f"\n\n**Details:** `{error_details}`"
        return self.send_log(enhanced_message, "error", title)

    # When an agent task fails
    def agent_task_error(self, agent_name: str, task_name: str, error_details: str = "") -> bool:
        title = f"{agent_name} Task Failed"
        enhanced_message = f"**Task:** `{task_name}`\nAttempting to reschedule."
        if error_details:
            enhanced_message += f"\n\n**Error:** `{error_details}`"
        return self.send_log(enhanced_message, "error", title)

    # When an agent fails to complete tasks after max retries
    def agent_error_max_retries(self, agent_name: str, error_details: str = "", max_retries: int = 3) -> bool:
        title = f"{agent_name} Max Retries Exceeded"
        enhanced_message = f"Failed after {max_retries} attempts."
        if error_details:
            enhanced_message += f"\n\n**Final Error:** `{error_details}`"
        return self.send_log(enhanced_message, "error", title)

    # When an agent is rescheduled
    def agent_rescheduled(self, agent_name: str, time_between_retries: int) -> bool:
        title = f"{agent_name} Rescheduled"
        enhanced_message = f"Retrying in {time_between_retries} seconds"
        return self.send_log(enhanced_message, "info", title)

    # When an agent task starts
    def agent_task_started(self, agent_name: str, task_name: str) -> bool:
        title = f"{agent_name} Task Started"
        enhanced_message = f"**Task:** `{task_name}`"
        return self.send_log(enhanced_message, "info", title)

    # When an agent task completes
    def agent_task_completed(self, agent_name: str, task_name: str, duration: float) -> bool:
        title = f"{agent_name} Task Complete"
        enhanced_message = f"**Task:** `{task_name}`\n**Duration:** {duration:.1f}s"
        return self.send_log(enhanced_message, "success", title)

    # When an agent completes all tasks
    def agent_all_tasks_completed(
        self, agent_name: str, duration: float, next_run_time: datetime.datetime | None
    ) -> bool:
        title = f"{agent_name} All Tasks Complete"
        enhanced_message = f"**Total Duration:** {duration:.1f}s"
        if next_run_time:
            enhanced_message += f"\n**Next run is scheduled for:** {next_run_time.strftime('%Y-%m-%d %H:%M:%S')} (UTC)"
        return self.send_log(enhanced_message, "success", title)

    # When OCR detection succeeds
    def ocr_success(self, snapshot: numpy.ndarray, keywords: list[str]) -> bool:
        title = "🔍 OCR Success"
        keywords_str = ", ".join(f"`{kw}`" for kw in keywords)
        enhanced_message = f"**Found:** {keywords_str}"
        return self.send_snapshot(snapshot, enhanced_message, title, "success")

    # When OCR detection times out
    def ocr_timeout(self, snapshot: numpy.ndarray, keywords: list[str], timeout_duration: float) -> bool:
        title = "⏱️ OCR Timeout"
        keywords_str = ", ".join(f"`{kw}`" for kw in keywords)
        enhanced_message = f"**Timeout:** {timeout_duration}s\n**Searched for:** {keywords_str}"
        return self.send_snapshot(snapshot, enhanced_message, title, "error")

    def send_snapshot(
        self, snapshot: numpy.ndarray, message: str | None = None, title: str | None = None, level: str = "error"
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
                colors = self._get_enhanced_colors()
                color = colors.get(level.lower(), colors["error"])

                embed_title = title or "Snapshot"
                embed = DiscordEmbed(title=embed_title, description=message or "", color=color)
                embed.set_image(url="attachment://snapshot.png")
                embed.set_footer(text=f"OpenAH Agent v{get_app_info().version}")
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
