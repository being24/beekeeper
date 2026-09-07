# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import io
import json
from typing import Self
from urllib.request import Request

import pytest

from beekeeper_mcp.client import BeekeeperClient


class Response(io.BytesIO):
    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def test_search_library_calls_only_the_query_endpoint() -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def opener(request: Request, *, timeout: float) -> Response:
        calls.append((request.full_url, json.loads(request.data or b"{}")))
        assert timeout == 5.0
        return Response(json.dumps(["C:\\Music\\one.mp3"]).encode())

    client = BeekeeperClient(opener=opener)

    assert client.search_library("domain=Music") == ["C:\\Music\\one.mp3"]
    assert calls == [("http://localhost:8080/Library_QueryFilesEx", {"query": "domain=Music"})]


def test_write_method_is_rejected_before_an_http_request() -> None:
    def opener(_request: Request, *, timeout: float) -> Response:
        pytest.fail(f"HTTP request should not be made (timeout={timeout})")

    client = BeekeeperClient(opener=opener)

    with pytest.raises(ValueError, match="not allowed"):
        client._call("Library_SetFileTag", {})


def test_now_playing_maps_metadata_fields() -> None:
    responses = {
        "NowPlaying_GetFileTags": ["Title", "Artist", "Album", "AA", "Rock", "1", "1", "80"],
        "NowPlaying_GetFileUrl": "C:\\Music\\one.mp3",
        "Player_GetPosition": 1200,
        "Player_GetPlayState": 3,
    }

    def opener(request: Request, *, timeout: float) -> Response:
        del timeout
        method = request.full_url.rsplit("/", 1)[-1]
        return Response(json.dumps(responses[method]).encode())

    result = BeekeeperClient(opener=opener).now_playing()

    assert result["title"] == "Title"
    assert result["playState"] == 3
    assert result["positionMilliseconds"] == 1200
