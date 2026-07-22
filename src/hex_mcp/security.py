"""Compatibility exports for tool result and Hex API sanitization."""

from hex_mcp.redaction import REDACTED, redact_secrets, redact_text, redact_tool_result
from hex_mcp.tool_safety import HardenedToolTransform, error_result

__all__ = [
    "REDACTED",
    "HardenedToolTransform",
    "error_result",
    "redact_secrets",
    "redact_text",
    "redact_tool_result",
]
