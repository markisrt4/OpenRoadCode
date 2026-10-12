# SPDX-License-Identifier: MIT
"""Receiver requests, UI dispatch, retirement, and native cleanup contracts."""
from threading import Event, Thread
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from controllers.radio.rf_radio_session import ReceiverSession
from controllers.radio.radio_profile_controller import RadioProfileController
from controllers.sdr.sdrpp_control import SDRPPControl
from ui.radio.radio_profile_state import RadioProfileState
from ui.radio.rf_radio_if import AircraftPresentation, RadioAction, RadioHost, RadioRequest, RadioTelemetry


@pytest.fixture
def receiver():
    radio = Mock(spec=RadioProfileController)
    radio.state = RadioProfileState("FM", 100_000_000, "WFM", "fm_radio", "FM")
    radio.active_profile_key = "fm_radio"
    radio.catalog.profiles = (SimpleNamespace(key="fm_radio", label="FM", group="FM", presets=()),)
    control, telemetry, application, aircraft, surface = Mock(spec=SDRPPControl), Mock(), Mock(), Mock(spec=AircraftPresentation), Mock()
    control.themes.return_value = ("Light", "Dark")
    control.waterfall_visible.return_value = True
    control.bandplan_visible.return_value = False
    control.fft_hold_enabled.return_value = False
    application.fullscreen = False
    application.window_process_id.return_value = 123
    telemetry.read_state.return_value = RadioTelemetry(signal_db=-43.5, snr_db=20, rds="STATION")
    work, ui = [], []
    closed = Mock()
    session = ReceiverSession(radio, control, telemetry, application, aircraft, surface,
                              display=":1", run_work=work.append, run_ui=ui.append, on_close=closed)
    view = Mock()
    session.bind(view)
    return SimpleNamespace(**locals())


def launch(r):
    r.session.request(RadioRequest(RadioAction.LAUNCH, host=RadioHost(10, 20, 800, 400)))
    r.work.pop(0)()


def test_launch_and_measurements_are_dispatched_as_immutable_values(receiver):
    r = receiver
    launch(r)
    r.application.present.assert_called_once()
    assert r.surface.embed.call_args.args == (123, 10, 800, 400)
    # Worker completion does not call the GUI directly.
    assert r.view.set_radio_state.call_count == 1
    for deliver in r.ui:
        deliver()
    assert r.view.set_radio_state.call_args.args[0].view == "sdrpp"
    r.session.request(RadioRequest(RadioAction.REFRESH))
    r.session.request(RadioRequest(RadioAction.REFRESH))
    assert len(r.work) == 1
    r.work.pop()()
    r.ui[-1]()
    state = r.view.set_radio_state.call_args.args[0]
    assert state.telemetry.signal_db == -43.5
    assert state.telemetry.rds == "STATION"
    assert state.themes == ("Light", "Dark")
    assert not hasattr(state.profiles[0], "config_path")


@pytest.mark.parametrize("action,method", [
    (RadioAction.PREVIOUS, "previous_preset"), (RadioAction.NEXT, "next_preset"),
    (RadioAction.TUNE_UP, "tune_up"), (RadioAction.TUNE_DOWN, "tune_down"),
])
def test_tuning_requests_execute_off_frontend(receiver, action, method):
    r = receiver
    r.session.request(RadioRequest(action))
    getattr(r.radio, method).assert_not_called()
    r.work.pop()()
    getattr(r.radio, method).assert_called_once()


def test_queued_launch_and_delivery_are_dropped_after_close(receiver):
    r = receiver
    r.session.request(RadioRequest(RadioAction.LAUNCH, host=RadioHost(10, 20, 800, 400)))
    r.session.close()
    r.session.close()
    r.work.pop()()
    for deliver in r.ui:
        deliver()
    r.application.present.assert_not_called()
    r.surface.embed.assert_not_called()
    assert r.view.set_radio_state.call_count == 1
    r.closed.assert_called_once()
    r.session.request(RadioRequest(RadioAction.NEXT))
    assert not r.work
    with pytest.raises(RuntimeError, match="closed"):
        r.session.bind(Mock())


def test_late_application_launch_cannot_embed_in_destroyed_host(receiver):
    r = receiver
    entered, release = Event(), Event()
    def present():
        entered.set()
        assert release.wait(2)
    r.application.present.side_effect = present
    r.session.request(RadioRequest(RadioAction.LAUNCH, host=RadioHost(10, 20, 800, 400)))
    thread = Thread(target=r.work.pop())
    thread.start()
    assert entered.wait(2)
    r.session.close()
    release.set()
    thread.join(2)
    assert not thread.is_alive()
    r.surface.embed.assert_not_called()
    for deliver in r.ui:
        deliver()
    assert r.view.set_radio_state.call_count == 1


def test_embedding_is_cancelled_and_detached_before_close_returns(receiver):
    r = receiver
    entered, retired = Event(), Event()
    def embed(*args, cancelled, **kwargs):
        entered.set()
        from time import monotonic
        deadline = monotonic() + 2
        while not cancelled() and monotonic() < deadline:
            retired.wait(0.001)
        assert cancelled()
        raise RuntimeError("cancelled")
    r.surface.embed.side_effect = embed
    r.session.request(RadioRequest(RadioAction.LAUNCH, host=RadioHost(10, 20, 800, 400)))
    worker = Thread(target=r.work.pop())
    worker.start()
    assert entered.wait(2)
    closer = Thread(target=r.session.close)
    closer.start()
    worker.join(2)
    closer.join(2)
    assert not worker.is_alive() and not closer.is_alive()
    r.surface.detach.assert_called_with(20)
    r.surface.clear.assert_called()
    for deliver in r.ui:
        deliver()
    assert r.view.set_radio_state.call_count == 1


def test_adsb_explicitly_releases_rf_and_stop_is_owned_by_session(receiver):
    r = receiver
    r.application.presented = False
    r.session.request(RadioRequest(RadioAction.ADSB, host=RadioHost(10, 20, 800, 400, 5, 6), color_scheme="light"))
    r.work.pop()()
    r.application.relinquish_for_adsb.assert_called_once()
    r.aircraft.configure_browser_window.assert_called_once_with(position=(5, 6), size=(800, 400))
    r.aircraft.set_preferred_color_scheme.assert_called_once_with("light")
    r.session.deactivate()
    r.aircraft.stop.assert_called_once_with(":1")
    r.session.close()
    r.aircraft.stop.assert_called_once()


def test_cleanup_failure_still_releases_ownership(receiver):
    r = receiver
    r.surface.detach.side_effect = RuntimeError("detach failed")
    r.session._host = RadioHost(10, 20, 800, 400)
    with pytest.raises(RuntimeError, match="detach failed"):
        r.session.close()
    r.surface.clear.assert_called_once()
    r.closed.assert_called_once()


def test_telemetry_monitor_keeps_numeric_measurements_and_legacy_formatting():
    from controllers.sdr.sdr_telemetry_monitor import SDRTelemetryMonitor
    from protocols.sdrpp_telemetry import SDRPPTelemetry
    radio, client = Mock(), Mock()
    client.read.return_value = SDRPPTelemetry(center_frequency_hz=100_000_000,
                                             signal_peak_db=-43.25, snr_db=18.5)
    radio.read_rds.return_value = " STATION "
    monitor = SDRTelemetryMonitor(radio, client)
    state = monitor.read_state(include_rds=True)
    assert state == RadioTelemetry(100_000_000, -43.25, 18.5, "STATION")
    assert monitor.read().signal == "-43.2 dB"
    assert monitor.read_state().rds == ""
