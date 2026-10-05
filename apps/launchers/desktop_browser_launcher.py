# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Hand POI web destinations to the Linux desktop's configured browser."""
from __future__ import annotations

import shutil
import subprocess

from tools.map_builder.builder.web_urls import valid_website


class DesktopBrowserLauncherError(RuntimeError):
    """The desktop could not accept a browser launch request."""


class DesktopBrowserLauncher:
    def open_uri(self, uri: str) -> None:
        uri = valid_website(uri)
        if uri is None:
            raise ValueError("POI destination must be a valid HTTP or HTTPS URL")
        gio = shutil.which("gio")
        opener = gio or shutil.which("xdg-open")
        if opener is None:
            raise DesktopBrowserLauncherError("Install gio or xdg-utils and configure a default browser")
        command = [opener, "open", uri] if gio else [opener, uri]
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    check=False, timeout=5)
        except subprocess.TimeoutExpired as exc:
            raise DesktopBrowserLauncherError(
                "Browser handoff timed out; check whether the browser opened"
            ) from exc
        except OSError as exc:
            raise DesktopBrowserLauncherError(f"Unable to open desktop browser: {exc}") from exc
        if result.returncode:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
            raise DesktopBrowserLauncherError(f"Desktop browser handoff failed: {detail}")
