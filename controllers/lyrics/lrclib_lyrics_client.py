# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


_TIMESTAMP = re.compile(
    r"\[(?P<minutes>\d+):(?P<seconds>\d+(?:\.\d+)?)\]"
)


@dataclass(frozen=True, slots=True)
class LyricLine:
    time_ms: int
    text: str


@dataclass(frozen=True, slots=True)
class LyricsResult:
    synced_lines: tuple[LyricLine, ...] = ()
    plain_lines: tuple[str, ...] = ()


class LrclibLyricsClient:
    """Fetch and cache synchronized lyrics from LRCLIB."""

    API_URL = "https://lrclib.net/api/get"

    def __init__(
        self,
        *,
        max_entries: int = 64,
        fetch_json: Callable[[str], dict[str, Any]] | None = None,
    ) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self._max_entries = max_entries
        self._fetch_json = fetch_json or self._request_json
        self._cache: OrderedDict[
            tuple[str, str, str, int],
            LyricsResult | None,
        ] = OrderedDict()
        self._lock = threading.RLock()

    def get_lyrics(
        self,
        *,
        track_name: str,
        artist_name: str,
        album_name: str = "",
        duration_ms: int = 0,
    ) -> LyricsResult | None:
        key = (
            track_name.strip(),
            artist_name.strip(),
            album_name.strip(),
            max(0, duration_ms // 1000),
        )
        if not key[0] or not key[1]:
            return None

        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]

        parameters = {
            "track_name": key[0],
            "artist_name": key[1],
            "album_name": key[2],
            "duration": str(key[3]),
        }
        payload = self._fetch_json(
            f"{self.API_URL}?{urllib.parse.urlencode(parameters)}"
        )
        result = LyricsResult(
            synced_lines=self.parse_synced(
                str(payload.get("syncedLyrics") or "")
            ),
            plain_lines=tuple(
                line.strip()
                for line in str(
                    payload.get("plainLyrics") or ""
                ).splitlines()
                if line.strip()
            ),
        )
        if not result.synced_lines and not result.plain_lines:
            cached_result = None
        else:
            cached_result = result

        with self._lock:
            self._cache[key] = cached_result
            while len(self._cache) > self._max_entries:
                self._cache.popitem(last=False)
        return cached_result

    @staticmethod
    def parse_synced(value: str) -> tuple[LyricLine, ...]:
        lines: list[LyricLine] = []
        for raw_line in value.splitlines():
            match = _TIMESTAMP.match(raw_line)
            if match is None:
                continue
            minutes = int(match.group("minutes"))
            seconds = float(match.group("seconds"))
            text = raw_line[match.end():].strip()
            if text:
                lines.append(
                    LyricLine(
                        time_ms=int(
                            (minutes * 60 + seconds) * 1000
                        ),
                        text=text,
                    )
                )
        return tuple(sorted(lines, key=lambda line: line.time_ms))

    @staticmethod
    def _request_json(url: str) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "OpenRoadCode/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(
                    response.read().decode("utf-8")
                )
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return {}
            raise RuntimeError(
                f"LRCLIB request failed with HTTP {error.code}"
            ) from error
        except (urllib.error.URLError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Unable to retrieve lyrics: {error}") from error
        if not isinstance(payload, dict):
            raise RuntimeError("LRCLIB returned an unexpected response")
        return payload
