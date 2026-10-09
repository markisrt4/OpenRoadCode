# SPDX-License-Identifier: MIT

"""Exercise browser contracts and lifecycle without Tk, network, or audio processes."""

from collections import deque
from dataclasses import replace
from unittest.mock import Mock

import pytest

from controllers.radio.streaming_radio_browser import StreamingRadioBrowser
from controllers.radio.streaming_radio_backend_if import StreamingRadioBackendIf, StreamingRadioFavoritesIf
from controllers.radio.streaming_radio_directory_if import StreamingRadioDirectoryIf
from ui.radio.streaming_radio_session_if import StreamingRadioUiIf
from ui.radio.streaming_radio_state import StreamingRadioBrowseMode as Mode, StreamingRadioPlaybackState
from ui.radio.streaming_radio_types import StreamingRadioStation


@pytest.fixture
def browser():
    station = StreamingRadioStation("one", "Station One", "https://radio.test/one",
                                    artwork_url="https://radio.test/art.png")
    directory = Mock(spec=StreamingRadioDirectoryIf)
    directory.stations_near.return_value = (station,)
    directory.stations_by_region.return_value = ()
    directory.stations_by_ids.return_value = (station,)
    playback = Mock(spec=StreamingRadioBackendIf)
    playback.snapshot.return_value = StreamingRadioPlaybackState()
    favorites = Mock(spec=StreamingRadioFavoritesIf)
    favorites.station_ids = frozenset()
    favorites.ordered_station_ids = ()
    def toggle(station_id):
        ids = set(favorites.station_ids)
        ids.symmetric_difference_update((station_id,))
        favorites.station_ids = frozenset(ids)
        favorites.ordered_station_ids = tuple(sorted(ids))
        return station_id in ids
    favorites.toggle.side_effect = toggle
    work, ui = deque(), deque()
    artwork = Mock(return_value=b"image bytes")
    view = Mock(spec=StreamingRadioUiIf)
    session = StreamingRadioBrowser(
        directory, playback, favorites, run_work=work.append, run_ui=ui.append,
        load_artwork=artwork,
    )
    session.activate(view)
    return session, directory, playback, favorites, artwork, view, work, ui, station


def drain(queue):
    while queue:
        queue.popleft()()


def loaded(browser):
    drain(browser[6])
    drain(browser[7])
    return browser[5].set_streaming_state.call_args.args[0]


def test_directory_worker_delivers_immutable_state_only_through_dispatch(browser):
    session, directory, playback, favorites, artwork, view, work, ui, station = browser
    view.set_streaming_request_handler.assert_called_once_with(session)
    assert view.set_streaming_state.call_args.args[0].loading
    view.reset_mock()
    drain(work)
    assert not view.mock_calls
    drain(ui)
    state = view.set_streaming_state.call_args.args[0]
    assert state.stations == (station,)
    assert not state.loading
    with pytest.raises(AttributeError):
        state.loading = True
    directory.stations_near.assert_called_once_with(
        latitude=42.3314, longitude=-83.0458, radius_km=80.0,
        state="Michigan", country_code="US", limit=50,
    )


def test_latest_mode_wins_when_directory_results_arrive_out_of_order(browser):
    session, directory, playback, favorites, artwork, view, work, ui, station = browser
    session.request_mode(Mode.REGIONAL)
    local, regional = work.popleft(), work.popleft()
    regional()
    local()
    drain(ui)
    state = view.set_streaming_state.call_args.args[0]
    assert state.mode is Mode.REGIONAL and state.stations == ()


def test_hide_before_worker_starts_drops_directory_and_queued_playback(browser):
    session, directory, playback, favorites, artwork, view, work, ui, station = browser
    session.deactivate()
    view.set_streaming_request_handler.assert_called_with(None)
    view.reset_mock()
    drain(work)
    drain(ui)
    directory.stations_near.assert_not_called()
    assert not view.mock_calls
    assert not playback.stop.called


def test_close_drops_directory_results_already_queued(browser):
    session, directory, playback, favorites, artwork, view, work, ui, station = browser
    drain(work)
    session.close()
    view.reset_mock()
    drain(ui)
    assert not view.mock_calls
    playback.stop.assert_not_called()
    session.close()
    with pytest.raises(RuntimeError, match="closed"):
        session.activate(view)


def test_favorites_resolve_persisted_identifiers_in_user_order(browser):
    session, directory, playback, favorites, artwork, view, work, ui, station = browser
    favorites.station_ids = frozenset(("two", "one"))
    favorites.ordered_station_ids = ("two", "one")
    session.request_mode(Mode.FAVORITES)
    loaded(browser)
    directory.stations_by_ids.assert_called_once_with(("two", "one"))
    assert view.set_streaming_state.call_args.args[0].favorite_station_ids == frozenset(("two", "one"))


def test_empty_favorites_do_not_issue_directory_request(browser):
    browser[0].request_mode(Mode.FAVORITES)
    state = loaded(browser)
    browser[1].stations_by_ids.assert_not_called()
    assert state.stations == () and not state.loading


def test_directory_failure_is_reported_as_display_state(browser):
    browser[1].stations_near.side_effect = OSError("unreachable")
    state = loaded(browser)
    assert state.error and not state.loading and not state.stations
    assert "unreachable" in state.message


