# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Bind an optional GPIO switch to the ORC shell's power dialog."""

from collections.abc import Callable

from hardware_io.buttons.push_button_callback_if import PushButtonCallbackIf
from hardware_io.buttons.push_button_if import PushButtonIf
from hardware_io.gpio import RpiGpioHeader


class PowerButtonCallback(PushButtonCallbackIf):
    def __init__(
        self, dispatch_ui: Callable[[Callable[[], None]], None], show: Callable[[], None]
    ) -> None:
        self._dispatch_ui = dispatch_ui
        self._show = show

    def pressed(self) -> None:
        self._dispatch_ui(self._show)

    def released(self) -> None:
        pass


def create_power_button(
    physical_pin: str | None,
    dispatch_ui: Callable[[Callable[[], None]], None],
    show: Callable[[], None],
) -> PushButtonIf | None:
    if not physical_pin:
        return None

    try:
        pin = RpiGpioHeader.by_physical_pin(int(physical_pin))
        if pin.bcm is None or pin.bcm in {0, 1, 2, 3}:
            raise ValueError("choose a GPIO pin outside I²C and HAT identification")
    except ValueError as exc:
        raise ValueError(f"Invalid ORC_POWER_BUTTON_PIN: {exc}") from exc

    from hardware_io.buttons.rpi_gpio_push_button import RpiGpioPushButton

    return RpiGpioPushButton(pin, PowerButtonCallback(dispatch_ui, show))
