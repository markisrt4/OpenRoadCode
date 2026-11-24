# SPDX-License-Identifier: MIT
"""Receiver requests, UI dispatch, retirement, and native cleanup contracts."""
from dataclasses import replace
from threading import Event, Thread
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from controllers.radio.rf_radio_session import ReceiverSession
from controllers.radio.radio_profile_controller import RadioProfileController
from controllers.radio.native_radio_control import NativeRadioControl
from ui.radio.radio_profile_state import RadioProfileState
from ui.radio.rf_radio_if import AircraftPresentation, RadioAction, RadioHost, RadioRequest, RadioTelemetry


@pytest.fixture
def receiver():
    radio = Mock(spec=RadioProfileController)
    radio.state = RadioProfileState("FM", 100_000_000, "WFM", "fm_radio", "FM")
    radio.active_profile_key = "fm_radio"
    radio.catalog.profiles = (SimpleNamespace(key="fm_radio", label="FM", group="FM", presets=()),)
    control, application, aircraft, surface = Mock(spec=NativeRadioControl), Mock(), Mock(spec=AircraftPresentation), Mock()
    control.themes.return_value = ("Light", "Dark")
    control.waterfall_visible.return_value = True
    control.bandplan_visible.return_value = False
    control.fft_hold_enabled.return_value = False
    application.fullscreen = False
    application.window_process_id.return_value = 123
    work, ui = [], []
    closed = Mock()
    session = ReceiverSession(radio, control, application, aircraft, surface,
                              display=":1", run_work=work.append, run_ui=ui.append, on_close=closed)
    view = Mock()
    session.bind(view)
    return SimpleNamespace(**locals())


def launch(r):
    r.session.request(RadioRequest(RadioAction.LAUNCH, host=RadioHost(10, 20, 800, 400)))
    r.work.pop(0)()


def test_native_launch_dispatches_immutable_state(receiver):
    r = receiver
    launch(r)
    r.application.present.assert_not_called()
    r.surface.embed.assert_not_called()
    assert r.view.set_radio_state.call_count == 1
    for deliver in r.ui:
        deliver()
    state = r.view.set_radio_state.call_args.args[0]
    assert state.view == "none"
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
    r.session.request(RadioRequest(RadioAction.ADSB, host=RadioHost(10, 20, 800, 400)))
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


def test_sdrforge_stop_clears_stale_rds_without_changing_profile(receiver):
    r = receiver
    source = Mock()
    r.session._spectrum_source = source
    r.session._state = replace(
        r.session._state,
        telemetry=RadioTelemetry(
            frequency_hz=100_000_000, station_name="OLD FM",
            radio_text="Old song", rds="OLD", receiver_running=True),
        receiver_running=True,
    )
    source.latest_receiver.return_value = RadioTelemetry(
        frequency_hz=100_000_000, receiver_running=False)
    source.latest_spectrum.return_value = None

    r.session.refresh_spectrum()

    state = r.view.set_radio_state.call_args.args[0]
    assert state.station.mode_name == "WFM"
    assert state.telemetry.station_name == ""
    assert state.telemetry.radio_text == ""
    assert state.telemetry.rds == ""
    assert state.receiver_running is False


def test_sdrforge_old_frequency_cannot_replace_new_station_identity(receiver):
    r = receiver
    source = Mock()
    r.session._spectrum_source = source
    r.session._state = replace(
        r.session._state,
        telemetry=RadioTelemetry(
            frequency_hz=100_000_000, station_name="CURRENT",
            radio_text="Current song", rds="CURRENT"),
    )
    source.latest_receiver.return_value = RadioTelemetry(
        frequency_hz=99_500_000, station_name="STALE",
        radio_text="Old song", rds="STALE", mode="NFM",
        bandwidth_hz=12_500, receiver_running=True)
    source.latest_spectrum.return_value = None

    r.session.refresh_spectrum()

    state = r.view.set_radio_state.call_args.args[0]
    assert state.station.frequency_hz == 100_000_000
    assert state.station.mode_name == "WFM"
    assert state.telemetry.station_name == ""
    assert state.telemetry.radio_text == ""
    assert state.telemetry.rds == ""
    assert state.telemetry.mode is None
    assert state.telemetry.bandwidth_hz is None
    assert state.telemetry.receiver_running is None


