from loguru import logger

from lotkeeper_agent.common.xdo import XDO
from lotkeeper_agent.dependencies import text_detector
from lotkeeper_agent.detectors.text_detector import GameTexts
from lotkeeper_agent.models.wow_config import WoWAccount
from lotkeeper_agent.tasks.agent_task import AgentTask, TaskError


class LoginTask(AgentTask):
    def __init__(self, account: WoWAccount) -> None:
        super().__init__(name="Login to Game", description="Login to the game and select a character")
        self.text_detector = text_detector()
        self.account = account

    def run(self) -> bool:
        # 1 Wait for the login button to be detected
        logger.info("Step: Wait for login screen")
        if not self.text_detector.detect([GameTexts.LOGIN]):
            raise TaskError(self.name, "Failed to detect whether we are on the login screen")

        # 2 Log username but only partially, only show first 5 characters
        logger.info(f"Logging in as {self.account.username[:5]}")

        # 3 Clear any existing text and enter username
        logger.info("Step: Enter username")
        XDO.Interact.press_key("ctrl+a")
        XDO.Interact.type_text(self.account.username)

        # 4 Tab to password field
        logger.info("Step: Tab to password field")
        XDO.Interact.press_key("Tab")

        # 5 Clear and enter password
        logger.info("Step: Enter password")
        XDO.Interact.press_key("ctrl+a")
        XDO.Interact.type_text(self.account.password)

        # 6 Press Enter to login
        logger.info("Step: Submit details")
        XDO.Interact.press_key("Return")

        # 7 Wait for Create New Character text to be detected
        logger.info("Step: Wait for character selection screen")
        if not self.text_detector.detect([GameTexts.CREATE_NEW_CHARACTER]):
            raise TaskError(self.name, "Failed to detect whether we are on the character selection screen")

        # 8 Press Enter to enter the world
        logger.info("Step: Enter world")
        XDO.Interact.press_key("Return")

        # 8 Wait for the OAS IDLE text to be detected, meaning we are actually in-game
        logger.info("Step: Detect in-game screen")
        if not self.text_detector.detect([GameTexts.OAS_IDLE], timeout=120):  # extra long timeout due to gameload
            raise TaskError(self.name, "Failed to detect whether we are in-game")

        # 9 Return success
        return True
