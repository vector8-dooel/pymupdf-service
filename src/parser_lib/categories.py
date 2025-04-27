from enum import Enum
from typing import Optional


class CategoryEnum(str, Enum):
    CAPTION = "caption"
    FOOTNOTE = "footnote"
    FORMULA = "formula"
    LIST_ITEM = "list_item"
    PAGE_FOOTER = "page_footer"
    PAGE_HEADER = "page_header"
    PICTURE = "picture"
    SECTION_HEADER = "section_header"
    TABLE = "table"
    TEXT = "text"
    TITLE = "title"
    DOCUMENT_INDEX = "document_index"
    CODE = "code"
    CHECKBOX_SELECTED = "checkbox_selected"
    CHECKBOX_UNSELECTED = "checkbox_unselected"
    FORM = "form"
    KEY_VALUE_REGION = "key_value_region"
    PARAGRAPH = "paragraph"
    REFERENCE = "reference"
    IMAGE = "image"

    def __str__(self):
        return str(self.value)


class Element:
    def __init__(
        self,
        text: str,
        category: Optional[CategoryEnum] = None,
        start_page: Optional[int] = 1,
        end_page: Optional[int] = 1,
        b64: Optional[str] = None,
    ):
        self.text = text
        self.category = category
        self.start_page = start_page
        self.end_page = end_page
        self.b64 = b64
