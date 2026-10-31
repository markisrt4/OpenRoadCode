"""Route discovered songs to existing provider search experiences."""
from __future__ import annotations

from collections.abc import Callable

from ui.media.song_launch import SongDestination, SongLaunchRequest


class SongLaunchController:
    """Transport-free song routing. Providers own search and playback permissions."""

    def __init__(
        self,
        *,
        open_spotify_search: Callable[[str], None],
        open_youtube_search: Callable[[str], None],
        open_youtube_music_search: Callable[[str], None] | None = None,
    ) -> None:
        self._handlers = {
            SongDestination.SPOTIFY: open_spotify_search,
            SongDestination.YOUTUBE: open_youtube_search,
        }
        if open_youtube_music_search is not None:
            self._handlers[SongDestination.YOUTUBE_MUSIC] = open_youtube_music_search

    def launch_song(self, request: SongLaunchRequest) -> None:
        try:
            handler = self._handlers[request.destination]
        except KeyError as exc:
            raise ValueError(f"Song destination unavailable: {request.destination}") from exc
        handler(request.search_text)
