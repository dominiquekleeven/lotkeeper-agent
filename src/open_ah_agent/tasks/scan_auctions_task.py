from loguru import logger

from open_ah_agent.common.xdo import XDO
from open_ah_agent.dependencies import text_detector
from open_ah_agent.detectors.text_detector import GameTexts
from open_ah_agent.tasks.agent_task import AgentTask, TaskError, TaskErrorText, TimeUtils


class ScanAuctionsTask(AgentTask):
    def __init__(self) -> None:
        super().__init__(
            name="Scan Auction House",
            description="Scan the auction house for items",
        )
        self.text_detector = text_detector()

    def run(self) -> bool:
        logger.info("Step: preparing to scan auctions")

        # Todo add actual logic here
        # 1. Run /oas scan OR hit key for macro that does it for us
        # 2. Wait for scan to complete (we can do this easily by checking for file no longer changing in SavedVariables)
        # 3. Parse saved variables file and send it off to back-end API
        return True
