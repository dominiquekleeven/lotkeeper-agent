import subprocess
import time

from loguru import logger


class Interact:
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

    @staticmethod
    def type_text(text: str, delay: float = 0.5) -> bool:
        time.sleep(delay)
        return Interact.run_xdotool("type", text)

    @staticmethod
    def press_key(key: str, delay: float = 0.3) -> bool:
        time.sleep(delay)
        return Interact.run_xdotool("key", key)
