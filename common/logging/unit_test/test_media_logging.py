# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Verify safe media events across workers, caches, and player boundaries."""

from dataclasses import replace
import json
import logging
import threading
from unittest.mock import Mock, patch

import pytest

from apps.orcUi.adapters.managed_browser_media_player import ManagedBrowserMediaPlayer
from apps.orcUi.adapters.spotify_web_player_host import SpotifyWebPlayerHost
from apps.orcUi.media_application_service import MediaApplicationService
from common.logging.structured import JsonFormatter, current_operation, operation, validate_event
from controllers.audio.system_volume_handler import SystemVolumeHandler
from controllers.spotify.spotify_local_player import SpotifyLocalPlayer, SpotifyPlaybackMode
from controllers.spotify.spotify_media_presenter import SpotifyMediaPresenter
from controllers.spotify.spotify_state import SpotifyState
from controllers.spotify.spotify_state_service import SpotifyStateService
from controllers.spotify.spotify_web_api_controller import SpotifyWebApiController
from controllers.video.music_video_controller import MusicVideoController
from controllers.video.music_video_types import MusicVideo
from protocols.spotify.spotify_web_api_client import SpotifyWebApiError
from ui.media import MediaAvailability, MediaState, MediaUiStub, PlaybackState


def events(caplog):
    result = [
        json.loads(JsonFormatter().format(record))
        for record in caplog.records
        if record.name.startswith("media.")
    ]
    for item in result:
        validate_event(item)
    assert "private" not in json.dumps(result)
    return result


@pytest.mark.parametrize(
    "request_method,args,backend",
    [
        ("request_play", (), "play"),
        ("request_pause", (), "pause"),
        ("request_next_track", (), "next_track"),
        ("request_previous_track", (), "previous_track"),
        ("request_seek", (12.34,), "seek_to_position_ms"),
        ("request_volume", (140,), "set_volume_percent"),
        ("request_transfer_playback", ("private-device",), "transfer_playback"),
        ("request_play_track", ("spotify:track:private-track",), "play_track"),
    ],
)
def test_queued_commands_keep_operation_across_real_worker_thread(
    caplog, request_method, args, backend
):
    caplog.set_level(logging.DEBUG)
    controller = Mock()
    service = SpotifyStateService(controller)
    with operation("ui-action"):
        getattr(service, request_method)(*args)
    getattr(controller, backend).assert_not_called()
    worker = threading.Thread(target=service._drain_commands)
    worker.start()
    worker.join(timeout=2)
    assert not worker.is_alive()
    getattr(controller, backend).assert_called_once()
    emitted = events(caplog)
    assert [item["event"] for item in emitted] == ["command.queued", "command.completed"]
    assert all(item["operation_id"] == "ui-action" for item in emitted)
    assert current_operation() is None


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("private token"),
        SpotifyWebApiError(500, "private response"),
        SpotifyWebApiError(429, "private response", retry_after_seconds=7),
    ],
)
def test_command_failure_has_no_success_and_preserves_rate_backoff(caplog, capsys, error):
    caplog.set_level(logging.INFO)
    controller = Mock()
    controller.play.side_effect = error
    service = SpotifyStateService(controller)
    service.request_play()
    service._drain_commands()
    emitted = events(caplog)
    names = [item["event"] for item in emitted]
    assert "command.failed" in names and "command.completed" not in names
    assert emitted[0]["operation_id"] == emitted[1]["operation_id"]
    if isinstance(error, SpotifyWebApiError) and error.status_code == 429:
        assert service._backoff_until > 0
        assert emitted[-1]["event"] == "api.rate_limited"
        assert emitted[-1]["retry_after_s"] == 7
        assert emitted[-1]["operation_id"] == emitted[0]["operation_id"]
    assert not capsys.readouterr().out