def test_sdrforge_same_frequency_preserves_rds_between_updates(receiver):
    r = receiver
    source = Mock()
    r.session._spectrum_source = source
    r.session._state = replace(
        r.session._state,
        telemetry=RadioTelemetry(
            frequency_hz=100_000_000, station_name="LIVE",
            radio_text="Current song", rds="LIVE", receiver_running=True),
    )
    source.latest_receiver.return_value = RadioTelemetry(
        frequency_hz=100_000_000, mode="WFM", receiver_running=True)
    source.latest_spectrum.return_value = None

    r.session.refresh_spectrum()

    state = r.view.set_radio_state.call_args.args[0]
    assert state.telemetry.station_name == "LIVE"
    assert state.telemetry.radio_text == "Current song"
    assert state.telemetry.rds == "LIVE"
    assert state.telemetry.mode == "WFM"


def test_rest_running_status_wins_over_delayed_zmq_stop(receiver):
    r = receiver
    source = Mock()
    r.session._spectrum_source = source
    r.session._rest_receiver_running = True
    source.latest_receiver.return_value = RadioTelemetry(
        frequency_hz=100_000_000, mode="WFM", receiver_running=False)
    source.latest_spectrum.return_value = None

    r.session.refresh_spectrum()

    state = r.view.set_radio_state.call_args.args[0]
    assert state.receiver_running is True
    assert state.telemetry.receiver_running is False


def test_rest_stopped_status_wins_over_delayed_zmq_start(receiver):
    r = receiver
    source = Mock()
    r.session._spectrum_source = source
    r.session._rest_receiver_running = False
    source.latest_receiver.return_value = RadioTelemetry(
        frequency_hz=100_000_000, mode="WFM", receiver_running=True)
    source.latest_spectrum.return_value = None

    r.session.refresh_spectrum()

    state = r.view.set_radio_state.call_args.args[0]
    assert state.receiver_running is False
    assert state.telemetry.receiver_running is True


def test_local_retune_immediately_invalidates_old_receiver_telemetry(receiver):
    r = receiver
    r.session._state = replace(
        r.session._state,
        telemetry=RadioTelemetry(
            frequency_hz=100_000_000, mode="NFM",
            station_name="OLD", radio_text="Old track", receiver_running=True),
    )
    new_station = replace(r.session._state.station, frequency_hz=101_100_000)
    r.session._set_station(new_station)

    state = r.session._state
    assert state.station.frequency_hz == 101_100_000
    assert state.telemetry == RadioTelemetry()


def test_same_frequency_station_refresh_preserves_live_telemetry(receiver):
    r = receiver
    live = RadioTelemetry(
        frequency_hz=100_000_000, mode="WFM",
        station_name="LIVE", receiver_running=True)
    r.session._state = replace(r.session._state, telemetry=live)
    r.session._set_station(r.session._state.station)
    assert r.session._state.telemetry == live


def test_external_rigctl_retune_invalidates_previous_mode(receiver):
    r = receiver
    r.session._state = replace(
        r.session._state,
        telemetry=RadioTelemetry(
            frequency_hz=100_000_000, mode="NFM", receiver_running=True),
    )
    r.radio.refresh.return_value = replace(
        r.session._state.station, frequency_hz=102_500_000)
    r.session._native_view = "none"
    r.session._perform(RadioRequest(RadioAction.REFRESH), r.session._generation)

    assert r.session._state.station.frequency_hz == 102_500_000
    assert r.session._state.telemetry == RadioTelemetry()


def test_receiver_stop_clears_old_station_and_ignores_late_zmq(receiver, monkeypatch):
    r = receiver
    from unittest.mock import MagicMock

    response = MagicMock()
    response.__enter__.return_value.status = 200
    monkeypatch.setattr(
        "controllers.radio.rf_radio_session.urllib.request.urlopen",
        lambda *args, **kwargs: response,
    )
    source = Mock()
    r.session._spectrum_source = source
    r.session._state = replace(
        r.session._state,
        receiver_running=True,
        telemetry=RadioTelemetry(
            frequency_hz=100_000_000, mode="WFM", receiver_running=True,
            station_name="OLD", radio_text="Old song", rds="OLD"),
    )

    r.session._perform(RadioRequest(RadioAction.STOP_RECEIVER), r.session._generation)
    assert r.session._state.receiver_running is False
    assert r.session._state.telemetry == RadioTelemetry()

    source.latest_receiver.return_value = RadioTelemetry(
        frequency_hz=100_000_000, mode="WFM", receiver_running=True,
        station_name="OLD", radio_text="Old song", rds="OLD")
    source.latest_spectrum.return_value = None
    r.session.refresh_spectrum()
    state = r.view.set_radio_state.call_args.args[0]
    assert state.receiver_running is False
    assert state.telemetry.station_name == ""
    assert state.telemetry.radio_text == ""
    assert state.telemetry.rds == ""
    assert state.telemetry.mode is None
    # Preserve the raw delayed ZMQ report for diagnostics; REST owns UI state.
    assert state.telemetry.receiver_running is True


