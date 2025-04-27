# app/api/parse.py
from typing import Optional

from fastapi import UploadFile, File, Form

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from src.config.injection import Container
from src.models.data_schemas import ParseConfig

router = APIRouter(prefix="/v1/pdf", tags=["pdf"])


@router.post("/parse")
@inject
async def parse_pdf(
    file: UploadFile = File(...),
    footer_margin: Optional[int] = Form(None),
    header_margin: Optional[int] = Form(None),
    no_image_text: Optional[bool] = Form(None),
    tolerance: Optional[int] = Form(None),
    pdf_parse_service=Depends(Provide[Container.pdf_parse_service]),
):
    parse_config = ParseConfig(
        footer_margin=footer_margin,
        header_margin=header_margin,
        no_image_text=no_image_text,
        tolerance=tolerance,
    )
    return await pdf_parse_service.parse(file, parse_config)
