# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Streaming mono broadcast-FM demodulator for RTL-SDR IQ.

Designed for 2.4 MSPS IQ -> 240 kSPS discriminator -> 48 kHz mono PCM.
"""

from __future__ import annotations

import numpy as np
from scipy import signal

from hardware_io.sdr import IqBlock, IqSampleFormat


class WbfmMonoDemodulator:
    """Stateful FM discriminator, filtering, decimation and de-emphasis."""

    def __init__(self, sample_rate_hz: int = 2_400_000, audio_rate_hz: int = 48_000,
                 deemphasis_us: float = 75.0) -> None:
        if sample_rate_hz != 2_400_000 or audio_rate_hz != 48_000:
            raise ValueError("Initial WBFM implementation requires 2.4 MSPS IQ and 48 kHz PCM")
        self.sample_rate_hz = sample_rate_hz
        self.audio_rate_hz = audio_rate_hz
        self._rf_decimation = 10
        self._audio_decimation = 5
        self._rf_taps = signal.firwin(129, 100_000, fs=sample_rate_hz).astype(np.float32)
        self._audio_taps = signal.firwin(129, 15_000, fs=240_000).astype(np.float32)
        self._rf_state = np.zeros(len(self._rf_taps) - 1, dtype=np.complex64)
        self._audio_state = np.zeros(len(self._audio_taps) - 1, dtype=np.float32)
        self._rf_phase = 0
        self._audio_phase = 0
        self._previous_iq: complex | None = None
        tau = deemphasis_us * 1e-6
        self._deemphasis_alpha = 1 - np.exp(-1 / (audio_rate_hz * tau))
        self._deemphasis_state = 0.0

    def process(self, block: IqBlock) -> np.ndarray:
        """Return normalized float32 mono PCM; preserve state across blocks."""
        if block.sample_format != IqSampleFormat.U8_INTERLEAVED:
            raise ValueError("WBFM requires unsigned interleaved IQ")
        if block.sample_rate_hz != self.sample_rate_hz or len(block.samples) % 2:
            raise ValueError("Unexpected IQ rate or incomplete IQ sample")
        raw = np.frombuffer(block.samples, dtype=np.uint8).astype(np.float32)
        iq = ((raw[::2] - 127.5) + 1j * (raw[1::2] - 127.5)) / 127.5
        filtered, self._rf_state = signal.lfilter(
            self._rf_taps, [1.0], iq.astype(np.complex64), zi=self._rf_state
        )
        decimated = filtered[self._rf_phase::self._rf_decimation]
        self._rf_phase = (self._rf_phase - len(filtered)) % self._rf_decimation
        if not len(decimated):
            return np.empty(0, dtype=np.float32)
        if self._previous_iq is None:
            previous = np.concatenate((decimated[:1], decimated[:-1]))
        else:
            previous = np.concatenate(([self._previous_iq], decimated[:-1]))
        self._previous_iq = complex(decimated[-1])
        discriminator = np.angle(decimated * np.conj(previous)).astype(np.float32)
        audio_filtered, self._audio_state = signal.lfilter(
            self._audio_taps, [1.0], discriminator, zi=self._audio_state
        )
        audio = audio_filtered[self._audio_phase::self._audio_decimation]
        self._audio_phase = (self._audio_phase - len(audio_filtered)) % self._audio_decimation
        # FM broadcast 75 kHz deviation: normalize the discriminator output.
        audio = audio * (240_000 / (2 * np.pi * 75_000))
        output = np.empty(len(audio), dtype=np.float32)
        value = self._deemphasis_state
        alpha = self._deemphasis_alpha
        for index, sample in enumerate(audio):
            value += alpha * (float(sample) - value)
            output[index] = value
        self._deemphasis_state = value
        return np.clip(output, -1, 1)
