# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Logging gates for RF controls, streaming, directory and SDR health."""

import io
import json
import logging
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from common.logging.structured import JsonFormatter, current_operation, validate_event
from controllers.radio.adapters.radio_browser_directory import RadioBrowserDirectory
from controllers.radio.adapters.rigctl_radio_backend import RigctlRadioBackend
from controllers.radio.radio_controller import RadioController
from controllers.radio.radio_profile_controller import RadioProfileController
from controllers.radio.radio_types import RadioMode, RadioPreset
from controllers.radio.streaming_radio_controller import StreamingRadioController
from controllers.radio.streaming_radio_types import StreamingRadioStation
from controllers.sdr.sdr_resource_manager import SDRResourceManager
from controllers.sdr.sdr_telemetry_monitor import SDRTelemetryMonitor
from hardware_io.audio.mpv_streaming_audio_player import MpvStreamingAudioPlayer


def items(caplog):
    emitted = [
        json.loads(JsonFormatter().format(record))
        for record in caplog.records
        if record.name.startswith("radio.")
    ]
    for item in emitted:
        validate_event(item)
    return emitted


@pytest.fixture
def receiver():
    mode = RadioMode("WFM", 180_000, 100_000)
    preset = RadioPreset("Private preset label", 101_100_000, mode)
    return RadioController(Mock(), [preset], mode), preset


def test_preset_logs_one_operation_with_typed_frequency_and_no_label(receiver, caplog):
    caplog.set_level(logging.INFO)
    radio, preset = receiver
    radio.tune_preset(preset)
    emitted = items(caplog)
    assert [item["event"] for item in emitted] == [
        "mode.changed",
        "frequency.tuned",
        "preset.selected",
    ]
    assert len({item["operation_id"] for item in emitted}) == 1
    assert emitted[-1]["frequency_hz"] == 101_100_000
    assert "Private preset label" not in json.dumps(emitted)
    assert current_operation() is None


def test_start_stop_are_logged_once_for_idempotent_calls(receiver, caplog):
    caplog.set_level(logging.INFO)
    radio, _ = receiver
    radio.start()
    radio.start()
    radio.stop()
    radio.stop()
    events = [item["event"] for item in items(caplog)]
    assert events.count("receiver.started") == 1
    assert events.count("receiver.stopped") == 1


@pytest.mark.parametrize("action", ["start", "mode", "frequency", "stop"])
def test_receiver_failures_do_not_emit_success(receiver, action, caplog):
    caplog.set_level(logging.INFO)
    radio, preset = receiver
    backend = radio.backend
    if action == "stop":
        radio.start()
        caplog.clear()
    method = {
        "start": backend.start,
        "mode": backend.set_mode,
        "frequency": backend.set_frequency,
        "stop": backend.stop,
    }[action]
    method.side_effect = OSError("private backend response")
    call = {
        "start": radio.start,
        "mode": lambda: radio.set_mode(preset.mode),
        "frequency": lambda: radio.set_frequency(102_000_000),
        "stop": radio.stop,
    }[action]
    before = radio.current_frequency_hz
    with pytest.raises(OSError):
        call()
    emitted = items(caplog)
    assert any(item["level"] == "ERROR" for item in emitted)
    assert not any(
        item["event"] in {"receiver.started", "receiver.stopped", "mode.changed", "frequency.tuned"}
        for item in emitted
    )
    assert radio.current_frequency_hz == before
    assert "private backend response" not in json.dumps(emitted)
    assert current_operation() is None


@pytest.mark.parametrize("response", ["RPRT -1", "RPRT invalid", "RPRT", ""])
def test_rigctl_failed_acknowledgement_is_a_logged_failure(response, caplog):
    caplog.set_level(logging.INFO)
    client = Mock()
    client.set_frequency.return_value = response
    mode = RadioMode("WFM", 180_000, 100_000)
    radio = RadioController(
        RigctlRadioBackend(client), [RadioPreset("FM", 101_100_000, mode)], mode
    )
    with pytest.raises((RuntimeError, TimeoutError)):
        radio.set_frequency(102_000_000)
    assert radio.current_frequency_hz == 101_100_000
    assert [item["event"] for item in items(caplog)] == ["frequency.failed"]
    if response == "RPRT -1":
        assert items(caplog)[0]["error_code"] == -1