def test_accepted_restart_does_not_claim_acquisition_is_running(receiver, monkeypatch):
    r = receiver
    from unittest.mock import MagicMock

    response = MagicMock()
    response.__enter__.return_value.status = 202
    monkeypatch.setattr(
        "controllers.radio.rf_radio_session.urllib.request.urlopen",
        lambda *args, **kwargs: response,
    )
    r.session._rest_receiver_running = False
    r.session._state = replace(
        r.session._state,
        receiver_running=False,
        telemetry=RadioTelemetry(
            frequency_hz=100_000_000, station_name="OLD", rds="OLD"),
    )

    r.session._perform(RadioRequest(RadioAction.START_RECEIVER), r.session._generation)
    assert r.session._rest_receiver_running is None
    assert r.session._state.receiver_running is False
    assert r.session._state.telemetry == RadioTelemetry()


def test_stopped_rest_does_not_resurrect_cached_rds(receiver):
    r = receiver
    source = Mock()
    r.session._spectrum_source = source
    r.session._rest_receiver_running = False
    r.session._state = replace(
        r.session._state,
        telemetry=RadioTelemetry(
            frequency_hz=100_000_000, receiver_running=True,
            station_name="OLD", radio_text="OLD TEXT", rds="OLD"),
    )
    source.latest_receiver.return_value = RadioTelemetry(
        frequency_hz=100_000_000, receiver_running=True)
    source.latest_spectrum.return_value = None

    r.session.refresh_spectrum()

    state = r.view.set_radio_state.call_args.args[0]
    assert state.receiver_running is False
    assert state.telemetry.rds == ""
    assert state.telemetry.radio_text == ""
    assert state.telemetry.station_name == ""
    assert state.telemetry.receiver_running is True


def test_profile_mode_change_on_same_frequency_invalidates_telemetry(receiver):
    r = receiver
    r.session._state = replace(
        r.session._state,
        telemetry=RadioTelemetry(
            frequency_hz=100_000_000, mode="WFM", receiver_running=True,
            station_name="OLD", rds="OLD"),
    )
    station = replace(r.session._state.station, mode_name="NFM", profile_key="weather")
    r.session._set_station(station)
    assert r.session._state.station.mode_name == "NFM"
    assert r.session._state.telemetry == RadioTelemetry()


def test_profile_change_with_same_mode_and_frequency_invalidates_telemetry(receiver):
    r = receiver
    r.session._state = replace(
        r.session._state,
        telemetry=RadioTelemetry(
            frequency_hz=100_000_000, mode="WFM", receiver_running=True),
    )
    station = replace(r.session._state.station, profile_key="alternate")
    r.session._set_station(station)
    assert r.session._state.telemetry == RadioTelemetry()


