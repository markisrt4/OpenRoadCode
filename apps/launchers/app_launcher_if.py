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
        """Launch the application.

        @param remote_display X11 display used for the application window.
        @param set_status Optional callback for launcher status messages.
        """
        ...

    def stop(self, remote_display: str, set_status: StatusCallback = None) -> None:
        """Stop the application.

        @param remote_display X11 display associated with the application window.
        @param set_status Optional callback for launcher status messages.
        """
        ...

    def toggle(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        """Toggle the application's running state.

        @param remote_display X11 display used for the application window.
        @param set_status Optional callback for launcher status messages.
        @return ``True`` when the application is running after the toggle.
        """
        ...

    def is_running(self) -> bool:
        """Return whether the application is currently running.

        @return ``True`` when the launcher considers the application active.
        """
        ...


@runtime_checkable
class HideableAppLauncherIf(AppLauncherIf, Protocol):
    """Launcher whose visible window can be hidden while its process stays warm."""

    def hide(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        """Hide the application without terminating it.

        @param remote_display X11 display containing the application window.
        @param set_status Optional callback for launcher status messages.
        @return ``True`` when the application window was hidden.
        """
        ...


@runtime_checkable
class WindowedAppLauncherIf(HideableAppLauncherIf, Protocol):
    """Launcher whose existing window can be explicitly shown or hidden."""

    def show(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        """Show and focus an already-running application window.

        @param remote_display X11 display containing the application window.
        @param set_status Optional callback for launcher status messages.
        @return ``True`` when an existing application window was shown.
        """
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
        """Close only the dashboard browser and keep its backend warm.

        @param remote_display X11 display containing the dashboard browser.
        @param set_status Optional callback for launcher status messages.
        """
        ...