@pytest.mark.parametrize("response", ["RPRT 0", "OK"])
def test_rigctl_successful_acknowledgements_are_preserved(response):
    assert RigctlRadioBackend._checked_response(response) == response


def test_frequency_polling_reports_loss_and_recovery_without_flood(receiver, caplog):
    caplog.set_level(logging.INFO)
    radio, _ = receiver
    radio.backend.get_frequency.side_effect = [OSError("failed")] * 5 + [
        radio.current_frequency_hz
    ] * 5
    for _ in range(5):
        with pytest.raises(OSError):
            radio.refresh_frequency()
    for _ in range(5):
        radio.refresh_frequency()
    assert [item["event"] for item in items(caplog)] == [
        "frequency.unavailable",
        "frequency.recovered",
    ]


def test_profile_start_shares_operation_with_rf_commands(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    from controllers.radio.radio_profiles import RadioProfileCatalog

    profile = RadioProfileController(
        client=Mock(), catalog=RadioProfileCatalog(user_presets_path=tmp_path / "presets.json")
    )
    caplog.clear()
    profile.select_profile("fm_radio")
    emitted = items(caplog)
    assert emitted[-1]["event"] == "profile.selected"
    assert emitted[-1]["profile_key"] == "fm_radio"
    assert len({item["operation_id"] for item in emitted}) == 1


def test_streaming_flow_correlates_with_player_and_excludes_url(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    process = Mock(pid=777, returncode=4)
    process.poll.return_value = None
    player = MpvStreamingAudioPlayer()
    monkeypatch.setattr(player, "_resolve_executable", lambda: "/test/mpv")
    monkeypatch.setattr(
        "hardware_io.audio.mpv_streaming_audio_player.subprocess.Popen",
        lambda *args, **kwargs: process,
    )
    station = StreamingRadioStation(
        "station-1", "Private station name", "https://user:password@example.test/live?token=secret"
    )
    controller = StreamingRadioController(player)
    controller.play(station)
    emitted = items(caplog)
    assert {item["event"] for item in emitted} == {
        "playback.requested",
        "player.started",
        "playback.started",
    }
    operation_id = emitted[0]["operation_id"]
    assert all(item["operation_id"] == operation_id for item in emitted)
    process.poll.return_value = 4
    assert not controller.is_playing
    exit_event = items(caplog)[-1]
    assert exit_event["event"] == "player.exited" and exit_event["level"] == "ERROR"
    assert exit_event["operation_id"] == operation_id
    encoded = json.dumps(items(caplog))
    assert (
        "secret" not in encoded
        and "password" not in encoded
        and "Private station name" not in encoded
    )


def test_streaming_failure_preserves_station_and_redacts_error(caplog):
    caplog.set_level(logging.INFO)
    player = Mock()
    controller = StreamingRadioController(player)
    first = StreamingRadioStation("one", "One", "https://example.test/one")
    controller.play(first)
    caplog.clear()
    player.play.side_effect = RuntimeError("https://user:password@example.test/live?token=secret")
    with pytest.raises(RuntimeError):
        controller.play(StreamingRadioStation("two", "Two", "https://example.test/two"))
    assert controller.current_station is first
    assert [item["event"] for item in items(caplog)] == ["playback.requested", "playback.failed"]
    assert "secret" not in json.dumps(items(caplog))


def test_repeated_streaming_stop_is_quiet(caplog):
    caplog.set_level(logging.INFO)
    controller = StreamingRadioController(Mock())
    controller.stop()
    assert not items(caplog)


def test_directory_records_counts_without_queries_locations_or_urls(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    payload = [
        {
            "stationuuid": "one",
            "name": "Secret station",
            "url": "https://user:password@example.test/live?token=secret",
        }
    ]
    monkeypatch.setattr(
        "controllers.radio.adapters.radio_browser_directory.urlopen",
        lambda *args, **kwargs: io.StringIO(json.dumps(payload)),
    )
    directory = RadioBrowserDirectory(api_base="https://user:password@example.test/json")
    stations = directory.search("private search text")
    assert len(stations) == 1
    emitted = items(caplog)
    assert emitted[-1]["station_count"] == 1
    assert "private search text" not in json.dumps(emitted) and "password" not in json.dumps(
        emitted
    )


def test_directory_failure_does_not_record_url_or_exception_text(monkeypatch, caplog):
    caplog.set_level(logging.INFO)

    def fail(*args, **kwargs):
        raise OSError("private search text https://user:password@example.test")

    monkeypatch.setattr("controllers.radio.adapters.radio_browser_directory.urlopen", fail)
    with pytest.raises(OSError):
        RadioBrowserDirectory().search("private search text")
    emitted = items(caplog)
    assert emitted[-1]["event"] == "directory.failed"
    assert "private search text" not in json.dumps(emitted) and "password" not in json.dumps(
        emitted
    )


def test_sdr_health_logs_only_transitions_and_never_rds_text(caplog):
    caplog.set_level(logging.INFO)
    snapshot = SimpleNamespace(center_frequency_hz=101_100_000, signal_peak_db=-42.0, snr_db=20.0)
    client = Mock()
    client.read.side_effect = [OSError("private")] * 5 + [snapshot] * 5
    radio = Mock(current_frequency_hz=101_100_000)
    radio.read_rds.return_value = "Private broadcast text"
    monitor = SDRTelemetryMonitor(radio, client)
    for _ in range(10):
        monitor.read(include_rds=True)
    assert [item["event"] for item in items(caplog)] == [
        "telemetry.unavailable",
        "telemetry.recovered",
    ]
    assert "Private broadcast text" not in json.dumps(items(caplog))


def test_rds_loss_recovery_and_missing_methods_remain_best_effort(caplog):
    caplog.set_level(logging.INFO)
    snapshot = SimpleNamespace(center_frequency_hz=None, signal_peak_db=None, snr_db=None)
    radio = Mock(current_frequency_hz=101_100_000)
    radio.read_rds.side_effect = [OSError("private")] * 3 + ["Private text"] * 3
    client = Mock()
    client.read.return_value = snapshot
    monitor = SDRTelemetryMonitor(radio, client)
    for _ in range(6):
        monitor.read(include_rds=True)
    assert [item["event"] for item in items(caplog)] == ["rds.unavailable", "rds.recovered"]
    assert "Private text" not in json.dumps(items(caplog))


def test_sdr_ownership_records_transfers_and_ignores_noops(caplog):
    caplog.set_level(logging.INFO)
    manager = SDRResourceManager()
    assert manager.acquire("radio")
    assert manager.acquire("radio")
    assert not manager.acquire("adsb", force=False)
    assert manager.acquire("adsb", force=True)
    manager.release("radio")
    manager.release("adsb")
    assert [item["event"] for item in items(caplog)] == [
        "sdr.acquired",
        "sdr.busy",
        "sdr.transferred",
        "sdr.released",
    ]


def test_profile_tuning_from_cold_receiver_shares_one_operation(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    from controllers.radio.radio_profiles import RadioProfileCatalog

    profile = RadioProfileController(
        client=Mock(), catalog=RadioProfileCatalog(user_presets_path=tmp_path / "presets.json")
    )
    caplog.clear()
    preset = profile.catalog.profile("fm_radio").presets[0]
    profile.tune_preset(preset)
    emitted = items(caplog)
    assert "receiver.started" in {item["event"] for item in emitted}
    assert "preset.selected" in {item["event"] for item in emitted}
    assert len({item["operation_id"] for item in emitted}) == 1