def test_usb_disconnect_rest_outage_and_reconnect_lifecycle(receiver, monkeypatch):
    """Exercise acquisition recovery without hardware, sockets, or Tk."""
    import json
    from io import BytesIO

    r = receiver
    source = Mock()
    r.session._spectrum_source = source
    r.session._native_view = "none"
    status = {"running": True}
    outage = {"active": False}

    def urlopen(request, timeout=1.5):
        if outage["active"]:
            raise OSError("SDRForge temporarily unreachable")
        url = request if isinstance(request, str) else request.full_url
        data = ({"muted": False} if url.endswith("/v1/audio") else status)
        return BytesIO(json.dumps(data).encode())

    monkeypatch.setattr(
        "controllers.radio.rf_radio_session.urllib.request.urlopen", urlopen)
    r.radio.refresh.return_value = r.session._state.station
    source.latest_spectrum.return_value = None

    # Healthy FM acquisition with decoded station metadata.
    r.session._perform(RadioRequest(RadioAction.REFRESH), r.session._generation)
    source.latest_receiver.return_value = RadioTelemetry(
        frequency_hz=100_000_000, mode="WFM", receiver_running=True,
        station_name="LIVE FM", radio_text="Now playing", rds="LIVE FM")
    r.session.refresh_spectrum()
    assert r.session._state.receiver_running is True
    assert r.session._state.telemetry.station_name == "LIVE FM"

    # USB loss: REST is reachable but reports acquisition stopped.
    status["running"] = False
    status["startup_error"] = "USB disconnected"
    r.session._perform(RadioRequest(RadioAction.REFRESH), r.session._generation)
    assert r.session._state.receiver_running is False
    assert r.session._state.telemetry == RadioTelemetry()
    assert "USB disconnected" in r.session._state.error

    # A delayed ZMQ packet cannot revive RDS or override REST.
    r.session.refresh_spectrum()
    assert r.session._state.receiver_running is False
    assert r.session._state.telemetry.station_name == ""
    assert r.session._state.telemetry.radio_text == ""

    # Both transports are temporarily unavailable; last known station survives.
    outage["active"] = True
    r.radio.refresh.side_effect = OSError("rigctl offline")
    r.session._perform(RadioRequest(RadioAction.REFRESH), r.session._generation)
    assert r.session._state.station.frequency_hz == 100_000_000
    assert r.session._state.receiver_running is False

    # Acquisition and rigctl recover, including an external retune.
    outage["active"] = False
    status.clear()
    status["running"] = True
    r.radio.refresh.side_effect = None
    r.radio.refresh.return_value = replace(
        r.session._state.station, frequency_hz=162_550_000,
        mode_name="NFM", profile_key="weather")
    r.session._perform(RadioRequest(RadioAction.REFRESH), r.session._generation)
    assert r.session._state.receiver_running is True
    assert r.session._state.station.frequency_hz == 162_550_000
    assert r.session._state.telemetry == RadioTelemetry()

    # The first fresh NFM snapshot becomes the only station identity.
    source.latest_receiver.return_value = RadioTelemetry(
        frequency_hz=162_550_000, mode="NFM", receiver_running=True)
    r.session.refresh_spectrum()
    assert r.session._state.telemetry.mode == "NFM"
    assert r.session._state.telemetry.station_name == ""
    assert r.session._state.telemetry.rds == ""
    assert r.session._state.receiver_running is True


def test_spectrum_frames_are_suppressed_while_rest_reports_stopped(receiver):
    from ui.radio.sdrforge_spectrum_if import SpectrumPresentation

    r = receiver
    source = Mock()
    r.session._spectrum_source = source
    r.session._rest_receiver_running = False
    r.session._state = replace(r.session._state, receiver_running=False)
    source.latest_receiver.return_value = None
    source.latest_spectrum.return_value = SpectrumPresentation(
        bins=(0.1, 0.9), center_frequency_hz=100_000_000)
    # Mock is not a SpectrumPresentationIf, so register a protocol-compliant
    # concrete test view to verify no spectrum presentation occurs.
    class View:
        def __init__(self):
            self.frames = []
        def set_radio_state(self, state):
            self.state = state
        def set_spectrum_presentation(self, snapshot):
            self.frames.append(snapshot)

    view = View()
    r.session._view = view
    r.session.refresh_spectrum()
    assert view.frames == []


def test_spectrum_recovery_follows_acquisition_while_running(receiver):
    from ui.radio.sdrforge_spectrum_if import SpectrumPresentation

    r = receiver
    source = Mock()
    r.session._spectrum_source = source
    r.session._rest_receiver_running = True
    r.session._state = replace(r.session._state, receiver_running=True)
    source.latest_receiver.return_value = None
    class View:
        def __init__(self):
            self.frames = []
        def set_radio_state(self, state):
            self.state = state
        def set_spectrum_presentation(self, snapshot):
            self.frames.append(snapshot)

    view = View()
    r.session._view = view
    old = SpectrumPresentation(bins=(0.2, 0.8), center_frequency_hz=94_700_000)
    fresh = SpectrumPresentation(bins=(0.4, 0.6), center_frequency_hz=100_000_000)
    source.latest_spectrum.return_value = old
    r.session.refresh_spectrum()
    assert view.frames == [old]
    source.latest_spectrum.return_value = fresh
    r.session.refresh_spectrum()
    assert view.frames == [old, fresh]
    in_band = SpectrumPresentation(
        bins=(0.3, 0.7), center_frequency_hz=99_800_000, sample_rate_hz=2_400_000,
    )
    source.latest_spectrum.return_value = in_band
    r.session.refresh_spectrum()
    assert view.frames == [old, fresh, in_band]


