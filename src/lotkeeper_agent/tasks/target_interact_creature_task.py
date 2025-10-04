from loguru import logger

from lotkeeper_agent.common.sleep_util import SleepUtil
from lotkeeper_agent.common.xdo import XDO
from lotkeeper_agent.common.xdo_game import XDOGame
from lotkeeper_agent.dependencies import text_detector
from lotkeeper_agent.detectors.text_detector import GameTexts
from lotkeeper_agent.tasks.agent_task import AgentTask, TaskError


class TargetInteractCreatureTask(AgentTask):
    def __init__(self, creature_name: str, interact_key: str = "F1") -> None:
        super().__init__(
            name="Interact with Target",
            description=f"Target creature via {creature_name} and interact via {interact_key}",
        )
        self.creature_name = creature_name
        self.interact_key = interact_key
        self.text_detector = text_detector()

    def run(self) -> bool:
        # 1 Press the target key
        logger.info(f"Step: Target {self.creature_name}")
        XDOGame.Game.target_creature(self.creature_name)

        # 2 Wait for the interaction to complete
        logger.info("Step: Wait for interaction to complete")
        SleepUtil.sleep_default()

        # 3 Press the interact key
        logger.info(f"Step: Press {self.interact_key} to interact")
        XDO.Interact.press_key(self.interact_key)

        # 4 Wait for the interaction to complete
        logger.info("Step: Wait for interaction to complete")
        SleepUtil.sleep_default()

        # 5 Wait for the choose search criteria text to be detected
        logger.info("Step: Detect auction house window")
        if not self.text_detector.detect([GameTexts.CHOOSE_SEARCH_CRITERIA]):
            raise TaskError(self.name, "Failed to detect whether the auction house window is open")

        # 6 Return success
        return True
