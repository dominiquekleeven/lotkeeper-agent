import time

from loguru import logger

from open_ah_agent.config import ENV
from open_ah_agent.interact import Interact
from open_ah_agent.sequences.sequence import Sequence
from open_ah_agent.window import Window


class InteractSequence(Sequence):
    def __init__(self, initial_delay: int = 15, target_key: str = "1", interact_key: str = "F1") -> None:
        """
        Interact sequence that targets an object and interacts with it.

        Args:
            initial_delay: The delay before the interaction starts. Defaults to 15 seconds.
            target_key: The key to target the object. Defaults to "1". (Hint, create a macro for this)
            interact_key: The key to interact with the object. Defaults to "F". (Hint, set interaction keyboard shortcut)
        """
        super().__init__(name="Interact", description=f"Interacts with the game by targetting via {target_key} and triggering interaction via {interact_key}")
        self.initial_delay = initial_delay
        self.target_key = target_key
        self.interact_key = interact_key
   

    def run(self) -> bool:
        if not Window.wait():
            logger.error("Could not find WoW window")
            return False
        
        if not Window.focus():
            logger.error("Could not focus WoW window")
            return False

        # Wait for the initial delay
        logger.info(f"Waiting {self.initial_delay} seconds for initial delay")
        time.sleep(self.initial_delay)

        # Press the target key
        logger.info(f"Pressing {self.target_key} to target")
        Interact.press_key(self.target_key)

        # Wait for the interaction to complete
        logger.info(f"Waiting for interaction to complete")
        time.sleep(self.get_random_delay())

        # Press the interact key
        logger.info(f"Pressing {self.interact_key} to interact")
        Interact.press_key(self.interact_key)

        # Wait for the interaction to complete
        logger.info(f"Waiting for interaction to complete")
        time.sleep(self.get_random_delay())

        # Return success
        logger.info(f"Interaction sequence completed")
        return True
