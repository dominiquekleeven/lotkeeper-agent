from abc import ABC, abstractmethod
import random

from loguru import logger

from open_ah_agent.window import Window


class Sequence(ABC):
    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    @abstractmethod
    def run(self) -> bool:
        pass

    def log_start(self) -> None:
        logger.info(f"Starting sequence: {self.name} - {self.description}")

    def log_complete(self, success: bool) -> None:
        status = "successfully" if success else "with errors"
        logger.info(f"Completed sequence: {self.name} - {self.description} {status}")


    def get_random_delay(self, delay: tuple[int, int] = (1, 3)) -> float:
        return random.uniform(delay[0], delay[1])

    def execute(self) -> bool:
        self.log_start()
        try:
            result = self.run()
            self.log_complete(result)
            return result
        except Exception as e:
            logger.error(f"Error in sequence: {self.name} - {self.description}: {e}")
            self.log_complete(False)
            return False
