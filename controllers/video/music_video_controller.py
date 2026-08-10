from __future__ import annotations

from controllers.spotify.spotify_controller_if import SpotifyControllerIf
from controllers.video.music_video_if import MusicVideoIf
from controllers.video.music_video_types import MusicVideo, MusicVideoQuery
from controllers.video.spotify_music_video_mapper import (
    SpotifyMusicVideoMapper,
)


class MusicVideoController:
    """Coordinate Spotify playback with music-video playback."""

    def __init__(
        self,
        spotify_controller: SpotifyControllerIf,
        music_video: MusicVideoIf,
    ) -> None:
        self._spotify_controller = spotify_controller
        self._music_video = music_video

        self._spotify_resume_position_ms = 0
        self._spotify_was_playing = False
        self._prepared_query: MusicVideoQuery | None = None
        self._prepared_video: MusicVideo | None = None

    def current_track_has_video(self) -> bool:
        """Find and cache a video match for the current Spotify track.

        @return `True` when the current track has a matching video.
        """
        query = self._current_query()
        if query is None:
            self._prepared_query = None
            self._prepared_video = None
            return False
        if query != self._prepared_query:
            self._prepared_query = query
            self._prepared_video = self._music_video.find_video(query)
        return self._prepared_video is not None

    def watch_current_track(self) -> bool:
        """Find and play a video for the current Spotify track."""
        state = self._spotify_controller.current_state()
        query = SpotifyMusicVideoMapper.create_query(state)
        if query is None:
            return False

        if query != self._prepared_query:
            self._prepared_query = query
            self._prepared_video = self._music_video.find_video(query)
        video = self._prepared_video

        if video is None:
            return False

        self._spotify_resume_position_ms = max(0, state.progress_ms or 0)
        self._spotify_was_playing = state.is_playing

        if self._spotify_was_playing:
            self._spotify_controller.pause()

        try:
            started = self._music_video.play_video(
                video,
                position_ms=self._spotify_resume_position_ms,
            )
        except Exception:
            self._restore_spotify_after_start_failure()
            raise

        if not started:
            self._restore_spotify_after_start_failure()

        return started

    def stop_video(self) -> None:
        """Stop video playback without changing Spotify playback."""
        self._music_video.stop_video()

    def return_to_spotify(self) -> None:
        """Stop the video and restore the saved Spotify playback state."""
        self._music_video.stop_video()

        self._spotify_controller.seek_to_position_ms(
            self._spotify_resume_position_ms
        )

        if self._spotify_was_playing:
            self._spotify_controller.play()
        else:
            self._spotify_controller.pause()

    def is_video_active(self) -> bool:
        """Return whether a music video is currently active."""
        return self._music_video.is_video_active()

    def _current_query(self) -> MusicVideoQuery | None:
        state = self._spotify_controller.current_state()
        if not state.is_available:
            return None
        return SpotifyMusicVideoMapper.create_query(state)

    def _restore_spotify_after_start_failure(self) -> None:
        if self._spotify_was_playing:
            self._spotify_controller.play()
