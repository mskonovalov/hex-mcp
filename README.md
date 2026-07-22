# hex-mcp

An MIT-licensed MCP server generated from the official Hex public API specification.

The server loads Hex's current OpenAPI document at startup and exposes its operations as deterministic, snake_case MCP tools through FastMCP.

## Capability modes

- `read-only` exposes only operations classified as non-mutating, regardless of the configured Hex token's permissions.
- `full` exposes the complete official API surface.

`read-only` is the default. It registers GET operations and the non-mutating `export_project` POST operation. Mutating tools do not exist in the MCP catalog in this mode, even when `HEX_API_TOKEN` has write permissions.

## Run locally

Requirements: Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --locked --dev
HEX_API_TOKEN=your_hex_token uv run hex-mcp
```

Enable the complete API surface explicitly:

```bash
HEX_API_TOKEN=your_hex_token HEX_MCP_MODE=full uv run hex-mcp
```

The default transport is stdio. To run Streamable HTTP:

```bash
HEX_API_TOKEN=your_hex_token HEX_TRANSPORT=http uv run hex-mcp
```

It listens on `http://127.0.0.1:8000/mcp` by default.

## MCP client configuration

From a local checkout:

```json
{
  "mcpServers": {
    "hex": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/hex-mcp", "run", "hex-mcp"],
      "env": {
        "HEX_API_TOKEN": "your_hex_token",
        "HEX_MCP_MODE": "read-only"
      }
    }
  }
}
```

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

## Design documents

- [Capability matrix](docs/capability-matrix.md)
- [Implementation plan](docs/implementation-plan.md)
