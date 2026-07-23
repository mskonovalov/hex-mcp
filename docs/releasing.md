# Releasing

## One-time PyPI setup

Create a GitHub environment named `pypi`, then add a pending trusted publisher on PyPI with these values:

| Field | Value |
| --- | --- |
| PyPI project | `hex-openapi-mcp` |
| GitHub owner | `mskonovalov` |
| GitHub repository | `hex-mcp` |
| Workflow | `release.yml` |
| Environment | `pypi` |

The pending publisher does not reserve the project name. Complete this setup immediately before publishing the first release.

## Release checks

- CI passes from a fresh locked environment.
- The wheel and source distribution both pass `tests/smoke_test.py`.
- The stdio and Streamable HTTP transports start from the built package.
- A Hex test workspace exposes exactly 25 tools in `read-only` mode and 53 tools in `full` mode.
- Representative read operations succeed across projects, runs, users, data connections, and semantic projects.
- Write and destructive operations are exercised only against disposable test-workspace resources.
- Logs and MCP results contain no token or connection credential values.

## Publish

The release workflow requires the tag to match the version in `pyproject.toml`. From an up-to-date `main` branch:

```bash
VERSION="$(uv version --short)"
git tag -a "v${VERSION}" -m "v${VERSION}"
git push origin "v${VERSION}"
```

The tag builds and smoke-tests both distributions before publishing them to PyPI through trusted publishing.
