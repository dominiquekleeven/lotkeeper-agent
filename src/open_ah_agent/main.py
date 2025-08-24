import sys

from loguru import logger

from open_ah_agent.agents.auction_house_agent import AuctionHouseAgent
from open_ah_agent.common.xdo_game import XDOGame
from open_ah_agent.config import ENV, AgentMode

if __name__ == "__main__":
    logger.info("===== OpenAH Agent =====")

    # Quick pre-checks
    # 1 Are we configured properly?
    if not ENV.WOW_USERNAME or not ENV.WOW_PASSWORD:
        logger.error("WOW_USERNAME or WOW_PASSWORD not set in config")
        sys.exit(1)

    if not ENV.WOW_SERVER or not ENV.WOW_REALM:
        logger.error("WOW_SERVER or WOW_REALM not set in config")
        sys.exit(1)

    # 2 Is the WoW executable available?
    wow_path = XDOGame.Paths.get_wow_executable_path()
    if not wow_path:
        logger.error("Failed to find WoW executable, exiting")
        sys.exit(1)

    match ENV.AGENT_MODE:
        # Manual mode is used for configuration and debugging
        case AgentMode.MANUAL:
            logger.info("Manual mode, starting WoW process...")
            wow_process = XDOGame.Process.start()
            if not wow_process:
                logger.error("Failed to start WoW, exiting")
                sys.exit(1)
            try:
                wow_process.wait()
            except KeyboardInterrupt:
                logger.info("Received interrupt, shutting down...")
                XDOGame.Process.cleanup(wow_process)

        # Auto mode is used to automatically run all configured tasks
        case AgentMode.AUTO:
            logger.info("Auto running agent tasks...")
            auction_house_agent = AuctionHouseAgent()
            auction_house_agent.start()

            logger.info("All agents have completed their tasks")
