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
    # __new__ deliberately skips Tk initialization. Supply the minimal
    # constructor state required by the legacy and native presentation paths.
    panel._sdrforge_view = None
    panel._last_receiver_running = None
    panel._receiver_start_pending = False
    panel._receiver_controls = None
    panel._scan_dismissed = False
    panel._scan_requested = False
    panel._scan_signature = None
    panel._scan_selected = set()
    panel._state = RfRadioState(
        RadioProfileState("Station", 100_000_000, "WFM", "fm_radio", "FM"), ()
    )
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


def test_native_power_button_reflects_backend_starting_state():
    panel = presentation()
    panel._sdrforge_view = Mock()
    panel._last_receiver_running = False
    panel._receiver_start_pending = False
    panel._receiver_controls = Mock()
    panel._receiver_mode_label = Mock()
    panel._receiver_signal_label = Mock()
    panel._receiver_power_button = Mock()
    panel._play_button = Mock()
    panel._scan_button = Mock()
    panel._live_rf_buttons = []
    panel._active_group = "OTHER"
    panel._subcategory_strip = Mock()
    panel._station_info = Mock()
    panel._scan_card = Mock()
    panel._scan_status = Mock()
    panel._scan_signature = None
    panel._render_scan_results = Mock()
    panel._favorites = Mock()
    panel._pending_group = None
    panel._render_subcategory_tiles = Mock()
    panel._render_favorites = Mock()
    panel._theme.ui.accent_success = "green"
    panel._theme.ui.accent_primary = "blue"
    panel._theme.ui.surface = "black"
    panel._state = RfRadioState(
        RadioProfileState("Station", 100_000_000, "WFM", "fm_radio", "FM"), ()
    )
    state = RfRadioState(
        panel._state.station, (), receiver_starting=True
    )
    panel.set_radio_state(state)
    panel._receiver_power_button.set_text.assert_called_with("STARTING SDR…")
    panel._receiver_power_button.set_enabled.assert_called_with(False)
    panel._session.request.assert_not_called()
    panel._toggle_receiver_power()
    panel._session.request.assert_not_called()


    # Acquisition completed: power control switches to STOP.
    running = RfRadioState(panel._state.station, (), receiver_running=True)
    panel.set_radio_state(running)
    panel._receiver_power_button.set_text.assert_called_with("■ STOP SDR")
    panel._receiver_power_button.set_enabled.assert_called_with(True)
    panel._toggle_receiver_power()
    assert panel._session.request.call_args.args[0].action is RadioAction.STOP_RECEIVER

    # After shutdown, a new explicit start is permitted.
    stopped = RfRadioState(panel._state.station, (), receiver_running=False)
    panel.set_radio_state(stopped)
    panel._receiver_power_button.set_text.assert_called_with("▶ START SDR")
    panel._receiver_power_button.set_enabled.assert_called_with(True)
    panel._session.request.reset_mock()
    panel._toggle_receiver_power()
    assert panel._session.request.call_args.args[0].action is RadioAction.START_RECEIVER
    panel._receiver_power_button.set_enabled.assert_called_with(False)


def test_empty_scan_keeps_discovery_card_open_until_closed():
    panel = presentation()
    panel._sdrforge_view = Mock()
    panel._receiver_controls = Mock()
    panel._receiver_mode_label = Mock()
    panel._receiver_signal_label = Mock()
    panel._receiver_power_button = Mock()
    panel._play_button = Mock()
    panel._scan_button = Mock()
    panel._live_rf_buttons = []
    panel._active_group = "FM"
    panel._subcategory_strip = Mock()
    panel._station_info = Mock()
    panel._favorites = Mock()
    panel._pending_group = None
    panel._render_subcategory_tiles = Mock()
    panel._render_favorites = Mock()
    panel._theme.ui.accent_success = "green"
    panel._theme.ui.accent_primary = "blue"
    panel._theme.ui.surface = "black"
    panel._scan_requested = True
    panel._scan_dismissed = False
    panel._state = RfRadioState(
        RadioProfileState("Station", 100_000_000, "WFM", "fm_radio", "FM"), ()
    )
    panel.set_radio_state(panel._state)
    panel._scan_card.place.assert_called()
    panel._scan_status.configure.assert_called_with(text="No stations found")
    panel._close_scan_results()
    assert not panel._scan_requested
    panel._scan_card.place_forget.assert_called()
