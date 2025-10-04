from loguru import logger

from lotkeeper_agent.agents.base_agent import AgentError, BaseAgent
from lotkeeper_agent.common.xdo_game import XDOGame
from lotkeeper_agent.models.wow_config import WoWAccount
from lotkeeper_agent.tasks.select_window_task import SelectWindowTask

WOW_WINDOW_PATTERNS = [
    "World of Warcraft",
    "WoW",
    "Ascension",
    "Turtle WoW",
    "Project Epoch",
    "Warmane",
    "ChromieCraft",
    ".*Warcraft.*",
]


class WoWAgent(BaseAgent):
    """
    WoW Agent, includes starting and stopping the WoW process as its setup and teardown processes

    Agents that rely on the WoW process should use this as their base agent.
    """

    def __init__(self, name: str, account: WoWAccount) -> None:
        super().__init__(name)
        self.account = account
        self.add_task(SelectWindowTask(WOW_WINDOW_PATTERNS))

    def setup(self) -> None:
        logger.info(f"Setting up WoW process for {self.account.username[:5]}")
        XDOGame.Paths.set_wtf_variable(XDOGame.Paths.WTFVariables.REALM_NAME, self.account.realm)

        logger.info("Starting the WoW process")
        self.window_process = XDOGame.Process.start()
        if not self.window_process:
            raise AgentError(self.name, "Failed to start WoW, exiting")

    def teardown(self) -> None:
        logger.info("Stopping the WoW process")
        XDOGame.Process.cleanup(self.window_process)
        self.window_process = None
