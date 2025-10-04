import httpx
from loguru import logger

from lotkeeper_agent.common.discord_logger import discord_logger
from lotkeeper_agent.common.sleep_util import SleepUtil
from lotkeeper_agent.common.xdo_game import XDOGame
from lotkeeper_agent.config import ENV
from lotkeeper_agent.dependencies import text_detector
from lotkeeper_agent.detectors.text_detector import GameTexts
from lotkeeper_agent.models.auction import Auction, AuctionData
from lotkeeper_agent.models.wow_config import WoWAccount
from lotkeeper_agent.tasks.agent_task import AgentTask, TaskError


class ScanAuctionsTask(AgentTask):
    def __init__(self, account: WoWAccount) -> None:
        super().__init__(
            name="Scan Auction House",
            description="Scan the auction house for items",
        )
        self.text_detector = text_detector()
        self.account = account

    def run(self) -> bool:
        # 1 Wait for OAS Addon to be detected, meaning we are able to start scanning
        logger.info("Step: Detect OAS Addon")
        if not self.text_detector.detect([GameTexts.OAS_IDLE]):
            raise TaskError(self.name, "Failed to detect whether the OAS Addon is loaded")

        # 2 Run /oas scan
        logger.info("Step: Running /oas scan")
        XDOGame.Game.enter_chat_command("/oas scan")

        # 3 Wait for the OAS Addon to indicate we are scanning
        logger.info("Step: Waiting for OAS Addon to indicate we are scanning")
        if not self.text_detector.detect([GameTexts.OAS_SCANNING]):
            raise TaskError(self.name, "Failed to detect whether the OAS Addon is scanning")

        # 4 Wait for scan to complete
        scan_timeout = 1800  # timeout of 30 minutes
        logger.info("Step: Waiting for scan to complete")
        if not self.text_detector.detect([GameTexts.OAS_COMPLETED], timeout=scan_timeout):
            raise TaskError(self.name, "Failed to detect whether the scan is complete")

        # 5 Reload game window to ensure saved variables are stored
        logger.info("Step: Reloading game window to ensure saved variables are stored")
        XDOGame.Game.reload()
        SleepUtil.sleep_fixed(10)  # Sleep for 10 to ensure saved variables are stored and game is ready

        # 6 Wait for the game to be ready
        logger.info("Step: Waiting for game to be ready after reload")
        if not self.text_detector.detect([GameTexts.OAS_IDLE]):
            raise TaskError(self.name, "Failed to detect whether the game is ready after reload")

        # 7 Get the saved variables file
        logger.info("Step: Getting saved variables file")
        saved_variables_path = XDOGame.Paths.get_saved_variables_path(self.account.username)
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

        # 9 Constructing auction data payload
        logger.info("Step: Constructing auction data payload")
        auction_data = AuctionData(
            server=ENV.WOW_SERVER,
            realm=self.account.get_realm_name_with_faction(),
            auctions=auctions,
        )

        # 10 Send auction data to Lotkeeper API
        logger.info("Step: Sending auction data to Lotkeeper API")
        try:
            endpoint = f"{ENV.LOT_HOST}/api/v1/agent/auctions"
            headers = {
                "X-Agent-Access-Token": f"{ENV.LOT_AGENT_TOKEN}",
                "Content-Type": "application/json",
            }
            response = httpx.post(endpoint, json=auction_data.model_dump(), headers=headers, timeout=60)
            response.raise_for_status()
            logger.info("Sent auction data to the Lotkeeper API")
            discord_logger.info(f"Sent {len(auctions)} auctions to the Lotkeeper API", "Scan Auction House Update")

        except Exception as e:
            logger.exception(f"Failed to send auction data to the Lotkeeper API: {e}")
            raise TaskError(self.name, f"Failed to send auction data to the Lotkeeper API: {e}") from e

        # 11 Return success
        return True
