# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Use Termux URLs for direct websites and Bridge app-first ordering."""
from __future__ import annotations

import subprocess
from urllib.parse import urlencode

from tools.map_builder.builder.web_urls import valid_website


class AndroidBridgeLauncherError(RuntimeError):
    """An Android destination handoff could not be requested."""


class AndroidBridgeLauncher:
    def __init__(self, executable: str = "termux-open-url") -> None:
        self._executable = executable

    def open_uri(self, uri: str) -> None:
        """A plain website needs only Termux's normal Android URL handler."""
        self._open_link(self._web_uri(uri))

    @staticmethod
    def _web_uri(uri: str) -> str:
        validated = valid_website(uri)
        if validated is None:
            raise ValueError("POI fallback must be a valid HTTP or HTTPS URL")
        return validated

    def open_package_or_uri(self, package: str | None, uri: str) -> str:
        uri = self._web_uri(uri)
        fields = {"uri": uri}
        if package and package.strip():
            fields["package"] = package.strip()
        link = "orcbridge://launch?" + urlencode(fields)
        self._open_link(link)
        # The bridge resolves package availability and web fallback asynchronously.
        return "Android"

    def _open_link(self, link: str) -> None:
        try:
            result = subprocess.run(
                [self._executable, link], capture_output=True, text=True,
                check=False, timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AndroidBridgeLauncherError(f"Unable to request Android URL launch: {exc}") from exc
        if result.returncode:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
            raise AndroidBridgeLauncherError(f"Android URL handoff failed: {detail}")
