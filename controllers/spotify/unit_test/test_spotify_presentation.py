# SPDX-License-Identifier: MIT

"""Presentation lifetime, track ordering, and request behavior without a GUI."""

from dataclasses import replace
from unittest.mock import Mock

import pytest

from controllers.lyrics.lrclib_lyrics_client import LyricLine, LyricsResult
from controllers.spotify.spotify_presentation import SpotifyPresentation
from ui.media import MediaAvailability, MediaState


@pytest.fixture
def session_setup():
    media = [MediaState(availability=MediaAvailability.AVAILABLE, title="one", artist="artist", artwork_uri="art-one", media_uri="one", duration_s=100, position_s=5, volume_percent=30)]
    online = [True]
    work, ui = [], []
    dispatcher = Mock()
    dispatcher.dispatch_ui.side_effect = ui.append
    view = Mock()
    volume = Mock()
    lyrics = LyricsResult(synced_lines=(LyricLine(0, "first"), LyricLine(10000, "second")))
    session = SpotifyPresentation(
        read_state=lambda: media[0], online=lambda: online[0],
        load_artwork=lambda uri: uri.encode(), load_lyrics=lambda _state: lyrics,
        video_available=lambda: True, video_active=lambda: False,
        watch_video=lambda _current, _restore: True, return_to_spotify=lambda _current: None,
        run_work=work.append, dispatcher=dispatcher, set_volume=volume,
    )
    session.activate(view)
    return session, view, media, online, work, ui, dispatcher, volume


def drain(work, ui):
    while work:
        work.pop(0)()
    while ui:
        ui.pop(0)()


def test_track_change_discards_completed_old_artwork_and_lyrics(session_setup):
    session, view, media, _, work, ui, _, _ = session_setup
    while work:
        work.pop(0)()
    media[0] = replace(media[0], title="two", media_uri="two", artwork_uri="art-two")
    session._tick()
    drain(work, ui)
    state = view.set_spotify_state.call_args.args[0]
    assert state.media.title == "two"
    assert state.artwork == b"art-two"
    assert state.lyric_current == "first"


@pytest.mark.parametrize("retire", ["deactivate", "close"])
def test_retirement_discards_queued_completions_and_cancels_timer(session_setup, retire):
    session, view, _, _, work, ui, dispatcher, _ = session_setup
    while work:
        work.pop(0)()
    getattr(session, retire)()
    view.set_spotify_state.reset_mock()
    drain(work, ui)
    view.set_spotify_state.assert_not_called()
    dispatcher.cancel_ui_callback.assert_called()
    view.set_video_request_handler.assert_called_with(None)


def test_offline_discards_pending_artwork_and_clears_state(session_setup):
    session, view, _, online, work, ui, _, _ = session_setup
    while work:
        work.pop(0)()
    online[0] = False
    session._tick()
    drain(work, ui)
    state = view.set_spotify_state.call_args.args[0]
    assert not state.online
    assert state.artwork is None
    assert state.lyric_current == ""
    assert state.video_available is False


def test_lyrics_follow_latest_position(session_setup):
    session, view, media, _, work, ui, _, _ = session_setup
    drain(work, ui)
    media[0] = replace(media[0], position_s=12)
    session._tick()
    state = view.set_spotify_state.call_args.args[0]
    assert state.lyric_current == "second"
    assert state.lyric_next == ""
    assert not work


def test_closed_session_cannot_reactivate_or_submit_video(session_setup):
    session, view, _, _, work, _, _, _ = session_setup
    session.close()
    work.clear()
    session.request_watch_video()
    session.request_volume(50)
    assert not work
    with pytest.raises(RuntimeError, match="closed"):
        session.activate(view)


def test_rapid_volume_intent_is_rendered_until_backend_confirms(session_setup):
    session, view, media, _, _, _, _, volume = session_setup
    session.request_volume(35)
    session.request_volume(40)
    session._tick()
    assert view.set_spotify_state.call_args.args[0].media.volume_percent == 40
    assert volume.call_args.args == (40,)
    media[0] = replace(media[0], volume_percent=40)
    session._tick()
    assert session._pending_volume is None


def test_video_requests_are_asynchronous_and_retired_before_start(session_setup):
    session, view, _, _, work, ui, _, _ = session_setup
    drain(work, ui)
    watch = Mock(return_value=True)
    session._watch_video = watch
    session.request_watch_video()
    assert view.set_spotify_state.call_args.args[0].video_busy
    watch.assert_not_called()
    session.deactivate()
    drain(work, ui)
    watch.assert_not_called()


def test_retirement_blocks_all_playback_commands(session_setup):
    session, view, _, _, _, _, _, volume = session_setup
    controls = Mock()
    session._playback = controls
    session._tracks = controls
    session._seek = controls
    session.request_play()
    controls.request_play.assert_called_once_with()
    controls.reset_mock()
    session.deactivate()
    session.request_play()
    session.request_pause()
    session.request_next_track()
    session.request_previous_track()
    session.request_seek(10)
    session.request_rewind(5)
    session.request_forward(5)
    session.request_volume(60)
    assert not controls.mock_calls
    volume.assert_not_called()
    view.set_spotify_request_handler.assert_called_with(None)


def test_returning_to_spotify_keeps_overlay_inactive_until_worker_finishes(session_setup):
    session, view, _, _, work, ui, _, _ = session_setup
    drain(work, ui)
    session._video_active = lambda: True
    session._tick()
    session.request_return_to_spotify()
    session._tick()
    assert not view.set_spotify_state.call_args.args[0].video_active
    drain(work, ui)
    assert not view.set_spotify_state.call_args.args[0].video_busy
