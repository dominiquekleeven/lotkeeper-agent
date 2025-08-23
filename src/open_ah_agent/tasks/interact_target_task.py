from loguru import logger

from open_ah_agent.common.xdo import XDO
from open_ah_agent.dependencies import text_detector
from open_ah_agent.detectors.text_detector import GameTexts
from open_ah_agent.tasks.agent_task import AgentTask, TaskError, TaskErrorText, TimeUtils


class InteractTargetTask(AgentTask):
    def __init__(self, target_key: str = "1", interact_key: str = "F1") -> None:
        super().__init__(
            name="Interact with Target",
            description=f"Target creature via {target_key} and interact via {interact_key}",
        )
        self.target_key = target_key
        self.interact_key = interact_key
        self.text_detector = text_detector()

    def run(self) -> bool:
        # 1 Wait for the trade text to be detected
        logger.info("Step: detect in-game screen")
        if not self.text_detector.detect([GameTexts.TRADE]):
            raise TaskError(TaskErrorText.COULD_NOT_DETECT_TEXT)

        # 2 Press the target key
        logger.info(f"Step: press {self.target_key} to target")
        XDO.Interact.press_key(self.target_key)

        # 3 Wait for the interaction to complete
        logger.info("Step: wait for interaction to complete")
        TimeUtils.delay()

        # 4 Press the interact key
        logger.info(f"Step: press {self.interact_key} to interact")
        XDO.Interact.press_key(self.interact_key)

        # 5 Wait for the interaction to complete
        logger.info("Step: wait for interaction to complete")
        TimeUtils.delay()

        # 6 Wait for the choose search criteria text to be detected
        logger.info("Step: detect auction house window")
        if not self.text_detector.detect([GameTexts.CHOOSE_SEARCH_CRITERIA]):
            raise TaskError(TaskErrorText.COULD_NOT_DETECT_TEXT)

        # 7 Return success
        return True
