from pydantic_settings import BaseSettings

DEFAULT_AGENT_TOKEN = "1234567890"


class AppEnvironment(BaseSettings):
    """Application environment settings."""

    # --- Agent ---
    OAH_AGENT_TOKEN: str = DEFAULT_AGENT_TOKEN

    # Starts doing agent tasks
    AGENT_MODE: bool = False

    # --- Credentials ---
    WOW_USERNAME: str = ""
    WOW_PASSWORD: str = ""


ENV = AppEnvironment()
