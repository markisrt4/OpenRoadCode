# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Platform-neutral request to launch an already installed Android app."""

from typing import Protocol


class InstalledAndroidAppLauncherIf(Protocol):
    def launch_installed_app(self, package: str, *, uri: str | None = None) -> str | None:
        """Launch the app, optionally delivering a deep link; None means unavailable.

        @param package Android package identifier.
        @param uri Optional app deep link.
        @return App display name on success, or None when unavailable.
        """
        ...

    def stop_installed_app(self, package: str) -> None:
        """Stop only the explicitly selected app, or raise if it cannot be stopped.

        @param package Android package identifier.
        """
        ...

    def resume_installed_app(self, package: str) -> None:
        """Bring the existing activity forward without resending a destination.

        @param package Android package identifier.
        """
        ...
