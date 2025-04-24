from pydantic_settings import BaseSettings
from pydantic import Field


class ServerConfig(BaseSettings):
    HOST: str = Field(
        env="HOST", description="host of the microservice", default="0.0.0.0"
    )
    PORT: int = Field(env="PORT", description="port of the microservice", default=8888)


ServerSettings = ServerConfig()
