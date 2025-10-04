from enum import Enum

from pydantic_settings import BaseSettings


class AgentMode(Enum):
    MANUAL = "MANUAL"
    AUTO = "AUTO"


class AppEnvironment(BaseSettings):
    """Application environment settings."""

    # --- Agent ---
    LOT_AGENT_TOKEN: str = ""
    LOT_HOST: str = ""

    AGENT_NAME: str = "Lotkeeper Agent"
    AGENT_IMAGE_URL: str = "https://i.imgur.com/guFPcId.png"

    # Run the agent in manual or auto mode
    AGENT_MODE: AgentMode = AgentMode.MANUAL

    # --- WoW ---
    WOW_SERVER: str = ""
    WOW_EXE: str = "WoW.exe"

    # --- Discord ---
    DISCORD_WEBHOOK_URL: str = ""


ENV = AppEnvironment()
