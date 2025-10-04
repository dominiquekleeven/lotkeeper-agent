from lotkeeper_agent.agents.wow_agent import WoWAgent
from lotkeeper_agent.models.wow_config import WoWAccount, WowFaction
from lotkeeper_agent.tasks.login_task import LoginTask
from lotkeeper_agent.tasks.scan_auctions_task import ScanAuctionsTask
from lotkeeper_agent.tasks.target_interact_creature_task import TargetInteractCreatureTask


class AuctioneerNames:
    AUCTIONEER_GOLOTHAS = "Auctioneer Golothas"
    AUCTIONEER_CAIN = "Auctioneer Cain"


class AuctionHouseAgent(WoWAgent):
    """
    Agent for the Auction House, includes logging in and targeting the auctioneer.
    """

    def __init__(self, account: WoWAccount) -> None:
        super().__init__(f"{account.get_realm_name_with_faction()} • Auction House Agent", account)

        # Default to the auctioneer in Darnassus
        auctioneer = AuctioneerNames.AUCTIONEER_GOLOTHAS

        # For horde we use the undeed auctioneer in Undercity
        if account.faction == WowFaction.HORDE:
            auctioneer = AuctioneerNames.AUCTIONEER_CAIN

        self.add_tasks(
            [
                LoginTask(account),
                TargetInteractCreatureTask(auctioneer),
                ScanAuctionsTask(account),
            ]
        )
