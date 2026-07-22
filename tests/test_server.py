from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

import hex_mcp.server as server_module
from hex_mcp.config import MCPMode, Settings, Transport
from hex_mcp.openapi import LoadedOpenAPI
from hex_mcp.server import ServerBundle, build_server, create_server, run


def settings(mode: MCPMode) -> Settings:
    return Settings(api_token=SecretStr("test-token"), mcp_mode=mode)


async def tool_names(bundle: ServerBundle) -> set[str]:
    tools = await bundle.provider.list_tools()
    return {tool.name for tool in tools}


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (MCPMode.READ_ONLY, {"list_projects", "export_project"}),
        (
            MCPMode.FULL,
            {
                "list_projects",
                "create_project",
                "export_project",
                "update_project",
                "delete_project",
            },
        ),
    ],
)
async def test_mode_controls_registered_tools(
    mode: MCPMode,
    expected: set[str],
    loaded_openapi: LoadedOpenAPI,
) -> None:
    bundle = build_server(settings(mode), loaded_openapi)
    try:
        assert await tool_names(bundle) == expected
    finally:
        await bundle.api_client.aclose()


async def test_api_client_uses_bearer_token(loaded_openapi: LoadedOpenAPI) -> None:
    bundle = build_server(settings(MCPMode.READ_ONLY), loaded_openapi)
    try:
        assert bundle.api_client.headers["Authorization"] == "Bearer test-token"
    finally:
        await bundle.api_client.aclose()


async def test_create_server_loads_configured_spec(
    tmp_path: Path,
    openapi_document: dict[str, object],
) -> None:
    source = tmp_path / "openapi.json"
    source.write_text(json.dumps(openapi_document), encoding="utf-8")
    configured = Settings(
        api_token=SecretStr("test-token"),
        openapi_spec=str(source),
    )

    bundle = await create_server(configured)
    try:
        assert bundle.openapi.source == str(source)
    finally:
        await bundle.api_client.aclose()


@pytest.mark.parametrize("transport", [Transport.STDIO, Transport.HTTP])
async def test_run_starts_configured_transport(
    transport: Transport,
    loaded_openapi: LoadedOpenAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured = Settings(
        api_token=SecretStr("test-token"),
        transport=transport,
    )
    bundle = build_server(configured, loaded_openapi)
    stdio = AsyncMock()
    http = AsyncMock()
    monkeypatch.setattr(bundle.server, "run_stdio_async", stdio)
    monkeypatch.setattr(bundle.server, "run_http_async", http)

    async def fake_create_server(_settings: Settings) -> ServerBundle:
        return bundle

    monkeypatch.setattr(server_module, "create_server", fake_create_server)
    try:
        await run(configured)
        if transport is Transport.HTTP:
            http.assert_awaited_once()
            stdio.assert_not_awaited()
        else:
            stdio.assert_awaited_once_with(show_banner=False)
            http.assert_not_awaited()
    finally:
        await bundle.api_client.aclose()
