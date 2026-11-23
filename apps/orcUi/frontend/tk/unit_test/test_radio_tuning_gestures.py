# SPDX-License-Identifier: MIT
"""Channel-grid regression tests for receiver tuning gestures."""

from apps.orcUi.frontend.tk.radio_tuning_gestures_mixin import next_channel


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
