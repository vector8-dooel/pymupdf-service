from pydantic import BaseModel, Field
from typing import Optional


class ParseConfig(BaseModel):
    footer_margin: Optional[int] = Field(
        None, description="Margin from the bottom of the page to ignore as footer."
    )
    header_margin: Optional[int] = Field(
        None, description="Margin from the top of the page to ignore as header."
    )
    no_image_text: Optional[bool] = Field(
        None, description="Whether to exclude text overlaid on images."
    )
    tolerance: Optional[int] = Field(
        None, description="Tolerance for merging table bounding boxes."
    )
