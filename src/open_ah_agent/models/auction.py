from typing import Any
from pydantic import BaseModel, Field


class Auction(BaseModel):
    seller: str = Field(description="The name of the seller", min_length=3)
    item_id: int = Field(description="The ID of the item being auctioned", gt=0)
    item_name: str = Field(description="The name of the item being auctioned", min_length=3)
    item_icon: str = Field(description="The icon of the item being auctioned", min_length=3)
    item_level: int = Field(description="The level of the item being auctioned", gt=0)
    item_quality: int = Field(description="The quality of the item being auctioned", ge=0)
    item_buyout_price: int = Field(description="The buyout price of the auction in copper", gt=0)
    item_starting_bid_price: int = Field(description="The starting bid price of the auction in copper", gt=0)
    item_quantity: int = Field(description="The quantity of the item being auctioned", gt=0)

    @classmethod
    def from_lua_table(cls, data: dict[str, Any]) -> "Auction":
        return Auction(
            seller=data["seller"],
            item_id=data["itemId"],
            item_name=data["name"],
            item_icon=data["texture"],
            item_level=data["level"],
            item_quality=data["quality"],
            item_buyout_price=data["buyoutPrice"],
            item_starting_bid_price=data["minBid"],
            item_quantity=data["count"],
        )


class AuctionData(BaseModel):
    server: str = Field(description="The server of the realm", min_length=3)
    realm: str = Field(description="The realm of the auctions", min_length=3)
    auctions: list[Auction] = Field(description="The auctions to insert")
