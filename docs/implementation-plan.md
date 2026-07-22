# Hex MCP implementation plan

## Outcome

Ship an MIT-licensed Python MCP server that exposes Hex's complete official public API through FastMCP's OpenAPI provider.

The official OpenAPI specification is the only capability source of truth. Tool names and schemas are derived from its operation IDs and request definitions.

## Architecture

- Python 3.12 or newer, packaged and locked with `uv`.
- FastMCP 3.x with `OpenAPIProvider` for dynamic tool generation.
- `httpx.AsyncClient` for authenticated calls to the Hex API.
- Pydantic settings for environment validation.
- Stdio and Streamable HTTP transports.
- Structured API responses with MCP annotations derived from HTTP semantics and an explicit safety classification.

## Capability modes

`HEX_MCP_MODE` controls which tools are registered:

- `read-only` is the default. It exposes the 23 GET operations plus the non-mutating `ExportProject` operation. Write tools do not exist in the MCP catalog and cannot be called by name.
- `full` exposes all 52 operations currently present in the official specification.

Hex token permissions are still enforced by Hex, but they are not used to decide which tools exist. A highly privileged token running in `read-only` mode remains limited to the read-only catalog.

## OpenAPI handling

- Load the specification from `https://static.hex.site/openapi.json` at startup by default.
- Support an explicitly configured local specification for reproducible or offline deployments.
- Do not commit the Hex specification into this repository.
- Validate that every generated tool has an `operationId`, unique name, request schema, and response definition.
- Log the specification version and content digest at startup so deployments can identify the exact contract they loaded.

## Authentication and security

- Support `HEX_API_TOKEN` and `HEX_API_BASE_URL`.
- Never log authorization headers, connection credentials, or secret-bearing request bodies.
- Return Hex status, reason, and trace ID without returning internal stack traces.
- Respect `Retry-After` for safe reads. Do not automatically retry non-idempotent writes.
- Mark DELETE operations and user deactivation as destructive.
- Redact known credential fields from data connection responses.
- Refuse to start for an unknown `HEX_MCP_MODE` value.

## Delivery sequence

| Pull request | Scope | Estimate |
| --- | --- | ---: |
| 1. Planning | Official API/CLI matrix, architecture, and capability-mode policy | Complete |
| 2. Generated server | Package, OpenAPI provider, auth, both modes, transports, and all generated operations | Complete |
| 3. Hardening | Tool transformations, annotations, redaction, error mapping, contract tests, and packaging | Complete |
| 4. Release | Live test-workspace verification, installation docs, CI, and `v0.1.0` | 1–2 days |

## Verification

- Unit tests for configuration, specification loading, operation classification, mode filtering, naming, and secret redaction.
- Contract tests using independently written minimal OpenAPI fixtures.
- MCP tests asserting exactly 24 tools in `read-only` mode and 52 tools in `full` mode for the current official specification.
- MCP Inspector smoke tests for stdio and Streamable HTTP.
- Live sandbox tests covering every API area, gated by explicit test-only credentials.
- Linting, formatting, type checking, and tests through `uv` scripts.

## Release acceptance criteria

- The full catalog matches every operation in the official specification.
- The read-only catalog contains no mutating operation.
- Generated names are deterministic and unique.
- Sensitive values never appear in logs, errors, snapshots, or MCP responses.
- The server runs from a fresh checkout through both supported transports.
- The repository contains no vendored Hex specification or proprietary CLI artifact.
