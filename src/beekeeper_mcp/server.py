# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import os
from base64 import urlsafe_b64decode, urlsafe_b64encode
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


def track_resource_uri(source_file_url: str) -> str:
    """Build a URI-safe identifier without exposing a file path as URI structure."""
    source_id = urlsafe_b64encode(source_file_url.encode("utf-8")).decode("ascii").rstrip("=")
    return f"beekeeper://library/track/{source_id}"


def _source_file_url(source_id: str) -> str:
    padding = "=" * (-len(source_id) % 4)
    try:
        return urlsafe_b64decode(source_id + padding).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError("Invalid MusicBee track identifier") from error


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
    matches = _client().search_library(unquote(query))
    return _json(
        [
            {"sourceFileUrl": source_file_url, "resourceUri": track_resource_uri(source_file_url)}
            for source_file_url in matches
        ]
    )


@mcp.resource("beekeeper://library/track/{source_id}")
def track_metadata(source_id: str) -> str:
    """Return metadata for one MusicBee library file without modifying it."""
    return _json(_client().track_metadata(_source_file_url(source_id)))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
