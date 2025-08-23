import subprocess
import time
from dataclasses import dataclass

from loguru import logger

from open_ah_agent.tasks.agent_task import TimeUtils

WINDOW_PATTERNS = [
    "World of Warcraft",
    "WoW",
    "Ascension",
    "Turtle WoW",
    "Project Epoch",
    "Warmane",
    "ChromieCraft",
    ".*Warcraft.*",
]


@dataclass
class WindowInfo:
    title: str
    id: str


class XDO:
    @staticmethod
    def run_xdotool(*args: str) -> bool:
        try:
            cmd = ["xdotool", *list(args)]
            result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.warning(f"xdotool command failed: {' '.join(cmd)}, stderr: {result.stderr}")
                return False
            return True
        except subprocess.TimeoutExpired:
            logger.error("xdotool command timed out")
            return False
        except Exception as e:
            logger.error(f"Failed to run xdotool: {e}")
            return False

    class Window:
        @staticmethod
        def wait(window_patterns: list[str] = WINDOW_PATTERNS, timeout: int = 60) -> tuple[bool, WindowInfo]:
            start_time = time.time()
            while time.time() - start_time < timeout:
                for pattern in window_patterns:
                    try:
                        result = subprocess.run(
                            ["xdotool", "search", "--name", pattern],
                            check=False,
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        if result.returncode == 0 and result.stdout.strip():
                            window_id = result.stdout.strip().split("\n")[0]
                            title_result = subprocess.run(
                                ["xdotool", "getwindowname", window_id],
                                check=False,
                                capture_output=True,
                                text=True,
                                timeout=5,
                            )
                            actual_title = title_result.stdout.strip() if title_result.returncode == 0 else pattern
                            logger.info(f"Found WoW window: '{actual_title}' (ID: {window_id})")
                            return True, WindowInfo(title=actual_title, id=window_id)
                    except subprocess.TimeoutExpired:
                        continue
                    except Exception:
                        continue

                time.sleep(2)

            logger.error(f"No WoW window found within {timeout} seconds")
            return False, WindowInfo(title="", id="")

        @staticmethod
        def focus(window_patterns: list[str] = WINDOW_PATTERNS) -> bool:
            for pattern in window_patterns:
                try:
                    result = subprocess.run(
                        ["xdotool", "search", "--name", pattern], check=False, capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        window_id = result.stdout.strip().split("\n")[0]
                        activate_result = subprocess.run(
                            ["xdotool", "windowactivate", window_id],
                            check=False,
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        if activate_result.returncode == 0:
                            return True
                        else:
                            logger.warning(f"Found window but failed to activate it: {activate_result.stderr}")
                except subprocess.TimeoutExpired:
                    continue
                except Exception as e:
                    logger.warning(f"Error trying pattern '{pattern}': {e}")
                    continue

            logger.error("Could not find WoW window")
            return False

    class Interact:
        @staticmethod
        def type_text(text: str) -> bool:
            for char in text:
                TimeUtils.type_delay()
                if not XDO.run_xdotool("type", char):
                    return False

            return True

        @staticmethod
        def press_key(key: str) -> bool:
            TimeUtils.key_delay()
            return XDO.run_xdotool("key", key)
