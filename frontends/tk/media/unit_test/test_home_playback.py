# SPDX-License-Identifier: MIT
"""Home transport routing and retirement without an X display."""

from unittest.mock import Mock

from frontends.tk.media.spotify_now_playing import SpotifyNowPlaying


def view():
    panel = object.__new__(SpotifyNowPlaying)
    panel._closed = False
    panel._handler = None
    panel._playing = False
    panel._can_control = True
    panel._transport = [Mock(), Mock(), Mock()]
    return panel


def test_home_transport_routes_to_bound_contract_and_tracks_pause_state():
    panel, handler = view(), Mock()
    panel.set_spotify_request_handler(handler)
    panel._request_transport("previous")
    panel._request_transport("play")
    panel._request_transport("next")
    handler.request_previous_track.assert_called_once()
    handler.request_play.assert_called_once()
    handler.request_next_track.assert_called_once()
    panel._playing = True
    panel._request_transport("play")
    handler.request_pause.assert_called_once()


def test_retired_offline_and_destroyed_home_controls_do_not_emit():
    panel, handler = view(), Mock()
    panel.set_spotify_request_handler(handler)
    panel.set_spotify_request_handler(None)
    panel._request_transport("play")
    panel.set_spotify_request_handler(handler)
    panel._can_control = False
    panel._request_transport("next")
    panel._can_control = True
    panel._closed = True
    panel._request_transport("previous")
    assert not handler.mock_calls
