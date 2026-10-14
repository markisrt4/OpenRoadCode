# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Stateful mono WBFM receiver: 2.4 MSPS IQ to 48 kHz PCM."""

from __future__ import annotations

import numpy as np
from scipy import signal

from hardware_io.sdr import IqBlock, IqSampleFormat


class WbfmMonoDemodulator:
    """Two-stage RF decimation, discriminator, audio filtering and de-emphasis."""

    def __init__(self, sample_rate_hz: int = 2_400_000, audio_rate_hz: int = 48_000,
                 deemphasis_us: float = 75.0) -> None:
        if sample_rate_hz != 2_400_000 or audio_rate_hz != 48_000:
            raise ValueError("WBFM currently requires 2.4 MSPS IQ and 48 kHz PCM")
        if deemphasis_us <= 0:
            raise ValueError("deemphasis_us must be positive")
        self.sample_rate_hz = sample_rate_hz
        self.audio_rate_hz = audio_rate_hz
        # Anti-alias filters: 2.4M -> 480k -> 240k. Filtering runs in
        # compiled SOS routines rather than a 129-tap full-rate complex FIR.
        self._rf_stages = (
            (5, signal.iirdesign(180_000, 240_000, 1, 65, fs=2_400_000, output="sos")),
            (2, signal.iirdesign(95_000, 120_000, 1, 65, fs=480_000, output="sos")),
        )
        self._rf_states = [
            np.zeros((len(sos), 2), dtype=np.complex128)
            for _, sos in self._rf_stages
        ]
        self._rf_phases = [0, 0]
        self._previous_iq: complex | None = None
        self._dc_state = 0j
        self._dc_alpha = 0.0001
        self._audio_sos = signal.iirdesign(
            15_000, 24_000, 1, 70, fs=240_000, output="sos"
        )
        self._audio_state = np.zeros((len(self._audio_sos), 2), dtype=np.float64)
        self._audio_phase = 0
        alpha = 1 - np.exp(-1 / (audio_rate_hz * deemphasis_us * 1e-6))
        self._deemphasis_b = np.array([alpha], dtype=np.float64)
        self._deemphasis_a = np.array([1, -(1 - alpha)], dtype=np.float64)
        self._deemphasis_state = np.zeros(1, dtype=np.float64)

    def process(self, block: IqBlock) -> np.ndarray:
        """Demodulate one IQ block; preserve all filter and decimation state."""
        if block.sample_format != IqSampleFormat.U8_INTERLEAVED:
            raise ValueError("WBFM requires unsigned interleaved IQ")
        if block.sample_rate_hz != self.sample_rate_hz or len(block.samples) % 2:
            raise ValueError("Unexpected IQ rate or incomplete IQ sample")
        raw = np.frombuffer(block.samples, dtype=np.uint8).astype(np.float32)
        iq = ((raw[::2] - 127.5) + 1j * (raw[1::2] - 127.5)) / 127.5
        samples = iq.astype(np.complex64)
        for stage, (factor, sos) in enumerate(self._rf_stages):
            samples, self._rf_states[stage] = signal.sosfilt(
                sos, samples, zi=self._rf_states[stage]
            )
            length = len(samples)
            samples = samples[self._rf_phases[stage]::factor]
            self._rf_phases[stage] = (self._rf_phases[stage] - length) % factor
        if not len(samples):
            return np.empty(0, dtype=np.float32)
        # Estimate the residual tuner DC spur on the 240 kSPS stream.
        # Stateful one-pole DC removal is deliberately slow relative to FM.
        dc, _ = signal.lfilter(
            [self._dc_alpha], [1, -(1 - self._dc_alpha)],
            samples, zi=[self._dc_state * (1 - self._dc_alpha)]
        )
        self._dc_state = complex(dc[-1])
        samples = samples - dc
        if self._previous_iq is None:
            previous = np.concatenate((samples[:1], samples[:-1]))
        else:
            previous = np.concatenate(([self._previous_iq], samples[:-1]))
        self._previous_iq = complex(samples[-1])
        discriminator = np.angle(samples * np.conj(previous))
        audio_filtered, self._audio_state = signal.sosfilt(
            self._audio_sos, discriminator, zi=self._audio_state
        )
        length = len(audio_filtered)
        audio = audio_filtered[self._audio_phase::5]
        self._audio_phase = (self._audio_phase - length) % 5
        audio = audio * (240_000 / (2 * np.pi * 75_000))
        output, self._deemphasis_state = signal.lfilter(
            self._deemphasis_b, self._deemphasis_a, audio,
            zi=self._deemphasis_state
        )
        return np.clip(output, -1, 1).astype(np.float32)
