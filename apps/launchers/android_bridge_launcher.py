# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Bring Android Bridge forward through Termux's Android URL handler."""
from __future__ import annotations

import subprocess
from urllib.parse import urlencode, urlsplit


class AndroidBridgeLauncherError(RuntimeError):
    """The Termux-to-Bridge handoff could not be requested."""


class AndroidBridgeLauncher:
    def __init__(self, executable: str = "termux-open-url") -> None:
        self._executable = executable

    def open_uri(self, uri: str) -> None:
        self.open_package_or_uri(None, uri)

    def open_package_or_uri(self, package: str | None, uri: str) -> str:
        uri = uri.strip()
        parsed = urlsplit(uri)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("POI fallback must be an HTTP or HTTPS URL")
        fields = {"uri": uri}
        if package and package.strip():
            fields["package"] = package.strip()
        link = "orcbridge://launch?" + urlencode(fields)
        try:
            result = subprocess.run(
                [self._executable, link], capture_output=True, text=True,
                check=False, timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AndroidBridgeLauncherError(f"Unable to open Android Bridge: {exc}") from exc
        if result.returncode:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
            raise AndroidBridgeLauncherError(f"Android Bridge handoff failed: {detail}")
        # The bridge resolves package availability and web fallback asynchronously.
        return "Android"
