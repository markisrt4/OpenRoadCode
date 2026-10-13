# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Convert interleaved unsigned 8-bit SDR IQ into frequency-domain power."""

from dataclasses import dataclass

import numpy as np

from hardware_io.sdr import IqBlock, IqSampleFormat


@dataclass(frozen=True)
class SpectrumFrame:
    """Calibrated frequency positions with relative power in dBFS."""

    center_frequency_hz: int
    sample_rate_hz: int
    bin_width_hz: float
    power_db: tuple[float, ...]
    timestamp_ns: int


class SpectrumAnalyzer:
    """Hann-windowed, complex FFT of RTL-SDR IQ samples."""

    def __init__(self, fft_size: int = 2048) -> None:
        if fft_size < 256 or fft_size & (fft_size - 1):
            raise ValueError("fft_size must be a power of two >= 256")
        self.fft_size = fft_size
        self._window = np.hanning(fft_size).astype(np.float32)

    def analyze(self, block: IqBlock) -> SpectrumFrame:
        if block.sample_format != IqSampleFormat.U8_INTERLEAVED:
            raise ValueError(f"Unsupported IQ format: {block.sample_format}")
        if block.sample_rate_hz <= 0 or len(block.samples) % 2:
            raise ValueError("IQ requires a positive sample rate and complete I/Q pairs")
        raw = np.frombuffer(block.samples, dtype=np.uint8)
        if raw.size < 2 * self.fft_size:
            raise ValueError("IQ block shorter than FFT window")
        raw = raw[: 2 * self.fft_size].astype(np.float32)
        iq = (raw[::2] - 127.5 + 1j * (raw[1::2] - 127.5)) / 127.5
        iq -= iq.mean()
        bins = np.fft.fftshift(np.fft.fft(iq * self._window))
        magnitude = np.abs(bins) / max(float(self._window.sum()), 1e-12)
        power_db = 20.0 * np.log10(np.maximum(magnitude, 1e-12))
        return SpectrumFrame(
            center_frequency_hz=block.center_frequency_hz,
            sample_rate_hz=block.sample_rate_hz,
            bin_width_hz=block.sample_rate_hz / self.fft_size,
            power_db=tuple(float(value) for value in power_db),
            timestamp_ns=block.timestamp_ns,
        )
