# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Small dependency-free Chrome DevTools Protocol client helpers."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DevToolsTarget:
    id: str
    title: str
    url: str


class ChromiumDevToolsClient:
    """Use Chromium's HTTP DevTools endpoint for simple page commands."""

    def __init__(self, *, host: str = "127.0.0.1", port: int = 9223, timeout_seconds: float = 1.0) -> None:
        self._base_url = f"http://{host}:{port}"
        self._timeout_seconds = timeout_seconds

    def targets(self) -> tuple[DevToolsTarget, ...]:
        payload = self._json_get("/json/list")
        if not isinstance(payload, list):
            return ()
        return tuple(
            DevToolsTarget(
                id=str(item.get("id", "")),
                title=str(item.get("title", "")),
                url=str(item.get("url", "")),
            )
            for item in payload
            if item.get("type") == "page" and item.get("id")
        )

    def earth_target(self) -> DevToolsTarget | None:
        for target in self.targets():
            if "earth.google.com" in target.url:
                return target
        return None

    def activate(self, target_id: str) -> bool:
        encoded = urllib.parse.quote(target_id, safe="")
        try:
            self._json_get(f"/json/activate/{encoded}")
            return True
        except (OSError, ValueError):
            return False

    def version(self) -> dict[str, Any]:
        payload = self._json_get("/json/version")
        return payload if isinstance(payload, dict) else {}

    def _json_get(self, path: str) -> Any:
        request = urllib.request.Request(self._base_url + path, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
            return json.load(response)
