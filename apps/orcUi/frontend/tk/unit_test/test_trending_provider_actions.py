"""Trending routes provider launch failures through the shell notification callback."""

from unittest.mock import Mock

import pytest

from apps.orcUi.frontend.tk.trending_radio_panel import TrendingRadioPanel
from ui.media.artist_profile import ArtistProfile
from ui.media.song_launch import SongDestination


def test_artist_selection_displays_loading_before_request():
    panel = Mock(_spotify_pane=None)
    song = {"artist": "Burl Ives"}

    TrendingRadioPanel._select(panel, song)

    assert [call[0] for call in panel.mock_calls] == [
        "_render",
        "_track_details.show_loading",
        "_on_artist_selected",
    ]


def test_selecting_song_while_spotify_is_open_restores_track_details():
    panel = Mock(_spotify_pane=Mock())
    song = {"artist": "Burl Ives"}

    TrendingRadioPanel._select(panel, song)

    panel._restore_track_details.assert_called_once_with()
    assert panel._selected == song


def test_late_artist_profile_is_ignored_after_selection_changes():
    panel = Mock(_kind="artists", _selected={"artist": "Elton John"})
    profile = ArtistProfile("Burl Ives", "American singer", "https://example.test")

    TrendingRadioPanel.set_artist_profile(panel, "Burl Ives", profile)

    panel._track_details.set_profile.assert_not_called()


def test_spotify_song_opens_in_the_left_trending_pane():
    panel = Mock(
        _kind="songs",
        _selected={"artist": "Burl Ives", "title": "A Song"},
        _video_pane=None,
        _spotify_pane=None,
    )

    TrendingRadioPanel._open_spotify(panel)

    panel._spotify_factory.assert_called_once_with(
        panel._left, "Burl Ives", "A Song"
    )
    panel._spotify_factory.return_value.grid.assert_called_once_with(
        row=0, column=0, sticky="nsew"
    )
    panel._on_artist_search.assert_not_called()


@pytest.mark.parametrize(
    ("action", "destination"),
    [
        (TrendingRadioPanel._play_selected, SongDestination.YOUTUBE),
        (TrendingRadioPanel._open_spotify, SongDestination.SPOTIFY),
    ],
)
def test_artist_selection_opens_provider_search(action, destination):
    panel = Mock(_kind="artists", _selected={"artist": "Burl Ives"})

    action(panel)

    panel._on_artist_search.assert_called_once_with(destination, "Burl Ives")


@pytest.mark.parametrize(("provider", "title"), [("youtube", "YouTube"), ("spotify", "Spotify")])
def test_provider_action_reports_launch_failure(provider, title):
    panel = Mock()
    action = Mock(side_effect=RuntimeError("Player could not open"))

    TrendingRadioPanel._invoke_provider(panel, provider, action)

    action.assert_called_once_with()
    panel._on_media_error.assert_called_once_with(title, "Player could not open")
