# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

import sys
from unittest.mock import Mock, patch

import pytest

from apps.orcUi.composition.rotary_input import RotaryInput, create_rotary_input
from ui.ui_action import UiAction


def test_rotary_events_reuse_semantic_actions_and_drop_delivery_after_close():
    first, second, volume, screen = Mock(), Mock(), Mock(), Mock()
    pending = []
    runtime = RotaryInput((first, second), pending.append, screen, volume)
    runtime.start()
    volume_callbacks = first.start.call_args.kwargs
    screen_callbacks = second.start.call_args.kwargs

    volume_callbacks["rotated"](2)
    volume_callbacks["rotated"](-1)
    volume_callbacks["button_pressed"]()
    screen_callbacks["rotated"](-2)
    screen_callbacks["rotated"](1)
    screen_callbacks["button_released"]()

    assert len(pending) == 4
    volume.request_volume_up.assert_not_called()
    screen.assert_not_called()
    for callback in pending:
        callback()
    assert volume.request_volume_up.call_count == 2
    volume.request_volume_down.assert_called_once_with()
    assert [call.args[0] for call in screen.call_args_list] == [
        UiAction.NAVIGATE_UP, UiAction.NAVIGATE_UP, UiAction.NAVIGATE_DOWN,
    ]

    screen_callbacks["rotated"](1)
    runtime.close()
    pending[-1]()
    assert screen.call_count == 3
    first.stop.assert_called_once_with()
    second.stop.assert_called_once_with()


def test_configured_encoders_share_i2c_and_keep_address_order():
    board, driver = Mock(), Mock()
    with patch.dict(sys.modules, {
        "board": board,
        "hardware_io.rotary_encoder.seesaw_rotary_encoder": driver,
    }):
        assert create_rotary_input("0x36,0x37", Mock(), Mock(), None) is not None

    board.I2C.assert_called_once_with()
    assert [call.kwargs for call in driver.SeesawRotaryEncoder.call_args_list] == [
        {"address": 0x36, "i2c": board.I2C.return_value},
        {"address": 0x37, "i2c": board.I2C.return_value},
    ]


def test_rotary_input_is_opt_in_and_rejects_duplicate_addresses():
    assert create_rotary_input(None, Mock(), Mock(), None) is None
    with pytest.raises(ValueError, match="two distinct I²C addresses"):
        create_rotary_input("0x36,0x36", Mock(), Mock(), None)
