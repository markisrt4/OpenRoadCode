# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Callable

from controllers.audio.streaming_audio_player_if import StreamingAudioPlayerIf
from controllers.radio.streaming_radio_types import StreamingRadioStation


class StreamingRadioController:
    """Coordinate streaming-radio station selection and audio playback."""

    def __init__(self, audio_player: StreamingAudioPlayerIf) -> None:
        self._audio_player = audio_player
        self._network_allowed: Callable[[], bool] = lambda: True
        self._current_station: StreamingRadioStation | None = None

    def set_network_allowed(self, allowed: Callable[[], bool]) -> None:
        self._network_allowed = allowed

    @property
    def current_station(self) -> StreamingRadioStation | None:
        """Return the station selected for current playback."""

        return self._current_station

    @property
    def is_playing(self) -> bool:
        """Return whether the streaming audio player is currently active."""

        return self._audio_player.is_playing

    def play(self, station: StreamingRadioStation) -> None:
        """Play ``station`` and make it the current station."""

        if not self._network_allowed():
            raise RuntimeError("Internet radio unavailable in offline mode")
        self._audio_player.play(station.stream_url)
        if not self._network_allowed():
            self.stop()
            raise RuntimeError("Internet radio stopped: offline mode")
        self._current_station = station

    def stop(self) -> None:
        """Stop streaming playback and clear the current station."""

        self._audio_player.stop()
        self._current_station = None
