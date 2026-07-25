import time

from controllers.spotify.spotify_controller_if import SpotifyControllerIf
from controllers.spotify.spotify_state import SpotifyState


class MockSpotifyController(SpotifyControllerIf):
    """Deterministic in-memory Spotify controller for demos and development."""
    def __init__(self) -> None:
        self._tracks = [
            ("Tom Sawyer", "Rush", "Moving Pictures", 276_000),
            ("Go For Soda", "Kim Mitchell", "Akimbo Alogo", 202_000),
            ("Carry On Wayward Son", "Kansas", "Leftoverture", 323_000),
            ("Subdivisions", "Rush", "Signals", 334_000),
        ]

        self._track_index = 0
        self._is_playing = True
        self._volume_percent = 70
        self._track_started_at = time.monotonic()
        self._paused_progress_ms = 0

    def current_state(self) -> SpotifyState:
        track_name, artist_name, album_name, duration_ms = self._tracks[self._track_index]

        progress_ms = self._current_progress_ms(duration_ms)

        return SpotifyState(
            is_available=True,
            is_playing=self._is_playing,
            track_name=track_name,
            artist_name=artist_name,
            album_name=album_name,
            device_name="Mock Phone",
            volume_percent=self._volume_percent,
            progress_ms=progress_ms,
            duration_ms=duration_ms,
            status_message="Playing" if self._is_playing else "Paused",
        )

    def play_pause(self) -> None:
        if self._is_playing:
            _, _, _, duration_ms = self._tracks[self._track_index]
            self._paused_progress_ms = self._current_progress_ms(duration_ms)
            self._is_playing = False
            return

        self._track_started_at = time.monotonic() - (self._paused_progress_ms / 1000.0)
        self._is_playing = True

    def next_track(self) -> None:
        self._track_index = (self._track_index + 1) % len(self._tracks)
        self._reset_progress()

    def previous_track(self) -> None:
        self._track_index = (self._track_index - 1) % len(self._tracks)
        self._reset_progress()

    def set_volume_percent(self, volume_percent: int) -> None:
        self._volume_percent = max(0, min(100, volume_percent))

    def _reset_progress(self) -> None:
        self._track_started_at = time.monotonic()
        self._paused_progress_ms = 0

    def _current_progress_ms(self, duration_ms: int) -> int:
        if not self._is_playing:
            return self._paused_progress_ms

        elapsed_ms = int((time.monotonic() - self._track_started_at) * 1000)

        if elapsed_ms >= duration_ms:
            self.next_track()
            return 0

        return elapsed_ms

    def seek_to_position_ms(self, position_ms: int) -> None:
        _, _, _, duration_ms = self._tracks[self._track_index]

        position_ms = max(
            0,
            min(duration_ms, position_ms),
        )

        self._paused_progress_ms = position_ms

        if self._is_playing:
            self._track_started_at = (
                time.monotonic() - (position_ms / 1000.0)
            )
