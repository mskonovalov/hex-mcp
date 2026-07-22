# Hex MCP capability matrix

Research date: 2026-07-22.

The parity baseline is the 26 tools documented by the abandoned [franccesco/hex-mcp README](https://github.com/franccesco/hex-mcp/blob/main/README.md). This document records behavior only; its AGPL-licensed source code, tests, and documentation will not be copied.

The CLI column was checked against the official [Hex CLI documentation](https://learn.hex.tech/docs/api-integrations/cli) and `hex 1.2026.07.21 --help`. The public API column was checked against the official [Hex API reference](https://learn.hex.tech/docs/api-integrations/api/reference). "Planned" means accepted into the proposed parity release, not already implemented.

| Area | Parity tool | Capability | Official CLI | Public API | Our MCP decision |
| --- | --- | --- | --- | --- | --- |
| Projects | `list_hex_projects` | List accessible projects with filters and pagination | Yes: `hex project list` | Direct: `ListProjects` | Planned: read-only phase |
| Projects | `search_hex_projects` | Search projects by a text pattern | Partial: list filters, but no text-search command | Composed from paginated `ListProjects` results | Planned: read-only phase |
| Projects | `get_hex_project` | Get project metadata | Yes: `hex project get` | Direct: `GetProject` | Planned: read-only phase |
| Runs | `run_hex_project` | Trigger a published project run with inputs | Yes: `hex app run`; draft runs also exist as `hex project run` | Direct: `RunProject` | Planned: execution phase |
| Runs | `get_hex_run_status` | Get one run's status | Yes: `hex run status` | Direct: `GetRunStatus` | Planned: read-only phase |
| Runs | `get_hex_project_runs` | List a project's run history | Yes: `hex run list` | Direct: `GetProjectRuns` | Planned: read-only phase |
| Runs | `cancel_hex_run` | Cancel an active run | Yes: `hex run cancel` | Direct: `CancelRun` | Planned: execution phase |
| Cells | `list_hex_cells` | List project cells and supported source content | Yes: `hex cell list` | Direct: `ListCells` | Planned: read-only phase |
| Cells | `update_hex_cell` | Update code, SQL, Markdown, output dataframe, or data connection fields supported by the API | Yes: `hex cell update` | Direct: `UpdateCell` | Planned: execution phase |
| Project sharing | `update_hex_project_user_sharing` | Grant or revoke project access for users | No write command | Direct: `EditProjectSharingUsers` | Planned: sharing phase |
| Project sharing | `update_hex_project_group_sharing` | Grant or revoke project access for groups | No write command | Direct: `EditProjectSharingGroups` | Planned: sharing phase |
| Project sharing | `update_hex_project_collection_sharing` | Add or remove a project from collections | No write command | Direct: `EditProjectSharingCollections` | Planned: sharing phase |
| Project sharing | `update_hex_project_workspace_sharing` | Change workspace-wide and public access | No write command | Direct: `EditProjectSharingOrgAndPublic` | Planned: sharing phase |
| Collections | `list_hex_collections` | List collections with pagination | Yes: `hex collection list` | Direct: `ListCollections` | Planned: read-only phase |
| Collections | `get_hex_collection` | Get collection details | Yes: `hex collection get` | Direct: `GetCollection` | Planned: read-only phase |
| Collections | `create_hex_collection` | Create a collection with optional sharing | No | Direct: `CreateCollection` | Planned: collections and groups phase |
| Collections | `update_hex_collection` | Update collection metadata or sharing | No | Direct: `EditCollection` | Planned: collections and groups phase |
| Groups | `list_hex_groups` | List workspace groups | Yes: `hex group list` | Direct: `ListGroups` | Planned: read-only phase |
| Groups | `get_hex_group` | Get group details | Yes: `hex group get` | Direct: `GetGroup` | Planned: read-only phase |
| Groups | `create_hex_group` | Create a group, optionally with members | Partial: `hex group create` creates a named group but exposes no initial-members option | Direct: `CreateGroup` | Planned: collections and groups phase |
| Groups | `update_hex_group` | Rename a group or add/remove members | No | Direct: `EditGroup` | Planned: collections and groups phase |
| Groups | `delete_hex_group` | Delete a group | Yes: `hex group delete` | Direct: `DeleteGroup` | Planned: collections and groups phase |
| Connections | `list_hex_data_connections` | List data connections | Yes: `hex connection list` | Direct: `ListDataConnections` | Planned: read-only phase |
| Connections | `get_hex_data_connection` | Get data connection metadata | Yes: `hex connection get` | Direct: `GetDataConnection` | Planned: read-only phase |
| Connections | `create_hex_data_connection` | Create a supported data connection | No | Direct: `CreateDataConnection` | Planned: connections phase |
| Connections | `update_hex_data_connection` | Update configuration, credentials, or sharing | No | Direct: `EditDataConnection` | Planned: connections phase |

## Coverage summary

| Surface | Full | Partial | Missing | Baseline support |
| --- | ---: | ---: | ---: | ---: |
| Official CLI 1.2026.07.21 | 15 | 2 | 9 | 17 of 26 have at least partial coverage |
| Hex public API | 25 direct | 1 composed | 0 | 26 of 26 |
| Proposed parity release | 26 planned | 0 | 0 | 26 of 26 |

The official [Hex MCP server](https://learn.hex.tech/docs/api-integrations/mcp-server) is a different product surface. It currently exposes four tools—project search plus create, get, and continue Thread operations—and does not provide this administration and orchestration parity set.

## CLI-only and newer API opportunities

These are deliberately outside the first parity release but should be evaluated immediately afterwards:

- Create, update, export, import, and open projects.
- Get, create, delete, and run cells; retrieve cell output and chart images.
- Draft project runs in addition to published app runs.
- Threads, users, guides, context topics, suggestions, semantic projects, queried-table observability, and embedded URLs.
- Data connection schema refresh.

Unstable endpoints, including cell output, should remain opt-in until their compatibility policy is defined.

## Client reuse finding

- The official [`hex-inc/hex-cli`](https://github.com/hex-inc/hex-cli) repository contains only a README and a [proprietary license](https://github.com/hex-inc/hex-cli/blob/main/LICENSE). It publishes binaries, not source or a reusable API-client package.
- Depending on the CLI executable would add a proprietary, macOS/Linux-only runtime dependency and still leave nine parity capabilities unavailable. It is therefore useful as an interoperability oracle, not as the MCP transport layer.
- Hex publishes a downloadable [OpenAPI specification](https://static.hex.site/openapi.json), but its metadata says `UNLICENSED`. We should use the public reference as documentation and write a small client around standard HTTP. We should not vendor the specification or commit generated derivatives unless Hex clarifies its license.
- The unofficial [`hex-api` package on PyPI](https://pypi.org/project/hex-api/) has one release from May 2025, points to a placeholder GitHub repository, and is maintained by the abandoned MCP's author. It is not a suitable production dependency even though its package metadata says MIT.
