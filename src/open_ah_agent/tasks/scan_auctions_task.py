from loguru import logger

from open_ah_agent.common.discord_logger import discord_logger
from open_ah_agent.common.xdo_game import XDOGame
from open_ah_agent.dependencies import text_detector
from open_ah_agent.detectors.text_detector import GameTexts
from open_ah_agent.tasks.agent_task import AgentTask, TaskError


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
        XDOGame.Game.reload()

        # 6 Wait for the game to be ready
        logger.info("Step: Waiting for game to be ready after reload")
        if not self.text_detector.detect([GameTexts.OAS_IDLE]):
            raise TaskError(self.name, "Failed to detect whether the game is ready after reload")

        # 7 Get the saved variables file
        saved_variables_path = XDOGame.Paths.get_saved_variables_path()
        if not saved_variables_path:
            # Since this is a pretty severe error, we also send it to discord
            discord_logger.error(
                f"Could not find the saved variables file at: {saved_variables_path}", "I/O Error: File Not Found"
            )
            raise TaskError(self.name, "Could not find the saved variables file")


        # 8 Parse the saved variables file
        # TODO: Implement this, the file is .lua and contains a table of all auctions.
        # We need to parse this and then map it to our own data model.
        # Then we can do whatever we want with the data.

        # At this point we KNOW we have a completed scan and we can start parsing the saved variables file.
        # \WTF\Account\<WOW_USERNAME>\SavedVariables\OpenAuctionScanner.lua
        # Ensure it exists, otherwise fail

        # Example of how the structure is stored in the saved variables file
        #     OAAData = {
        # {
        # 	["bidAmount"] = 0,
        # 	["quality"] = 1,
        # 	["link"] = "|cffffffff|Hitem:3190:0:0:0:0:0:0:0:1|h[Beatstick]|h|r",
        # 	["buyoutPrice"] = 865,
        # 	["count"] = 1,
        # 	["minBid"] = 821,
        # 	["texture"] = "Interface\\Icons\\INV_Mace_02",
        # 	["name"] = "Beatstick",
        # 	["className"] = "weapon",
        # 	["minIncrement"] = 0,
        # 	["level"] = 3,
        # 	["itemId"] = 3190,
        # 	["realm"] = "Kezan",
        # }, -- [1]
        # {
        # 	["bidAmount"] = 0,
        # 	["quality"] = 1,
        # 	["link"] = "|cffffffff|Hitem:1195:0:0:0:0:0:0:0:1|h[Kobold Mining Shovel]|h|r",
        # 	["buyoutPrice"] = 394,
        # 	["count"] = 1,
        # 	["minBid"] = 374,
        # 	["texture"] = "Interface\\Icons\\INV_Misc_Shovel_01",
        # 	["name"] = "Kobold Mining Shovel",
        # 	["className"] = "weapon",
        # 	["minIncrement"] = 0,
        # 	["level"] = 3,
        # 	["itemId"] = 1195,
        # 	["realm"] = "Kezan",
        # }, -- [2]

        return True
