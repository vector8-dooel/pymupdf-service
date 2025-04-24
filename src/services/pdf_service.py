# app/services/pdf_service.py
from concurrent.futures import ProcessPoolExecutor
from typing import Optional

from fastapi import UploadFile
from src.models.data_schemas import ParseConfig

from src.parser_lib.pdf_parser import PymupdfParser


class PDFParseService:
    """Thin wrapper around PymupdfParser so we construct it only once using a config dict."""

    def __init__(self, config: dict = None):
        # Merge provided config with defaults
        config = config or {}
        max_processors = config.get("max_processors", 2)
        footer_margin = config.get("footer_margin", 10)
        header_margin = config.get("header_margin", 10)
        no_image_text = config.get("no_image_text", False)
        tolerance = config.get("tolerance", 20)

        if max_processors <= 0:
            raise ValueError("Number of processors must be greater than 0")

        self._parser = PymupdfParser(
            max_processors=max_processors,
            footer_margin=footer_margin,
            header_margin=header_margin,
            no_image_text=no_image_text,
            tolerance=tolerance,
        )

        self._executor = ProcessPoolExecutor(max_workers=max_processors)

    async def parse(self, file: UploadFile, parse_config: Optional[ParseConfig]):
        """Parse the given PDF content and return elements and page count."""
        content = await file.read()
        elements, num_pages = await self._parser.parse(
            content, self._executor, parse_config
        )

        serializable_elements = [
            {
                "content": element.text,
                "content_type": element.category,
                "start_page": element.start_page,
                "end_page": element.end_page,
            }
            for element in elements
        ]

        return {"elements": serializable_elements, "num_pages": num_pages}
