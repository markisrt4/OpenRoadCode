# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Adapt Spotify controller state and commands to generic media UI contracts."""

from __future__ import annotations

from collections.abc import Callable

from controllers.spotify.spotify_controller_if import SpotifyControllerIf
from controllers.spotify.spotify_state import SpotifyState
from ui.media import (
    MediaAvailability,
    MediaState,
    MediaUiIf,
    PlaybackRequestHandlerIf,
    PlaybackState,
    SeekRequestHandlerIf,
    TrackRequestHandlerIf,
    VolumeRequestHandlerIf,
)


class SpotifyMediaPresenter(PlaybackRequestHandlerIf, TrackRequestHandlerIf, SeekRequestHandlerIf, VolumeRequestHandlerIf):
    """Bridge a Spotify backend to a toolkit-independent media UI."""

    def __init__(self, backend: SpotifyControllerIf, media_ui: MediaUiIf, fallback_volume_handler: VolumeRequestHandlerIf | None = None) -> None:
        self._backend = backend
        self._media_ui = media_ui
        self._fallback_volume_handler = fallback_volume_handler
        self._latest_state: MediaState | None = None

    def refresh(self) -> MediaState:
        state = self.read_state()
        self._media_ui.set_media_state(state)
        return state

    def read_state(self) -> MediaState:
        try:
            state = self._to_media_state(self._backend.current_state())
        except Exception as exc:
            state = MediaState(availability=MediaAvailability.ERROR, status_message=f"Spotify error: {exc}")
        self._latest_state = state
        return state

    def request_play(self) -> None:
        self._run_request(self._backend.play)

    def request_pause(self) -> None:
        self._run_request(self._backend.pause)

    def request_previous_track(self) -> None:
        self._run_request(self._backend.previous_track)

    def request_next_track(self) -> None:
        self._run_request(self._backend.next_track)

    def request_rewind(self, seconds: float) -> None:
        state = self._state_with_position()
        self.request_seek(max(0.0, (state.position_s or 0.0) - seconds))

    def request_forward(self, seconds: float) -> None:
        state = self._state_with_position()
        self.request_seek((state.position_s or 0.0) + seconds)

    def request_seek(self, position_s: float) -> None:
        position_ms = int(max(0.0, position_s) * 1000.0)
        self._run_request(lambda: self._backend.seek_to_position_ms(position_ms))

    def request_volume(self, volume_percent: int) -> None:
        clamped_volume = max(0, min(100, volume_percent))
        try:
            self._backend.set_volume_percent(clamped_volume)
        except Exception as exc:
            fallback = self._fallback_volume_handler
            if fallback is None or "VOLUME_CONTROL_DISALLOW" not in str(exc):
                self._publish_request_error(exc)
                raise
            fallback.request_volume(clamped_volume)

    def _state_with_position(self) -> MediaState:
        state = self._latest_state
        if state is None or state.position_s is None:
            state = self.refresh()
        return state

    def _run_request(self, request: Callable[[], None]) -> None:
        try:
            request()
        except Exception as exc:
            self._publish_request_error(exc)
            raise

    def _publish_request_error(self, error: Exception) -> None:
        error_state = MediaState(availability=MediaAvailability.ERROR, status_message=f"Spotify request failed: {error}")
        self._latest_state = error_state
        self._media_ui.set_media_state(error_state)

    @staticmethod
    def _to_media_state(state: SpotifyState) -> MediaState:
        if state.configuration_required:
            availability = MediaAvailability.CONFIGURATION_REQUIRED
        elif state.is_available:
            availability = MediaAvailability.AVAILABLE
        else:
            availability = MediaAvailability.UNAVAILABLE
        playback = PlaybackState.PLAYING if state.is_playing else PlaybackState.PAUSED
        return MediaState(
            availability=availability,
            playback=playback,
            title=state.track_name,
            artist=state.artist_name,
            album=state.album_name,
            artwork_uri=state.album_art_url,
            media_uri=state.track_uri,
            position_s=state.progress_ms / 1000.0 if state.progress_ms is not None else None,
            duration_s=state.duration_ms / 1000.0 if state.duration_ms is not None else None,
            volume_percent=state.volume_percent,
            supports_volume=state.supports_volume,
            device_name=state.device_name,
            status_message=state.status_message,
        )
