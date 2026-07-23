from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from hex_mcp.project_urls import (
    ProjectUrlResolution,
    normalize_project_title,
    parse_project_url,
    resolve_project_url,
)

PROJECT_ID = "019f681a-1870-731d-bf1e-b82d136117fa"
APP_URL = (
    "https://app.hex.tech/link-tree/app/"
    "Profile-Ads-Health-Dashboard-033qADkKFIi4rt3feMxx3C/latest"
)


def project(
    project_id: str = PROJECT_ID,
    title: str = "Profile Ads Health Dashboard",
) -> dict[str, object]:
    return {
        "id": project_id,
        "title": title,
        "owner": {"email": "owner@example.com"},
        "lastEditedAt": "2026-07-23T00:00:00Z",
    }


def api_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="https://app.hex.tech/api/",
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (PROJECT_ID, (PROJECT_ID, None)),
        (
            f"https://app.hex.tech/link-tree/hex/{PROJECT_ID}/draft",
            (PROJECT_ID, None),
        ),
        (APP_URL, (None, "Profile Ads Health Dashboard")),
        ("https://example.com/link-tree/hex/not-a-uuid/draft", (None, None)),
        ("https://app.hex.tech/link-tree/app/missing-compact-id/latest", (None, None)),
    ],
)
def test_parses_project_references(
    value: str,
    expected: tuple[str | None, str | None],
) -> None:
    assert parse_project_url(value) == expected


def test_normalizes_project_titles() -> None:
    assert normalize_project_title("Profile-Ads Health: Dashboard") == (
        "profileadshealthdashboard"
    )


async def test_resolves_direct_uuid_without_api_request() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("Direct UUIDs must not call the Hex API")

    async with api_client(handler) as client:
        result = await resolve_project_url(PROJECT_ID, client)

    assert result == {
        "status": "resolved",
        "projectId": PROJECT_ID,
        "title": None,
        "candidates": [],
        "message": "Project UUID extracted directly from the Hex URL.",
    }


async def test_resolves_app_url_across_all_project_pages() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.params.get("after") is None:
            return httpx.Response(
                200,
                json={
                    "values": [project(title="Another project")],
                    "pagination": {"after": "next-page"},
                },
            )
        return httpx.Response(
            200,
            json={"values": [project()], "pagination": {"after": None}},
        )

    async with api_client(handler) as client:
        result = await resolve_project_url(APP_URL, client)

    assert len(requests) == 2
    assert requests[0].url.params["limit"] == "100"
    assert requests[1].url.params["after"] == "next-page"
    expected: ProjectUrlResolution = {
        "status": "resolved",
        "projectId": PROJECT_ID,
        "title": "Profile Ads Health Dashboard",
        "candidates": [],
        "message": "Matched the app URL title to one accessible Hex project.",
    }
    assert result == expected


async def test_returns_ambiguous_project_candidates() -> None:
    second_id = "019f681a-1870-731d-bf1e-b82d136117fb"

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "values": [
                    project(),
                    project(second_id, "Profile-Ads Health Dashboard"),
                ],
                "pagination": {"after": None},
            },
        )

    async with api_client(handler) as client:
        result = await resolve_project_url(APP_URL, client)

    assert result["status"] == "ambiguous"
    assert result["projectId"] is None
    assert [candidate["projectId"] for candidate in result["candidates"]] == [
        PROJECT_ID,
        second_id,
    ]


async def test_returns_not_found_for_unmatched_app_title() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "values": [project(title="Another project")],
                "pagination": {"after": None},
            },
        )

    async with api_client(handler) as client:
        result = await resolve_project_url(APP_URL, client)

    assert result["status"] == "not_found"
    assert result["title"] == "Profile Ads Health Dashboard"


async def test_returns_invalid_url_without_api_request() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("Invalid URLs must not call the Hex API")

    async with api_client(handler) as client:
        result = await resolve_project_url("https://example.com/project", client)

    assert result["status"] == "invalid_url"


async def test_returns_safe_api_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "private details"})

    async with api_client(handler) as client:
        result = await resolve_project_url(APP_URL, client)

    assert result == {
        "status": "api_error",
        "projectId": None,
        "title": "Profile Ads Health Dashboard",
        "candidates": [],
        "message": "Hex API returned 403 Forbidden while listing accessible projects.",
    }
