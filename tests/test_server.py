# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
import json

from mcp import Client

from beekeeper_mcp import server

mcp = server.mcp


def test_server_exposes_resources_without_model_callable_tools() -> None:
    async def inspect_server() -> tuple[list[str], list[str], list[str]]:
        async with Client(mcp) as client:
            tools = [item.name for item in (await client.list_tools()).tools]
            resources = [str(item.uri) for item in (await client.list_resources()).resources]
            templates = [
                str(item.uri_template)
                for item in (await client.list_resource_templates()).resource_templates
            ]
            return tools, resources, templates

    tools, resources, templates = asyncio.run(inspect_server())

    assert tools == []
    assert resources == ["beekeeper://status", "beekeeper://now-playing"]
    assert templates == [
        "beekeeper://library/search/{query}",
        "beekeeper://library/track/{source_id}",
    ]


def test_search_resource_decodes_query(monkeypatch) -> None:
    class FakeClient:
        def search_library(self, query: str) -> list[str]:
            assert query == "artist=Massive Attack"
            return [r"C:\Music\Teardrop.flac"]

    monkeypatch.setattr(server, "_client", lambda: FakeClient())

    async def read_search() -> str:
        async with Client(mcp) as client:
            result = await client.read_resource(
                "beekeeper://library/search/artist%3DMassive%20Attack"
            )
            return result.contents[0].text

    payload = json.loads(asyncio.run(read_search()))

    assert payload == [
        {
            "sourceFileUrl": r"C:\Music\Teardrop.flac",
            "resourceUri": server.track_resource_uri(r"C:\Music\Teardrop.flac"),
        }
    ]


def test_track_resource_accepts_a_unicode_windows_path(monkeypatch) -> None:
    source_file_url = "F:\\MusicBee\\Music\\ミリプロ\\イケナイ太陽.flac"

    class FakeClient:
        def track_metadata(self, requested_url: str) -> dict[str, str]:
            assert requested_url == source_file_url
            return {"sourceFileUrl": requested_url, "title": "イケナイ太陽"}

    monkeypatch.setattr(server, "_client", lambda: FakeClient())

    async def read_track() -> str:
        async with Client(mcp) as client:
            result = await client.read_resource(server.track_resource_uri(source_file_url))
            return result.contents[0].text

    payload = json.loads(asyncio.run(read_track()))

    assert payload["title"] == "イケナイ太陽"
