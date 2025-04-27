# app/main.py
from fastapi import FastAPI
from uvicorn import Config, Server

from src.api.health_router import health_router
from src.api.parse import router
from src.config.config import ServerSettings
from src.config.injection import Container


def create_app() -> FastAPI:
    container = Container()

    app = FastAPI(title="PyMuPDF Extraction Service")

    app.container = container

    app.include_router(router, tags=["pdf"])
    app.include_router(health_router, tags=["Health"])

    return app


if __name__ == "__main__":
    app = create_app()
    # Run server
    server = Server(Config(app=app, host=ServerSettings.HOST, port=ServerSettings.PORT))
    server.run()
