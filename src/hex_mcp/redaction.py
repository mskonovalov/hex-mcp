"""Redact credentials from MCP tool results."""

from __future__ import annotations

import ast
import json
import re
from typing import Any

from fastmcp.tools import ToolResult
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


def _redact_content(block: mt.ContentBlock) -> mt.ContentBlock:
    if isinstance(block, mt.TextContent):
        return block.model_copy(update={"text": redact_text(block.text)})
    return block
