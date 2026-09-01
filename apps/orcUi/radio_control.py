# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose the existing ORC radio domain controller for orcUi."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from config.radio_config_manager import load_radio_config
from controllers.radio.adapters.rigctl_radio_backend import RigctlRadioBackend
from controllers.radio.radio_controller import RadioController
from controllers.radio.radio_types import RadioMode, RadioPreset, RadioRange
from protocols.rigctl.rigctl_client import RigctlClient


@dataclass(frozen=True)
class OrcUiRadioState:
    """Small presentation state consumed by the embedded radio panel."""

    label: str
    frequency_hz: int
    mode_name: str


class OrcUiRadioControl:
    """Drive SDR++ through the existing rigctl radio backend and preset model."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        if config_path is None:
            config_path = (
                Path(__file__).resolve().parents[2]
                / "config"
                / "radio"
                / "romeo"
                / "fm_radio.json"
            )
        config = load_radio_config(config_path)
        presets = [
            RadioPreset(
                label=item.label,
                frequency_hz=item.frequency_hz,
                mode=RadioMode(
                    name=item.mode.name,
                    bandwidth=item.mode.bandwidth,
                    step_hz=item.mode.step_hz,
                ),
            )
            for item in config.presets
        ]
        default_mode = RadioMode(
            name=config.default_mode.name,
            bandwidth=config.default_mode.bandwidth,
            step_hz=config.default_mode.step_hz,
        )
        radio_range = None
        if config.radio_range is not None:
            radio_range = RadioRange(
                min_frequency_hz=config.radio_range.min_frequency_hz,
                max_frequency_hz=config.radio_range.max_frequency_hz,
                start_frequency_hz=config.radio_range.start_frequency_hz,
            )
        self._radio = RadioController(
            backend=RigctlRadioBackend(RigctlClient()),
            presets=presets,
            default_mode=default_mode,
            radio_range=radio_range,
        )

    @property
    def state(self) -> OrcUiRadioState:
        frequency_hz = self._radio.current_frequency_hz
        preset = self._matching_preset(frequency_hz)
        return OrcUiRadioState(
            label=preset.label if preset is not None else self._format_frequency(frequency_hz),
            frequency_hz=frequency_hz,
            mode_name=self._radio.current_mode.name,
        )

    def next_preset(self) -> OrcUiRadioState:
        self._radio.next_preset()
        return self.state

    def previous_preset(self) -> OrcUiRadioState:
        self._radio.previous_preset()
        return self.state

    def tune_up(self) -> OrcUiRadioState:
        self._radio.frequency_up()
        return self.state

    def tune_down(self) -> OrcUiRadioState:
        self._radio.frequency_down()
        return self.state

    def _matching_preset(self, frequency_hz: int) -> RadioPreset | None:
        for preset in self._radio.presets:
            if preset.frequency_hz == frequency_hz:
                return preset
        return None

    @staticmethod
    def _format_frequency(frequency_hz: int) -> str:
        return f"{frequency_hz / 1_000_000:.1f} FM"
