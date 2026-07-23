# Hex MCP capability matrix

Research date: 2026-07-22.

The source of truth is Hex's official [OpenAPI specification](https://static.hex.site/openapi.json), which currently describes 52 operations. CLI coverage was checked with the official [Hex CLI](https://learn.hex.tech/docs/api-integrations/cli) version `1.2026.07.21`.

`read-only` is a hard server-side filter, independent of Hex token permissions. `full` exposes every operation in the specification.

| Area | Official operation | Capability | Official CLI | Read-only | Full |
| --- | --- | --- | --- | --- | --- |
| Projects | MCP helper: `resolve_project_url` | Resolve a Hex project URL to an API project UUID | No | Yes | Yes |
| Embedding | `CreatePresignedUrl` | Create an embedded app URL | No | No | Yes |
| Projects | `CreateProject` | Create a project | `hex project create` | No | Yes |
| Projects | `ListProjects` | List projects | `hex project list` | Yes | Yes |
| Projects | `GetQueriedTables` | List tables queried by a project | No | Yes | Yes |
| Projects | `EditProjectSharingCollections` | Change collection sharing | No | No | Yes |
| Projects | `EditProjectSharingOrgAndPublic` | Change workspace and public sharing | No | No | Yes |
| Projects | `EditProjectSharingGroups` | Change group sharing | No | No | Yes |
| Projects | `EditProjectSharingUsers` | Change user sharing | No | No | Yes |
| Projects | `UpdateProject` | Update project metadata | No direct command | No | Yes |
| Projects | `GetProject` | Get project details | `hex project get` | Yes | Yes |
| Semantic projects | `IngestSemanticProject` | Ingest a semantic project or model | No | No | Yes |
| Semantic projects | `UpdateSemanticProject` | Update a semantic project or model | No | No | Yes |
| Runs | `RunProject` | Trigger a published project run | `hex app run` | No | Yes |
| Runs | `GetProjectRuns` | List project runs | `hex run list` | Yes | Yes |
| Runs | `GetRunStatus` | Get run status | `hex run status` | Yes | Yes |
| Runs | `CancelRun` | Cancel a run | `hex run cancel` | No | Yes |
| Groups | `GetGroup` | Get group details | `hex group get` | Yes | Yes |
| Groups | `DeleteGroup` | Delete a group | `hex group delete` | No | Yes |
| Groups | `EditGroup` | Rename a group or change members | No | No | Yes |
| Groups | `ListGroups` | List groups | `hex group list` | Yes | Yes |
| Groups | `CreateGroup` | Create a group | `hex group create` | No | Yes |
| Data connections | `GetDataConnection` | Get connection details | `hex connection get` | Yes | Yes |
| Data connections | `EditDataConnection` | Update connection configuration or sharing | No | No | Yes |
| Data connections | `ListDataConnections` | List connections | `hex connection list` | Yes | Yes |
| Data connections | `CreateDataConnection` | Create a connection | No | No | Yes |
| Data connections | `UpdateDataConnectionSchema` | Refresh or update connection schema | No | No | Yes |
| Collections | `GetCollection` | Get collection details | `hex collection get` | Yes | Yes |
| Collections | `EditCollection` | Update collection metadata or sharing | No | No | Yes |
| Collections | `ListCollections` | List collections | `hex collection list` | Yes | Yes |
| Collections | `CreateCollection` | Create a collection | No | No | Yes |
| Guides | `UpsertGuideDraft` | Create or update a guide draft | Partial: `hex guide preview` | No | Yes |
| Guides | `PublishGuideDrafts` | Publish guide drafts | `hex guide publish` | No | Yes |
| Guides | `DeleteGuideDraft` | Delete a guide draft | Partial: `hex guide preview --prune` | No | Yes |
| Cells | `GetChartImageFromLogic` | Get a chart image from project logic | No direct command | Yes | Yes |
| Cells | `GetCell` | Get a cell | `hex cell get` | Yes | Yes |
| Cells | `UpdateCell` | Update cell source or connection | `hex cell update` | No | Yes |
| Cells | `DeleteCell` | Delete a cell | `hex cell delete` | No | Yes |
| Cells | `GetCellOutput` | Get the latest cell output | `hex cell get --with-output` | Yes | Yes |
| Cells | `CreateCell` | Create a cell | `hex cell create` | No | Yes |
| Cells | `ListCells` | List project cells | `hex cell list` | Yes | Yes |
| Projects | `ExportProject` | Export a project | `hex project export` | Yes | Yes |
| Cells | `GetChartImageFromRun` | Get a chart image from a completed run | No direct command | Yes | Yes |
| Threads | `CreateThread` | Create an agent thread | No | No | Yes |
| Threads | `ListThreads` | List agent threads | `hex thread list` | Yes | Yes |
| Threads | `GetThread` | Get thread status and response | `hex thread get` | Yes | Yes |
| Threads | `GetThreadMessages` | List thread messages | `hex thread messages` | Yes | Yes |
| Threads | `ContinueThread` | Continue a thread | No | No | Yes |
| Users | `Me` | Get the authenticated user | Partial: `hex auth status` | Yes | Yes |
| Users | `ListUsers` | List workspace users | `hex user list` | Yes | Yes |
| Users | `DeactivateUser` | Deactivate a user | No | No | Yes |
| Context | `ListTopics` | List context topics | `hex context topic list` | Yes | Yes |
| Guides | `ListDraftGuides` | List draft guides | No | Yes | Yes |

## Coverage summary

| Surface | Operations available |
| --- | ---: |
| Official Hex public API | 52 |
| MCP `read-only` mode | 25 |
| MCP `full` mode | 53 |

The official [Hex MCP server](https://learn.hex.tech/docs/api-integrations/mcp-server) currently exposes four tools focused on project search and agent Threads. This project instead exposes the official public API as a curated MCP surface.

## Generation approach

- FastMCP's OpenAPI provider builds tools from the official operation IDs and schemas.
- A read-only MCP helper resolves project URLs through direct UUID extraction or paginated project-title matching.
- Tool names are stable snake-case forms of official operation IDs.
- `read-only` mode includes GET operations plus `ExportProject`, which is a non-mutating POST operation.
- `full` mode includes every operation returned by the official specification.
- Operation metadata is transformed to add MCP read-only, destructive, and idempotency annotations.
- Unknown future non-GET operations never appear in `read-only` mode.
