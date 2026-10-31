"""Focused song-launch contract tests."""
import pytest

from controllers.media.song_launch_controller import SongLaunchController
from ui.media.song_launch import SongDestination, SongLaunchRequest


def test_song_request_is_immutable_and_normalized_for_search():
    request = SongLaunchRequest("  Loving Life Again  ", " Ella Langley ", SongDestination.YOUTUBE)
    assert request.search_text == "Ella Langley Loving Life Again"
    with pytest.raises(AttributeError):
        request.title = "Changed"


def test_song_launch_routes_to_requested_provider_only():
    opened = []
    controller = SongLaunchController(
        open_spotify_search=lambda text: opened.append(("spotify", text)),
        open_youtube_search=lambda text: opened.append(("youtube", text)),
    )
    controller.launch_song(SongLaunchRequest("Loving Life Again", "Ella Langley", SongDestination.YOUTUBE))
    assert opened == [("youtube", "Ella Langley Loving Life Again")]


def test_unavailable_destination_fails_without_fallback():
    controller = SongLaunchController(open_spotify_search=lambda _: None, open_youtube_search=lambda _: None)
    with pytest.raises(ValueError, match="unavailable"):
        controller.launch_song(SongLaunchRequest("Song", "Artist", SongDestination.YOUTUBE_MUSIC))


@pytest.mark.parametrize("title,artist", [("", "Artist"), ("Song", "  ")])
def test_missing_song_identity_rejected(title, artist):
    with pytest.raises(ValueError):
        SongLaunchRequest(title, artist, SongDestination.SPOTIFY)
