# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Bridge system audio control to toolkit-independent volume UI contracts."""

from __future__ import annotations

import logging
from collections.abc import Callable

from common.logging.structured import current_operation, event, operation
from controllers.audio.audio_controller_if import AudioControllerIf
from controllers.cache.persistent_cache_if import PersistentCacheIf
from ui.system import VolumeRequestHandlerIf, VolumeUiIf

LOGGER = logging.getLogger("media.audio")
VOLUME_CACHE_KEY = "system-volume-percent"


class SystemVolumeHandler(VolumeRequestHandlerIf):
    """Apply semantic system-volume requests and publish normalized state."""

    def __init__(
        self,
        *,
        audio_controller: AudioControllerIf,
        volume_ui: VolumeUiIf,
        set_status: Callable[[str], None] | None = None,
        cache: PersistentCacheIf | None = None,
    ) -> None:
        self._audio_controller = audio_controller
        self._volume_ui = volume_ui
        self._set_status = set_status or (lambda _message: None)
        self._available: bool | None = None
        self._cache = cache

    def refresh(self, *, restore_cached: bool = False) -> None:
        """Read and publish current system volume and mute state."""
        if not self._audio_controller.is_available:
            self._report_availability(False)
            self._volume_ui.set_volume(None)
            self._volume_ui.set_muted(None)
            self._set_status(self._audio_controller.status_message or "Volume unavailable")
            return
        try:
            level = self._restore_level() if restore_cached else None
            if level is None:
                level = self._audio_controller.get_volume_level()
            self._publish_level(level)
            self._volume_ui.set_muted(self._audio_controller.is_muted())
            self._report_availability(True)
        except (OSError, RuntimeError) as error:
            self._report_availability(False, error)
            self._volume_ui.set_volume(None)
            self._volume_ui.set_muted(None)
            self._set_status("Volume unavailable")

    def request_volume(self, volume_percent: float) -> None:
        """Apply an absolute normalized system-volume request."""
        maximum = self._audio_controller.maximum_level
        level = round(max(0.0, min(100.0, volume_percent)) * maximum / 100.0)
        try:
            self._execute(
                "volume",
                lambda: self._publish_level(
                    self._audio_controller.set_volume_level(level), remember=True
                ),
            )
        except (OSError, RuntimeError):
            self._set_status("Volume change failed")

    def request_volume_up(self) -> None:
        """Increase system volume by one backend-defined step."""
        try:
            self._execute(
                "volume_up",
                lambda: self._publish_level(self._audio_controller.volume_up(), remember=True),
            )
        except (OSError, RuntimeError):
            self._set_status("Volume up failed")

    def request_volume_down(self) -> None:
        """Decrease system volume by one backend-defined step."""
        try:
            self._execute(
                "volume_down",
                lambda: self._publish_level(self._audio_controller.volume_down(), remember=True),
            )
        except (OSError, RuntimeError):
            self._set_status("Volume down failed")

    def request_mute(self, muted: bool) -> None:
        """Apply an explicit system mute state."""
        try:
            self._execute("mute", lambda: self._apply_mute(muted))
        except (OSError, RuntimeError):
            self._set_status("Mute request failed")

    def _apply_mute(self, muted: bool) -> None:
        current = self._audio_controller.is_muted()
        resulting = self._audio_controller.toggle_mute() if current != muted else current
        self._volume_ui.set_muted(resulting)

    def _execute(self, action: str, command: Callable[[], None]) -> None:
        with operation(current_operation()):
            try:
                command()
            except (OSError, RuntimeError) as error:
                event(
                    LOGGER,
                    logging.ERROR,
                    "audio.command_failed",
                    "System audio command failed",
                    action=action,
                    exception_type=type(error).__name__,
                )
                raise
            event(
                LOGGER,
                logging.DEBUG,
                "audio.command_completed",
                "System audio command completed",
                action=action,
            )

    def _report_availability(self, available: bool, error: Exception | None = None) -> None:
        if self._available == available:
            return
        self._available = available
        event(
            LOGGER,
            logging.INFO if available else logging.WARNING,
            "audio.availability_changed",
            "System audio availability changed",
            available=available,
            exception_type=type(error).__name__ if error is not None else None,
        )

    def _restore_level(self) -> int | None:
        if self._cache is None:
            return None
        maximum = self._audio_controller.maximum_level
        if maximum <= 0:
            return None
        try:
            raw = self._cache.get(VOLUME_CACHE_KEY)
            percent = float(raw) if raw is not None else -1.0
            if 0.0 <= percent <= 100.0:
                return self._audio_controller.set_volume_level(round(percent * maximum / 100.0))
        except (OSError, RuntimeError, ValueError) as error:
            LOGGER.warning("Could not restore cached system volume (%s)", type(error).__name__)
        return None

    def _publish_level(self, level: int, *, remember: bool = False) -> None:
        maximum = self._audio_controller.maximum_level
        if maximum <= 0:
            self._volume_ui.set_volume(None)
            return
        percent = max(0.0, min(100.0, level * 100.0 / maximum))
        self._volume_ui.set_volume(percent)
        if remember and self._cache is not None:
            try:
                self._cache.put(VOLUME_CACHE_KEY, str(percent).encode("ascii"))
            except OSError as error:
                LOGGER.warning("Could not cache system volume (%s)", type(error).__name__)
