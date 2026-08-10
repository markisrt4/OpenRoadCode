from __future__ import annotations

from controllers.spotify.spotify_state import SpotifyState
from controllers.video.music_video_types import MusicVideoQuery


class SpotifyMusicVideoMapper:
    """Convert a Spotify playback snapshot into a music-video query."""

    @staticmethod
    def create_query(state: SpotifyState) -> MusicVideoQuery | None:
        """Create a query when the state contains usable track metadata."""
        if not state.artist_name or not state.track_name:
            return None

        return MusicVideoQuery(
            artist=state.artist_name,
            title=state.track_name,
            album=state.album_name,
            duration_ms=state.duration_ms,
        )
