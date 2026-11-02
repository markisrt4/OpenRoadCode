# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Five-point manual tuner gain sweep with offline audio-band diagnostics."""

from __future__ import annotations

import argparse
import ctypes
import json
from pathlib import Path
import wave

import numpy as np
from scipy import signal

from development.sdrpp.native_fm_gain_mode_compare import capture, demodulate
from hardware_io.sdr import RtlSdrSource


def supported_gains() -> list[float] | None:
    source = RtlSdrSource()
    try:
        source.open()
        lib = source._library
        getter = getattr(lib, "rtlsdr_get_tuner_gains", None)
        if getter is None:
            return None
        getter.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
        getter.restype = ctypes.c_int
        count = getter(source._device, None)
        if count <= 0:
            return None
        values = (ctypes.c_int * count)()
        result = getter(source._device, values)
        if result <= 0:
            return None
        return [round(v / 10.0, 1) for v in values[:result]]
    finally:
        source.close()


def audio_bands(path: Path) -> dict:
    with wave.open(str(path), "rb") as wav:
        audio = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
        rate = wav.getframerate()
    values = audio.astype(np.float64) / 32768.0
    frequency, power = signal.welch(values, fs=rate, nperseg=4096)
    bands = ((0, 5000), (5000, 10000), (10000, 15000))
    energy = {}
    for low, high in bands:
        selected = (frequency >= low) & (frequency < high)
        energy[f"{low}_{high}_hz"] = float(np.trapezoid(
            power[selected], frequency[selected]))
    total = sum(energy.values())
    return {
        "band_power": energy,
        "band_fraction": {key: float(value / total) if total else 0.0
                          for key, value in energy.items()},
        "peak_abs": float(np.max(np.abs(values))),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frequency", type=int, default=104_300_000)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("--seconds must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    gains = supported_gains()
    print(f"Supported tuner gains (dB): {gains}", flush=True)
    report = {"frequency_hz": args.frequency, "rtl_agc": False,
              "supported_gains_db": gains, "captures": {}}
    for gain in (20.0, 25.0, 30.0, 35.0, 40.0):
        name = f"manual_{int(gain)}"
        iq = args.output_dir / f"{name}.u8"
        wav = args.output_dir / f"{name}.wav"
        print(f"Capturing {name}...", flush=True)
        metrics = capture(iq, args.frequency, gain, args.seconds, False)
        metrics.update(demodulate(iq, wav))
        metrics["audio_spectrum"] = audio_bands(wav)
        report["captures"][name] = metrics
        print(f"{name}: IQ RMS={metrics['iq_rms_normalized']:.5f}; "
              f"audio RMS={metrics['audio_rms']:.5f}", flush=True)
    (args.output_dir / "gain_sweep.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Results: {args.output_dir / 'gain_sweep.json'}")
    print("Band energies reflect different broadcast content, not distortion directly.")
    print("Requested gain may be rounded by librtlsdr to a supported step.")


if __name__ == "__main__":
    main()
