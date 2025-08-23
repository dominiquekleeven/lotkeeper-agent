from open_ah_agent.agents.base_agent import BaseAgent
from open_ah_agent.tasks.interact_target_task import InteractTargetTask
from open_ah_agent.tasks.login_task import LoginTask
from open_ah_agent.tasks.scan_auctions_task import ScanAuctionsTask
from open_ah_agent.tasks.window_select_task import WindowSelectTask


class AuctionHouseAgent(BaseAgent):
    """Agent for the Auction House"""

    def __init__(self) -> None:
        super().__init__("Auction House Agent")
        tasks = [
            WindowSelectTask(),
            LoginTask(),
            InteractTargetTask(),
            ScanAuctionsTask(),
        ]
        self.add_tasks(tasks)
