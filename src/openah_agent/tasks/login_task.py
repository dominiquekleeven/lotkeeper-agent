from loguru import logger

from openah_agent.common.xdo import XDO
from openah_agent.config import ENV
from openah_agent.dependencies import text_detector
from openah_agent.detectors.text_detector import GameTexts
from openah_agent.tasks.agent_task import AgentTask, TaskError


class LoginTask(AgentTask):
    def __init__(self) -> None:
        super().__init__(name="Login to Game", description="Login to the game and select a character")
        self.text_detector = text_detector()

        # Get username and password
        username = ENV.WOW_USERNAME
        password = ENV.WOW_PASSWORD

        # Pre checks
        if not username or not password:
            logger.warning("WOW_USERNAME or WOW_PASSWORD not set in config")
            raise TaskError(self.name, "Agent configuration is missing username or password")

        self.username = username
        self.password = password

    def run(self) -> bool:
        # 1 Wait for the login button to be detected
        logger.info("Step: Wait for login screen")
        if not self.text_detector.detect([GameTexts.LOGIN]):
            raise TaskError(self.name, "Failed to detect whether we are on the login screen")

        # 2 Log username but only partially, only show first 3 characters
        logger.info(f"Logging in as {self.username[:3]}...")

        # 3 Clear any existing text and enter username
        logger.info("Step: Enter username")
        XDO.Interact.press_key("ctrl+a")
        XDO.Interact.type_text(self.username)

        # 4 Tab to password field
        logger.info("Step: Tab to password field")
        XDO.Interact.press_key("Tab")

        # 5 Clear and enter password
        logger.info("Step: Enter password")
        XDO.Interact.press_key("ctrl+a")
        XDO.Interact.type_text(self.password)

        # 6 Press Enter to login
        logger.info("Step: Submit details")
        XDO.Interact.press_key("Return")

        # Todo:
        # Improve robustness by checking for edge cases, like:
        # - Disconnected message
        # - Realm Selection screen instead of character selection screen

        # 7 Wait for New Character text to be detected
        logger.info("Step: Wait for character selection screen")
        if not self.text_detector.detect([GameTexts.NEW_CHARACTER]):
            raise TaskError(self.name, "Failed to detect whether we are on the character selection screen")

        # 8 Press Enter to enter the world
        logger.info("Step: Enter world")
        XDO.Interact.press_key("Return")

        # 8 Wait for the trade or LFG channel text to be detected, meaning we are actually in-game
        logger.info("Step: Detect in-game screen")
        if not self.text_detector.detect([GameTexts.TRADE, GameTexts.LFG_CHANNEL], timeout=120): # extra long timeout due to gameload
            raise TaskError(self.name, "Failed to detect whether we are in-game")

        # 9 Return success
        return True
