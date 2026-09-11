# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Bridge system audio control to toolkit-independent volume UI contracts."""

from __future__ import annotations

from collections.abc import Callable

from controllers.audio.audio_controller_if import AudioControllerIf
from ui.system import VolumeRequestHandlerIf, VolumeUiIf


class SystemVolumeHandler(VolumeRequestHandlerIf):
    """Apply semantic system-volume requests and publish normalized state."""

    def __init__(
        self,
        *,
        audio_controller: AudioControllerIf,
        volume_ui: VolumeUiIf,
        set_status: Callable[[str], None] | None = None,
    ) -> None:
        self._audio_controller = audio_controller
        self._volume_ui = volume_ui
        self._set_status = set_status or (lambda _message: None)

    def refresh(self) -> None:
        """Read and publish current system volume and mute state."""
        if not self._audio_controller.is_available:
            self._volume_ui.set_volume(None)
            self._volume_ui.set_muted(None)
            self._set_status(
                self._audio_controller.status_message or "Volume unavailable"
            )
            return
        try:
            self._publish_level(self._audio_controller.get_volume_level())
            self._volume_ui.set_muted(self._audio_controller.is_muted())
        except (OSError, RuntimeError) as error:
            self._volume_ui.set_volume(None)
            self._volume_ui.set_muted(None)
            self._set_status(f"Volume unavailable: {error}")

    def request_volume(self, volume_percent: float) -> None:
        """Apply an absolute normalized system-volume request."""
        maximum = self._audio_controller.maximum_level
        level = round(max(0.0, min(100.0, volume_percent)) * maximum / 100.0)
        try:
            self._publish_level(self._audio_controller.set_volume_level(level))
        except (OSError, RuntimeError) as error:
            self._set_status(f"Volume change failed: {error}")

    def request_volume_up(self) -> None:
        """Increase system volume by one backend-defined step."""
        try:
            self._publish_level(self._audio_controller.volume_up())
        except (OSError, RuntimeError) as error:
            self._set_status(f"Volume up failed: {error}")

    def request_volume_down(self) -> None:
        """Decrease system volume by one backend-defined step."""
        try:
            self._publish_level(self._audio_controller.volume_down())
        except (OSError, RuntimeError) as error:
            self._set_status(f"Volume down failed: {error}")

    def request_mute(self, muted: bool) -> None:
        """Apply an explicit system mute state."""
        try:
            current = self._audio_controller.is_muted()
            resulting = (
                self._audio_controller.toggle_mute()
                if current != muted
                else current
            )
            self._volume_ui.set_muted(resulting)
        except (OSError, RuntimeError) as error:
            self._set_status(f"Mute request failed: {error}")

    def _publish_level(self, level: int) -> None:
        maximum = self._audio_controller.maximum_level
        if maximum <= 0:
            self._volume_ui.set_volume(None)
            return
        self._volume_ui.set_volume(
            max(0.0, min(100.0, level * 100.0 / maximum))
        )
