from pydantic_settings import BaseSettings

DEFAULT_AGENT_TOKEN = "1234567890"


class AppEnvironment(BaseSettings):
    """Application environment settings."""

    # --- Agent ---
    OAH_AGENT_TOKEN: str = DEFAULT_AGENT_TOKEN

    # Automatically run tasks
    IDLE_MODE: bool = True

    # --- Credentials ---
    WOW_USERNAME: str = ""
    WOW_PASSWORD: str = ""

    # --- Discord ---
    DISCORD_WEBHOOK_URL: str = ""


ENV = AppEnvironment()
