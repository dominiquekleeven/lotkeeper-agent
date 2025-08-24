import io
from datetime import datetime
from http import HTTPStatus

import cv2
import numpy
from discord_webhook import DiscordEmbed, DiscordWebhook
from loguru import logger

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

    def _format_timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _format_embed(self, message: str, level: str, title: str | None = None) -> DiscordEmbed:
        colors = self._get_enhanced_colors()
        color = colors.get(level.lower(), colors["info"])

        if not title:
            title = f"{level.upper()}"

        embed = DiscordEmbed(title=title, description=message, color=color)

        embed.set_footer(text=f"OpenAH Agent  •  {self._format_timestamp()}")

        if level.lower() in ["success", "error"]:
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/916750808889917440.png")  # Robot emoji

        return embed

    def send_log(self, message: str, level: str = "info", title: str | None = None) -> bool:
        if not self._is_enabled():
            logger.debug(f"Discord logging disabled. Would send: [{level.upper()}] {message}")
            return False

        try:
            webhook = DiscordWebhook(
                url=self.webhook_url, username=ENV.AGENT_NAME, avatar_url=ENV.AGENT_IMAGE_URL
            )
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

    def agent_running_tasks(self, agent_name: str, tasks: list[str]) -> bool:
        title = f"`{agent_name}` Started Running Tasks"
        tasks_str = ", ".join(f"`{task}`" for task in tasks)
        enhanced_message = f"**Task List:** {tasks_str}"
        return self.send_log(enhanced_message, "info", title)

    def agent_error(self, agent_name: str, error_details: str = "") -> bool:
        title = f"`{agent_name}` Encountered an Error"
        enhanced_message = "The agent encountered an unexpected error."
        if error_details:
            enhanced_message += f"\n\n**Error Details:** `{error_details}`"
        return self.send_log(enhanced_message, "error", title)

    def agent_task_failed(self, agent_name: str, task_name: str, error_details: str = "") -> bool:
        title = f"`{agent_name}` Failed to Complete `{task_name}`"
        enhanced_message = "The task failed to complete successfully."
        if error_details:
            enhanced_message += f"\n\n**Error Details:** `{error_details}`"
        return self.send_log(enhanced_message, "error", title)

    def agent_task_started(self, agent_name: str, task_name: str) -> bool:
        title = f"`{agent_name}` Started `{task_name}`"
        enhanced_message = "The task has been initiated and is now running."
        return self.send_log(enhanced_message, "info", title)

    def agent_task_completed(self, agent_name: str, task_name: str, duration: float) -> bool:
        title = f"`{agent_name}` Completed `{task_name}`"
        enhanced_message = f"The task completed successfully in **{duration} seconds**."
        return self.send_log(enhanced_message, "success", title)

    def agent_all_tasks_completed(self, agent_name: str, duration: float) -> bool:
        title = f"`{agent_name}` Completed All Tasks"
        enhanced_message = f"All tasks have been completed successfully in **{duration} seconds**."
        return self.send_log(enhanced_message, "success", title)

    def ocr_success(self, snapshot: numpy.ndarray, keywords: list[str]) -> bool:
        title = "🔎 OCR Detection Success"
        keywords_str = ", ".join(f"`{kw}`" for kw in keywords)
        enhanced_message = f"Text detection operation completed successfully.\n\n**Target Keywords:** {keywords_str}"
        return self.send_snapshot(snapshot, enhanced_message, title, "success")

    def ocr_timeout(self, snapshot: numpy.ndarray, keywords: list[str], timeout_duration: float) -> bool:
        title = "⌛️ OCR Timeout"
        keywords_str = ", ".join(f"`{kw}`" for kw in keywords)
        enhanced_message = f"Text detection operation exceeded the timeout threshold.\n\n**Target Keywords:** {keywords_str}\n**Timeout Duration:** `{timeout_duration}s`"
        return self.send_snapshot(snapshot, enhanced_message, title, "error")

    def send_snapshot(
        self, snapshot: numpy.ndarray, message: str | None = None, title: str | None = None, level: str = "error"
    ) -> bool:
        if not self._is_enabled():
            logger.debug(f"Discord logging disabled. Would send screenshot: {message}")
            return False

        try:
            webhook = DiscordWebhook(
                url=self.webhook_url, username=ENV.AGENT_NAME, avatar_url=ENV.AGENT_IMAGE_URL
            )

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
                embed.set_footer(text=f"OpenAH Agent  •  {self._format_timestamp()}")

                webhook.add_embed(embed)

            response = webhook.execute()

            if response.status_code == HTTPStatus.OK:
                logger.debug("Discord snapshot sent successfully")
                return True
            else:
                logger.error(f"Failed to send Discord snapshot. Status: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error sending Discord snapshot: {e}")
            return False


# Create a module-level instance for direct usage
discord_logger = DiscordLogger()
