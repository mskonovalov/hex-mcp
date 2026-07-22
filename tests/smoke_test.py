from importlib.metadata import distribution

import hex_mcp

package = distribution("hex-openapi-mcp")

assert package.version == hex_mcp.__version__
assert any(
    entry_point.group == "console_scripts"
    and entry_point.name == "hex-mcp"
    and entry_point.value == "hex_mcp.server:main"
    for entry_point in package.entry_points
)
