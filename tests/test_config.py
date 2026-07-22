from __future__ import annotations

import pytest
from pydantic import ValidationError

from hex_mcp.config import MCPMode, Settings, Transport


def test_defaults_to_read_only_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HEX_API_TOKEN", "test-token")

    settings = Settings(_env_file=None)

    assert settings.mcp_mode is MCPMode.READ_ONLY
    assert settings.transport is Transport.STDIO
    assert settings.api_base_url == "https://app.hex.tech/api"


def test_reads_full_http_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HEX_API_TOKEN", "test-token")
    monkeypatch.setenv("HEX_MCP_MODE", "full")
    monkeypatch.setenv("HEX_TRANSPORT", "http")

    settings = Settings(_env_file=None)

    assert settings.mcp_mode is MCPMode.FULL
    assert settings.transport is Transport.HTTP


def test_rejects_unknown_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HEX_API_TOKEN", "test-token")
    monkeypatch.setenv("HEX_MCP_MODE", "unsafe")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_requires_api_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HEX_API_TOKEN", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_rejects_empty_api_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HEX_API_TOKEN", "")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
