"""Sanitize tool results and Hex API errors."""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Sequence
from typing import Any

from fastmcp.server.transforms import GetToolNext, Transform
from fastmcp.tools import Tool, ToolResult
from fastmcp.tools.tool_transform import TransformedTool, forward
from fastmcp.utilities.versions import VersionSpec
from mcp import types as mt

REDACTED = "[REDACTED]"
SECRET_KEYS = frozenset(
    {
        "accesskeyid",
        "accesstoken",
        "apikey",
        "clientsecret",
        "connectionstring",
        "jdbcurl",
        "passphrase",
        "password",
        "privatekey",
        "projectsecrets",
        "refreshtoken",
        "secret",
        "secretaccesskey",
        "serviceaccountjsonconfig",
        "sharedsecrets",
        "token",
    }
)
HEX_TOKEN_PATTERN = re.compile(r"\b(?:hxtp|hxtw)_[A-Za-z0-9_-]+\b")
BEARER_PATTERN = re.compile(r"(?i)(bearer\s+)[^\s,;'\"]+")
HTTP_ERROR_PATTERN = re.compile(
    r"^HTTP error (?P<status>\d+): (?P<reason>.*?)(?: - (?P<body>.*))?$"
)


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _redact_secret(item)
            if _is_secret_key(str(key))
            else redact_secrets(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item) for item in value)
    if isinstance(value, str):
        return _redact_tokens(value)
    return value


def redact_text(value: str) -> str:
    for loader in (json.loads, ast.literal_eval):
        try:
            parsed = loader(value)
        except (SyntaxError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(parsed, (dict, list, tuple)):
            return json.dumps(redact_secrets(parsed), separators=(",", ":"))
    return _redact_tokens(value)


def error_result(error: Exception) -> ToolResult:
    message = str(error)
    match = HTTP_ERROR_PATTERN.match(message)
    if match:
        status = int(match.group("status"))
        reason = match.group("reason")
        details = _parse_error_body(match.group("body"))
        payload: dict[str, Any] = {
            "type": "hex_api_error",
            "status": status,
            "reason": reason,
            "message": f"Hex API returned {status} {reason}",
        }
        trace_id = _trace_id(details)
        if trace_id is not None:
            payload["traceId"] = trace_id
        return _tool_error(payload)

    if message.startswith("HTTP request timed out"):
        return _tool_error(
            {"type": "hex_api_timeout", "message": "Hex API request timed out"}
        )
    if message.startswith("Request error"):
        return _tool_error(
            {"type": "hex_api_unavailable", "message": "Hex API request failed"}
        )
    if message.startswith("Error building request"):
        return _tool_error(
            {"type": "invalid_request", "message": "Invalid Hex API arguments"}
        )
    return _tool_error(
        {"type": "internal_error", "message": "Hex MCP tool execution failed"}
    )


def redact_tool_result(result: ToolResult) -> ToolResult:
    content = [_redact_content(block) for block in result.content]
    structured_content = redact_secrets(result.structured_content)
    meta = redact_secrets(result.meta)
    return result.model_copy(
        update={
            "content": content,
            "structured_content": structured_content,
            "meta": meta,
        }
    )


class HardenedToolTransform(Transform):
    async def list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]:
        return [_hardened_tool(tool) for tool in tools]

    async def get_tool(
        self,
        name: str,
        call_next: GetToolNext,
        *,
        version: VersionSpec | None = None,
    ) -> Tool | None:
        tool = await call_next(name, version=version)
        return _hardened_tool(tool) if tool is not None else None


def _is_secret_key(value: str) -> bool:
    normalized = "".join(
        character for character in value.lower() if character.isalnum()
    )
    return normalized in SECRET_KEYS


def _redact_secret(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _redact_secret(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_secret(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_secret(item) for item in value)
    if isinstance(value, str):
        return REDACTED
    return value


def _redact_tokens(value: str) -> str:
    value = HEX_TOKEN_PATTERN.sub(REDACTED, value)
    return BEARER_PATTERN.sub(r"\1[REDACTED]", value)


def _parse_error_body(value: str | None) -> Any:
    if value is None:
        return None
    for loader in (json.loads, ast.literal_eval):
        try:
            return redact_secrets(loader(value))
        except (SyntaxError, ValueError, json.JSONDecodeError):
            continue
    return redact_text(value)


def _trace_id(details: Any) -> str | None:
    if not isinstance(details, dict):
        return None
    for key in ("traceId", "trace_id"):
        value = details.get(key)
        if isinstance(value, str):
            return _redact_tokens(value)
    return None


def _tool_error(payload: dict[str, Any]) -> ToolResult:
    structured_content = {"error": payload}
    return ToolResult(
        content=json.dumps(structured_content, separators=(",", ":")),
        structured_content=structured_content,
        is_error=True,
    )


def _redact_content(block: mt.ContentBlock) -> mt.ContentBlock:
    if isinstance(block, mt.TextContent):
        return block.model_copy(update={"text": redact_text(block.text)})
    return block


def _hardened_tool(tool: Tool) -> TransformedTool:
    return TransformedTool.from_tool(
        tool,
        transform_fn=_safe_forward,
        output_schema=tool.output_schema,
    )


async def _safe_forward(**kwargs: Any) -> ToolResult:
    try:
        return redact_tool_result(await forward(**kwargs))
    except Exception as error:
        return error_result(error)
