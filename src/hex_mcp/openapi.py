"""Load and validate the official Hex OpenAPI specification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

HTTP_METHODS = frozenset({"delete", "get", "patch", "post", "put"})


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

    validate_openapi(document)
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    info = document.get("info", {})
    version = info.get("version", "unknown") if isinstance(info, dict) else "unknown"
    return LoadedOpenAPI(
        document=document,
        source=source,
        version=str(version),
        digest=hashlib.sha256(canonical).hexdigest(),
    )


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
