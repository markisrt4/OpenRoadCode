# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Coordinate native SDR processing and selectable asynchronous audio."""

from __future__ import annotations

from controllers.radio.native_radio_service import NativeRadioService
from hardware_io.audio.pcm_playback_worker import PcmPlaybackWorker


class RadioAudioSession:
    """Bind one radio service to one PCM worker without coupling either layer.

    Other PCM consumers may be attached by the caller using the original sink.
    This session owns the worker lifecycle but leaves source lifecycle to the
    injected radio service. The session must be stopped before disposal.
    """

    def __init__(self, radio: NativeRadioService, playback: PcmPlaybackWorker) -> None:
        self.radio = radio
        self.playback = playback
        self._started = False
        self._original_sink = radio.pcm_sink

    def select_channel(self, name: str | None) -> None:
        self.playback.select_channel(name)

    def start(self) -> None:
        if self._started:
            return
        self.playback.start()
        self.radio.pcm_sink = self._deliver
        try:
            self.radio.start()
        except BaseException:
            self.radio.pcm_sink = self._original_sink
            self.playback.stop()
            raise
        self._started = True

    def process_once(self):
        if not self._started:
            raise RuntimeError("radio audio session is not started")
        return self.radio.process_once()

    def stop(self) -> None:
        if not self._started:
            return
        try:
            self.radio.stop()
        finally:
            self.radio.pcm_sink = self._original_sink
            self._started = False
            self.playback.stop()

    def _deliver(self, name, pcm) -> None:
        if self._original_sink is not None:
            self._original_sink(name, pcm)
        self.playback.submit(name, pcm)
