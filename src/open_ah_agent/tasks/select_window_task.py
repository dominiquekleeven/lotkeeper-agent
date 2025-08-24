from loguru import logger

from open_ah_agent.common.xdo import XDO
from open_ah_agent.tasks.agent_task import AgentTask, TaskError


class SelectWindowTask(AgentTask):
    def __init__(self, window_patterns: list[str]) -> None:
        super().__init__(
            name="Wait for Game Window", description="Wait for the World of Warcraft window to be available"
        )
        self.window_patterns = window_patterns

    def run(self) -> bool:
        # 1 Wait for the window to be available
        logger.info("Step: Waiting for the World of Warcraft window")
        ok, _info = XDO.Window.wait(self.window_patterns)
        if not ok:
            logger.error("Could not find the World of Warcraft window")
            raise TaskError(self.name, "Could not find the World of Warcraft window")

        # 2 Focus the window
        logger.info("Step: Focusing the World of Warcraft window")
        if not XDO.Window.focus(self.window_patterns):
            logger.error("Could not focus the World of Warcraft window")
            raise TaskError(self.name, "Could not focus the World of Warcraft window")

        # 3 Return success
        return True
