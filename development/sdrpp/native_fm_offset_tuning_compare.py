# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Three capture-only RTL-SDR center-frequency trials with offline correction.

Run separately from SDR++ and other SDR clients. Uses same gain and sample rate
for each trial. No production receiver changes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import wave

import numpy as np

from controllers.radio.dsp.wbfm_mono_demodulator import WbfmMonoDemodulator
from hardware_io.sdr import IqBlock, RtlSdrSource

RATE = 2_400_000
CHUNK_BYTES = 262_144


def capture(path: Path, frequency: int, seconds: float, gain: float) -> dict:
    source = RtlSdrSource()
    total = 0
    read_ms = []
    target = int(seconds * RATE * 2)
    start = time.perf_counter()
    try:
        source.open()
        source.set_sample_rate(RATE)
        source.set_center_frequency(frequency)
        source.set_gain(gain)
        source.set_rtl_agc(False)
        source.start()
        with path.open("wb", buffering=1024 * 1024) as output:
            while total < target:
                before = time.perf_counter()
                block = source.read_iq()
                read_ms.append((time.perf_counter() - before) * 1000)
                output.write(block.samples)
                total += len(block.samples)
    finally:
        source.stop()
        source.close()
    return {
        "hardware_frequency_hz": frequency,
        "gain_db": gain,
        "bytes": total,
        "rf_seconds": total / (2 * RATE),
        "wall_seconds": time.perf_counter() - start,
        "read_ms_p95": float(np.percentile(read_ms, 95)),
        "read_ms_max": float(np.max(read_ms)),
    }


def demodulate(path: Path, wav_path: Path, hardware_frequency: int,
               station_frequency: int) -> dict:
    decoder = WbfmMonoDemodulator()
    offset = station_frequency - hardware_frequency
    sample_index = 0
    audio_count = 0
    power = 0.0
    with path.open("rb") as source, wave.open(str(wav_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(48_000)
        while raw := source.read(CHUNK_BYTES):
            if len(raw) % 2:
                raise ValueError("Incomplete IQ sample")
            if offset:
                values = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
                iq = ((values[::2] - 127.5) + 1j * (values[1::2] - 127.5)) / 127.5
                count = len(iq)
                # A station at offset Hz from the hardware center is mixed
                # to DC by exp(-j*2*pi*offset*t).
                phase = -2j * np.pi * offset * (
                    np.arange(count, dtype=np.float64) + sample_index
                ) / RATE
                mixed = iq * np.exp(phase)
                sample_index += count
                # The production decoder accepts U8. Re-quantization is an
                # avoidable extra variable; see note below.
                iq_bytes = np.empty(count * 2, dtype=np.uint8)
                iq_bytes[::2] = np.clip(np.rint(mixed.real * 127.5 + 127.5), 0, 255)
                iq_bytes[1::2] = np.clip(np.rint(mixed.imag * 127.5 + 127.5), 0, 255)
                raw = iq_bytes.tobytes()
            pcm = decoder.process(IqBlock(
                samples=raw, center_frequency_hz=station_frequency,
                sample_rate_hz=RATE, timestamp_ns=0
            ))
            audio_count += len(pcm)
            power += float(np.dot(pcm.astype(np.float64), pcm.astype(np.float64)))
            wav.writeframes(np.rint(pcm * 32767).astype("<i2").tobytes())
    return {"station_offset_hz": offset, "pcm_samples": audio_count,
            "audio_rms": float(np.sqrt(power / max(audio_count, 1)))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--station", type=int, default=104_300_000)
    parser.add_argument("--gain", type=float, default=40.0)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("--seconds must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, delta in (("direct", 0), ("high", 200_000), ("low", -200_000)):
        frequency = args.station + delta
        print(f"{name}: capturing {frequency/1e6:.3f} MHz...", flush=True)
        capture_path = args.output_dir / f"{name}.u8"
        wav_path = args.output_dir / f"{name}.wav"
        capture_stats = capture(capture_path, frequency, args.seconds, args.gain)
        audio_stats = demodulate(capture_path, wav_path, frequency, args.station)
        report[name] = {**capture_stats, **audio_stats}
        print(f"{name}: {audio_stats['pcm_samples']} PCM samples, "
              f"RMS={audio_stats['audio_rms']:.5f}", flush=True)
    (args.output_dir / "results.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Completed. Results: {args.output_dir / 'results.json'}")
    print("Note: offset paths re-quantize mixed IQ to U8. This adds quantization")
    print("noise and makes the test directional rather than a definitive DSP A/B.")


if __name__ == "__main__":
    main()