@pytest.mark.parametrize(
    "load,backend",
    [
        ("load_saved_tracks", "saved_tracks"),
        ("load_recently_played", "recently_played"),
        ("load_playlists", "playlists"),
        ("load_playlist_tracks", "playlist_tracks"),
    ],
)
def test_library_load_logs_counts_without_metadata_or_identifiers(caplog, load, backend):
    caplog.set_level(logging.INFO)
    controller = Mock()
    items = (Mock(name="private-track"), Mock(name="private-track"))
    getattr(controller, backend).return_value = items
    service = SpotifyStateService(controller)
    args = ("private-playlist",) if load == "load_playlist_tracks" else ()
    assert getattr(service, load)(*args) == items
    emitted = events(caplog)
    assert [item["event"] for item in emitted] == ["library.load_started", "library.load_completed"]
    assert emitted[1]["item_count"] == 2
    assert emitted[0]["operation_id"] == emitted[1]["operation_id"]
    if not args:
        assert getattr(service, load)() == items
        assert events(caplog) == emitted
        getattr(controller, backend).assert_called_once()


def test_failed_library_refresh_preserves_cache(caplog):
    caplog.set_level(logging.INFO)
    controller = Mock()
    controller.saved_tracks.return_value = (Mock(),)
    service = SpotifyStateService(controller)
    previous = service.load_saved_tracks()
    caplog.clear()
    controller.saved_tracks.side_effect = RuntimeError("private path and playlist")
    with pytest.raises(RuntimeError):
        service.load_saved_tracks(refresh=True)
    assert service.cached_saved_tracks() == previous
    emitted = events(caplog)
    assert [item["event"] for item in emitted] == ["library.load_started", "library.load_failed"]
    assert emitted[1]["exception_type"] == "RuntimeError"


def test_polling_logs_only_state_transitions_at_info(caplog):
    caplog.set_level(logging.INFO)
    service = SpotifyStateService(Mock())
    state = MediaState(
        availability=MediaAvailability.AVAILABLE,
        playback=PlaybackState.PLAYING,
        media_uri="spotify:track:private-one",
        title="private song",
        device_name="private device",
        position_s=1,
    )
    service._presenter.read_state = Mock(return_value=state)
    service._refresh_state()
    baseline = events(caplog)
    for position in [2, 3, 4]:
        service._presenter.read_state.return_value = replace(state, position_s=position)
        service._refresh_state()
    assert events(caplog) == baseline
    service._presenter.read_state.return_value = replace(state, playback=PlaybackState.PAUSED)
    service._refresh_state()
    assert events(caplog)[-1]["event"] == "state.playback_changed"
    service._presenter.read_state.return_value = replace(
        state, media_uri="spotify:track:private-two"
    )
    service._refresh_state()
    assert events(caplog)[-1]["event"] == "state.track_changed"


def test_swallowed_api_errors_log_one_loss_then_recovery(caplog):
    caplog.set_level(logging.INFO)
    client = Mock()
    client.request_json.side_effect = [
        SpotifyWebApiError(401, "private token"),
        SpotifyWebApiError(401, "private token"),
        None,
    ]
    controller = SpotifyWebApiController(client)
    assert not controller.current_state().is_available
    assert not controller.current_state().is_available
    assert (
        not controller.current_state().is_available
    )  # 204 is a healthy API without an active device.
    emitted = events(caplog)
    assert [item["event"] for item in emitted] == ["api.state_failed", "api.state_recovered"]
    assert emitted[0]["http_status"] == 401


def test_presenter_error_fallback_logs_transition_without_exception_message(caplog):
    caplog.set_level(logging.INFO)
    backend = Mock()
    backend.current_state.side_effect = [
        RuntimeError("private response"),
        RuntimeError("private response"),
        SpotifyState(),
    ]
    presenter = SpotifyMediaPresenter(backend, MediaUiStub())
    assert presenter.read_state().availability is MediaAvailability.ERROR
    assert presenter.read_state().availability is MediaAvailability.ERROR
    presenter.read_state()
    assert [item["event"] for item in events(caplog)] == [
        "state.read_failed",
        "state.read_recovered",
    ]


def make_player(service, host, browser):
    return SpotifyLocalPlayer(
        spotify_service=service,
        host_factory=lambda: host,
        browser_factory=lambda _url: browser,
        browser_candidates=("browser",),
        browser_finder=lambda _candidate: "/private/browser",
        registration_timeout_seconds=0.2,
    )


def run_player_request(player):
    real_thread = threading.Thread
    threads = []

    def create_thread(*args, **kwargs):
        thread = real_thread(*args, **kwargs)
        threads.append(thread)
        return thread

    with patch(
        "controllers.spotify.spotify_local_player.threading.Thread", side_effect=create_thread
    ):
        player.request_player()
    for thread in threads:
        thread.join(timeout=2)
        assert not thread.is_alive()


