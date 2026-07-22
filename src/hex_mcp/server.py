"""FastMCP server generated from Hex's OpenAPI specification."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx
from fastmcp import FastMCP
from fastmcp.server.providers.openapi import MCPType, OpenAPIProvider, RouteMap

from hex_mcp import __version__
from hex_mcp.config import MCPMode, Settings, Transport
from hex_mcp.openapi import LoadedOpenAPI, load_openapi, operation_names

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ServerBundle:
    server: FastMCP
    provider: OpenAPIProvider
    api_client: httpx.AsyncClient
    openapi: LoadedOpenAPI


def route_maps(mode: MCPMode) -> list[RouteMap]:
    if mode is MCPMode.FULL:
        return [RouteMap(mcp_type=MCPType.TOOL)]
    return [
        RouteMap(methods=["GET"], mcp_type=MCPType.TOOL),
        RouteMap(
            methods=["POST"],
            pattern=r"^/v1/projects/export$",
            mcp_type=MCPType.TOOL,
        ),
        RouteMap(mcp_type=MCPType.EXCLUDE),
    ]


def build_server(settings: Settings, openapi: LoadedOpenAPI) -> ServerBundle:
    api_client = httpx.AsyncClient(
        base_url=settings.api_base_url.rstrip("/") + "/",
        headers={
            "Authorization": f"Bearer {settings.api_token.get_secret_value()}",
            "Accept": "application/json",
            "User-Agent": f"hex-mcp/{__version__}",
        },
        timeout=settings.request_timeout_seconds,
    )
    provider = OpenAPIProvider(
        openapi.document,
        api_client,
        route_maps=route_maps(settings.mcp_mode),
        mcp_names=operation_names(openapi.document),
        validate_output=True,
    )

    @asynccontextmanager
    async def lifespan(_server: FastMCP) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await api_client.aclose()

    server = FastMCP(
        name="Hex",
        instructions=(
            "Tools are generated from Hex's official OpenAPI specification. "
            f"Capability mode: {settings.mcp_mode.value}."
        ),
        providers=[provider],
        lifespan=lifespan,
    )
    return ServerBundle(
        server=server,
        provider=provider,
        api_client=api_client,
        openapi=openapi,
    )


async def create_server(settings: Settings) -> ServerBundle:
    openapi = await load_openapi(
        settings.openapi_spec,
        timeout_seconds=settings.request_timeout_seconds,
    )
    return build_server(settings, openapi)


async def run(settings: Settings) -> None:
    bundle = await create_server(settings)
    LOGGER.info(
        "Loaded OpenAPI version=%s sha256=%s source=%s mode=%s",
        bundle.openapi.version,
        bundle.openapi.digest,
        bundle.openapi.source,
        settings.mcp_mode.value,
    )
    if settings.transport is Transport.HTTP:
        await bundle.server.run_http_async(
            transport="streamable-http",
            host=settings.http_host,
            port=settings.http_port,
            path=settings.http_path,
            show_banner=False,
        )
    else:
        await bundle.server.run_stdio_async(show_banner=False)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run(Settings()))


if __name__ == "__main__":
    main()
