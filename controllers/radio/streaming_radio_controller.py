# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging

from common.logging.structured import current_operation, event, operation
from controllers.audio.streaming_audio_player_if import StreamingAudioPlayerIf
from controllers.radio.streaming_radio_types import StreamingRadioStation

LOGGER = logging.getLogger("radio.streaming")


class StreamingRadioController:
    """Coordinate streaming-radio station selection and audio playback."""

    def __init__(self, audio_player: StreamingAudioPlayerIf) -> None:
        self._audio_player = audio_player
        self._current_station: StreamingRadioStation | None = None

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
        with operation(current_operation()):
            event(
                LOGGER,
                logging.INFO,
                "playback.requested",
                "Streaming playback requested",
                station_id=station.station_id,
            )
            try:
                self._audio_player.play(station.stream_url)
            except Exception as error:
                event(
                    LOGGER,
                    logging.ERROR,
                    "playback.failed",
                    "Streaming playback request failed",
                    station_id=station.station_id,
                    exception_type=type(error).__name__,
                )
                raise
            self._current_station = station
            event(
                LOGGER,
                logging.INFO,
                "playback.started",
                "Streaming player started",
                station_id=station.station_id,
            )

    def stop(self) -> None:
        """Stop streaming playback and clear the current station."""
        with operation(current_operation()):
            try:
                self._audio_player.stop()
            except Exception as error:
                event(
                    LOGGER,
                    logging.ERROR,
                    "playback.stop_failed",
                    "Streaming playback stop failed",
                    exception_type=type(error).__name__,
                )
                raise
            if self._current_station is not None:
                event(
                    LOGGER,
                    logging.INFO,
                    "playback.stopped",
                    "Streaming playback stopped",
                    station_id=self._current_station.station_id,
                )
            self._current_station = None
