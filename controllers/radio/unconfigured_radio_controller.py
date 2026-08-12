# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unavailable implementation for systems without radio control."""

from __future__ import annotations

from collections.abc import Sequence
from typing import NoReturn

from .radio_controller_if import RadioControllerIf
from .radio_types import RadioMode, RadioPreset


class UnconfiguredRadioController(RadioControllerIf):
    """Report that radio control has not been configured."""

    def __init__(
        self,
        reason: str = "Radio control is not configured",
        *,
        presets: Sequence[RadioPreset] = (),
    ) -> None:
        self._reason = reason
        self._presets = tuple(presets)

    @property
    def is_started(self) -> bool:
        return False

    @property
    def is_available(self) -> bool:
        return False

    @property
    def status_message(self) -> str | None:
        return self._reason

    @property
    def presets(self) -> tuple[RadioPreset, ...]:
        return self._presets

    def start(self) -> int:
        self._raise_unavailable()

    def stop(self) -> None:
        pass

    def get_frequency(self) -> int:
        self._raise_unavailable()

    def refresh_frequency(self) -> int:
        self._raise_unavailable()

    def set_mode(self, mode: RadioMode) -> RadioMode:
        self._raise_unavailable()

    def tune_preset(self, preset: RadioPreset) -> RadioPreset:
        self._raise_unavailable()

    def tune_preset_index(self, index: int) -> RadioPreset:
        self._raise_unavailable()

    def next_preset(self) -> RadioPreset:
        self._raise_unavailable()

    def previous_preset(self) -> RadioPreset:
        self._raise_unavailable()

    def next_station(self) -> RadioPreset:
        self._raise_unavailable()

    def previous_station(self) -> RadioPreset:
        self._raise_unavailable()

    def frequency_up(self, delta_hz: int | None = None) -> int:
        self._raise_unavailable()

    def frequency_down(self, delta_hz: int | None = None) -> int:
        self._raise_unavailable()

    def set_frequency(self, frequency_hz: int) -> int:
        self._raise_unavailable()

    def get_signal_strength(self) -> float | str | None:
        self._raise_unavailable()

    def get_snr(self) -> float | str | None:
        self._raise_unavailable()

    def get_rds(self) -> str | None:
        self._raise_unavailable()

    def _raise_unavailable(self) -> NoReturn:
        raise RuntimeError(self._reason)
