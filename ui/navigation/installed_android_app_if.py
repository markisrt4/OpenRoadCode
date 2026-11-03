# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Platform-neutral request to launch an already installed Android app."""
from typing import Protocol


class InstalledAndroidAppLauncherIf(Protocol):
    def launch_installed_app(self, package: str, *, uri: str | None = None) -> str | None:
        """Launch the app, optionally delivering a deep link; None means unavailable."""
        ...

    def stop_installed_app(self, package: str) -> None:
        """Stop only the explicitly selected app, or raise if it cannot be stopped."""
        ...

    def resume_installed_app(self, package: str) -> None:
        """Bring the existing activity forward without resending a destination."""
        ...
