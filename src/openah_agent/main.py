import sys
import time

# Configure logger globally
from loguru import logger

from openah_agent.agents.auction_house_agent import AuctionHouseAgent
from openah_agent.common.app_info import get_app_info
from openah_agent.common.xdo_game import XDOGame
from openah_agent.config import ENV, AgentMode
from openah_agent.scheduler import AgentScheduler

if __name__ == "__main__":
    logger.info(f"===== OpenAH Agent v{get_app_info().version} =====")

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

    # 3 Set default WTF variables (realm and UI scale)
    XDOGame.Paths.set_wtf_variable(XDOGame.Paths.WTFVariables.REALM_NAME, ENV.WOW_REALM)
    XDOGame.Paths.set_wtf_variable(XDOGame.Paths.WTFVariables.UI_SCALE, "1.0")

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
            logger.info("Starting agent scheduler...")
            scheduler = AgentScheduler()
            scheduler.start()

            # Define agents
            auction_house_agent = (
                AuctionHouseAgent()
                .with_interval_hours(1)
                .with_max_retries(1)
                .with_time_between_tasks(10.0)
            )

            # Add agents
            scheduler.add_agent(auction_house_agent, run_immediately=True)
            logger.info("Agent scheduler is running. Press Ctrl+C to stop.")

            # Keep main thread alive while scheduler runs in background
            try:
                while scheduler.is_running():
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutting down agent scheduler...")
                scheduler.stop()
                logger.info("Agent scheduler stopped")
