# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""PortAudio-backed PCM output, lazily importing optional sounddevice."""

from __future__ import annotations

import numpy as np

from hardware_io.audio.pcm_output_if import PcmOutputIf


class SounddevicePcmOutputAdapter(PcmOutputIf):
    """Blocking 48 kHz mono float32 playback with configurable priming."""

    def __init__(self, *, latency: str = "high", prime_ms: int = 1000,
                 volume: float = 0.6, sounddevice_module=None) -> None:
        if latency not in ("low", "high"):
            raise ValueError("latency must be low or high")
        if prime_ms < 0 or not 0 <= volume <= 1:
            raise ValueError("prime_ms must be nonnegative and volume in [0, 1]")
        self._latency = latency
        self._prime_ms = prime_ms
        self._volume = volume
        self._sd = sounddevice_module
        self._stream = None
        self._sample_rate_hz = None
        self.underflows = 0

    def open(self, sample_rate_hz: int = 48_000) -> None:
        if sample_rate_hz <= 0:
            raise ValueError("sample rate must be positive")
        if self._stream is not None:
            if sample_rate_hz != self._sample_rate_hz:
                raise RuntimeError("close before changing the sample rate")
            return
        if self._sd is None:
            try:
                import sounddevice as sd
            except ImportError as exc:
                raise RuntimeError("PCM playback requires pip install sounddevice") from exc
            self._sd = sd
        stream = self._sd.OutputStream(
            samplerate=sample_rate_hz, channels=1, dtype="float32",
            latency=self._latency,
        )
        try:
            stream.start()
            if self._prime_ms:
                silence = np.zeros((round(sample_rate_hz * self._prime_ms / 1000), 1),
                                   dtype=np.float32)
                if len(silence) and stream.write(silence):
                    self.underflows += 1
        except Exception:
            stream.close()
            raise
        self._stream = stream
        self._sample_rate_hz = sample_rate_hz

    def write(self, samples: np.ndarray) -> None:
        if self._stream is None:
            raise RuntimeError("PCM output is not open")
        pcm = np.asarray(samples)
        if pcm.ndim != 1 or not np.issubdtype(pcm.dtype, np.number):
            raise ValueError("PCM must be a one-dimensional numeric array")
        if not np.all(np.isfinite(pcm)):
            raise ValueError("PCM must contain finite samples")
        if not len(pcm):
            return
        data = np.ascontiguousarray(
            np.clip(pcm.astype(np.float32) * self._volume, -1, 1)[:, None]
        )
        if self._stream.write(data):
            self.underflows += 1

    def drain(self) -> None:
        if self._stream is None:
            return
        # PortAudio stop waits for pending output buffers to finish.
        self._stream.stop()
        self._stream.start()

    def close(self) -> None:
        stream, self._stream = self._stream, None
        self._sample_rate_hz = None
        if stream is not None:
            try:
                stream.stop()
            finally:
                stream.close()
