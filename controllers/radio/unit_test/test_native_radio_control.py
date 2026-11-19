# SPDX-License-Identifier: MIT
"""Native display controls must not require an SDR++ service."""
from controllers.radio.native_radio_control import NativeRadioControl


def test_native_controls_are_local_and_toggle_independently():
    control = NativeRadioControl()
    assert control.waterfall_visible()
    assert not control.bandplan_visible()
    assert not control.fft_hold_enabled()
    assert control.toggle_waterfall() is False
    assert control.toggle_bandplan() is True
    assert control.toggle_fft_hold() is True
    assert control.auto_range() is True
    assert not control.waterfall_visible()
    assert control.bandplan_visible()
    assert control.fft_hold_enabled()


def test_native_theme_selection():
    control = NativeRadioControl()
    assert control.themes() == ("Light", "Dark")
    assert control.set_theme("Light")
    assert control.theme() == "Light"
    assert not control.set_theme("Unknown")
    assert control.theme() == "Light"