def test_local_player_thread_correlates_registration_and_queued_transfer(caplog):
    caplog.set_level(logging.INFO)
    backend = Mock()
    service = SpotifyStateService(backend)
    host = Mock(url="http://private-host/", error=None, device_id="private-device")
    player = make_player(service, host, Mock())
    with operation("player-start"):
        run_player_request(player)
    assert player.state().mode is SpotifyPlaybackMode.PLAYER and not player.state().busy
    service._drain_commands()
    emitted = events(caplog)
    assert {item["event"] for item in emitted} >= {
        "player.requested",
        "player.registered",
        "command.completed",
    }
    assert all(item["operation_id"] == "player-start" for item in emitted)
    run_player_request(player)
    assert events(caplog) == emitted
    player.close()
    player.close()
    assert [item["event"] for item in events(caplog)].count("player.released") == 1
    host.close.assert_called_once()


def test_local_player_failure_cleans_up_without_success(caplog):
    caplog.set_level(logging.INFO)
    host = Mock(url="http://private-host/", error="private SDK token error", device_id=None)
    browser = Mock()
    player = make_player(Mock(), host, browser)
    run_player_request(player)
    emitted = events(caplog)
    assert "player.failed" in [item["event"] for item in emitted]
    assert "player.registered" not in [item["event"] for item in emitted]
    assert player.state().mode is SpotifyPlaybackMode.REMOTE
    browser.stop.assert_called_once()
    host.close.assert_called_once()


def test_sdk_callback_thread_keeps_id_and_redacts_untrusted_error(caplog, capsys):
    caplog.set_level(logging.INFO)
    host = SpotifyWebPlayerHost.__new__(SpotifyWebPlayerHost)
    host._lock = threading.Lock()
    host._device_id = None
    host._error = None
    host._operation_id = "sdk-start"

    def callback():
        host._set_device_id("private-device")
        host._set_device_id("private-device")
        host._set_error("private token", category="private-category")
        host._set_error("private token again", category="authentication_error")
        host._set_device_id("private-device")

    thread = threading.Thread(target=callback)
    thread.start()
    thread.join(timeout=2)
    emitted = events(caplog)
    assert [item["event"] for item in emitted] == ["sdk.ready", "sdk.error", "sdk.ready"]
    assert emitted[1]["category"] == "unknown"
    assert all(item["operation_id"] == "sdk-start" for item in emitted)
    assert not capsys.readouterr().out


def test_managed_browser_commands_log_no_target_and_respect_close_policy(caplog):
    caplog.set_level(logging.INFO)
    manager = Mock()
    manager.is_running.return_value = False
    player = ManagedBrowserMediaPlayer(manager, "youtube", resolve_target=lambda target: target)
    assert player.play("https://private-target/?token=private", display=":1")
    manager.is_running.return_value = True
    player.stop()
    manager.is_running.return_value = False
    player.stop()
    emitted = events(caplog)
    assert [item["event"] for item in emitted] == [
        "browser.requested",
        "browser.show_completed",
        "browser.close_completed",
    ]
    assert emitted[0]["operation_id"] == emitted[1]["operation_id"]


def test_browser_failure_has_no_show_completed(caplog):
    caplog.set_level(logging.INFO)
    manager = Mock()
    manager.show.side_effect = RuntimeError("private browser path")
    player = ManagedBrowserMediaPlayer(manager, "netflix", resolve_target=lambda target: target)
    with pytest.raises(RuntimeError):
        player.play("https://private-target/", display=":1")
    assert [item["event"] for item in events(caplog)] == ["browser.requested", "browser.failed"]


def test_video_failure_restores_spotify_without_logging_metadata(caplog):
    caplog.set_level(logging.INFO)
    spotify, video = Mock(), Mock()
    spotify.current_state.return_value = SpotifyState(
        is_available=True,
        is_playing=True,
        track_name="private song",
        artist_name="private artist",
        progress_ms=12000,
    )
    video.find_video.return_value = MusicVideo("private-id", "private title", "private channel")
    video.play_video.side_effect = RuntimeError("private URL")
    controller = MusicVideoController(spotify, video)
    with pytest.raises(RuntimeError):
        controller.watch_current_track()
    spotify.pause.assert_called_once()
    spotify.play.assert_called_once()
    emitted = events(caplog)
    assert [item["event"] for item in emitted] == [
        "video.requested",
        "video.lookup_completed",
        "video.failed",
    ]
    assert len({item["operation_id"] for item in emitted}) == 1


