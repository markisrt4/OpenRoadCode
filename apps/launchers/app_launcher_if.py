# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeAlias, runtime_checkable


StatusCallback: TypeAlias = Callable[[str], None] | None


@runtime_checkable
class AppLauncherIf(Protocol):
    """Thread-compatible interface for launching external applications.

    Implementations may perform process management synchronously, but their
    methods must be safe to invoke from a worker thread.
    """

    def launch(self, remote_display: str, set_status: StatusCallback = None) -> None:
        """Launch the application."""
        ...

    def stop(self, remote_display: str, set_status: StatusCallback = None) -> None:
        """Stop the application."""
        ...

    def toggle(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        """Toggle the application's running state."""
        ...

    def is_running(self) -> bool:
        """Return whether the application is currently running."""
        ...


@runtime_checkable
class PreloadableAppLauncherIf(AppLauncherIf, Protocol):
    """Launcher capable of warming application resources without presenting UI."""

    def prepare(self) -> None:
        """Prepare backend or process resources without presenting the app."""
        ...


@runtime_checkable
class BrowserDashboardLauncherIf(AppLauncherIf, Protocol):
    """Launcher whose browser view can close without stopping its server."""

    def close_browser(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> None:
        """Close only the dashboard browser and keep its backend warm."""
        ...
