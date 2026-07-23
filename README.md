# hex-mcp

An MIT-licensed MCP server generated from the official Hex public API specification.

The server loads Hex's current OpenAPI document at startup and exposes its operations as deterministic, snake_case MCP tools through FastMCP.

The PyPI distribution and installed command are named `hex-openapi-mcp`. The shorter `hex-mcp` command remains available, and the Python import is `hex_mcp`.

## Capability modes

- `read-only` exposes only operations classified as non-mutating, regardless of the configured Hex token's permissions.
- `full` exposes the complete official API surface.

`read-only` is the default. It registers GET operations and the non-mutating `export_project` POST operation. Mutating tools do not exist in the MCP catalog in this mode, even when `HEX_API_TOKEN` has write permissions.

## Install

Requirements: Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

Run the server directly from PyPI:

```bash
HEX_API_TOKEN=your_hex_token uvx hex-openapi-mcp
```

Enable the complete API surface explicitly:

```bash
HEX_API_TOKEN=your_hex_token HEX_MCP_MODE=full uvx hex-openapi-mcp
```

The default transport is stdio. To run Streamable HTTP:

```bash
HEX_API_TOKEN=your_hex_token HEX_TRANSPORT=http uvx hex-openapi-mcp
```

It listens on `http://127.0.0.1:8000/mcp` by default.

## Run from source

Requirements: Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --locked --dev
HEX_API_TOKEN=your_hex_token uv run hex-openapi-mcp
```

## MCP client configuration

From PyPI:

```json
{
  "mcpServers": {
    "hex": {
      "command": "uvx",
      "args": ["hex-openapi-mcp"],
      "env": {
        "HEX_API_TOKEN": "your_hex_token",
        "HEX_MCP_MODE": "read-only"
      }
    }
  }
}
```

For a local checkout, use `"command": "uv"` with `"args": ["--directory", "/absolute/path/to/hex-mcp", "run", "hex-openapi-mcp"]`.

For stdio, the MCP client passes `HEX_API_TOKEN` only to the child process. Do not put the token in command-line arguments.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `HEX_API_TOKEN` | Required | Hex personal or workspace bearer token |
| `HEX_MCP_MODE` | `read-only` | `read-only` or `full` tool catalog |
| `HEX_API_BASE_URL` | `https://app.hex.tech/api` | Hex API base URL |
| `HEX_OPENAPI_SPEC` | `https://static.hex.site/openapi.json` | Official spec URL or a local JSON file |
| `HEX_TRANSPORT` | `stdio` | `stdio` or `http` |
| `HEX_HTTP_HOST` | `127.0.0.1` | Streamable HTTP bind host |
| `HEX_HTTP_PORT` | `8000` | Streamable HTTP bind port |
| `HEX_HTTP_PATH` | `/mcp` | Streamable HTTP endpoint path |
| `HEX_REQUEST_TIMEOUT_SECONDS` | `30` | Spec download and Hex API timeout |

## Development

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

The repository does not vendor Hex's specification. Contract behavior can be tested offline by setting `HEX_OPENAPI_SPEC` to an independently supplied local copy.

## Safety and reliability

- Every tool has MCP read-only, destructive, idempotent, and open-world annotations derived from its official operation and HTTP method.
- Tool results and Hex error bodies recursively redact known credential fields and Hex bearer tokens before they reach MCP output or error logging.
- Hex HTTP errors preserve the status, reason, and trace ID in a structured MCP error without exposing internal stack traces.
- GET requests retry transient `429`, `502`, `503`, and `504` responses up to twice, respect `Retry-After`, and use bounded exponential backoff. Write requests are never retried automatically.

Hex's specification currently publishes two semantic paths with backend regex syntax as literal OpenAPI paths. Those literals return `404`, while both expanded routes exist. The loader normalizes them to the current `/v1/semantic-projects/...` naming before generating tools while retaining the original specification digest for observability.

The specification also applies its UUID-based `ProjectId` schema inconsistently. The loader normalizes all `projectId` inputs to the UUID contract so compact IDs from `/app/` URLs are rejected before a Hex API request.

Streamable HTTP currently uses the single server-wide `HEX_API_TOKEN` and has no inbound client authentication. Keep the default loopback bind unless access is protected by a trusted authentication proxy.

## Design documents

- [Capability matrix](docs/capability-matrix.md)
- [Implementation plan](docs/implementation-plan.md)
- [Release process](docs/releasing.md)
