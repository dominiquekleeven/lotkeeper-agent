import os
import subprocess
import sys
from pathlib import Path

from loguru import logger

from open_ah_agent.agents.auction_house_agent import AuctionHouseAgent

from .config import ENV


def start_wow_process() -> subprocess.Popen[bytes] | None:
    """Start the WoW executable using Wine."""
    data_dir = Path("/data")
    wow_executable = os.environ.get("WOW_EXE", "WoW.exe")

    logger.info(f"Looking for {wow_executable} in {data_dir}")

    if not data_dir.exists():
        logger.error(f"Data directory {data_dir} does not exist")
        return None

    wow_path = data_dir / wow_executable
    if not wow_path.exists():
        logger.error(f"{wow_executable} not found in {data_dir}")
        logger.info("Available files in /data:")
        try:
            for item in data_dir.iterdir():
                logger.info(f"  {item.name}")
        except Exception as e:
            logger.error(f"Could not list directory contents: {e}")
        return None

    logger.info(f"Found {wow_executable}, starting game...")

    # Set up Wine environment
    wine_env = os.environ.copy()
    wine_env.update({"WINEDEBUG": "-all", "WINEPREFIX": "/home/wineuser/.wine", "DISPLAY": ":99"})

    try:
        # Start WoW with Wine
        process = subprocess.Popen(
            ["wine", str(wow_path)],
            cwd=str(data_dir),
            env=wine_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info(f"Wine started with PID: {process.pid}")
        return process
    except Exception as e:
        logger.error(f"Failed to start WoW: {e}")
        return None


def cleanup_wow_process(wow_process: subprocess.Popen[bytes] | None) -> None:
    """Cleanup the WoW process."""
    if wow_process and wow_process.poll() is None:
        logger.info("Shutting down WoW process...")
        wow_process.terminate()
        wow_process.wait()
        logger.info("WoW process shut down")


if __name__ == "__main__":
    logger.info("===== OpenAH Agent =====")

    # Start WoW first
    wow_process = start_wow_process()
    if not wow_process:
        logger.error("Failed to start WoW, exiting")
        sys.exit(1)

    # Handle the configured mode
    match ENV.IDLE_MODE:
        case True:
            logger.info("Idle mode, keeping WoW process running...")
            try:
                wow_process.wait()
            except KeyboardInterrupt:
                logger.info("Received interrupt, shutting down...")
                cleanup_wow_process(wow_process)
        case False:
            logger.info("Auto running agent tasks...")
            try:
                auction_house_agent = AuctionHouseAgent()
                auction_house_agent.run()
            except Exception as e:
                logger.error(f"Agent failed to run tasks: {e}")
            finally:
                cleanup_wow_process(wow_process)
