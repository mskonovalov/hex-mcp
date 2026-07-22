"""Runtime configuration."""

from enum import StrEnum

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPMode(StrEnum):
    READ_ONLY = "read-only"
    FULL = "full"


class Transport(StrEnum):
    STDIO = "stdio"
    HTTP = "http"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HEX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_token: SecretStr = Field(min_length=1)
    api_base_url: str = "https://app.hex.tech/api"
    openapi_spec: str = "https://static.hex.site/openapi.json"
    mcp_mode: MCPMode = MCPMode.READ_ONLY
    transport: Transport = Transport.STDIO
    http_host: str = "127.0.0.1"
    http_port: int = Field(default=8000, ge=1, le=65535)
    http_path: str = "/mcp"
    request_timeout_seconds: float = Field(default=30.0, gt=0)
