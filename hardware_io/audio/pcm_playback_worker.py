# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Bounded, channel-selectable PCM playback independent of radio hardware."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass

import numpy as np

from hardware_io.audio.pcm_output_if import PcmOutputIf


@dataclass(frozen=True)
class PcmPlaybackStatus:
    running: bool
    selected_channel: str | None
    queued_blocks: int
    dropped_blocks: int
    played_blocks: int
    last_error: str | None


class PcmPlaybackWorker:
    """Route one channel to a blocking PCM device on a dedicated thread.

    The caller must never block on audio output. When the queue is full,
    incoming PCM is dropped rather than stalling SDR acquisition.
    """

    def __init__(self, output: PcmOutputIf, *, queue_blocks: int = 32,
                 sample_rate_hz: int = 48_000, prebuffer_ms: int = 0) -> None:
        if queue_blocks < 1 or sample_rate_hz <= 0 or prebuffer_ms < 0:
            raise ValueError("queue_blocks and sample_rate_hz must be positive")
        self._output = output
        self._queue: queue.Queue[tuple[int, np.ndarray]] = queue.Queue(maxsize=queue_blocks)
        self._sample_rate_hz = sample_rate_hz
        self._prebuffer_samples = round(prebuffer_ms * sample_rate_hz / 1000)
        self._buffered_samples = 0
        self._prebuffer_ready = threading.Event()
        if not self._prebuffer_samples:
            self._prebuffer_ready.set()
        self._lock = threading.Lock()
        self._selected: str | None = None
        self._generation = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._dropped = 0
        self._played = 0
        self._error: str | None = None

    @property
    def status(self) -> PcmPlaybackStatus:
        with self._lock:
            return PcmPlaybackStatus(
                self._thread is not None and self._thread.is_alive(),
                self._selected, self._queue.qsize(), self._dropped,
                self._played, self._error
            )

    def select_channel(self, name: str | None) -> None:
        """Switch playback channel and discard previously queued audio."""
        with self._lock:
            self._selected = name
            self._generation += 1
            self._clear_queue()
            self._buffered_samples = 0
            if self._prebuffer_samples:
                self._prebuffer_ready.clear()

    def start(self) -> None:
        with self._lock:
            if self._thread is not None:
                raise RuntimeError("playback worker already started")
            self._stop.clear()
            self._error = None
            self._clear_queue()
            self._buffered_samples = 0
            if self._prebuffer_samples:
                self._prebuffer_ready.clear()
            else:
                self._prebuffer_ready.set()
        self._output.open(self._sample_rate_hz)
        thread = threading.Thread(target=self._run, name="pcm-playback", daemon=True)
        with self._lock:
            self._thread = thread
        thread.start()

    def submit(self, name: str, samples: np.ndarray) -> bool:
        """Enqueue selected PCM without waiting for playback."""
        with self._lock:
            if (self._thread is None or self._stop.is_set()
                    or self._error is not None or name != self._selected):
                return False
            pcm = np.asarray(samples, dtype=np.float32)
            if pcm.ndim != 1 or not len(pcm) or not np.all(np.isfinite(pcm)):
                return False
            try:
                self._queue.put_nowait((self._generation, pcm.copy()))
                self._buffered_samples += len(pcm)
                if self._buffered_samples >= self._prebuffer_samples:
                    self._prebuffer_ready.set()
                return True
            except queue.Full:
                self._dropped += 1
                return False

    def stop(self) -> None:
        with self._lock:
            thread = self._thread
            if thread is None:
                return
            self._stop.set()
            self._clear_queue()
        thread.join(timeout=5.0)
        if thread.is_alive():
            raise RuntimeError("audio playback is blocked; output not closed")
        with self._lock:
            self._thread = None
        self._output.close()

    def _clear_queue(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                return

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                if not self._prebuffer_ready.wait(timeout=0.05):
                    continue
                try:
                    generation, pcm = self._queue.get(timeout=0.05)
                except queue.Empty:
                    continue
                with self._lock:
                    current = generation == self._generation
                if not current or self._stop.is_set():
                    continue
                self._output.write(pcm)
                with self._lock:
                    self._buffered_samples = max(0, self._buffered_samples - len(pcm))
                with self._lock:
                    self._played += 1
        except Exception as exc:
            with self._lock:
                self._error = str(exc)
            self._stop.set()
