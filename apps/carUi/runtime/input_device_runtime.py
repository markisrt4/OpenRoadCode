# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Construct optional keyboard and standalone pushbutton devices."""

from dataclasses import dataclass
from pathlib import Path

from config.runtime_config import InputConfig
from hardware_io.buttons.push_button_if import PushButtonIf
from hardware_io.keyboard import KeyboardReaderIf


@dataclass(frozen=True, slots=True)
class InputDeviceRuntime:
    keyboards: tuple[KeyboardReaderIf, ...] = ()
    push_buttons: tuple[PushButtonIf, ...] = ()
    push_button_actions: tuple[str, ...] = ()


def create_input_device_runtime(config: InputConfig) -> InputDeviceRuntime:
    keyboards: tuple[KeyboardReaderIf, ...] = ()
    if config.keyboard.enabled:
        from hardware_io.keyboard.keyboard_reader import KeyboardReader
        keyboards = (KeyboardReader(device_path=config.keyboard.device_path),)

    buttons: list[PushButtonIf] = []
    actions: list[str] = []
    if "Raspberry Pi" in _model_name():
        from hardware_io.buttons.rpi_gpio_push_button import RpiGpioPushButton
        from hardware_io.gpio.rpi_gpio_header import RpiGpioHeader
        for item in config.push_buttons:
            buttons.append(RpiGpioPushButton(
                RpiGpioHeader.by_physical_pin(item.pin),
                active_low=item.active_low,
                debounce_seconds=item.debounce_seconds,
            ))
            actions.append(item.action)
    return InputDeviceRuntime(keyboards, tuple(buttons), tuple(actions))


def _model_name() -> str:
    try:
        return Path("/proc/device-tree/model").read_text(errors="ignore")
    except OSError:
        return ""
