# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Callable
import threading

from ui.radio.streaming_radio_state import StreamingRadioPlaybackState

from controllers.audio.streaming_audio_player_if import StreamingAudioPlayerIf
from ui.radio.streaming_radio_types import (StreamingRadioStation)


class StreamingRadioController:
    """Coordinate streaming-radio station selection and audio playback."""

    def __init__(self, audio_player: StreamingAudioPlayerIf) -> None:
        self._audio_player = audio_player
        self._network_allowed: Callable[[], bool] = lambda: True
        self._current_station: StreamingRadioStation | None = None
        self._operation_lock = threading.Lock()
        self._close_lock = threading.Lock()
        self._closed = False
        self._snapshot = StreamingRadioPlaybackState()

    def set_network_allowed(self, allowed: Callable[[], bool]) -> None:
        self._network_allowed = allowed

    @property
    def current_station(self) -> StreamingRadioStation | None:
        """Return the station selected for current playback."""

        return self.snapshot().station

    @property
    def is_playing(self) -> bool:
        """Return whether the streaming audio player is currently active."""

        return self.snapshot().is_playing

    def snapshot(self) -> StreamingRadioPlaybackState:
        """Read current playback without waiting for an in-flight native operation."""
        if not self._operation_lock.acquire(blocking=False):
            return self._snapshot
        try:
            self._snapshot = StreamingRadioPlaybackState(
                self._current_station, self._audio_player.is_playing,
            )
            return self._snapshot
        finally:
            self._operation_lock.release()

    def play(self, station: StreamingRadioStation) -> None:
        """Serialize native playback and recheck connectivity after startup."""
        with self._operation_lock:
            if self._closed:
                raise RuntimeError("Streaming radio is closed")
            if not self._network_allowed():
                raise RuntimeError("Internet radio unavailable in offline mode")
            self._audio_player.play(station.stream_url)
            if not self._network_allowed():
                self._audio_player.stop()
                self._current_station = None
                self._snapshot = StreamingRadioPlaybackState()
                raise RuntimeError("Internet radio stopped: offline mode")
            self._current_station = station
            self._snapshot = StreamingRadioPlaybackState(station, self._audio_player.is_playing)

    def stop(self) -> None:
        """Serialize stopping against startup and clear the selected station."""
        with self._operation_lock:
            if self._closed:
                return
            self._audio_player.stop()
            self._current_station = None
            self._snapshot = StreamingRadioPlaybackState()

    def stop_if_offline(self) -> None:
        """Recheck current connectivity after acquiring native operation ownership."""
        with self._operation_lock:
            if self._closed or self._network_allowed():
                return
            self._audio_player.stop()
            self._current_station = None
            self._snapshot = StreamingRadioPlaybackState()

    def close(self) -> None:
        """Retire playback before waiting for pending native operations to finish."""
        with self._close_lock:
            if self._closed:
                return
            self._closed = True
        with self._operation_lock:
            self._audio_player.stop()
            self._current_station = None
            self._snapshot = StreamingRadioPlaybackState()
