# app/api/routes.py
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from app.parser.pdf_parser import PymupdfParser

router = APIRouter()

@router.post("/parse")
async def parse_pdf(file: UploadFile = File(...)):
    content = await file.read()

    # Use default values internally
    parser = PymupdfParser(
        max_processors=2,
        footer_margin=10,
        header_margin=10,
        no_image_text=False,
        tolerance=20,
    )

    elements, num_pages = parser.parse(content)

    # Convert elements to JSON-serializable format
    serializable_elements = [
        {
            "content": element.text,
            "content_type": element.category,
            "start_page": element.start_page,
            "end_page": element.end_page
        }
        for element in elements
    ]

    return {
        "elements": serializable_elements,
        "num_pages": num_pages
    }