from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from hex_mcp.openapi import (
    PROJECT_ID_INPUT_SCHEMA,
    load_openapi,
    normalize_hex_openapi,
    operation_names,
    to_snake_case,
    validate_openapi,
)


async def test_loads_local_openapi(
    tmp_path: Path, openapi_document: dict[str, Any]
) -> None:
    source = tmp_path / "openapi.json"
    source.write_text(json.dumps(openapi_document), encoding="utf-8")

    loaded = await load_openapi(str(source))

    assert loaded.document == normalize_hex_openapi(openapi_document)
    assert loaded.version == "test"
    assert len(loaded.digest) == 64


@pytest.mark.parametrize(
    ("operation_id", "expected"),
    [
        ("ListProjects", "list_projects"),
        ("GetHTTPStatus", "get_http_status"),
        ("Me", "me"),
    ],
)
def test_to_snake_case(operation_id: str, expected: str) -> None:
    assert to_snake_case(operation_id) == expected


def test_builds_names_from_operation_ids(openapi_document: dict[str, Any]) -> None:
    assert operation_names(openapi_document) == {
        "ListProjects": "list_projects",
        "CreateProject": "create_project",
        "ExportProject": "export_project",
        "UpdateProject": "update_project",
        "DeleteProject": "delete_project",
    }


def test_normalizes_hex_semantic_route(openapi_document: dict[str, Any]) -> None:
    operation = {
        "post": {
            "operationId": "IngestSemanticProject",
            "responses": {"201": {"description": "Ingested"}},
        }
    }
    openapi_document["paths"][
        "/v1/semantic-(projects|models)/{semanticProjectId}/ingest"
    ] = operation

    normalized = normalize_hex_openapi(openapi_document)

    assert (
        normalized["paths"]["/v1/semantic-projects/{semanticProjectId}/ingest"]
        == operation
    )
    assert not any("(projects|models)" in path for path in normalized["paths"])


def test_normalizes_project_id_inputs(openapi_document: dict[str, Any]) -> None:
    openapi_document["paths"]["/v1/cells"] = {
        "get": {
            "operationId": "ListCells",
            "parameters": [
                {
                    "name": "projectId",
                    "in": "query",
                    "required": True,
                    "schema": {"type": "string"},
                }
            ],
            "responses": {"200": {"description": "Cells"}},
        },
        "post": {
            "operationId": "CreateCell",
            "requestBody": {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "projectId": {
                                    "type": "string",
                                    "nullable": True,
                                }
                            },
                        }
                    }
                }
            },
            "responses": {"201": {"description": "Cell"}},
        },
    }

    normalized = normalize_hex_openapi(openapi_document)

    list_parameter = normalized["paths"]["/v1/cells"]["get"]["parameters"][0]
    create_property = normalized["paths"]["/v1/cells"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]["properties"]["projectId"]
    assert list_parameter["description"] == PROJECT_ID_INPUT_SCHEMA["description"]
    assert list_parameter["schema"] == PROJECT_ID_INPUT_SCHEMA
    assert create_property == {**PROJECT_ID_INPUT_SCHEMA, "nullable": True}
    assert openapi_document["paths"]["/v1/cells"]["get"]["parameters"][0]["schema"] == {
        "type": "string"
    }


def test_rejects_missing_operation_id(openapi_document: dict[str, Any]) -> None:
    del openapi_document["paths"]["/v1/projects"]["get"]["operationId"]

    with pytest.raises(ValueError, match="Missing operationId"):
        validate_openapi(openapi_document)


def test_rejects_missing_openapi_version(openapi_document: dict[str, Any]) -> None:
    del openapi_document["openapi"]

    with pytest.raises(ValueError, match="missing an openapi version"):
        validate_openapi(openapi_document)


def test_rejects_missing_paths(openapi_document: dict[str, Any]) -> None:
    del openapi_document["paths"]

    with pytest.raises(ValueError, match="must contain paths"):
        validate_openapi(openapi_document)


def test_rejects_duplicate_operation_id(openapi_document: dict[str, Any]) -> None:
    openapi_document["paths"]["/v1/projects"]["post"]["operationId"] = "ListProjects"

    with pytest.raises(ValueError, match="Duplicate operationId"):
        validate_openapi(openapi_document)


def test_rejects_missing_responses(openapi_document: dict[str, Any]) -> None:
    del openapi_document["paths"]["/v1/projects"]["get"]["responses"]

    with pytest.raises(ValueError, match="Missing responses"):
        validate_openapi(openapi_document)
