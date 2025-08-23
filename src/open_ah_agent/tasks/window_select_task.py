from loguru import logger

from open_ah_agent.common.xdo import XDO
from open_ah_agent.tasks.agent_task import AgentTask, TaskError, TaskErrorText


class WindowSelectTask(AgentTask):
    def __init__(self) -> None:
        super().__init__(name="Wait for Game Window", description="Wait for the WoW window to be available")

    def run(self) -> bool:
        # 1 Wait for the window to be available
        logger.info("Step: Waiting for WoW window")
        ok, _info = XDO.Window.wait()
        if not ok:
            logger.error("Could not find WoW window")
            raise TaskError(TaskErrorText.COULD_NOT_FIND_WINDOW)

        # 2 Focus the window
        logger.info("Step: Focusing WoW window")
        if not XDO.Window.focus():
            logger.error("Could not focus WoW window")
            raise TaskError(TaskErrorText.COULD_NOT_FOCUS_WINDOW)

        # 3 Return success
        return True
