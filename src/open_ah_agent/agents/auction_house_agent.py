from open_ah_agent.agents.wow_agent import WoWAgent
from open_ah_agent.tasks.login_task import LoginTask
from open_ah_agent.tasks.scan_auctions_task import ScanAuctionsTask
from open_ah_agent.tasks.target_interact_creature_task import TargetInteractCreatureTask


class AuctioneerNames:
    AUCTIONEER_FITCH = "Auctioneer Fitch"


class AuctionHouseAgent(WoWAgent):
    """
    Agent for the Auction House, includes logging in and targeting the auctioneer.
    """

    def __init__(self) -> None:
        super().__init__("Auction House Agent")
        tasks = [LoginTask(), TargetInteractCreatureTask(AuctioneerNames.AUCTIONEER_FITCH), ScanAuctionsTask()]
        self.add_tasks(tasks)
