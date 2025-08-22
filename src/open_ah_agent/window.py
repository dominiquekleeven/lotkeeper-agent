import subprocess
import time
from dataclasses import dataclass

from loguru import logger

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


@dataclass
class WindowInfo:
    title: str
    id: str


class Window:
    @staticmethod
    def wait(window_patterns: list[str] = WOW_WINDOW_PATTERNS, timeout: int = 60) -> tuple[bool, WindowInfo]:
        start_time = time.time()
        while time.time() - start_time < timeout:
            for pattern in window_patterns:
                try:
                    result = subprocess.run(
                        ["xdotool", "search", "--name", pattern], check=False, capture_output=True, text=True, timeout=5
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
    def focus(window_patterns: list[str] = WOW_WINDOW_PATTERNS) -> bool:
        for pattern in window_patterns:
            try:
                result = subprocess.run(
                    ["xdotool", "search", "--name", pattern], check=False, capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    window_id = result.stdout.strip().split("\n")[0]
                    activate_result = subprocess.run(
                        ["xdotool", "windowactivate", window_id], check=False, capture_output=True, text=True, timeout=5
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
