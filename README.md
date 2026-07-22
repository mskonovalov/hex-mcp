# hex-mcp

An MIT-licensed MCP server generated from the official Hex public API specification.

The server is designed around two capability modes:

- `read-only` exposes only operations classified as non-mutating, regardless of the configured Hex token's permissions.
- `full` exposes the complete official API surface.

This repository is currently in the planning phase. No server implementation has been committed yet.

- [Capability matrix](docs/capability-matrix.md)
- [Implementation plan](docs/implementation-plan.md)
