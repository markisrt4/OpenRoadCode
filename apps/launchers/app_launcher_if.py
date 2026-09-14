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
        """! @brief Launch the application for normal presentation.

        @param remote_display Display identifier used for the application presentation.
        @param set_status Optional callback used to report launcher status text.
        """
        ...

    def stop(self, remote_display: str, set_status: StatusCallback = None) -> None:
        """! @brief Stop the application.

        @param remote_display Display identifier associated with the application.
        @param set_status Optional callback used to report launcher status text.
        """
        ...

    def toggle(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        """! @brief Toggle the application's running state.

        @param remote_display Display identifier used for the application presentation.
        @param set_status Optional callback used to report launcher status text.
        @return True when the application is running after the toggle, otherwise False.
        """
        ...

    def is_running(self) -> bool:
        """! @brief Return whether the application is currently running.

        @return True when the application is running, otherwise False.
        """
        ...


@runtime_checkable
class HideableAppLauncherIf(AppLauncherIf, Protocol):
    """Launcher whose visible window can be hidden while its process stays warm."""

    def hide(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        """! @brief Hide the application without terminating it.

        @param remote_display Display identifier associated with the application window.
        @param set_status Optional callback used to report launcher status text.
        @return True when the application was hidden successfully, otherwise False.
        """
        ...


@runtime_checkable
class WindowedAppLauncherIf(HideableAppLauncherIf, Protocol):
    """Launcher whose existing window can be explicitly shown or hidden."""

    def show(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        """! @brief Show an already-running application window.

        @param remote_display Display identifier on which the window should be shown.
        @param set_status Optional callback used to report launcher status text.
        @return True when the application window was shown successfully, otherwise False.
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
        """! @brief Warm the application on its target display while keeping it hidden.

        @param remote_display Display identifier used while preparing the application.
        @param set_status Optional callback used to report launcher status text.
        """
        ...


@runtime_checkable
class BrowserDashboardLauncherIf(AppLauncherIf, Protocol):
    """Launcher whose browser view can close without stopping its server."""

    def close_browser(self, remote_display: str, set_status: StatusCallback = None) -> None:
        """! @brief Close only the dashboard browser and keep its backend warm.

        @param remote_display Display identifier associated with the dashboard browser.
        @param set_status Optional callback used to report launcher status text.
        """
        ...
