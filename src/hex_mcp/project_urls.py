"""Resolve Hex project URLs to API project UUIDs."""

from __future__ import annotations

import re
from typing import Literal, TypedDict
from urllib.parse import unquote, urlparse
from uuid import UUID

import httpx

APP_SLUG_PATTERN = re.compile(r"^(?P<title>.+)-[A-Za-z0-9_-]{22}$")


class ProjectCandidate(TypedDict):
    projectId: str
    title: str
    ownerEmail: str
    lastEditedAt: str


class ProjectUrlResolution(TypedDict):
    status: Literal["resolved", "ambiguous", "not_found", "invalid_url", "api_error"]
    projectId: str | None
    title: str | None
    candidates: list[ProjectCandidate]
    message: str


def parse_project_url(value: str) -> tuple[str | None, str | None]:
    """Return the direct project UUID or app title encoded in a Hex URL."""
    value = value.strip()
    try:
        return str(UUID(value)), None
    except ValueError:
        pass

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname != "app.hex.tech":
        return None, None

    parts = [unquote(part) for part in parsed.path.split("/") if part]
    for index, part in enumerate(parts[:-1]):
        if part == "hex":
            try:
                return str(UUID(parts[index + 1])), None
            except ValueError:
                return None, None
        if part == "app":
            match = APP_SLUG_PATTERN.fullmatch(parts[index + 1])
            if match is None:
                return None, None
            return None, match.group("title").replace("-", " ").strip()
    return None, None


def normalize_project_title(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


async def resolve_project_url(
    value: str,
    api_client: httpx.AsyncClient,
) -> ProjectUrlResolution:
    project_id, requested_title = parse_project_url(value)
    if project_id is not None:
        return {
            "status": "resolved",
            "projectId": project_id,
            "title": None,
            "candidates": [],
            "message": "Project UUID extracted directly from the Hex URL.",
        }
    if requested_title is None:
        return {
            "status": "invalid_url",
            "projectId": None,
            "title": None,
            "candidates": [],
            "message": "Expected a Hex /hex/<uuid>/ or /app/<title>-<slug>/ URL.",
        }

    matches: list[ProjectCandidate] = []
    after: str | None = None
    while True:
        params: dict[str, str | int] = {"limit": 100}
        if after is not None:
            params["after"] = after
        response = await api_client.get("v1/projects", params=params)
        if not response.is_success:
            return {
                "status": "api_error",
                "projectId": None,
                "title": requested_title,
                "candidates": [],
                "message": (
                    f"Hex API returned {response.status_code} {response.reason_phrase} "
                    "while listing accessible projects."
                ),
            }

        payload = response.json()
        for project in payload["values"]:
            if normalize_project_title(project["title"]) == normalize_project_title(
                requested_title
            ):
                matches.append(
                    {
                        "projectId": project["id"],
                        "title": project["title"],
                        "ownerEmail": project["owner"]["email"],
                        "lastEditedAt": project["lastEditedAt"],
                    }
                )

        after = payload["pagination"].get("after")
        if not after:
            break

    if len(matches) == 1:
        match = matches[0]
        return {
            "status": "resolved",
            "projectId": match["projectId"],
            "title": match["title"],
            "candidates": [],
            "message": "Matched the app URL title to one accessible Hex project.",
        }
    if matches:
        return {
            "status": "ambiguous",
            "projectId": None,
            "title": requested_title,
            "candidates": matches,
            "message": "Multiple accessible projects match the app URL title.",
        }
    return {
        "status": "not_found",
        "projectId": None,
        "title": requested_title,
        "candidates": [],
        "message": "No accessible project matches the app URL title.",
    }
