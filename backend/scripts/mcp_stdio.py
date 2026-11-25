"""Run the BariBhara MCP server over stdio (for Claude Desktop, MCP Inspector, ...).

    npx @modelcontextprotocol/inspector uv --directory backend run python -m scripts.mcp_stdio

stdout carries the MCP protocol, so nothing else may print to it; logs go to stderr.
"""

import logging
import sys

from app.mcp.server import mcp


def main() -> None:
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
