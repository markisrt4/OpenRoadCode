# SPDX-License-Identifier: MIT
"""Headless checks of semantic requests and frontend-only measurement formatting."""
from types import SimpleNamespace
from unittest.mock import Mock

from apps.orcUi.frontend.tk.radio_panel import RadioPanel
from ui.radio.radio_profile_state import RadioProfileState
from ui.radio.rf_radio_if import RadioAction, RadioTelemetry, RfRadioState


def presentation():
    panel = RadioPanel.__new__(RadioPanel)
    panel._session = Mock()
    panel._theme = SimpleNamespace(ui=SimpleNamespace(text="white", text_muted="gray", accent_danger="red"))
    for name in ("_station_label", "_frequency_label", "_metadata_label", "_signal_label",
                 "_snr_label", "_launch_status", "_controls", "_telemetry_overlay", "_controls_button",
                 "_paint_groups", "_refresh_display_controls"):
        setattr(panel, name, Mock())
    return panel


def test_receiver_measurements_are_formatted_in_frontend():
    panel = presentation()
    state = RfRadioState(RadioProfileState("Station", 100_000_000, "WFM", "fm_radio", "FM"), (),
                         telemetry=RadioTelemetry(signal_db=-42.25, snr_db=17.75, rds="RDS"), view="sdrpp")
    panel.set_radio_state(state)
    panel._frequency_label.configure.assert_called_with(text="100.000 MHz   WFM", fg="gray")
    panel._signal_label.configure.assert_called_with(text="SIGNAL -42.2 dB")
    panel._snr_label.configure.assert_called_with(text="SNR 17.8 dB")
    panel._metadata_label.configure.assert_called_with(text="RDS")
    panel._session.request.assert_not_called()


def test_tune_button_emits_a_semantic_request():
    panel = presentation()
    panel._tune_up()
    request = panel._session.request.call_args.args[0]
    assert request.action is RadioAction.TUNE_UP
    assert request.host is None
