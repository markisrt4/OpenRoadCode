# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import importlib
import sys
from types import ModuleType
from unittest.mock import Mock, patch

from hardware_io.buttons.push_button_callback_if import PushButtonCallbackIf
from hardware_io.buttons.push_button_state import PushButtonState
from hardware_io.gpio import RpiGpioHeader


def test_physical_pin_11_reports_button_transitions_and_releases_gpio() -> None:
    gpiozero = ModuleType("gpiozero")
    gpio_button = Mock()
    setattr(gpiozero, "Button", gpio_button)
    with patch.dict(sys.modules, {"gpiozero": gpiozero}):
        driver = importlib.import_module("hardware_io.buttons.rpi_gpio_push_button")
    callback = Mock(spec=PushButtonCallbackIf)
    pin = RpiGpioHeader.by_physical_pin(11)

    with patch.object(driver, "Button", gpio_button):
        with driver.RpiGpioPushButton(pin, callback) as button:
            gpio_button.assert_called_once_with(pin=17, pull_up=True, bounce_time=0.05)
            gpio_button.return_value.is_pressed = False
            assert button.get_state() is PushButtonState.RELEASED
            gpio_button.return_value.when_pressed()
            gpio_button.return_value.is_pressed = True
            assert button.get_state() is PushButtonState.PRESSED
            gpio_button.return_value.when_released()

        callback.pressed.assert_called_once_with()
        callback.released.assert_called_once_with()
        gpio_button.return_value.close.assert_called_once_with()
