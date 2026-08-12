# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Connect system audio control to toolkit-independent volume UI contracts."""

from __future__ import annotations

from collections.abc import Callable

from ui.system import VolumeRequestHandlerIf, VolumeUiIf


class VolumeManager(VolumeRequestHandlerIf):
    """Handle volume requests and publish normalized system volume state."""

    def __init__(
        self,
        *,
        audio_controller,
        volume_ui: VolumeUiIf,
        set_status: Callable[[str], None],
    ) -> None:
        self._audio_controller = audio_controller
        self._volume_ui = volume_ui
        self._set_status = set_status

    def refresh(self) -> None:
        """Read and publish the current system volume and mute state."""
        try:
            self._publish_level(self._audio_controller.get_volume_level())
            self._volume_ui.set_muted(self._audio_controller.is_muted())
        except Exception as exc:
            self._volume_ui.set_volume(None)
            self._volume_ui.set_muted(None)
            self._set_status(f"Volume unavailable: {exc}")

    def request_volume(self, volume_percent: float) -> None:
        """Apply a requested normalized volume percentage.

        @param volume_percent Requested volume clamped to 0 through 100.
        """
        maximum = self._audio_controller.maximum_level
        level = round(max(0.0, min(100.0, volume_percent)) * maximum / 100.0)
        try:
            self._publish_level(self._audio_controller.set_volume_level(level))
            self._set_status("Volume changed")
        except Exception as exc:
            self._set_status(f"Volume change failed: {exc}")

    def request_volume_up(self) -> None:
        """Increase system volume by the controller-defined increment."""
        try:
            self._publish_level(self._audio_controller.volume_up())
            self._set_status("Volume up")
        except Exception as exc:
            self._set_status(f"Volume up failed: {exc}")

    def request_volume_down(self) -> None:
        """Decrease system volume by the controller-defined increment."""
        try:
            self._publish_level(self._audio_controller.volume_down())
            self._set_status("Volume down")
        except Exception as exc:
            self._set_status(f"Volume down failed: {exc}")

    def request_mute(self, muted: bool) -> None:
        """Apply a requested mute state.

        @param muted True to mute system audio.
        """
        try:
            current = self._audio_controller.is_muted()
            resulting = (
                self._audio_controller.toggle_mute()
                if current != muted
                else current
            )
            self._volume_ui.set_muted(resulting)
            self._set_status("Volume muted" if resulting else "Volume unmuted")
        except Exception as exc:
            self._set_status(f"Mute request failed: {exc}")

    def volume_up(self) -> None:
        """Increase system volume for legacy action bindings."""
        self.request_volume_up()

    def volume_down(self) -> None:
        """Decrease system volume for legacy action bindings."""
        self.request_volume_down()

    def toggle_mute(self) -> None:
        """Invert the current system mute state."""
        try:
            self.request_mute(not self._audio_controller.is_muted())
        except Exception as exc:
            self._set_status(f"Mute toggle failed: {exc}")

    def _publish_level(self, level: int) -> None:
        maximum = self._audio_controller.maximum_level
        if maximum <= 0:
            self._volume_ui.set_volume(None)
            return
        self._volume_ui.set_volume(
            max(0.0, min(100.0, level * 100.0 / maximum))
        )
