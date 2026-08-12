# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Build Car TUI radio controllers from shared runtime configuration."""

from dataclasses import dataclass

from config.runtime_config import RuntimeConfig
from config.radio_config_manager import load_radio_config
from controllers.radio import (
    RadioController,
    RadioControllerIf,
    RadioControllerStub,
    RadioMode,
    RadioPreset,
    RadioRange,
    UnconfiguredRadioController,
)
from controllers.radio.adapters.rigctl_radio_backend import RigctlRadioBackend
from protocols.rigctl import RigctlClient


@dataclass(frozen=True, slots=True)
class CarTuiRadio:
    """Name one selectable receiver and its controller."""

    key: str
    label: str
    controller: RadioControllerIf


_RADIO_CATEGORIES = (
    ("fm", "FM Broadcast", "fm_radio"),
    ("scanner", "Scanner", "police_fire"),
    ("airband", "AM Airband", "airband"),
    ("weather", "FM Weather Band", "weather_band"),
)


def build_car_tui_radios(
    config: RuntimeConfig,
    *,
    simulate: bool,
) -> tuple[CarTuiRadio, ...]:
    """Build the four Car TUI categories from shared radio profiles."""
    radios = []
    for key, label, stack_key in _RADIO_CATEGORIES:
        try:
            stack = config.radio(stack_key)
        except KeyError:
            radios.append(CarTuiRadio(
                key,
                label,
                UnconfiguredRadioController(
                    f"Radio stack '{stack_key}' is not configured"
                ),
            ))
            continue

        radio_config = load_radio_config(stack.config_path)
        default_mode = _mode(radio_config.default_mode)
        presets = tuple(
            RadioPreset(item.label, item.frequency_hz, _mode(item.mode))
            for item in radio_config.presets
        )
        radio_range = _range(radio_config)
        if not stack.enabled:
            controller: RadioControllerIf = UnconfiguredRadioController(
                f"Radio stack '{stack_key}' is disabled",
                presets=presets,
            )
        elif simulate:
            controller = RadioControllerStub(
                presets=presets,
                default_mode=default_mode,
                radio_range=radio_range,
                rds="OpenRoadCode" if key == "fm" else None,
            )
        else:
            controller = RadioController(
                backend=RigctlRadioBackend(RigctlClient(
                    host=config.rigctl.host,
                    port=config.rigctl.port,
                )),
                presets=list(presets),
                default_mode=default_mode,
                radio_range=radio_range,
            )
        radios.append(CarTuiRadio(key, label, controller))
    return tuple(radios)


def _mode(value) -> RadioMode:
    return RadioMode(value.name, value.bandwidth, value.step_hz)


def _range(radio_config) -> RadioRange | None:
    value = radio_config.radio_range
    if value is not None:
        return RadioRange(
            value.min_frequency_hz,
            value.max_frequency_hz,
            value.start_frequency_hz,
        )
    if not radio_config.presets:
        return None
    frequencies = tuple(item.frequency_hz for item in radio_config.presets)
    return RadioRange(min(frequencies), max(frequencies), frequencies[0])