def test_native_receiver_does_not_require_legacy_telemetry(receiver, monkeypatch):
    """Native SDRForge status refresh works with no SDR++ telemetry client."""
    r = receiver
    r.session._native_view = "none"
    monkeypatch.setattr(
        "controllers.radio.rf_radio_session.urllib.request.urlopen",
        Mock(side_effect=OSError("REST temporarily unavailable")),
    )
    r.radio.refresh.return_value = r.radio.state
    r.session._perform(RadioRequest(RadioAction.REFRESH), r.session._generation)
    assert not hasattr(r.session, "_telemetry")
    assert r.session._state.station.frequency_hz == 100_000_000


def test_native_launch_never_starts_or_embeds_sdrpp(receiver):
    r = receiver
    r.session.request(RadioRequest(RadioAction.LAUNCH))
    r.work.pop(0)()
    r.application.present.assert_not_called()
    r.application.window_process_id.assert_not_called()
    r.surface.embed.assert_not_called()
    assert r.session._state.view == "none"
    assert not r.session._state.loading


def test_native_launch_preserves_adsb_embedding_path(receiver):
    r = receiver
    r.session.request(RadioRequest(
        RadioAction.ADSB, host=RadioHost(10, 20, 800, 400)))
    r.work.pop(0)()
    r.aircraft.launch.assert_called_once()
    r.surface.embed.assert_called_once()
    r.application.present.assert_not_called()


def test_native_rest_outage_clears_running_state_and_stale_telemetry(receiver, monkeypatch):
    r = receiver
    r.session._state = replace(
        r.session._state,
        receiver_running=True,
        telemetry=RadioTelemetry(
            frequency_hz=100_000_000, station_name="OLD", rds="OLD",
        ),
    )

    def unavailable(*_args, **_kwargs):
        raise ConnectionRefusedError("connection refused")

    monkeypatch.setattr(
        "controllers.radio.rf_radio_session.urllib.request.urlopen", unavailable
    )
    r.session.request(RadioRequest(RadioAction.REFRESH))
    r.work.pop()()
    r.ui.pop()()
    state = r.view.set_radio_state.call_args.args[0]
    assert state.receiver_running is False
    assert state.telemetry.station_name == ""
    assert state.telemetry.rds == ""
    assert "SDRForge service unavailable:" in state.error
    assert "connection refused" in state.error


def test_native_rest_reconnection_clears_outage_error(receiver, monkeypatch):
    r = receiver
    r.session._state = replace(
        r.session._state,
        receiver_running=False,
        error="SDRForge service unavailable: connection refused",
    )

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            import json
            return json.dumps(self.payload).encode()

    def connected(url, timeout):
        if url.endswith("/v1/audio"):
            return Response({"muted": False})
        return Response({"running": True, "startup_error": None})

    monkeypatch.setattr(
        "controllers.radio.rf_radio_session.urllib.request.urlopen", connected
    )
    r.session.request(RadioRequest(RadioAction.REFRESH))
    r.work.pop()()
    r.ui.pop()()
    state = r.view.set_radio_state.call_args.args[0]
    assert state.receiver_running is True
    assert state.error == ""


@pytest.mark.parametrize("running,starting", [
    (False, False), (False, True), (True, False),
])
def test_native_refresh_tracks_receiver_lifecycle(receiver, monkeypatch, running, starting):
    import json
    from io import BytesIO

    r = receiver
    r.session._native_view = "none"
    calls = []

    def urlopen(request, timeout=1.5):
        calls.append(request)
        payload = (
            {"muted": False} if request.endswith("/v1/audio")
            else {"running": running, "starting": starting, "startup_error": None}
        )
        return BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr(
        "controllers.radio.rf_radio_session.urllib.request.urlopen", urlopen
    )
    r.radio.refresh.return_value = r.session._state.station
    r.session._perform(RadioRequest(RadioAction.REFRESH), r.session._generation)
    assert r.session._state.receiver_running is running
    assert r.session._state.receiver_starting is (starting and not running)
    assert not any(
        isinstance(call, str) and call.endswith("/v1/receiver/start")
        for call in calls
    )


