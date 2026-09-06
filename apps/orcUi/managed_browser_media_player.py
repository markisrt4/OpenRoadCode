# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Adapt AppRuntimeManager browser launchers to the media-player contract."""

from __future__ import annotations

from collections.abc import Callable

from apps.launchers.browser_launcher import BrowserKioskLauncher
from controllers.application_runtime import AppRuntimeManager


class ManagedBrowserMediaPlayer:
    """Route media browser lifecycle through the shared application runtime."""

    def __init__(
        self,
        manager: AppRuntimeManager,
        key: str,
        *,
        resolve_target: Callable[[str], str],
    ) -> None:
        self._manager = manager
        self._key = key
        self._resolve_target = resolve_target

    def play(
        self,
        target: str,
        *,
        display: str,
        window_position: tuple[int, int] | None = None,
        window_size: tuple[int, int] | None = None,
    ) -> bool:
        """Launch a media target through the shared X11 runtime manager."""
        del display
        launcher = self._manager.launcher(self._key, BrowserKioskLauncher)
        resolved_target = self._resolve_target(target)

        if self._manager.is_running(self._key):
            self._manager.close(self._key)

        launcher.set_url(resolved_target)
        if window_position is not None and window_size is not None:
            launcher.configure_app_window(
                position=window_position,
                size=window_size,
            )

        self._manager.show(self._key)
        return True

    def stop(self) -> None:
        """Close the managed browser through shared runtime lifecycle policy."""
        if self._manager.is_running(self._key):
            self._manager.close(self._key)

    def is_active(self) -> bool:
        """Return whether the managed browser process is running."""
        return self._manager.is_running(self._key)
