from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from fastmcp import Client
from pydantic import SecretStr

import hex_mcp.server as server_module
from hex_mcp.config import MCPMode, Settings, Transport
from hex_mcp.openapi import LoadedOpenAPI, normalize_hex_openapi
from hex_mcp.server import (
    ServerBundle,
    build_server,
    create_server,
    retry_transport,
    run,
)


def settings(mode: MCPMode) -> Settings:
    return Settings(api_token=SecretStr("test-token"), mcp_mode=mode)


async def tool_names(bundle: ServerBundle) -> set[str]:
    tools = await bundle.server.list_tools()
    return {tool.name for tool in tools}


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (
            MCPMode.READ_ONLY,
            {"list_projects", "export_project", "resolve_project_url"},
        ),
        (
            MCPMode.FULL,
            {
                "list_projects",
                "create_project",
                "export_project",
                "update_project",
                "delete_project",
                "resolve_project_url",
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


async def test_tools_have_safety_annotations(loaded_openapi: LoadedOpenAPI) -> None:
    bundle = build_server(settings(MCPMode.FULL), loaded_openapi)
    try:
        provider_tools = {
            tool.name: tool for tool in await bundle.provider.list_tools()
        }
        tools = {tool.name: tool for tool in await bundle.server.list_tools()}
        list_annotations = tools["list_projects"].annotations
        export_annotations = tools["export_project"].annotations
        delete_annotations = tools["delete_project"].annotations
        resolver_annotations = tools["resolve_project_url"].annotations

        assert list_annotations is not None
        assert list_annotations.readOnlyHint is True
        assert list_annotations.destructiveHint is False
        assert export_annotations is not None
        assert export_annotations.readOnlyHint is True
        assert export_annotations.idempotentHint is True
        assert delete_annotations is not None
        assert delete_annotations.destructiveHint is True
        assert delete_annotations.idempotentHint is True
        assert resolver_annotations is not None
        assert resolver_annotations.readOnlyHint is True
        assert resolver_annotations.destructiveHint is False
        assert resolver_annotations.idempotentHint is True
        resolver_description = tools["resolve_project_url"].description
        assert resolver_description is not None
        assert "UUID" in resolver_description
        assert (
            tools["resolve_project_url"].parameters["properties"]["url"]["description"]
            == "A Hex URL containing /hex/<uuid>/ or /app/<title>-<compact-id>/."
        )
        assert tools["list_projects"].output_schema is not None
        assert (
            tools["list_projects"].output_schema
            == provider_tools["list_projects"].output_schema
        )
    finally:
        await bundle.api_client.aclose()


async def test_resolve_project_url_tool_uses_accessible_project_title(
    loaded_openapi: LoadedOpenAPI,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/projects"
        return httpx.Response(
            200,
            json={
                "values": [
                    {
                        "id": "019f681a-1870-731d-bf1e-b82d136117fa",
                        "title": "Profile Ads Health Dashboard",
                        "owner": {"email": "owner@example.com"},
                        "lastEditedAt": "2026-07-23T00:00:00Z",
                    }
                ],
                "pagination": {"after": None},
            },
        )

    bundle = build_server(
        settings(MCPMode.READ_ONLY),
        loaded_openapi,
        api_transport=httpx.MockTransport(handler),
    )
    async with Client(bundle.server) as client:
        result = await client.call_tool(
            "resolve_project_url",
            {
                "url": (
                    "https://app.hex.tech/link-tree/app/"
                    "Profile-Ads-Health-Dashboard-033qADkKFIi4rt3feMxx3C/latest"
                )
            },
        )

    assert result.structured_content == {
        "status": "resolved",
        "projectId": "019f681a-1870-731d-bf1e-b82d136117fa",
        "title": "Profile Ads Health Dashboard",
        "candidates": [],
        "message": "Matched the app URL title to one accessible Hex project.",
    }


@pytest.mark.parametrize(
    ("method", "first_status", "expected_status", "expected_attempts"),
    [
        ("GET", 429, 200, 2),
        ("POST", 503, 503, 1),
    ],
)
async def test_retries_only_safe_reads(
    method: str,
    first_status: int,
    expected_status: int,
    expected_attempts: int,
) -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(first_status, headers={"Retry-After": "0"})
        return httpx.Response(200)

    async with httpx.AsyncClient(
        transport=retry_transport(httpx.MockTransport(handler))
    ) as client:
        response = await client.request(method, "https://app.hex.tech/api/v1/projects")

    assert response.status_code == expected_status
    assert attempts == expected_attempts


async def test_redacts_successful_tool_response(
    loaded_openapi: LoadedOpenAPI,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "password": "database-password",
                "projectSecrets": ["warehouse-password"],
                "visible": "value",
            },
        )

    bundle = build_server(
        settings(MCPMode.READ_ONLY),
        loaded_openapi,
        api_transport=httpx.MockTransport(handler),
    )
    async with Client(bundle.server) as client:
        result = await client.call_tool("list_projects")

    assert result.structured_content == {
        "password": "[REDACTED]",
        "projectSecrets": ["[REDACTED]"],
        "visible": "value",
    }


async def test_returns_sanitized_hex_error_without_logging_secret(
    loaded_openapi: LoadedOpenAPI,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "traceId": "trace-1",
                "password": "database-password",
                "message": "denied",
            },
        )

    bundle = build_server(
        settings(MCPMode.READ_ONLY),
        loaded_openapi,
        api_transport=httpx.MockTransport(handler),
    )
    with caplog.at_level(logging.DEBUG):
        async with Client(bundle.server) as client:
            result = await client.call_tool("list_projects", raise_on_error=False)

    assert result.is_error is True
    assert result.structured_content == {
        "error": {
            "type": "hex_api_error",
            "status": 403,
            "reason": "Forbidden",
            "message": "Hex API returned 403 Forbidden",
            "traceId": "trace-1",
        }
    }
    assert "database-password" not in caplog.text
    assert "database-password" not in str(result)


async def test_semantic_tool_uses_normalized_api_path(
    openapi_document: dict[str, object],
) -> None:
    paths = openapi_document["paths"]
    assert isinstance(paths, dict)
    paths["/v1/semantic-(projects|models)/{semanticProjectId}/ingest"] = {
        "post": {
            "operationId": "IngestSemanticProject",
            "parameters": [
                {
                    "name": "semanticProjectId",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                }
            ],
            "responses": {"201": {"description": "Ingested"}},
        }
    }
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(201, json={})

    loaded = LoadedOpenAPI(
        document=normalize_hex_openapi(openapi_document),
        source="test-openapi.json",
        version="test",
        digest="test-digest",
    )
    bundle = build_server(
        settings(MCPMode.FULL),
        loaded,
        api_transport=httpx.MockTransport(handler),
    )
    tool = await bundle.provider.get_tool("ingest_semantic_project")
    assert tool is not None
    try:
        await tool.run({"semanticProjectId": "semantic-project-id"})
    finally:
        await bundle.api_client.aclose()

    assert seen_urls == [
        "https://app.hex.tech/api/v1/semantic-projects/semantic-project-id/ingest"
    ]


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