def test_stale_zmq_running_flag_is_diagnostic_only_after_rest_stop(receiver):
    r = receiver
    r.session._rest_receiver_running = False
    r.session._state = replace(r.session._state, receiver_running=False)
    source = Mock()
    source.latest_receiver.return_value = RadioTelemetry(
        frequency_hz=100_000_000, receiver_running=True, rds="STALE"
    )
    source.latest_spectrum.return_value = None
    r.session._spectrum_source = source
    r.session.refresh_spectrum()
    state = r.view.set_radio_state.call_args.args[0]
    assert state.receiver_running is False
    # Preserve the raw delayed ZMQ flag for diagnostics, not UI authority.
    assert state.telemetry.receiver_running is True
    assert state.telemetry.rds == ""


def test_native_close_never_stops_shared_receiver(receiver, monkeypatch):
    r = receiver
    r.session._owns_receiver = False
    requests = Mock()
    monkeypatch.setattr(
        "controllers.radio.rf_radio_session.urllib.request.urlopen", requests
    )
    r.session.close()
    requests.assert_not_called()


def test_native_receiver_full_simulated_lifecycle(receiver, monkeypatch):
    """Start, fail, reconnect, stop and recover without RF hardware or Tk."""
    import json
    from io import BytesIO

    r = receiver
    r.session._native_view = "none"
    source = Mock()
    r.session._spectrum_source = source
    source.latest_spectrum.return_value = None
    source.latest_receiver.return_value = None
    status = {"running": False, "starting": False, "startup_error": None}
    offline = {"value": False}
    starts = []

    class Response(BytesIO):
        status = 202

    def urlopen(request, timeout=1.5):
        if offline["value"]:
            raise ConnectionRefusedError("connection refused")
        url = request if isinstance(request, str) else request.full_url
        if url.endswith("/v1/receiver/start"):
            starts.append(url)
            status.update(running=False, starting=True, startup_error=None)
            return Response(b"{}")
        if url.endswith("/v1/receiver/stop"):
            status.update(running=False, starting=False, startup_error=None)
            return Response(b"{}")
        payload = {"muted": False} if url.endswith("/v1/audio") else status
        return Response(json.dumps(payload).encode())

    monkeypatch.setattr(
        "controllers.radio.rf_radio_session.urllib.request.urlopen", urlopen
    )
    r.radio.refresh.return_value = r.session._state.station

    def execute(action):
        r.session.request(RadioRequest(action))
        r.work.pop(0)()
        r.ui.pop(0)()
        return r.view.set_radio_state.call_args.args[0]

    assert not execute(RadioAction.REFRESH).receiver_running
    assert len(starts) == 0

    accepted = execute(RadioAction.START_RECEIVER)
    assert not accepted.receiver_running
    assert accepted.receiver_starting
    assert len(starts) == 1

    starting = execute(RadioAction.REFRESH)
    assert starting.receiver_starting
    assert not starting.receiver_running

    status.update(running=False, starting=False, startup_error="USB disconnected")
    failed = execute(RadioAction.REFRESH)
    assert not failed.receiver_starting
    assert not failed.receiver_running
    assert "USB disconnected" in failed.error

    offline["value"] = True
    unavailable = execute(RadioAction.REFRESH)
    assert not unavailable.receiver_running
    assert not unavailable.receiver_starting
    assert "service unavailable" in unavailable.error

    offline["value"] = False
    status.update(running=False, starting=False, startup_error=None)
    recovered = execute(RadioAction.REFRESH)
    assert recovered.error == ""
    assert not recovered.receiver_running
    assert len(starts) == 1  # Recovery never restarts shared acquisition.

    status.update(running=True, starting=False)
    running = execute(RadioAction.REFRESH)
    assert running.receiver_running
    assert not running.receiver_starting
    source.latest_receiver.return_value = RadioTelemetry(
        frequency_hz=100_000_000, mode="WFM", receiver_running=True,
        station_name="LIVE", rds="LIVE"
    )
    r.session.refresh_spectrum()
    assert r.session._state.telemetry.station_name == "LIVE"

    stopped = execute(RadioAction.STOP_RECEIVER)
    assert not stopped.receiver_running
    assert not stopped.receiver_starting
    assert stopped.telemetry == RadioTelemetry()
    r.session.refresh_spectrum()
    assert not r.session._state.receiver_running
    assert r.session._state.telemetry.station_name == ""
    assert r.session._state.telemetry.receiver_running is True
    assert len(starts) == 1
