# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Client for localhost Android host actions exposed by the ORC Android Bridge."""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request


class AndroidHostActionClientError(RuntimeError):
    """Raised when the Android Bridge cannot satisfy a host action."""


class AndroidHostActionClient:
    """Ask the Android host to launch packages or open URIs."""

    def __init__(self, base_url: str = "http://127.0.0.1:8770", timeout_s: float = 2.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s

    def launch_package(self, package: str) -> None:
        package = package.strip()
        if not package:
            raise ValueError("Android package name must not be empty")
        self._post("/launch/package", {"package": package})

    def open_uri(self, uri: str) -> None:
        uri = uri.strip()
        if not uri:
            raise ValueError("Android URI must not be empty")
        self._post("/open/uri", {"uri": uri})

    def open_package_or_uri(self, package: str | None, uri: str) -> str:
        if package:
            try:
                self.launch_package(package)
                return "app"
            except AndroidHostActionClientError:
                pass
        self.open_uri(uri)
        return "uri"

    def _post(self, path: str, fields: dict[str, str]) -> None:
        data = urllib.parse.urlencode(fields).encode("utf-8")
        request = urllib.request.Request(
            self._base_url + path,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_s) as response:
                if response.status != 200:
                    raise AndroidHostActionClientError(
                        f"Android host action failed with HTTP {response.status}"
                    )
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            raise AndroidHostActionClientError(
                f"Android host action request failed: {exc}"
            ) from exc
