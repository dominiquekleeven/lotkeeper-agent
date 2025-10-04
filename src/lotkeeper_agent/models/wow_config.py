from enum import Enum

from pydantic import BaseModel


class WowFaction(Enum):
    ALLIANCE = "alliance"
    HORDE = "horde"
    CROSSFACTION = "crossfaction"


class WoWAccount(BaseModel):
    """Represents a single WoW account configuration."""

    username: str
    realm: str
    password: str
    faction: WowFaction = WowFaction.CROSSFACTION

    def get_realm_name_with_faction(self) -> str:
        """Get the realm name with the faction suffix (Alliance or Horde)"""

        match self.faction:
            case WowFaction.ALLIANCE:
                return f"{self.realm} Alliance"
            case WowFaction.HORDE:
                return f"{self.realm} Horde"
            case WowFaction.CROSSFACTION:
                return f"{self.realm}"


class WoWConfig(BaseModel):
    """Represents the complete WoW configuration with multiple accounts."""

    accounts: list[WoWAccount]
