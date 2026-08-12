# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unavailable implementation for systems without audio control."""

from __future__ import annotations

from typing import NoReturn

from .audio_controller_if import AudioControllerIf


class UnconfiguredAudioController(AudioControllerIf):
    """Report that audio control has not been configured."""

    def __init__(
        self,
        reason: str = "Audio control is not configured",
        *,
        maximum_level: int = 20,
    ) -> None:
        if maximum_level <= 0:
            raise ValueError("maximum_level must be greater than zero")

        self._reason = reason
        self._maximum_level = maximum_level

    @property
    def is_available(self) -> bool:
        return False

    @property
    def status_message(self) -> str | None:
        return self._reason

    @property
    def maximum_level(self) -> int:
        return self._maximum_level

    def volume_up(self) -> int:
        self._raise_unavailable()

    def volume_down(self) -> int:
        self._raise_unavailable()

    def get_volume_level(self) -> int:
        self._raise_unavailable()

    def set_volume_level(self, level: int) -> int:
        self._raise_unavailable()

    def is_muted(self) -> bool:
        self._raise_unavailable()

    def toggle_mute(self) -> bool:
        self._raise_unavailable()

    def _raise_unavailable(self) -> NoReturn:
        raise RuntimeError(self._reason)