def test_playback_requests_are_serialized_and_duplicate_requests_are_ignored(browser):
    session, directory, playback, favorites, artwork, view, work, ui, station = browser
    loaded(browser)
    session.request_play("one")
    session.request_play("one")
    session.request_stop()
    assert len(work) == 1
    assert view.set_streaming_state.call_args.args[0].playback_busy
    playback.play.side_effect = lambda item: setattr(playback.snapshot, "return_value", StreamingRadioPlaybackState(item, True))
    loaded(browser)
    playback.play.assert_called_once_with(station)
    assert view.set_streaming_state.call_args.args[0].playback.is_playing
    session.request_stop()
    loaded(browser)
    playback.stop.assert_called_once()


def test_hidden_play_request_that_has_not_started_has_no_effect(browser):
    loaded(browser)
    browser[0].request_play("one")
    browser[0].deactivate()
    browser[5].reset_mock()
    drain(browser[6])
    drain(browser[7])
    browser[2].play.assert_not_called()
    assert not browser[5].mock_calls


def test_old_playback_completion_cannot_release_new_session_busy_state(browser):
    session, directory, playback, favorites, artwork, view, work, ui, station = browser
    loaded(browser)
    session.request_play("one")
    drain(work)  # Old completion is queued.
    session.deactivate()
    next_view = Mock(spec=StreamingRadioUiIf)
    session.activate(next_view)
    session.request_play("one")
    drain(ui)  # Old completion must not publish or clear the new pending request.
    assert next_view.set_streaming_state.call_args.args[0].playback_busy
    drain(work)
    drain(ui)
    assert not next_view.set_streaming_state.call_args.args[0].playback_busy


def test_playback_failure_does_not_leave_browser_busy(browser):
    loaded(browser)
    browser[2].play.side_effect = OSError("no player")
    browser[0].request_play("one")
    state = loaded(browser)
    assert state.error and not state.playback_busy
    assert "no player" in state.message


def test_in_flight_playback_can_finish_after_hide_without_touching_view(browser):
    session, directory, playback, favorites, artwork, view, work, ui, station = browser
    loaded(browser)
    def play(item):
        session.deactivate()
        playback.snapshot.return_value = StreamingRadioPlaybackState(item, True)
    playback.play.side_effect = play
    session.request_play("one")
    drain(work)
    view.reset_mock()
    drain(ui)
    assert not view.mock_calls
    assert playback.snapshot().is_playing
    playback.stop.assert_not_called()


def test_favorite_save_runs_on_worker_and_failure_preserves_membership(browser):
    session, directory, playback, favorites, artwork, view, work, ui, station = browser
    loaded(browser)
    favorites.toggle.side_effect = OSError("disk full")
    session.request_toggle_favorite("one")
    session.request_toggle_favorite("one")
    favorites.toggle.assert_not_called()
    state = loaded(browser)
    favorites.toggle.assert_called_once_with("one")
    assert state.favorite_station_ids == frozenset()
    assert state.error and "disk full" in state.message


def test_favorite_mode_reloads_current_metadata_after_membership_change(browser):
    session, directory, playback, favorites, artwork, view, work, ui, station = browser
    loaded(browser)
    session.request_toggle_favorite("one")
    loaded(browser)
    assert view.set_streaming_state.call_args.args[0].favorite_station_ids == frozenset(("one",))
    session.request_mode(Mode.FAVORITES)
    loaded(browser)
    session.request_toggle_favorite("one")
    loaded(browser)
    loaded(browser)  # Membership change queued another directory load.
    assert not view.set_streaming_state.call_args.args[0].stations


def test_artwork_download_is_deduplicated_and_never_delivered_after_close(browser):
    session, directory, playback, favorites, artwork, view, work, ui, station = browser
    loaded(browser)
    session.request_artwork("one")
    session.request_artwork("one")
    assert len(work) == 1
    drain(work)
    session.close()
    drain(ui)
    artwork.assert_called_once_with(station.artwork_url)
    view.set_station_artwork.assert_not_called()


def test_cached_artwork_is_reused_but_old_url_result_is_rejected(browser):
    session, directory, playback, favorites, artwork, view, work, ui, station = browser
    loaded(browser)
    session.request_artwork("one")
    loaded(browser)
    session.request_artwork("one")
    artwork.assert_called_once()
    assert view.set_station_artwork.call_count == 2
    session.request_mode(Mode.REGIONAL)
    directory.stations_by_region.return_value = (replace(station, artwork_url="https://radio.test/new.png"),)
    loaded(browser)
    session.request_artwork("one")
    loaded(browser)
    assert artwork.call_count == 2
    assert artwork.call_args.args == ("https://radio.test/new.png",)


def test_artwork_failure_keeps_placeholder_and_invalid_station_requests_are_ignored(browser):
    session, directory, playback, favorites, artwork, view, work, ui, station = browser
    loaded(browser)
    artwork.side_effect = OSError("bad image")
    session.request_artwork("one")
    loaded(browser)
    view.set_station_artwork.assert_not_called()
    session.request_artwork("unknown")
    session.request_play("unknown")
    session.request_toggle_favorite("unknown")
    assert not work


def test_pending_favorite_and_artwork_work_are_dropped_on_hide(browser):
    loaded(browser)
    browser[0].request_artwork("one")
    browser[0].request_toggle_favorite("one")
    browser[0].deactivate()
    drain(browser[6])
    drain(browser[7])
    browser[3].toggle.assert_not_called()
    browser[4].assert_not_called()
