# app/api/parse.py
from fastapi import UploadFile, File

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from src.config.injection import Container

router = APIRouter(prefix="/v1/pdf", tags=["pdf"])


@router.post("/parse")
@inject
async def parse_pdf(
    file: UploadFile = File(...),
    pdf_parse_service=Depends(Provide[Container.pdf_parse_service]),
):
    return await pdf_parse_service.parse(file)