def test_audio_availability_polling_is_quiet_and_recovers(caplog):
    caplog.set_level(logging.INFO)
    audio = Mock(is_available=True, maximum_level=20)
    audio.get_volume_level.side_effect = [
        RuntimeError("private sink"),
        RuntimeError("private sink"),
        10,
    ]
    handler = SystemVolumeHandler(audio_controller=audio, volume_ui=Mock())
    handler.refresh()
    handler.refresh()
    handler.refresh()
    emitted = events(caplog)
    assert [item["available"] for item in emitted] == [False, True]
    audio.set_volume_level.side_effect = RuntimeError("private audio error")
    handler.request_volume(50)
    assert events(caplog)[-1]["event"] == "audio.command_failed"
    assert events(caplog)[-1]["operation_id"]


def test_media_service_cleanup_stops_worker_even_if_local_player_close_fails(caplog):
    caplog.set_level(logging.INFO)
    with patch("apps.orcUi.media_application_service.create_spotify_local_player") as factory:
        service = MediaApplicationService(Mock())
    service._spotify = Mock()
    service._started = True
    factory.return_value.close.side_effect = RuntimeError("private failure")
    with pytest.raises(RuntimeError):
        service.close()
    service._spotify.close.assert_called_once()
    assert not service._started
    assert [item["event"] for item in events(caplog)] == ["media.close_failed"]


def test_volume_and_seek_do_not_flood_info_logs(caplog):
    caplog.set_level(logging.INFO)
    service = SpotifyStateService(Mock())
    for position in [1, 2, 3]:
        service.request_seek(position)
        service.request_volume(position)
    service._drain_commands()
    assert not events(caplog)


def test_worker_stop_timeout_does_not_claim_success(caplog):
    caplog.set_level(logging.INFO)
    service = SpotifyStateService(Mock())
    thread = Mock()
    thread.is_alive.return_value = True
    service._thread = thread
    service.close()
    service.close()
    emitted = events(caplog)
    assert [item["event"] for item in emitted] == ["worker.stop_pending"]
    thread.join.assert_called_once_with(timeout=1.0)


def test_local_player_browser_stop_failure_does_not_claim_release(caplog):
    caplog.set_level(logging.INFO)
    browser = Mock()
    browser.stop.side_effect = RuntimeError("private process")
    host = Mock(url="http://private-host/", error=None, device_id="private-device")
    player = make_player(Mock(), host, browser)
    run_player_request(player)
    caplog.clear()
    player.close()
    host.close.assert_called_once()
    assert [item["event"] for item in events(caplog)] == ["browser.stop_failed"]


def test_video_false_start_restores_spotify_and_has_no_launch_success(caplog):
    caplog.set_level(logging.INFO)
    spotify, video = Mock(), Mock()
    spotify.current_state.return_value = SpotifyState(
        is_available=True, is_playing=True, track_name="private song", artist_name="private artist"
    )
    video.find_video.return_value = MusicVideo("private-id", "private title", "private channel")
    video.play_video.return_value = False
    controller = MusicVideoController(spotify, video)
    assert not controller.watch_current_track()
    spotify.play.assert_called_once()
    assert events(caplog)[-1]["event"] == "video.not_started"
    baseline = events(caplog)
    assert controller.current_track_has_video()
    assert events(caplog) == baseline


def test_media_start_failure_can_be_retried_and_lifecycle_is_idempotent(caplog):
    caplog.set_level(logging.INFO)
    with patch("apps.orcUi.media_application_service.create_spotify_local_player"):
        service = MediaApplicationService(Mock())
    service._spotify = Mock()
    service._spotify.start.side_effect = [RuntimeError("private startup"), None]
    with pytest.raises(RuntimeError):
        service.start()
    assert not service._started
    service.start()
    service.start()
    service.close()
    service.close()
    assert [item["event"] for item in events(caplog)] == [
        "media.start_failed",
        "media.started",
        "media.stopped",
    ]
