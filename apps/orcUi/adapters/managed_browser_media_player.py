# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Adapt AppRuntimeManager browser launchers to the media-player contract."""

from __future__ import annotations

from collections.abc import Callable
import logging

from common.logging.structured import current_operation, event, operation

from apps.launchers.browser_launcher import BrowserKioskLauncher
from controllers.application_runtime import AppRuntimeManager

LOGGER = logging.getLogger("media.browser")


class ManagedBrowserMediaPlayer:
    """Route media browser lifecycle through the shared application runtime."""

    def __init__(
        self,
        manager: AppRuntimeManager,
        key: str,
        *,
        resolve_target: Callable[[str], str],
        preferred_color_scheme: Callable[[], str] | None = None,
        network_allowed: Callable[[], bool] = lambda: True,
    ) -> None:
        self._network_allowed = network_allowed
        self._manager = manager
        self._key = key
        self._resolve_target = resolve_target
        self._preferred_color_scheme = preferred_color_scheme

    def play(
        self,
        target: str,
        *,
        display: str,
        window_position: tuple[int, int] | None = None,
        window_size: tuple[int, int] | None = None,
    ) -> bool:
        """Launch a media target through the shared X11 runtime manager."""
        with operation(current_operation()):
            event(
                LOGGER,
                logging.INFO,
                "browser.requested",
                "Media browser requested",
                player=self._key,
            )
            try:
                return self._play(
                    target,
                    display=display,
                    window_position=window_position,
                    window_size=window_size,
                )
            except Exception as error:
                event(
                    LOGGER,
                    logging.ERROR,
                    "browser.failed",
                    "Media browser launch failed",
                    player=self._key,
                    exception_type=type(error).__name__,
                )
                raise

    def _play(self, target: str, *, display: str, window_position=None, window_size=None) -> bool:
        del display
        if not self._network_allowed():
            raise RuntimeError("Online video unavailable in offline mode")
        launcher = self._manager.launcher(self._key, BrowserKioskLauncher)
        resolved_target = self._resolve_target(target)

        if self._manager.is_running(self._key):
            self._manager.close(self._key)

        if self._preferred_color_scheme is not None:
            launcher.set_preferred_color_scheme(self._preferred_color_scheme())
        launcher.set_url(resolved_target)
        if window_position is not None and window_size is not None:
            launcher.configure_app_window(
                position=window_position,
                size=window_size,
            )

        if not self._network_allowed():
            return False
        self._manager.show(self._key)
        if not self._network_allowed():
            self.stop()
            return False
        event(
            LOGGER,
            logging.INFO,
            "browser.show_completed",
            "Media browser show completed",
            player=self._key,
        )
        return True

    def stop(self) -> None:
        """Close the managed browser through shared runtime lifecycle policy."""
        if self._manager.is_running(self._key):
            with operation(current_operation()):
                try:
                    self._manager.close(self._key)
                except Exception as error:
                    event(
                        LOGGER,
                        logging.ERROR,
                        "browser.stop_failed",
                        "Media browser stop failed",
                        player=self._key,
                        exception_type=type(error).__name__,
                    )
                    raise
                event(
                    LOGGER,
                    logging.INFO,
                    "browser.close_completed",
                    "Media browser close completed",
                    player=self._key,
                )

    def is_active(self) -> bool:
        """Return whether the managed browser process is running."""
        return self._manager.is_running(self._key)
