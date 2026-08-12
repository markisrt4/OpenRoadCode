# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Deterministic in-memory audio controller."""

from __future__ import annotations

from .audio_controller_if import AudioControllerIf


class AudioControllerStub(AudioControllerIf):
    """Provide configurable audio state for demos and UI development."""

    def __init__(
        self,
        *,
        maximum_level: int = 20,
        initial_level: int = 10,
        muted: bool = False,
    ) -> None:
        if maximum_level <= 0:
            raise ValueError("maximum_level must be greater than zero")

        self._maximum_level = maximum_level
        self._level = self._clamp_level(initial_level)
        self._muted = muted

    @property
    def is_available(self) -> bool:
        return True

    @property
    def status_message(self) -> str | None:
        return None

    @property
    def maximum_level(self) -> int:
        return self._maximum_level

    def volume_up(self) -> int:
        return self.set_volume_level(self._level + 1)

    def volume_down(self) -> int:
        return self.set_volume_level(self._level - 1)

    def get_volume_level(self) -> int:
        return self._level

    def set_volume_level(self, level: int) -> int:
        self._level = self._clamp_level(level)
        return self._level

    def is_muted(self) -> bool:
        return self._muted

    def toggle_mute(self) -> bool:
        self._muted = not self._muted
        return self._muted

    def _clamp_level(self, level: int) -> int:
        return max(0, min(level, self._maximum_level))
