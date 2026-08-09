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


class SpotifyMediaPresenter(
    PlaybackRequestHandlerIf,
    TrackRequestHandlerIf,
    SeekRequestHandlerIf,
    VolumeRequestHandlerIf,
):
    """Bridge a Spotify backend to a toolkit-independent media UI."""

    def __init__(self, backend: SpotifyControllerIf, media_ui: MediaUiIf) -> None:
        self._backend = backend
        self._media_ui = media_ui
        self._latest_state: MediaState | None = None

    def refresh(self) -> MediaState:
        """Read and publish the latest Spotify playback state."""
        try:
            state = self._to_media_state(self._backend.current_state())
        except Exception as exc:
            state = MediaState(
                availability=MediaAvailability.ERROR,
                status_message=f"Spotify error: {exc}",
            )

        self._latest_state = state
        self._media_ui.set_media_state(state)
        return state

    def request_play(self) -> None:
        state = self.refresh()
        if state.playback is not PlaybackState.PLAYING:
            self._run_request(self._backend.play_pause)

    def request_pause(self) -> None:
        state = self.refresh()
        if state.playback is PlaybackState.PLAYING:
            self._run_request(self._backend.play_pause)

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
        self._run_request(
            lambda: self._backend.set_volume_percent(clamped_volume)
        )

    def _state_with_position(self) -> MediaState:
        state = self._latest_state
        if state is None or state.position_s is None:
            state = self.refresh()
        return state

    def _run_request(self, request: Callable[[], None]) -> None:
        try:
            request()
        except Exception as exc:
            error_state = MediaState(
                availability=MediaAvailability.ERROR,
                status_message=f"Spotify request failed: {exc}",
            )
            self._latest_state = error_state
            self._media_ui.set_media_state(error_state)
            raise
        else:
            self.refresh()

    @staticmethod
    def _to_media_state(state: SpotifyState) -> MediaState:
        if state.configuration_required:
            availability = MediaAvailability.CONFIGURATION_REQUIRED
        elif state.is_available:
            availability = MediaAvailability.AVAILABLE
        else:
            availability = MediaAvailability.UNAVAILABLE

        playback = (
            PlaybackState.PLAYING if state.is_playing else PlaybackState.PAUSED
        )
        return MediaState(
            availability=availability,
            playback=playback,
            title=state.track_name,
            artist=state.artist_name,
            album=state.album_name,
            artwork_uri=state.album_art_url,
            media_uri=state.track_uri,
            position_s=(
                state.progress_ms / 1000.0
                if state.progress_ms is not None
                else None
            ),
            duration_s=(
                state.duration_ms / 1000.0
                if state.duration_ms is not None
                else None
            ),
            volume_percent=state.volume_percent,
            device_name=state.device_name,
            status_message=state.status_message,
        )
