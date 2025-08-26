import httpx
from loguru import logger

from open_ah_agent.common.discord_logger import discord_logger
from open_ah_agent.common.xdo_game import XDOGame
from open_ah_agent.config import ENV
from open_ah_agent.dependencies import text_detector
from open_ah_agent.detectors.text_detector import GameTexts
from open_ah_agent.models.auction import Auction, AuctionData
from open_ah_agent.tasks.agent_task import AgentTask, TaskError, TimeUtils


class ScanAuctionsTask(AgentTask):
    def __init__(self) -> None:
        super().__init__(
            name="Scan Auction House",
            description="Scan the auction house for items",
        )
        self.text_detector = text_detector()

    def run(self) -> bool:
        # 1 Wait for OAS Addon to be detected, meaning we are able to start scanning
        logger.info("Step: Detect OAS Addon")
        if not self.text_detector.detect([GameTexts.OAS_IDLE]):
            raise TaskError(self.name, "Failed to detect whether the OAS Addon is loaded")

        # 2 Run /oas scan
        XDOGame.Game.enter_chat_command("/oas scan")

        # 3 Wait for the OAS Addon to indicate we are scanning
        if not self.text_detector.detect([GameTexts.OAS_SCANNING]):
            raise TaskError(self.name, "Failed to detect whether the OAS Addon is scanning")

        # 4 Wait for scan to complete
        scan_timeout = 1200  # timeout of 20 minutes
        logger.info("Step: Waiting for scan to complete")
        if not self.text_detector.detect([GameTexts.OAS_COMPLETED], timeout=scan_timeout):
            raise TaskError(self.name, "Failed to detect whether the scan is complete")

        # 5 Reload game window to ensure saved variables are stored
        logger.info("Step: Reloading game window to ensure saved variables are stored")
        XDOGame.Game.reload()
        TimeUtils.fixed_delay(10)

        # 6 Wait for the game to be ready
        logger.info("Step: Waiting for game to be ready after reload")
        if not self.text_detector.detect([GameTexts.OAS_IDLE]):
            raise TaskError(self.name, "Failed to detect whether the game is ready after reload")

        # 7 Get the saved variables file
        saved_variables_path = XDOGame.Paths.get_saved_variables_path()
        if not saved_variables_path:
            discord_logger.error(
                f"Could not find the saved variables file at: {saved_variables_path}", "I/O Error: File Not Found"
            )
            raise TaskError(self.name, "Could not find the saved variables file")

        # 8 Parse the saved variables file to JSON / Python dict
        logger.info("Step: Parsing saved variables file")
        try:
            table_entries = XDOGame.Paths.parse_saved_variables_lua(saved_variables_path, "OAAData")
            logger.info(f"Parsed auction data with {len(table_entries)} entries")
            auctions = [Auction.from_lua_table(entry) for entry in table_entries]
            logger.info(f"Mapped {len(auctions)} auctions")
        except Exception as e:
            logger.exception(f"Failed to parse saved variables file: {e}")
            raise TaskError(self.name, f"Failed to parse saved variables file: {e}") from e

        discord_logger.info(f"Parsed and mapped a total of {len(auctions)} auctions", "Scan Auction House Update")

        # 9 Check if we can attempt to send the auctions to the OpenAH API
        logger.info("Step: Checking if we can send auctions to OpenAH API")
        if not ENV.OAH_HOST or not ENV.OAH_AGENT_TOKEN:
            raise TaskError(self.name, "OpenAH Host or Agent Token not set in config, cannot send auction data")

        # 10 Constructing auction data payload
        logger.info("Step: Constructing auction data payload")
        auction_data = AuctionData(
            server=ENV.WOW_SERVER,
            realm=ENV.WOW_REALM,
            auctions=auctions,
        )

        # 11 Send auction data to OpenAH API
        logger.info("Step: Sending auction data to OpenAH API")
        try:
            endpoint = f"{ENV.OAH_HOST}/api/v1/agent/auctions"
            headers = {
                "X-Agent-Access-Token": f"{ENV.OAH_AGENT_TOKEN}",
                "Content-Type": "application/json",
            }
            response = httpx.post(endpoint, json=auction_data.model_dump(), headers=headers, timeout=60)
            response.raise_for_status()
            logger.info("Sent auction data to the OpenAH API")
            discord_logger.info(f"Sent {len(auctions)} auctions to the OpenAH API", "Scan Auction House Update")

        except Exception as e:
            logger.exception(f"Failed to send auction data to the OpenAH API: {e}")
            raise TaskError(self.name, f"Failed to send auction data to the OpenAH API: {e}") from e

        # 12 Return success
        return True
