# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Offline ORC-versus-FIR WBFM pipeline comparison using identical recorded IQ.

FIR reference uses polyphase decimation and a conjugate-product discriminator.
It is an independent filtering/resampling path, not an SDR++ clone.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import wave

import numpy as np
from scipy import signal

from controllers.radio.dsp.wbfm_mono_demodulator import WbfmMonoDemodulator
from hardware_io.sdr import IqBlock

RF_RATE = 2_400_000
FM_RATE = 240_000
PCM_RATE = 48_000
CHUNK = 262_144


def read_iq(path: Path):
    with path.open("rb") as stream:
        while raw := stream.read(CHUNK):
            if len(raw) % 2:
                raise ValueError("Incomplete interleaved IQ sample")
            yield raw


def write_wav(path: Path, audio: np.ndarray) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(PCM_RATE)
        wav.writeframes(np.rint(np.clip(audio, -1, 1) * 32767)
                        .astype("<i2").tobytes())


def original(path: Path) -> np.ndarray:
    receiver = WbfmMonoDemodulator()
    chunks = [receiver.process(IqBlock(
        samples=raw, center_frequency_hz=104_300_000,
        sample_rate_hz=RF_RATE, timestamp_ns=0
    )) for raw in read_iq(path)]
    return np.concatenate(chunks)


def reference(path: Path) -> tuple[np.ndarray, dict]:
    # Entire-file polyphase filtering avoids block boundary transients.
    # This path deliberately does not use the production IIR RF stages.
    data = np.fromfile(path, dtype=np.uint8)
    if len(data) % 2:
        raise ValueError("Incomplete interleaved IQ sample")
    values = data.astype(np.float32)
    iq = ((values[::2] - 127.5) + 1j * (values[1::2] - 127.5)) / 127.5
    del data, values
    # Two polyphase FIR stages, retaining >100 kHz of FM baseband.
    stage1 = signal.resample_poly(iq, 1, 5, window=("kaiser", 8.6))
    del iq
    stage2 = signal.resample_poly(stage1, 1, 2, window=("kaiser", 8.6))
    del stage1
    dc = signal.sosfilt(signal.butter(2, 20, btype="highpass",
                                    fs=FM_RATE, output="sos"), stage2)
    del stage2
    product = dc[1:] * np.conj(dc[:-1])
    phase = np.concatenate(([0.0], np.angle(product)))
    frequency_hz = phase * FM_RATE / (2 * np.pi)
    deviation = {
        "frequency_hz_mean": float(np.mean(frequency_hz)),
        "frequency_hz_std": float(np.std(frequency_hz)),
        "frequency_hz_p01": float(np.percentile(frequency_hz, 1)),
        "frequency_hz_p99": float(np.percentile(frequency_hz, 99)),
        "fraction_over_75khz": float(np.mean(np.abs(frequency_hz) > 75_000)),
        "fraction_over_100khz": float(np.mean(np.abs(frequency_hz) > 100_000)),
    }
    # FIR audio anti-alias before 5:1 resampling to 48 kHz.
    mono = signal.resample_poly(
        frequency_hz / 75_000, 1, 5,
        window=signal.firwin(301, 15_000, fs=FM_RATE, window=("kaiser", 8.6))
    )
    alpha = 1 - np.exp(-1 / (PCM_RATE * 75e-6))
    mono = signal.lfilter([alpha], [1, -(1-alpha)], mono)
    return np.clip(mono, -1, 1).astype(np.float32), deviation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iq-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.iq_file.is_file():
        parser.error(f"Missing IQ recording: {args.iq_file}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    print("Processing production ORC pipeline...", flush=True)
    baseline = original(args.iq_file)
    write_wav(args.output_dir / "orc.wav", baseline)
    print("Processing polyphase FIR reference (may take a while)...", flush=True)
    alternative, deviation = reference(args.iq_file)
    write_wav(args.output_dir / "fir_reference.wav", alternative)
    report = {"iq_file": str(args.iq_file), "samples": {
        "orc": len(baseline), "fir_reference": len(alternative)
    }, "rms": {
        "orc": float(np.sqrt(np.mean(baseline.astype(np.float64)**2))),
        "fir_reference": float(np.sqrt(np.mean(alternative.astype(np.float64)**2)))
    }, "instantaneous_frequency": deviation}
    (args.output_dir / "comparison.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    print(f"WAV files: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
