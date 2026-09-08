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
        """Launch the application for normal presentation.

        @param remote_display X11 display target used for presentation.
        @param set_status Optional callback for user-visible status updates.
        """
        ...

    def stop(self, remote_display: str, set_status: StatusCallback = None) -> None:
        """Stop the application.

        @param remote_display X11 display target associated with the application.
        @param set_status Optional callback for user-visible status updates.
        """
        ...

    def toggle(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        """Toggle the application's running state.

        @param remote_display X11 display target used for presentation.
        @param set_status Optional callback for user-visible status updates.
        @return True when the application is running after the toggle.
        """
        ...

    def is_running(self) -> bool:
        """Return whether the application is currently running.

        @return True when the application is running.
        """
        ...


@runtime_checkable
class HideableAppLauncherIf(AppLauncherIf, Protocol):
    """Launcher whose visible window can be hidden while its process stays warm."""

    def hide(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        """Hide the application without terminating it.

        @param remote_display X11 display target associated with the application.
        @param set_status Optional callback for user-visible status updates.
        @return True when an application window was hidden successfully.
        """
        ...


@runtime_checkable
class WindowedAppLauncherIf(HideableAppLauncherIf, Protocol):
    """Launcher whose existing window can be explicitly shown or hidden."""

    def show(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        """Show an already-running application window.

        @param remote_display X11 display target used for presentation.
        @param set_status Optional callback for user-visible status updates.
        @return True when an application window was shown successfully.
        """
        ...


@runtime_checkable
class PreloadableAppLauncherIf(AppLauncherIf, Protocol):
    """Launcher capable of warming resources without presenting its UI."""

    def prepare(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> None:
        """Warm the application on its target display while keeping it hidden.

        @param remote_display X11 display target used while preparing the application.
        @param set_status Optional callback for user-visible status updates.
        """
        ...


@runtime_checkable
class BrowserDashboardLauncherIf(AppLauncherIf, Protocol):
    """Launcher whose browser view can close without stopping its server."""

    def close_browser(self, remote_display: str, set_status: StatusCallback = None) -> None:
        """Close only the dashboard browser and keep its backend warm.

        @param remote_display X11 display target associated with the browser.
        @param set_status Optional callback for user-visible status updates.
        """
        ...
