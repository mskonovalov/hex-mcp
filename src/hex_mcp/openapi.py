"""Load and validate the official Hex OpenAPI specification."""

from __future__ import annotations

import hashlib
import json
import logging
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

HTTP_METHODS = frozenset({"delete", "get", "patch", "post", "put"})
HEX_PATH_REPLACEMENTS = {
    "/v1/semantic-(projects|models)/{semanticProjectId}": (
        "/v1/semantic-projects/{semanticProjectId}"
    ),
    "/v1/semantic-(projects|models)/{semanticProjectId}/ingest": (
        "/v1/semantic-projects/{semanticProjectId}/ingest"
    ),
}
PROJECT_ID_INPUT_SCHEMA = {
    "type": "string",
    "format": "uuid",
    "pattern": (
        "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    ),
    "description": (
        "Hex project UUID in canonical 8-4-4-4-12 format. The compact ID in "
        "an /app/ URL is not a valid projectId."
    ),
}
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadedOpenAPI:
    document: dict[str, Any]
    source: str
    version: str
    digest: str


async def load_openapi(source: str, timeout_seconds: float = 30.0) -> LoadedOpenAPI:
    if urlparse(source).scheme in {"http", "https"}:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(source)
            response.raise_for_status()
            document = response.json()
    else:
        document = json.loads(Path(source).read_text(encoding="utf-8"))

    if not isinstance(document, dict):
        raise ValueError("OpenAPI document must be a JSON object")

    canonical = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    document = normalize_hex_openapi(document)
    validate_openapi(document)
    info = document.get("info", {})
    version = info.get("version", "unknown") if isinstance(info, dict) else "unknown"
    return LoadedOpenAPI(
        document=document,
        source=source,
        version=str(version),
        digest=hashlib.sha256(canonical).hexdigest(),
    )


def normalize_hex_openapi(document: dict[str, Any]) -> dict[str, Any]:
    """Correct known inconsistencies in Hex's published OpenAPI document.

    IngestSemanticProject and UpdateSemanticProject use ``(projects|models)``
    inside their path keys. OpenAPI treats that text literally, so FastMCP sends
    requests to a route that Hex returns as 404. Hex recognizes both expanded
    aliases; ``semantic-projects`` matches the current operation and parameter
    naming, so the two exact keys are replaced before FastMCP parses the document.

    Hex also defines a strict ProjectId UUID schema but leaves several projectId
    inputs as unconstrained strings. Those inputs are normalized to the UUID
    contract so invalid compact app URL IDs fail before an API request is sent.
    """
    paths = document.get("paths")
    if not isinstance(paths, dict):
        return document

    normalized = deepcopy(document)
    normalized_paths = normalized["paths"]
    matching_paths = set(paths).intersection(HEX_PATH_REPLACEMENTS)
    if matching_paths:
        normalized_paths = {
            HEX_PATH_REPLACEMENTS.get(path, path): path_item
            for path, path_item in normalized_paths.items()
        }
        if len(normalized_paths) != len(paths):
            raise ValueError("Hex semantic path normalization would overwrite a path")
        normalized["paths"] = normalized_paths
        LOGGER.warning(
            "Normalized %d malformed Hex semantic OpenAPI path(s)",
            len(matching_paths),
        )

    project_id_inputs = 0
    for path_item in normalized_paths.values():
        if not isinstance(path_item, dict):
            continue

        parameter_owners = [path_item]
        parameter_owners.extend(
            operation
            for method, operation in path_item.items()
            if method.lower() in HTTP_METHODS and isinstance(operation, dict)
        )
        for owner in parameter_owners:
            parameters = owner.get("parameters")
            if not isinstance(parameters, list):
                continue
            for parameter in parameters:
                if (
                    not isinstance(parameter, dict)
                    or parameter.get("name") != "projectId"
                ):
                    continue
                parameter["description"] = PROJECT_ID_INPUT_SCHEMA["description"]
                parameter["schema"] = dict(PROJECT_ID_INPUT_SCHEMA)
                project_id_inputs += 1

        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            content = operation.get("requestBody", {}).get("content", {})
            if not isinstance(content, dict):
                continue
            for media_type in content.values():
                if not isinstance(media_type, dict):
                    continue
                schema = media_type.get("schema")
                if not isinstance(schema, dict):
                    continue
                properties = schema.get("properties")
                if not isinstance(properties, dict):
                    continue
                project_id = properties.get("projectId")
                if not isinstance(project_id, dict):
                    continue
                properties["projectId"] = {
                    **project_id,
                    **PROJECT_ID_INPUT_SCHEMA,
                }
                properties["projectId"].pop("$ref", None)
                project_id_inputs += 1

    if project_id_inputs:
        LOGGER.warning(
            "Normalized %d Hex projectId input schema(s) to UUIDs",
            project_id_inputs,
        )
    return normalized


def validate_openapi(document: dict[str, Any]) -> None:
    if not isinstance(document.get("openapi"), str):
        raise ValueError("OpenAPI document is missing an openapi version")

    paths = document.get("paths")
    if not isinstance(paths, dict) or not paths:
        raise ValueError("OpenAPI document must contain paths")

    operation_ids: set[str] = set()
    for path, path_item in paths.items():
        if not isinstance(path, str) or not isinstance(path_item, dict):
            raise ValueError("OpenAPI paths must map strings to path items")
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                raise ValueError(f"Invalid operation for {method.upper()} {path}")
            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str) or not operation_id:
                raise ValueError(f"Missing operationId for {method.upper()} {path}")
            if operation_id in operation_ids:
                raise ValueError(f"Duplicate operationId: {operation_id}")
            if not isinstance(operation.get("responses"), dict):
                raise ValueError(f"Missing responses for operationId: {operation_id}")
            operation_ids.add(operation_id)


def operation_names(document: dict[str, Any]) -> dict[str, str]:
    names: dict[str, str] = {}
    paths = document["paths"]
    for path_item in paths.values():
        for method, operation in path_item.items():
            if method.lower() in HTTP_METHODS:
                operation_id = operation["operationId"]
                names[operation_id] = to_snake_case(operation_id)
    return names


def to_snake_case(value: str) -> str:
    characters: list[str] = []
    for index, character in enumerate(value):
        if character.isupper() and index > 0:
            previous = value[index - 1]
            following = value[index + 1] if index + 1 < len(value) else ""
            if previous.islower() or (previous.isupper() and following.islower()):
                characters.append("_")
        characters.append(character.lower())
    return "".join(characters)
