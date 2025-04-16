# app/main.py
from fastapi import FastAPI
from app.api.routes import router
# from app.core.logging_config import setup_logging

app = FastAPI(title="PyMuPDF Extraction Service")
# setup_logging()

app.include_router(router, prefix="/api/v1", tags=["pdf"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}