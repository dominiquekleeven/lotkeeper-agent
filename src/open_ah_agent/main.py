import os
from typing import Sequence

from loguru import logger

from open_ah_agent.sequences.interact_sequence import InteractSequence
from open_ah_agent.sequences.login_sequence import LoginSequence

from .config import ENV


class OpenAHAgent:
    def __init__(self) -> None:
        self.display = os.environ.get("DISPLAY", ":99")

    def execute(self, sequence: Sequence) -> bool:
        return sequence.execute()


# --- Entrypoint ---
if __name__ == "__main__":
    logger.info("===== OpenAH Agent =====")
    agent = OpenAHAgent()

    if ENV.AGENT_MODE:
        # General note about sequences:
        # They are designed to be executed in order
        # They are unable to handle failure states, they always assume success
        # Important to not expect 100% success rate, have a fallback plan e.g. execute on a schedule.

        completed_login = agent.execute(LoginSequence())
        if not completed_login:
            logger.error("Login sequence failed")
            exit(1)

        completed_interact = agent.execute(InteractSequence())

        if not completed_interact:
            logger.error("Interact sequence failed")
            exit(1)

    else:
        logger.info("Doing nothing, since agent mode is not set.")
