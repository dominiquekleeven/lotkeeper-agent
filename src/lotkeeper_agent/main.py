import sys
import time

# Configure logger globally
from loguru import logger

from lotkeeper_agent.agents.auction_house_agent import AuctionHouseAgent
from lotkeeper_agent.agents.base_agent import CronExpression
from lotkeeper_agent.common.app_info import get_app_info
from lotkeeper_agent.common.xdo_game import XDOGame
from lotkeeper_agent.config import ENV, AgentMode
from lotkeeper_agent.models.wow_config import WoWConfig
from lotkeeper_agent.scheduler import AgentScheduler

if __name__ == "__main__":
    logger.info(f"===== Lotkeeper Agent v{get_app_info().version} =====")

    # Is the WoW server set?
    if not ENV.WOW_SERVER:
        logger.error("WOW_SERVER not set in config")
        sys.exit(1)

    # Is the Lotkeeper Host or Agent Token set?
    if not ENV.LOT_HOST or not ENV.LOT_AGENT_TOKEN:
        logger.error("Lotkeeper Host or Agent Token not set in config, we cannot connect to Lotkeeper API")
        sys.exit(1)

    # Is the WoW executable available?
    wow_path = XDOGame.Paths.get_wow_executable_path()
    if not wow_path:
        logger.error("Failed to find WoW executable, exiting")
        sys.exit(1)

    # Load the WoW config
    wow_config = WoWConfig.model_validate_json(open("/data/config/wow.json").read())
    if not wow_config or not wow_config.accounts or len(wow_config.accounts) == 0:
        logger.error("Failed to load WoW config or no accounts found, exiting")
        sys.exit(1)

    logger.info(f"Loaded {len(wow_config.accounts)} accounts from config")

    # Set default WTF variables (UI scale)
    XDOGame.Paths.set_wtf_variable(XDOGame.Paths.WTFVariables.UI_SCALE, "1.0")

    match ENV.AGENT_MODE:
        # Manual mode is used for configuration and debugging
        case AgentMode.MANUAL:
            logger.info("Manual mode, starting WoW process ...")
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
            logger.info("Setting up agent scheduler...")
            scheduler = AgentScheduler()

            # Define agents
            for account in wow_config.accounts:
                auction_house_agent = (
                    AuctionHouseAgent(account)
                    .with_cron_expression(CronExpression.HOURLY)
                    .with_max_retries(1)
                    .with_time_between_tasks(10.0)
                )
                # Add agent to scheduler
                scheduler.add_agent(auction_house_agent)

            # Start scheduler after all jobs are added
            logger.info("Starting agent scheduler...")
            scheduler.start()

            logger.info("Agent scheduler is running. Press Ctrl+C to stop.")

            # Keep main thread alive while scheduler runs in background
            try:
                while scheduler.is_running():
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutting down agent scheduler...")
                scheduler.stop()
                logger.info("Agent scheduler stopped")
