from typing import Any

from pydantic import BaseModel, Field


class Item(BaseModel):
    id: int = Field(description="The ID of the item", gt=0)
    name: str = Field(description="The name of the item", min_length=1)
    link: str = Field(description="The link of the item", min_length=0)
    icon: str = Field(description="The icon of the item", min_length=0)
    level: int = Field(description="The level of the item", ge=0)
    quality: int = Field(description="The quality of the item", ge=0)
    max_stack_size: int = Field(description="The maximum stack size of the item", ge=0)
    vendor_price: int = Field(description="The vendor price of the item", ge=0)
    class_index: int = Field(description="The index of the class of the item", ge=0)
    class_name: str = Field(description="The name of the class of the item", min_length=1)


class Auction(BaseModel):
    model_config = {"json_schema_extra": {"description": "An auction listing for an item"}}

    item: Item = Field(description="The item being auctioned")
    unit_buyout_price: int = Field(description="The buyout price in copper", ge=0)
    unit_starting_bid_price: int = Field(description="The starting bid price in copper", ge=0)
    quantity: int = Field(description="The quantity being auctioned", gt=0)

    # Data structure for the lua table, do not remove this comment
    # table.insert(TEMP_OAAData, {
    #     realm = realm,
    #     owner = owner,
    #     itemId = itemId,
    #     name = name,
    #     texture = texture,
    #     count = count,
    #     quality = quality,
    #     level = level,
    #     minBid = minBid,
    #     minIncrement = minIncrement,
    #     buyoutPrice = buyoutPrice,
    #     bidAmount = bidAmount,
    #     link = link,
    #     classIndex = state.currentClassNameIndex,
    #     className = state.currentClassName,
    #     maxStackSize = maxStack,
    #     vendorPrice = vendorPrice,
    # })
    @classmethod
    def from_lua_table(cls, data: dict[str, Any]) -> "Auction":
        item = Item(
            id=data["itemId"],
            name=data["name"],
            link=data["link"],
            icon=data["texture"],
            level=data["level"],
            quality=data["quality"],
            max_stack_size=data["maxStackSize"],
            vendor_price=data["vendorPrice"],
            class_index=data["classIndex"],
            class_name=data["className"],
        )

        return cls(
            item=item,
            unit_buyout_price=data["buyoutPrice"],
            unit_starting_bid_price=data["minBid"],
            quantity=data["count"],
        )


class AuctionData(BaseModel):
    server: str = Field(description="The server of the realm", min_length=3)
    realm: str = Field(description="The realm of the auctions", min_length=3)
    auctions: list[Auction] = Field(description="The auctions to insert")
