from pydantic import BaseModel, Field

class ItemMetadata(BaseModel):
    item_id: int = Field(description="The ID of the item", gt=0)
    item_name: str = Field(description="The name of the item", min_length=1)
    item_link: str = Field(description="The link of the item", min_length=0)
    item_icon: str = Field(description="The icon of the item", min_length=0)
    item_level: int = Field(description="The level of the item", ge=0)
    item_quality: int = Field(description="The quality of the item", ge=0)
    item_max_stack_size: int = Field(description="The maximum stack size of the item", ge=0)
    item_vendor_price: int = Field(description="The vendor price of the item", ge=0)
    item_class_index: int = Field(description="The index of the class of the item", ge=0)
    item_class_name: str = Field(description="The name of the class of the item", min_length=1)

