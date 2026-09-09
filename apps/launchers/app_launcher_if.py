# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeAlias, runtime_checkable


StatusCallback: TypeAlias = Callable[[str], None] | None


@runtime_checkable
class AppLauncherIf(Protocol):
    """Thread-compatible interface for launching external applications."""

    def launch(self, remote_display: str, set_status: StatusCallback = None) -> None:
        """Launch the application for normal presentation."""
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
class HideableAppLauncherIf(AppLauncherIf, Protocol):
    """Launcher whose visible window can be hidden while its process stays warm."""

    def hide(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        """Hide the application without terminating it."""
        ...


@runtime_checkable
class WindowedAppLauncherIf(HideableAppLauncherIf, Protocol):
    """Launcher whose existing window can be explicitly shown or hidden."""

    def show(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        """Show an already-running application window."""
        ...


@runtime_checkable
class PreloadableAppLauncherIf(AppLauncherIf, Protocol):
    """Launcher capable of warming resources without presenting its UI."""

    def prepare(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> None:
        """Warm the application on its target display while keeping it hidden."""
        ...


@runtime_checkable
class BrowserDashboardLauncherIf(AppLauncherIf, Protocol):
    """Launcher whose browser view can close without stopping its server."""

    def close_browser(self, remote_display: str, set_status: StatusCallback = None) -> None:
        """Close only the dashboard browser and keep its backend warm."""
        ...
