# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Synchronous hardware-independent SDR acquisition and PCM processing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from controllers.radio.multi_mode_radio_receiver import MultiModeRadioReceiver
from hardware_io.sdr.sdr_source_if import SdrSourceIf


@dataclass(frozen=True)
class RadioServiceStatus:
    started: bool
    processed_blocks: int
    processed_iq_samples: int
    discontinuities: int
    last_error: str | None


class NativeRadioService:
    """Own one SDR source and deliver per-channel PCM to an injected sink.

    process_once is intentionally synchronous for deterministic testing.
    Call it from a dedicated worker when integrating with a UI or audio sink.
    """

    def __init__(
        self, source: SdrSourceIf, receiver: MultiModeRadioReceiver,
        *, center_frequency_hz: int, sample_rate_hz: int = 2_400_000,
        gain_db: float | None = 30.0,
        pcm_sink: Callable[[str, np.ndarray], None] | None = None,
    ) -> None:
        if center_frequency_hz <= 0 or sample_rate_hz <= 0:
            raise ValueError("center frequency and sample rate must be positive")
        self.source = source
        self.receiver = receiver
        self.center_frequency_hz = center_frequency_hz
        self.sample_rate_hz = sample_rate_hz
        self.gain_db = gain_db
        self.pcm_sink = pcm_sink
        self._started = False
        self._blocks = 0
        self._samples = 0
        self._discontinuities = 0
        self._last_error: str | None = None
        self._last_timestamp_ns: int | None = None
        self._last_duration_ns = 0
        self._last_dropped_blocks: int | None = None

    @property
    def status(self) -> RadioServiceStatus:
        return RadioServiceStatus(self._started, self._blocks, self._samples,
                                  self._discontinuities, self._last_error)

    def start(self) -> None:
        if self._started:
            return
        self.source.open()
        try:
            self.source.set_sample_rate(self.sample_rate_hz)
            self.source.set_gain(self.gain_db)
            self.source.set_center_frequency(self.center_frequency_hz)
            self.receiver.reset()
            self.source.start()
        except Exception as exc:
            self._last_error = str(exc)
            self.source.close()
            raise
        self._started = True
        self._last_timestamp_ns = None
        self._last_dropped_blocks = None
        self._last_error = None

    def stop(self) -> None:
        if not self._started:
            return
        try:
            self.source.stop()
        finally:
            self._started = False
            self.source.close()
            self.receiver.reset()

    def process_once(self) -> dict[str, np.ndarray]:
        """Acquire one IQ block, demodulate, then dispatch independent PCM."""
        if not self._started:
            raise RuntimeError("radio service is not started")
        try:
            block = self.source.read_iq()
            if block.sample_rate_hz != self.sample_rate_hz:
                raise ValueError("unexpected source sample rate")
            if block.center_frequency_hz != self.center_frequency_hz:
                raise ValueError("unexpected source center frequency")
            dropped = self._source_dropped_blocks()
            gap = (self._last_timestamp_ns is not None and
                   block.timestamp_ns > self._last_timestamp_ns +
                   max(self._last_duration_ns * 2, 20_000_000))
            dropped_changed = (dropped is not None and
                               self._last_dropped_blocks is not None and
                               dropped > self._last_dropped_blocks)
            if gap or dropped_changed:
                self.receiver.reset()
                self._discontinuities += 1
            pcm = self.receiver.process(block)
            self._last_timestamp_ns = block.timestamp_ns
            self._last_duration_ns = round(
                len(block.samples) * 1_000_000_000 / (2 * self.sample_rate_hz)
            )
            self._last_dropped_blocks = dropped
            self._blocks += 1
            self._samples += len(block.samples) // 2
            if self.pcm_sink is not None:
                for name, audio in pcm.items():
                    self.pcm_sink(name, audio)
            return pcm
        except Exception as exc:
            self._last_error = str(exc)
            self.receiver.reset()
            self._last_timestamp_ns = None
            raise

    def _source_dropped_blocks(self) -> int | None:
        stats_fn = getattr(self.source, "get_acquisition_stats", None)
        if not callable(stats_fn):
            return None
        stats = stats_fn()
        value = stats.get("dropped_blocks")
        return int(value) if value is not None else None
