# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import os
from functools import lru_cache
from urllib.parse import unquote

from mcp.server import MCPServer

from beekeeper_mcp.client import BeekeeperClient, JsonValue

mcp = MCPServer(
    "Beekeeper",
    instructions=(
        "Read-only access to MusicBee through Beekeeper. "
        "Library changes are intentionally not exposed through MCP; use the Web API directly."
    ),
)


@lru_cache(maxsize=1)
def _client() -> BeekeeperClient:
    return BeekeeperClient(os.getenv("BEEKEEPER_URL", "http://localhost:8080"))


def _json(value: JsonValue) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


@mcp.resource("beekeeper://status")
def status() -> str:
    """Return Beekeeper connectivity, client count, and read-only configuration."""
    return _json(_client().status())


@mcp.resource("beekeeper://now-playing")
def now_playing() -> str:
    """Return the current MusicBee track and playback state."""
    return _json(_client().now_playing())


@mcp.resource("beekeeper://library/search/{query}")
def search_library(query: str) -> str:
    """Search the MusicBee library without modifying it."""
    return _json(_client().search_library(unquote(query)))


@mcp.resource("beekeeper://library/track/{source_file_url}")
def track_metadata(source_file_url: str) -> str:
    """Return metadata for one MusicBee library file without modifying it."""
    return _json(_client().track_metadata(unquote(source_file_url)))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
