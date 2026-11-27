# SPDX-License-Identifier: MIT
"""Local Android Bridge Spotify MediaSession transport (no browser or DRM)."""

from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class AndroidSpotifyMedia:
    def __init__(self, base_url: str = "http://127.0.0.1:8772", timeout: float = 1.5):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def status(self) -> dict:
        with urlopen(self.base_url + "/media/spotify/status", timeout=self.timeout) as response:
            data = json.load(response)
        if not isinstance(data, dict):
            raise ValueError("Unexpected Spotify media response")
        return data

    def command(self, action: str) -> dict:
        if action not in {"play", "pause", "next", "previous"}:
            raise ValueError("Unsupported Spotify media command")
        request = Request(
            self.base_url + "/media/spotify/control",
            data=urlencode({"command": action}).encode("ascii"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            data = json.load(response)
        if not isinstance(data, dict):
            raise ValueError("Unexpected Spotify command response")
        return data
