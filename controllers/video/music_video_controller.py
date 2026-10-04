# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging

from common.logging.structured import current_operation, event, operation

from controllers.spotify.spotify_controller_if import SpotifyControllerIf
from controllers.video.music_video_if import MusicVideoIf
from controllers.video.music_video_types import MusicVideo, MusicVideoQuery
from controllers.video.spotify_music_video_mapper import (
    SpotifyMusicVideoMapper,
)

LOGGER = logging.getLogger("media.video")


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
            self._prepared_video = self._find_video(query)
        return self._prepared_video is not None

    def watch_current_track(self) -> bool:
        """Find and play a video for the current Spotify track."""
        with operation(current_operation()):
            event(LOGGER, logging.INFO, "video.requested", "Music video requested")
            try:
                started = self._watch_current_track()
            except Exception as error:
                event(
                    LOGGER,
                    logging.ERROR,
                    "video.failed",
                    "Music video launch failed",
                    exception_type=type(error).__name__,
                )
                raise
            event(
                LOGGER,
                logging.INFO,
                "video.launch_completed" if started else "video.not_started",
                "Music video launch completed" if started else "Music video did not start",
            )
            return started

    def _watch_current_track(self) -> bool:
        state = self._spotify_controller.current_state()
        query = SpotifyMusicVideoMapper.create_query(state)
        if query is None:
            return False

        if query != self._prepared_query:
            self._prepared_query = query
            self._prepared_video = self._find_video(query)
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
        with operation(current_operation()):
            try:
                active = self._music_video.is_video_active()
                self._music_video.stop_video()
            except Exception as error:
                event(
                    LOGGER,
                    logging.ERROR,
                    "video.stop_failed",
                    "Music video stop failed",
                    exception_type=type(error).__name__,
                )
                raise
            if active:
                event(LOGGER, logging.INFO, "video.stopped", "Music video stopped")

    def return_to_spotify(self) -> None:
        """Stop the video and restore the saved Spotify playback state."""
        with operation(current_operation()):
            try:
                self._return_to_spotify()
            except Exception as error:
                event(
                    LOGGER,
                    logging.ERROR,
                    "video.return_failed",
                    "Return to Spotify failed",
                    exception_type=type(error).__name__,
                )
                raise
            event(LOGGER, logging.INFO, "video.return_completed", "Spotify playback state restored")

    def _return_to_spotify(self) -> None:
        self.stop_video()

        self._spotify_controller.seek_to_position_ms(self._spotify_resume_position_ms)

        if self._spotify_was_playing:
            self._spotify_controller.play()
        else:
            self._spotify_controller.pause()

    def is_video_active(self) -> bool:
        """Return whether a music video is currently active."""
        return self._music_video.is_video_active()

    def _find_video(self, query: MusicVideoQuery) -> MusicVideo | None:
        with operation(current_operation()):
            event(LOGGER, logging.DEBUG, "video.lookup_started", "Music video lookup started")
            try:
                video = self._music_video.find_video(query)
            except Exception as error:
                event(
                    LOGGER,
                    logging.ERROR,
                    "video.lookup_failed",
                    "Music video lookup failed",
                    exception_type=type(error).__name__,
                )
                raise
            event(
                LOGGER,
                logging.INFO,
                "video.lookup_completed",
                "Music video lookup completed",
                matched=video is not None,
            )
            return video

    def _current_query(self) -> MusicVideoQuery | None:
        state = self._spotify_controller.current_state()
        if not state.is_available:
            return None
        return SpotifyMusicVideoMapper.create_query(state)

    def _restore_spotify_after_start_failure(self) -> None:
        if self._spotify_was_playing:
            self._spotify_controller.play()
