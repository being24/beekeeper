# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from typing import Protocol, Self, TypeVar
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
T = TypeVar("T")


class HttpResponse(Protocol):
    def __enter__(self) -> Self: ...

    def __exit__(self, *args: object) -> None: ...

    def read(self) -> bytes: ...


class HttpOpener(Protocol):
    def __call__(self, request: Request, *, timeout: float) -> HttpResponse: ...


class BeekeeperError(RuntimeError):
    """Raised when the Beekeeper Web API cannot satisfy a read request."""


class BeekeeperClient:
    """Small client exposing only side-effect-free Beekeeper operations."""

    _READ_METHODS = frozenset(
        {
            "Library_GetFileTags",
            "Library_QueryFilesEx",
            "NowPlaying_GetFileTags",
            "NowPlaying_GetFileUrl",
            "Player_GetPosition",
            "Player_GetPlayState",
            "Setting_GetReadOnly_BK",
        }
    )

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        timeout: float = 5.0,
        opener: HttpOpener = urlopen,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._opener = opener

    def status(self) -> dict[str, JsonValue]:
        status = self._get_json("status")
        if not isinstance(status, dict):
            raise BeekeeperError("Beekeeper returned an invalid status response")
        status["readOnly"] = self._call("Setting_GetReadOnly_BK", {})
        return status

    def now_playing(self) -> dict[str, JsonValue]:
        fields = [65, 32, 30, 31, 59, 86, 52, 75]
        values = self._call("NowPlaying_GetFileTags", {"fields": fields})
        if not isinstance(values, list) or len(values) != len(fields):
            raise BeekeeperError("Beekeeper returned invalid now-playing metadata")
        return {
            "sourceFileUrl": self._call("NowPlaying_GetFileUrl", {}),
            "playState": self._call("Player_GetPlayState", {}),
            "positionMilliseconds": self._call("Player_GetPosition", {}),
            "title": values[0],
            "artist": values[1],
            "album": values[2],
            "albumArtist": values[3],
            "genre": values[4],
            "trackNumber": values[5],
            "discNumber": values[6],
            "rating": values[7],
        }

    def search_library(self, query: str) -> list[str]:
        result = self._call("Library_QueryFilesEx", {"query": query})
        if not isinstance(result, list) or not all(isinstance(item, str) for item in result):
            raise BeekeeperError("Beekeeper returned an invalid library search response")
        return result

    def track_metadata(self, source_file_url: str) -> dict[str, JsonValue]:
        fields = [65, 32, 30, 31, 59, 86, 52, 75, 44]
        values = self._call(
            "Library_GetFileTags",
            {"sourceFileUrl": source_file_url, "fields": fields},
        )
        if not isinstance(values, list) or len(values) != len(fields):
            raise BeekeeperError("Beekeeper returned invalid track metadata")
        names = [
            "title",
            "artist",
            "album",
            "albumArtist",
            "genre",
            "trackNumber",
            "discNumber",
            "rating",
            "comment",
        ]
        return {"sourceFileUrl": source_file_url, **dict(zip(names, values, strict=True))}

    def _call(self, method: str, parameters: dict[str, JsonValue]) -> JsonValue:
        if method not in self._READ_METHODS:
            raise ValueError(
                f"Beekeeper method is not allowed by the read-only MCP bridge: {method}"
            )
        return self._request(method, parameters)

    def _get_json(self, path: str) -> JsonValue:
        return self._request(path, None)

    def _request(self, path: str, parameters: dict[str, JsonValue] | None) -> JsonValue:
        data = None if parameters is None else json.dumps(parameters).encode("utf-8")
        request = Request(
            f"{self._base_url}/{path}",
            data=data,
            headers={"Content-Type": "application/json"} if data is not None else {},
            method="POST" if data is not None else "GET",
        )
        try:
            response = self._opener(request, timeout=self._timeout)
            with response:
                payload = response.read().decode("utf-8")
            return json.loads(payload)
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            raise BeekeeperError(f"Beekeeper request failed for {path}: {error}") from error
