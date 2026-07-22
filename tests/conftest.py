from __future__ import annotations

from typing import Any

import pytest

from hex_mcp.openapi import LoadedOpenAPI


@pytest.fixture
def openapi_document() -> dict[str, Any]:
    return {
        "openapi": "3.0.3",
        "info": {"title": "Hex test API", "version": "test"},
        "servers": [{"url": "https://app.hex.tech/api"}],
        "paths": {
            "/v1/projects": {
                "get": {
                    "operationId": "ListProjects",
                    "responses": {"200": {"description": "Projects"}},
                },
                "post": {
                    "operationId": "CreateProject",
                    "responses": {"201": {"description": "Created"}},
                },
            },
            "/v1/projects/export": {
                "post": {
                    "operationId": "ExportProject",
                    "responses": {"200": {"description": "Export"}},
                }
            },
            "/v1/projects/{projectId}": {
                "parameters": [
                    {
                        "name": "projectId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "patch": {
                    "operationId": "UpdateProject",
                    "responses": {"200": {"description": "Updated"}},
                },
                "delete": {
                    "operationId": "DeleteProject",
                    "responses": {"204": {"description": "Deleted"}},
                },
            },
        },
    }


@pytest.fixture
def loaded_openapi(openapi_document: dict[str, Any]) -> LoadedOpenAPI:
    return LoadedOpenAPI(
        document=openapi_document,
        source="test-openapi.json",
        version="test",
        digest="test-digest",
    )
