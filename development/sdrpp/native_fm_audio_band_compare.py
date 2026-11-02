# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Listen to isolated audio bands and band attenuation from one FM IQ capture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import wave

import numpy as np
from scipy import signal

from controllers.radio.dsp.wbfm_mono_demodulator import WbfmMonoDemodulator
from hardware_io.sdr import IqBlock

IQ_RATE = 2_400_000
AUDIO_RATE = 48_000
BLOCK = 262_144
BANDS = (
    ("bass", 0, 500),
    ("lower_mids", 500, 2000),
    ("upper_mids", 2000, 5000),
    ("presence", 4000, 7000),
    ("highs", 5000, 10000),
    ("very_highs", 10000, 15000),
)
NOTCHES = (
    ("lower_mids", 500, 2000),
    ("upper_mids", 2000, 5000),
    ("presence", 4000, 7000),
    ("highs", 7000, 15000),
)


def sos_for_band(low: int, high: int) -> np.ndarray:
    if low == 0:
        return signal.butter(6, high, btype="lowpass", fs=AUDIO_RATE, output="sos")
    return signal.butter(6, (low, high), btype="bandpass",
                         fs=AUDIO_RATE, output="sos")


def write_wav(path: Path, audio: np.ndarray) -> dict:
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    rms = float(np.sqrt(np.mean(audio ** 2))) if len(audio) else 0.0
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(AUDIO_RATE)
        wav.writeframes(np.rint(np.clip(audio, -1, 1) * 32767)
                        .astype("<i2").tobytes())
    return {"rms": rms, "peak": peak, "samples": len(audio)}


def decode(iq_file: Path, frequency: int) -> np.ndarray:
    receiver = WbfmMonoDemodulator()
    chunks = []
    with iq_file.open("rb") as stream:
        while raw := stream.read(BLOCK):
            chunks.append(receiver.process(IqBlock(
                samples=raw, center_frequency_hz=frequency,
                sample_rate_hz=IQ_RATE, timestamp_ns=0)))
    return np.concatenate(chunks).astype(np.float64) if chunks else np.empty(0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iq-file", type=Path, required=True)
    parser.add_argument("--frequency", type=int, default=104_300_000)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.iq_file.is_file():
        parser.error(f"IQ file not found: {args.iq_file}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    print("Demodulating IQ once...", flush=True)
    audio = decode(args.iq_file, args.frequency)
    if not len(audio):
        parser.error("IQ file contains no audio")
    report = {"source": str(args.iq_file), "frequency_hz": args.frequency,
              "attenuation_db": -6.0, "recordings": {}}
    report["recordings"]["reference"] = write_wav(
        args.output_dir / "reference.wav", audio)
    for name, low, high in BANDS:
        print(f"Isolating {name} ({low}-{high} Hz)...", flush=True)
        band = signal.sosfilt(sos_for_band(low, high), audio)
        report["recordings"][f"isolated_{name}"] = write_wav(
            args.output_dir / f"isolated_{name}.wav", band)
    attenuation = 10 ** (-6 / 20)
    for name, low, high in NOTCHES:
        print(f"Attenuating {name} ({low}-{high} Hz)...", flush=True)
        # Subtract 75% of the filtered band. Overlap and filter phase
        # mean the result is an approximate, not flat, -6 dB EQ.
        band = signal.sosfilt(sos_for_band(low, high), audio)
        adjusted = audio - (1 - attenuation) * band
        report["recordings"][f"reduced_{name}"] = write_wav(
            args.output_dir / f"reduced_{name}.wav", adjusted)
    (args.output_dir / "band_comparison.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Done: {args.output_dir}")
    print("Band-limited audio sounds unnatural; listen for artifacts, not fidelity.")
    print("Attenuation is approximate due to bandpass phase response.")


if __name__ == "__main__":
    main()
