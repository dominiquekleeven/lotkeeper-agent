from typing import Any

from pydantic import BaseModel, Field
from openah_agent.models.item_metadata import ItemMetadata

class Auction(BaseModel):
    model_config = {"json_schema_extra": {"description": "An auction listing for an item"}}

    item_id: int = Field(description="The ID of the item being auctioned", gt=0)
    item_metadata: ItemMetadata = Field(description="The metadata for the item being auctioned")
    item_buyout_price: int = Field(description="The buyout price of the auction in copper", ge=0)
    item_starting_bid_price: int = Field(description="The starting bid price of the auction in copper", ge=0)
    item_quantity: int = Field(description="The quantity of the item being auctioned", ge=0)

    @classmethod
    def from_lua_table(cls, data: dict[str, Any]) -> "Auction":
        item_metadata = ItemMetadata(
            item_id=data["itemId"],
            item_name=data["name"],
            item_link=data["link"],
            item_icon=data["texture"],
            item_level=data["level"],
            item_quality=data["quality"],
            item_max_stack_size=data["maxStackSize"],
            item_vendor_price=data["vendorPrice"],
            item_class_index=data["classIndex"],
            item_class_name=data["className"],
        )
        
        return cls(
            item_id=data["itemId"],
            item_metadata=item_metadata,
            item_buyout_price=data["buyoutPrice"],
            item_starting_bid_price=data["minBid"],
            item_quantity=data["count"],
        )


class AuctionData(BaseModel):
    server: str = Field(description="The server of the realm", min_length=3)
    realm: str = Field(description="The realm of the auctions", min_length=3)
    auctions: list[Auction] = Field(description="The auctions to insert")
