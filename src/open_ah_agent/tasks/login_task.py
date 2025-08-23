from loguru import logger

from open_ah_agent.common.xdo import XDO
from open_ah_agent.config import ENV
from open_ah_agent.dependencies import text_detector
from open_ah_agent.detectors.text_detector import GameTexts
from open_ah_agent.tasks.agent_task import AgentTask, TaskError, TaskErrorText


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
            raise TaskError(TaskErrorText.PRECHECK_FAILURE)

        self.username = username
        self.password = password

    def run(self) -> bool:
        # 1 Wait for the login button to be detected
        logger.info("Step: Waiting for login screen")
        if not self.text_detector.detect([GameTexts.LOGIN]):
            raise TaskError(TaskErrorText.COULD_NOT_DETECT_TEXT)

        # 2 Log username but only partially, only show first 3 characters
        logger.info(f"Logging in as {self.username[:3]}...")

        # 3 Clear any existing text and enter username
        logger.info("Step: Enter username")
        XDO.Interact.press_key("ctrl+a")
        XDO.Interact.type_text(self.username)

        # 4 Tab to password field
        logger.info("Step: Tab to password")
        XDO.Interact.press_key("Tab")

        # 5 Clear and enter password
        logger.info("Step: Enter password")
        XDO.Interact.press_key("ctrl+a")
        XDO.Interact.type_text(self.password)

        # 6 Press Enter to login
        logger.info("Step: Submit details")
        XDO.Interact.press_key("Return")

        # 7 Wait for Enter World text to be detected
        logger.info("Step: Waiting for character selection screen")
        if not self.text_detector.detect([GameTexts.CHARACTER]):
            raise TaskError(TaskErrorText.COULD_NOT_DETECT_TEXT)

        # 8 Press Enter to enter the world
        logger.info("Step: Enter world")
        XDO.Interact.press_key("Return")

        # 9 Return success
        return True
