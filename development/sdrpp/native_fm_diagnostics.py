# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Offline RTL-SDR IQ diagnostics and synthetic WBFM tone fidelity test."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import signal

from controllers.radio.dsp.wbfm_mono_demodulator import WbfmMonoDemodulator
from hardware_io.sdr import IqBlock

RATE = 2_400_000
AUDIO_RATE = 48_000
CHUNK = 131_072


def pack(iq: np.ndarray) -> bytes:
    data = np.empty(len(iq) * 2, dtype=np.uint8)
    data[::2] = np.clip(np.rint(127.5 + 110 * iq.real), 0, 255).astype(np.uint8)
    data[1::2] = np.clip(np.rint(127.5 + 110 * iq.imag), 0, 255).astype(np.uint8)
    return data.tobytes()


def decode(data: bytes) -> np.ndarray:
    decoder = WbfmMonoDemodulator()
    pieces = []
    for pos in range(0, len(data), CHUNK * 2):
        piece = data[pos:pos + CHUNK * 2]
        pieces.append(decoder.process(IqBlock(piece, 104_300_000, RATE, 0)))
    return np.concatenate(pieces)


def synthetic_test(seconds: float, tone_hz: float, deviation_hz: float) -> dict:
    count = int(seconds * RATE)
    n = np.arange(count, dtype=np.float64)
    modulation = np.sin(2 * np.pi * tone_hz * n / RATE)
    phase = np.cumsum(2 * np.pi * deviation_hz / RATE * modulation)
    audio = decode(pack(np.exp(1j * phase)))
    # Ignore initial filter transients; measure a coherent FFT interval.
    settled = audio[int(0.15 * AUDIO_RATE):]
    period = max(1, int(round(AUDIO_RATE / tone_hz)))
    length = (len(settled) // period) * period
    settled = settled[:length]
    if length < 1024:
        raise ValueError("Synthetic test duration is too short")
    centered = settled - np.mean(settled)
    spectrum = np.fft.rfft(centered)
    freq = np.fft.rfftfreq(length, 1 / AUDIO_RATE)
    def power_near(hz: float) -> float:
        mask = np.abs(freq - hz) <= max(2.0, AUDIO_RATE / length * 1.5)
        return float(np.sum(np.abs(spectrum[mask]) ** 2))
    fundamental = power_near(tone_hz)
    harmonics = sum(power_near(tone_hz * k) for k in range(2, 9)
                    if tone_hz * k < AUDIO_RATE / 2)
    thd = np.sqrt(harmonics / fundamental) if fundamental else float("inf")
    return {
        "tone_hz": tone_hz,
        "deviation_hz": deviation_hz,
        "audio_rms": float(np.sqrt(np.mean(centered ** 2))),
        "audio_peak": float(np.max(np.abs(centered))),
        "thd_percent": float(thd * 100),
        "note": "THD from a quantized synthetic mono FM tone; not a live RF measurement",
    }


def iq_diagnostics(path: Path, station_offset_hz: float) -> dict:
    count = 0
    edge = 0
    near_edge = 0
    sum_i = sum_q = sum_i2 = sum_q2 = 0.0
    spectrum_acc = None
    windows = 0
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK * 2):
            raw = np.frombuffer(chunk, dtype=np.uint8)
            if len(raw) % 2:
                raise ValueError("Incomplete interleaved IQ sample")
            count += len(raw) // 2
            edge += int(np.count_nonzero((raw == 0) | (raw == 255)))
            near_edge += int(np.count_nonzero((raw <= 3) | (raw >= 252)))
            i = raw[::2].astype(np.float64) - 127.5
            q = raw[1::2].astype(np.float64) - 127.5
            sum_i += float(np.sum(i))
            sum_q += float(np.sum(q))
            sum_i2 += float(np.dot(i, i))
            sum_q2 += float(np.dot(q, q))
            if len(i) >= 8192:
                iq = i[:8192] + 1j * q[:8192]
                power = np.abs(np.fft.fftshift(np.fft.fft(iq * np.hanning(len(iq))))) ** 2
                spectrum_acc = power if spectrum_acc is None else spectrum_acc + power
                windows += 1
    if count == 0:
        raise ValueError("Empty IQ recording")
    result = {
        "samples": count,
        "duration_seconds": count / RATE,
        "adc_exact_rail_percent": 100 * edge / (2 * count),
        "adc_near_rail_percent": 100 * near_edge / (2 * count),
        "i_mean_normalized": sum_i / count / 127.5,
        "q_mean_normalized": sum_q / count / 127.5,
        "iq_rms_normalized": np.sqrt((sum_i2 + sum_q2) / count) / 127.5,
    }
    if windows:
        freqs = np.fft.fftshift(np.fft.fftfreq(8192, 1 / RATE))
        spectrum = spectrum_acc / windows
        # Report relative power near expected station vs other frequencies.
        station = np.abs(freqs - station_offset_hz) < 100_000
        result["station_band_to_other_power_db"] = float(
            10 * np.log10((np.mean(spectrum[station]) + 1e-12) /
                          (np.mean(spectrum[~station]) + 1e-12))
        )
        result["spectral_peak_offset_hz"] = float(freqs[np.argmax(spectrum)])
        result["spectral_peak_note"] = "Peak can be a DC spur or interferer, not necessarily the FM station"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iq-file", type=Path, help="Raw U8 interleaved IQ recording")
    parser.add_argument("--station-offset-khz", type=float, default=0,
                        help="Station minus hardware center; use -200 for 104.3/104.5 MHz")
    parser.add_argument("--seconds", type=float, default=0.6)
    parser.add_argument("--tone-hz", type=float, default=1000)
    parser.add_argument("--deviation-hz", type=float, default=25000)
    args = parser.parse_args()
    if args.seconds < 0.3 or not 100 <= args.tone_hz <= 2000 or not 0 < args.deviation_hz <= 75000:
        parser.error("Need >=0.3 seconds, tone 100-2000 Hz, deviation 0-75000 Hz")
    report = {"synthetic": synthetic_test(args.seconds, args.tone_hz, args.deviation_hz)}
    if args.iq_file:
        report["capture"] = iq_diagnostics(args.iq_file, args.station_offset_khz * 1000)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
