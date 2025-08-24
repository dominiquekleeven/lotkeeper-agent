import os
import subprocess
from pathlib import Path
from typing import Any

from loguru import logger
import lupa

from open_ah_agent.common.xdo import XDO
from open_ah_agent.config import ENV


class XDOGame:
    """Utility class for WoW related operations using XDO"""

    class Game:
        """Game related operations"""

        @staticmethod
        def enter_chat_command(command: str) -> bool:
            """Enter a chat command"""

            if not command.startswith("/"):
                command = f"/{command}"

            XDO.Interact.press_key("Return")  # Open chat
            XDO.Interact.press_key("ctrl+a")  # Select all
            XDO.Interact.type_text(command)  # Type text
            XDO.Interact.press_key("Return")  # Send
            return True

        @staticmethod
        def reload() -> bool:
            """Reload the game"""

            XDOGame.Game.enter_chat_command("/reload")
            return True

        @staticmethod
        def target_creature(creature_name: str) -> bool:
            """Target a creature by name"""

            XDOGame.Game.enter_chat_command(f"/target {creature_name}")
            return True

    class Paths:
        """Path related operations"""

        @staticmethod
        def get_data_dir() -> Path:
            """Get the path to the data directory"""

            return Path("/data")

        @staticmethod
        def get_wow_executable_path() -> Path | None:
            """Get the path to the WoW executable"""

            data_dir = XDOGame.Paths.get_data_dir()
            wow_executable = os.environ.get("WOW_EXE", "WoW.exe")
            wow_path = data_dir / wow_executable

            if not data_dir.exists():
                logger.error(f"Data directory {data_dir} does not exist")
                return None

            if not wow_path.exists():
                logger.error(f"{wow_executable} not found in {data_dir}")
                return None

            return wow_path

        @staticmethod
        def get_saved_variables_path() -> Path | None:
            """Get the path to the saved variables file"""
            username = ENV.WOW_USERNAME
            username = username.lower()

            data_dir = XDOGame.Paths.get_data_dir()
            saved_variables_path = data_dir / "WTF" / "Account" / username / "SavedVariables" / "OpenAuctionScanner.lua"

            # Debug logging to see what we're looking for
            logger.debug(f"Looking for saved variables at: {saved_variables_path}")
            logger.debug(f"Username (lowercase): {username}")

            # Check if saved variables path exists
            if not saved_variables_path.exists():
                logger.error(f"Saved variables file {saved_variables_path} does not exist")
                return None

            return saved_variables_path

        @staticmethod
        def parse_saved_variables_lua(saved_variables_path: Path, variable_name: str) -> Any:
            """Parse a WoW SavedVariables.lua file and return the given variable as a Python dict/list."""
            lua = lupa.LuaRuntime(unpack_returned_tuples=True)

            # Load file contents
            with open(saved_variables_path, "r", encoding="utf-8") as f:
                lua_code = f.read()

            # Execute Lua code (defines the global tables)
            lua.execute(lua_code)

            # Get the specific saved variable (e.g., "MyAddonDB")
            lua_table = lua.globals()[variable_name]

            # Convert Lua table to Python recursively
            def lua_to_python(obj: Any) -> Any:
                if lupa.lua_type(obj) == "table":
                    # Decide list vs dict
                    keys = list(obj.keys())
                    if all(isinstance(k, (int, float)) for k in keys):
                        return [lua_to_python(obj[k]) for k in sorted(keys)]
                    else:
                        return {k: lua_to_python(v) for k, v in obj.items()}
                else:
                    return obj

            return lua_to_python(lua_table)

    class Process:
        """Process related operations"""

        @staticmethod
        def start() -> subprocess.Popen[bytes] | None:
            """Start the WoW executable using Wine."""

            wow_path = XDOGame.Paths.get_wow_executable_path()
            if not wow_path:
                logger.error("Failed to find WoW executable, exiting")
                return None

            logger.info(f"Found {wow_path}, starting game...")

            # Set up Wine environment
            wine_env = os.environ.copy()
            wine_env.update({"WINEDEBUG": "-all", "WINEPREFIX": "/home/wineuser/.wine", "DISPLAY": ":99"})

            try:
                # Start WoW with Wine
                process = subprocess.Popen(
                    ["wine", str(wow_path)],
                    cwd=str(wow_path.parent),
                    env=wine_env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                logger.info(f"Wine started with PID: {process.pid}")
                return process
            except Exception as e:
                logger.error(f"Failed to start WoW: {e}")
                return None

        @staticmethod
        def cleanup(wow_process: subprocess.Popen[bytes] | None) -> None:
            """Cleanup the WoW process."""

            if not wow_process:
                logger.warning("Requested to cleanup WoW process, but no process was found")
                return

            if wow_process.poll() is None:
                logger.info("Shutting down WoW process...")
                wow_process.terminate()
                wow_process.wait()
                logger.info("WoW process shut down")
