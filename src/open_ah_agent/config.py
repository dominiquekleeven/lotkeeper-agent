from enum import Enum

from pydantic_settings import BaseSettings

DEFAULT_AGENT_TOKEN = "1234567890"


class AgentMode(Enum):
    MANUAL = "MANUAL"
    AUTO = "AUTO"


class AppEnvironment(BaseSettings):
    """Application environment settings."""

    # --- Agent ---
    OAH_AGENT_TOKEN: str = DEFAULT_AGENT_TOKEN

    AGENT_NAME: str = "OpenAH Agent"
    AGENT_IMAGE_URL: str = "https://i.imgur.com/77FVlal.jpeg"

    # Run the agent in manual or auto mode
    AGENT_MODE: AgentMode = AgentMode.MANUAL

    # --- Credentials ---
    WOW_USERNAME: str = ""
    WOW_PASSWORD: str = ""
    WOW_SERVER: str = ""
    WOW_REALM: str = ""

    # --- Discord ---
    DISCORD_WEBHOOK_URL: str = ""


ENV = AppEnvironment()
