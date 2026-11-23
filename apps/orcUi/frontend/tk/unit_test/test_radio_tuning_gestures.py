# SPDX-License-Identifier: MIT
"""Channel-grid regression tests for receiver tuning gestures."""

from types import SimpleNamespace
from unittest.mock import Mock

from apps.orcUi.frontend.tk.radio_tuning_gestures_mixin import (
    RadioTuningGesturesMixin,
    next_channel,
)
from ui.radio.rf_radio_if import RadioAction, RadioRequest


def test_us_fm_channel_up_from_center():
    assert next_channel(94_700_000, 1, low=88_100_000,
                        high=107_900_000, step=200_000) == 94_900_000


def test_us_fm_channel_down_from_center():
    assert next_channel(94_700_000, -1, low=88_100_000,
                        high=107_900_000, step=200_000) == 94_500_000


def test_us_fm_channel_snap_from_manual_half_step():
    assert next_channel(94_800_000, 1, low=88_100_000,
                        high=107_900_000, step=200_000) == 94_900_000
    assert next_channel(94_800_000, -1, low=88_100_000,
                        high=107_900_000, step=200_000) == 94_700_000


def test_us_fm_channel_clamps_to_band():
    assert next_channel(107_900_000, 1, low=88_100_000,
                        high=107_900_000, step=200_000) == 107_900_000


def test_fm_buttons_and_wheel_share_channel_grid_without_range():
    panel = RadioTuningGesturesMixin()
    panel._state = SimpleNamespace(
        receiver_running=True,
        view="none",
        station=SimpleNamespace(frequency_hz=94_700_000, mode_name="WFM"),
        tuning_range=None,
    )
    panel._session = Mock()
    panel._manual_tune(1)
    panel._gesture_tune(1)
    expected = RadioRequest(RadioAction.TUNE_FREQUENCY, frequency_hz=94_900_000)
    assert panel._session.request.call_count == 2
    assert all(
        call.args == (expected,) for call in panel._session.request.call_args_list
    )
