# Hex MCP implementation plan

## Outcome

Ship a clean-room MIT-licensed MCP server that implements all 26 capabilities in the [capability matrix](capability-matrix.md), without depending on the AGPL server or proprietary Hex CLI.

The parity release will keep the documented tool names so existing client prompts and configurations can migrate with minimal change. Behavior and schemas will be defined from Hex's public API documentation rather than copied from the abandoned implementation.

## Architecture

- TypeScript on the current Node.js LTS line, managed with Yarn.
- Official Model Context Protocol TypeScript SDK and Zod for strict input and output schemas.
- A small asynchronous `HexClient` using standard `fetch`, bearer authentication, configurable base URL, request timeouts, safe error mapping, and cursor pagination helpers.
- Domain modules for projects, runs, cells, sharing, collections, groups, and connections, following the same separation of client/config/server/tools used by [Airbyte MCP](https://github.com/blstrco/airbyte/tree/main/airbyte/airbyte-mcp) without copying its implementation.
- Stdio transport for local clients and Streamable HTTP for self-hosting. The first HTTP release will support caller-supplied Hex bearer tokens and a server token fallback; a full OAuth gateway is a separate design because it requires an authorization model and Hex client registration.
- Structured JSON results with concise text summaries, MCP tool annotations for read-only, destructive, and idempotent behavior, and explicit pagination cursors.

## Clean-room and dependency rules

- Do not copy or translate code, tests, docstrings, examples, or generated artifacts from `franccesco/hex-mcp`.
- Do not shell out to the Hex CLI or read its private credential store.
- Do not vendor the currently unlicensed Hex OpenAPI file or generated code derived from it.
- Implement requests from the official API reference and validate behavior with independently written contract fixtures.
- Record source URLs and research dates when an endpoint contract is added or changed.

## Authentication and security

- Support `HEX_API_TOKEN` and `HEX_API_BASE_URL`, defaulting to `https://app.hex.tech/api/v1`.
- Never log authorization headers, connection credentials, or mutation request bodies containing secrets.
- Return Hex status, reason, and trace ID in errors without returning credentials or internal stack traces.
- Respect `Retry-After` on rate limits. Retry safe reads only; do not automatically retry non-idempotent creates.
- Mark cancellation, deletion, permission changes, and connection mutations accurately with MCP annotations.
- Redact known credential fields from connection responses and add regression tests for secret leakage.

## Delivery sequence

Each implementation pull request starts from the latest `main`, is independently reviewable, and includes its own tests and documentation.

| Pull request | Scope | Tools delivered | Estimate |
| --- | --- | ---: | ---: |
| 0. Foundation | Package, config, HTTP client, safe errors, pagination, stdio/HTTP entry points, test harness, and CI | 0 | 1–2 days |
| 1. Read-only surface | Projects, run history/status, cells, collections, groups, and connections | 12 | 2–3 days |
| 2. Execution and cell mutation | Trigger/cancel runs and update cells | 3 | 1–2 days |
| 3. Project sharing | User, group, collection, workspace, and public access changes | 4 | 1–2 days |
| 4. Collections and groups | Collection create/update and group create/update/delete | 5 | 1–2 days |
| 5. Data connection writes | Create/update connections with secret-safe schemas and fixtures | 2 | 2 days |
| 6. Release hardening | Live sandbox smoke suite, packaging, install docs, compatibility report, and `v0.1.0` | 0 | 1 day |

Expected total: 9–14 engineering days, depending mainly on access to a safe Hex test workspace and representative credentials for each supported connection type.

## Verification per pull request

- Unit tests for validation, pagination, error mapping, rate limiting, and secret redaction.
- Mocked HTTP contract tests for every endpoint and meaningful response variant.
- MCP registration tests that assert tool name, schema, annotations, and structured output.
- Type checking, linting, formatting checks, and all tests through Yarn scripts.
- MCP Inspector smoke test for both stdio and Streamable HTTP transports.
- Optional live tests gated by explicit test-only environment variables; CI never receives production credentials.

## Parity release acceptance criteria

- All 26 matrix tools are registered and documented.
- Each tool has success, authentication failure, permission failure, not-found, rate-limit, and representative validation coverage where applicable.
- A sandbox workspace smoke test covers at least one successful operation in every domain and cleans up objects it creates.
- No AGPL or proprietary code or artifacts are present in the repository.
- No token or connection secret appears in logs, errors, snapshots, or MCP responses.
- The package can be installed and launched from a fresh checkout using the documented Yarn commands.

## Decisions needed before implementation

- Confirm that `v0.1.0` should preserve the 26 legacy tool names rather than adopt new names.
- Provide or approve creation of a non-production Hex workspace for live integration testing.
- Decide whether Streamable HTTP with bearer-token forwarding is required in `v0.1.0` or can follow the stdio release.
- Decide whether connection creation/update should ship in the general server or behind an explicit opt-in because those tools handle database credentials.

After parity, plan a separate `v0.2` matrix for the newer public API and CLI capabilities instead of expanding the first release mid-implementation.
