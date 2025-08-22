import time

from loguru import logger

from open_ah_agent.config import ENV
from open_ah_agent.interact import Interact
from open_ah_agent.sequences.sequence import Sequence
from open_ah_agent.window import Window


class LoginSequence(Sequence):
    def __init__(self, initial_delay: int = 10) -> None:
        super().__init__(name="Login", description="Handles the login process and character selection")
        self.initial_delay = initial_delay

    def run(self) -> bool:
        if not Window.wait():
            logger.error("Could not find WoW window")
            return False
        
        if not Window.focus():
            logger.error("Could not focus WoW window")
            return False

        # Get username and password
        username = ENV.WOW_USERNAME
        password = ENV.WOW_PASSWORD

        # Pre checks
        if not username or not password:
            logger.warning("WOW_USERNAME or WOW_PASSWORD not set in config")
            return False

        # Log username but only partially, only show first 3 characters
        logger.info(f"Logging in as {username[:3]}...")
        
        # Wait for the initial delay
        logger.info(f"Waiting {self.initial_delay} seconds before starting login sequence.")
        time.sleep(self.initial_delay)

        # Clear any existing text and enter username
        logger.info("Step: Enter username")
        Interact.press_key("ctrl+a")
        time.sleep(0.3)
        Interact.type_text(username)

        # Tab to password field
        logger.info("Step: Tab to password")
        time.sleep(0.5)
        Interact.press_key("Tab")

        # Clear and enter password
        logger.info("Step: Enter password")
        time.sleep(0.3)
        Interact.press_key("ctrl+a")
        time.sleep(0.3)
        Interact.type_text(password)

        # Press Enter to login
        logger.info("Step: Submit details")
        time.sleep(0.8)
        Interact.press_key("Return")

        # Wait a bit for character selection to load and then press enter again to login to the world
        logger.info("Step: Wait for character selection")
        time.sleep(15)
        Interact.press_key("Return")

        logger.info("Login sequence completed")
        return True
