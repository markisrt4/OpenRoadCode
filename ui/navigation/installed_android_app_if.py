# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Platform-neutral request to launch an already installed Android app."""
from typing import Protocol


class InstalledAndroidAppLauncherIf(Protocol):
    def launch_installed_app(self, package: str) -> str | None:
        """Return the launched app's display name, or None when unavailable."""
        ...
