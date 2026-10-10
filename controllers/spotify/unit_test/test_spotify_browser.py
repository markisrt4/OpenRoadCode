# SPDX-License-Identifier: MIT

"""Library contract tests with explicitly ordered work and frontend queues."""

from unittest.mock import Mock

import pytest

from controllers.spotify.spotify_browser import SpotifyBrowser
from ui.media.spotify_browse_if import SpotifyCollection, SpotifyLocalPlayerState, SpotifyPlaybackMode
from ui.media.spotify_library import SpotifyLibraryTrack, SpotifyPlaylist


@pytest.fixture
def setup_browser():
    service = Mock()
    service.cached_saved_tracks.return_value = None
    service.cached_recently_played.return_value = None
    service.cached_playlists.return_value = None
    service.load_saved_tracks.return_value = (SpotifyLibraryTrack("liked", "artist", None, "liked-uri", "liked-art"),)
    service.load_recently_played.return_value = (SpotifyLibraryTrack("recent", "artist", None, "recent-uri", "recent-art"),)
    service.load_playlists.return_value = (SpotifyPlaylist("playlist-id", "playlist", "playlist-uri", "playlist-art"),)
    service.load_playlist_tracks.return_value = (SpotifyLibraryTrack("playlist-track", "artist", None, "playlist-track-uri"),)
    player = Mock()
    player.state.return_value = SpotifyLocalPlayerState(available=True)
    dispatcher = Mock()
    work, ui = [], []
    dispatcher.dispatch_ui.side_effect = ui.append
    online = [True]
    show_now = Mock()
    loader = Mock(side_effect=lambda uri: uri.encode())
    session = SpotifyBrowser(service, player, run_work=work.append, dispatcher=dispatcher,
        load_artwork=loader, online=lambda: online[0], show_now_playing=show_now)
    view = Mock()
    session.activate(view)
    return session, service, player, view, work, ui, online, show_now, dispatcher


def drain(work, ui):
    while work or ui:
        while work:
            work.pop(0)()
        while ui:
            ui.pop(0)()


def test_recent_selection_supersedes_queued_liked_results(setup_browser):
    session, service, _, view, work, ui, _, _, _ = setup_browser
    session.request_collection(SpotifyCollection.LIKED)
    work.pop(0)()
    session.request_collection(SpotifyCollection.RECENT)
    drain(work, ui)
    state = view.set_browse_state.call_args.args[0]
    assert state.tracks == service.load_recently_played.return_value
    assert state.collection is SpotifyCollection.RECENT
    view.set_browse_artwork.assert_called_once_with("recent-art", b"recent-art")


@pytest.mark.parametrize("retire", ["deactivate", "close"])
def test_retired_browser_drops_completions_and_requests(setup_browser, retire):
    session, service, player, view, work, ui, _, show_now, dispatcher = setup_browser
    session.request_collection(SpotifyCollection.LIKED)
    work.pop(0)()
    getattr(session, retire)()
    view.set_browse_state.reset_mock()
    session.request_playback_mode(SpotifyPlaybackMode.PLAYER)
    session.request_play_track("liked-uri")
    drain(work, ui)
    view.set_browse_state.assert_not_called()
    view.set_browse_artwork.assert_not_called()
    service.request_play_track.assert_not_called()
    player.request_player.assert_not_called()
    show_now.assert_not_called()
    dispatcher.cancel_ui_callback.assert_called()
    view.set_browse_request_handler.assert_called_with(None)


def test_cached_collection_avoids_library_worker(setup_browser):
    session, service, _, view, work, ui, _, _, _ = setup_browser
    service.cached_saved_tracks.return_value = service.load_saved_tracks.return_value
    session.request_collection(SpotifyCollection.LIKED)
    assert view.set_browse_state.call_args.args[0].tracks == service.load_saved_tracks.return_value
    drain(work, ui)
    service.load_saved_tracks.assert_not_called()


def test_playlist_drilldown_and_back_to_playlists(setup_browser):
    session, service, _, view, work, ui, _, _, _ = setup_browser
    session.request_collection(SpotifyCollection.PLAYLISTS)
    drain(work, ui)
    session.request_playlist("playlist-id")
    drain(work, ui)
    state = view.set_browse_state.call_args.args[0]
    assert state.collection is SpotifyCollection.PLAYLIST
    assert state.title == "PLAYLIST"
    assert state.tracks == service.load_playlist_tracks.return_value
    service.load_playlist_tracks.assert_called_once_with("playlist-id", limit=18)
    session.request_collection(SpotifyCollection.PLAYLISTS)
    drain(work, ui)
    assert view.set_browse_state.call_args.args[0].collection is SpotifyCollection.PLAYLISTS


def test_play_request_only_accepts_displayed_track(setup_browser):
    session, service, _, _, work, ui, _, show_now, _ = setup_browser
    session.request_collection(SpotifyCollection.LIKED)
    drain(work, ui)
    session.request_play_track("unknown")
    service.request_play_track.assert_not_called()
    session.request_play_track("liked-uri")
    service.request_play_track.assert_called_once_with("liked-uri")
    show_now.assert_called_once_with()


def test_playback_destination_guards_busy_and_unavailable_player(setup_browser):
    session, service, player, view, _, _, _, _, _ = setup_browser
    player.state.return_value = SpotifyLocalPlayerState(available=False)
    session.request_playback_mode(SpotifyPlaybackMode.PLAYER)
    player.request_player.assert_not_called()
    player.state.return_value = SpotifyLocalPlayerState(available=True, busy=True)
    session.request_playback_mode(SpotifyPlaybackMode.REMOTE)
    player.request_remote.assert_not_called()
    player.state.return_value = SpotifyLocalPlayerState(available=True)
    session.request_playback_mode(SpotifyPlaybackMode.PLAYER)
    player.request_player.assert_called_once_with()
    service.request_refresh.assert_called_once_with()


def test_offline_discards_library_completion_and_actions(setup_browser):
    session, service, _, view, work, ui, online, _, _ = setup_browser
    session.request_collection(SpotifyCollection.LIKED)
    work.pop(0)()
    online[0] = False
    session._tick()
    drain(work, ui)
    state = view.set_browse_state.call_args.args[0]
    assert not state.tracks
    assert not state.loading
    assert "Offline" in state.message
    session.request_play_track("liked-uri")
    service.request_play_track.assert_not_called()


def test_library_failure_is_presented_and_superseded_error_is_ignored(setup_browser):
    session, service, _, view, work, ui, _, _, _ = setup_browser
    service.load_saved_tracks.side_effect = RuntimeError("failed")
    session.request_collection(SpotifyCollection.LIKED)
    drain(work, ui)
    assert "failed" in view.set_browse_state.call_args.args[0].message
    assert not view.set_browse_state.call_args.args[0].loading
    session.request_collection(SpotifyCollection.LIKED)
    work.pop(0)()
    session.request_collection(SpotifyCollection.RECENT)
    drain(work, ui)
    assert not view.set_browse_state.call_args.args[0].message


def test_artwork_for_previous_collection_cannot_reach_new_cards(setup_browser):
    session, _, _, view, work, ui, _, _, _ = setup_browser
    session.request_collection(SpotifyCollection.LIKED)
    work.pop(0)()
    ui.pop(0)()
    work.pop(0)()
    session.request_collection(SpotifyCollection.NOW)
    drain(work, ui)
    view.set_browse_artwork.assert_not_called()


def test_closed_browser_cannot_reactivate(setup_browser):
    session, _, _, view, _, _, _, _, _ = setup_browser
    session.close()
    with pytest.raises(RuntimeError, match="closed"):
        session.activate(view)
