# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

import sys
from unittest.mock import Mock, patch

import pytest

from apps.orcUi.composition.power_button import create_power_button
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp


def test_gpio_press_queues_existing_dialog_and_release_does_nothing():
    gpio_driver = Mock()
    app = OrcUiApp.__new__(OrcUiApp)
    app._closing = False
    app._power_dialog = Mock()
    pending = []
    with patch.dict(
        sys.modules,
        {
            "hardware_io.buttons.rpi_gpio_push_button": gpio_driver,
        },
    ):
        button = create_power_button("11", pending.append, app.show_power_dialog)

    assert button is gpio_driver.RpiGpioPushButton.return_value
    pin, callback = gpio_driver.RpiGpioPushButton.call_args.args
    assert pin.bcm == 17
    callback.pressed()
    callback.released()
    assert len(pending) == 1
    app._power_dialog.show.assert_not_called()
    pending[0]()
    app._power_dialog.show.assert_called_once_with()
    app._closing = True
    pending[0]()
    app._power_dialog.show.assert_called_once_with()


def test_power_button_is_opt_in_and_rejects_i2c_clock():
    assert create_power_button(None, Mock(), Mock()) is None
    with pytest.raises(ValueError, match="ORC_POWER_BUTTON_PIN"):
        create_power_button("5", Mock(), Mock())
