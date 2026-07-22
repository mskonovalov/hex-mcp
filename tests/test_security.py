from __future__ import annotations

import pytest
from fastmcp.tools import ToolResult
from mcp.types import TextContent

from hex_mcp.security import REDACTED, error_result, redact_secrets, redact_tool_result


def test_redacts_nested_credentials_and_hex_tokens() -> None:
    token = "hxtp" + "_example_token"
    value = {
        "connectionDetails": {
            "postgres": {"password": "database-password", "username": "analyst"},
            "bigquery": {"serviceAccountJsonConfig": "private-json"},
        },
        "projectSecrets": ["warehouse-password", "api-token"],
        "message": f"Bearer {token}",
    }

    assert redact_secrets(value) == {
        "connectionDetails": {
            "postgres": {"password": REDACTED, "username": "analyst"},
            "bigquery": {"serviceAccountJsonConfig": REDACTED},
        },
        "projectSecrets": [REDACTED, REDACTED],
        "message": f"Bearer {REDACTED}",
    }


def test_redacts_structured_and_text_tool_content() -> None:
    result = ToolResult(
        content='{"accessToken":"secret","visible":"value"}',
        structured_content={"privateKey": "secret", "visible": "value"},
    )

    redacted = redact_tool_result(result)

    assert redacted.structured_content == {
        "privateKey": REDACTED,
        "visible": "value",
    }
    content = redacted.content[0]
    assert isinstance(content, TextContent)
    assert content.text == '{"accessToken":"[REDACTED]","visible":"value"}'


def test_maps_hex_error_without_exposing_credentials() -> None:
    result = error_result(
        ValueError(
            "HTTP error 403: Forbidden - "
            "{'traceId': 'trace-1', 'password': 'secret', 'message': 'denied'}"
        )
    )

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
    content = result.content[0]
    assert isinstance(content, TextContent)
    assert "secret" not in content.text


def test_masks_unknown_internal_error() -> None:
    result = error_result(RuntimeError("internal implementation detail"))

    assert result.is_error is True
    assert result.structured_content == {
        "error": {
            "type": "internal_error",
            "message": "Hex MCP tool execution failed",
        }
    }
    content = result.content[0]
    assert isinstance(content, TextContent)
    assert "implementation detail" not in content.text


@pytest.mark.parametrize(
    ("message", "error_type", "public_message"),
    [
        (
            "HTTP request timed out (ReadTimeout)",
            "hex_api_timeout",
            "Hex API request timed out",
        ),
        (
            "Request error (ConnectError): connection refused",
            "hex_api_unavailable",
            "Hex API request failed",
        ),
        (
            "Error building request for POST /v1/projects: invalid body",
            "invalid_request",
            "Invalid Hex API arguments",
        ),
    ],
)
def test_maps_known_failures(
    message: str,
    error_type: str,
    public_message: str,
) -> None:
    result = error_result(ValueError(message))

    assert result.structured_content == {
        "error": {"type": error_type, "message": public_message}
    }
