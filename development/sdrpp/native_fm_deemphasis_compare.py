# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Compare de-emphasis filters on identical captured IQ, plus dual AGC."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import wave

import numpy as np
from scipy import signal

from development.sdrpp.native_fm_gain_mode_compare import capture
from hardware_io.sdr import IqBlock
from controllers.radio.dsp.wbfm_mono_demodulator import WbfmMonoDemodulator

RATE = 2_400_000
AUDIO_RATE = 48_000
BLOCK = 262_144


def configure(receiver: WbfmMonoDemodulator, mode: str) -> None:
    tau = 75e-6
    if mode == "existing":
        return
    if mode == "bilinear":
        # Analog H(s)=1/(1+s*tau), mapped with bilinear transform.
        b, a = signal.bilinear([1.0], [tau, 1.0], fs=AUDIO_RATE)
    elif mode == "bypass":
        b, a = np.array([1.0]), np.array([1.0])
    else:
        raise ValueError(mode)
    receiver._deemphasis_b = np.asarray(b, dtype=np.float64)
    receiver._deemphasis_a = np.asarray(a, dtype=np.float64)
    receiver._deemphasis_state = np.zeros(max(len(a), len(b)) - 1)


def decode(iq_path: Path, wav_path: Path, mode: str) -> dict:
    receiver = WbfmMonoDemodulator()
    configure(receiver, mode)
    count = 0
    power = 0.0
    peaks = 0.0
    with iq_path.open("rb") as stream, wave.open(str(wav_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(AUDIO_RATE)
        while raw := stream.read(BLOCK):
            pcm = receiver.process(IqBlock(
                samples=raw, center_frequency_hz=104_300_000,
                sample_rate_hz=RATE, timestamp_ns=0))
            wav.writeframes(np.rint(pcm * 32767).astype("<i2").tobytes())
            count += len(pcm)
            power += float(np.sum(pcm.astype(np.float64) ** 2))
            if len(pcm):
                peaks = max(peaks, float(np.max(np.abs(pcm))))
    return {"samples": count, "rms": float(np.sqrt(power / count)),
            "peak": peaks}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frequency", type=int, default=104_300_000)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--iq-file", type=Path,
                        help="Use an existing U8 IQ capture instead of capturing")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {"frequency_hz": args.frequency, "captures": {}, "filters": {}}
    if args.iq_file is None:
        if args.seconds <= 0:
            parser.error("--seconds must be positive")
        manual = args.output_dir / "manual_30.u8"
        dual = args.output_dir / "tuner_agc_rtl_agc.u8"
        print("Capturing manual 30 dB, RTL AGC off...", flush=True)
        report["captures"]["manual_30"] = capture(
            manual, args.frequency, 30.0, args.seconds, False)
        print("Capturing tuner AGC + RTL AGC...", flush=True)
        report["captures"]["tuner_agc_rtl_agc"] = capture(
            dual, args.frequency, None, args.seconds, True)
    else:
        manual = args.iq_file
        dual = None
    for mode in ("existing", "bilinear", "bypass"):
        path = args.output_dir / f"manual_30_{mode}.wav"
        print(f"Decoding {mode}...", flush=True)
        report["filters"][mode] = decode(manual, path, mode)
    if dual is not None:
        report["filters"]["dual_agc_existing"] = decode(
            dual, args.output_dir / "dual_agc_existing.wav", "existing")
    (args.output_dir / "deemphasis_comparison.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("Bypass will sound brighter/louder; match playback levels before comparing.")
    print("De-emphasis changes tonal balance; it cannot repair RF distortion.")


if __name__ == "__main__":
    main()
