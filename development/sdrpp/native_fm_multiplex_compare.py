# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Analyze FM multiplex and compare mono audio pilot-rejection filters offline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import wave

import numpy as np
from scipy import signal

from controllers.radio.dsp.wbfm_mono_demodulator import WbfmMonoDemodulator

RF_RATE = 240_000
AUDIO_RATE = 48_000
SCALE = RF_RATE / (2 * np.pi * 75_000)


def discriminator_stream(path: Path, receiver: WbfmMonoDemodulator):
    with path.open("rb") as stream:
        while raw_bytes := stream.read(262_144):
            if len(raw_bytes) % 2:
                raise ValueError("IQ file ends with an incomplete I/Q pair")
            raw = np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32)
            iq = ((raw[::2] - 127.5) + 1j * (raw[1::2] - 127.5)) / 127.5
            samples = iq.astype(np.complex64)
            for stage, (factor, sos) in enumerate(receiver._rf_stages):
                samples, receiver._rf_states[stage] = signal.sosfilt(
                    sos, samples, zi=receiver._rf_states[stage]
                )
                n = len(samples)
                samples = samples[receiver._rf_phases[stage]::factor]
                receiver._rf_phases[stage] = (receiver._rf_phases[stage] - n) % factor
            if not len(samples):
                continue
            dc, _ = signal.lfilter(
                [receiver._dc_alpha], [1, -(1 - receiver._dc_alpha)],
                samples, zi=[receiver._dc_state * (1 - receiver._dc_alpha)]
            )
            receiver._dc_state = complex(dc[-1])
            samples = samples - dc
            previous = (np.concatenate((samples[:1], samples[:-1]))
                        if receiver._previous_iq is None else
                        np.concatenate(([receiver._previous_iq], samples[:-1])))
            receiver._previous_iq = complex(samples[-1])
            yield np.angle(samples * np.conj(previous))


def filter_audio(mpx: np.ndarray, sos: np.ndarray, deemphasis_b: np.ndarray,
                 deemphasis_a: np.ndarray) -> np.ndarray:
    filtered = signal.sosfilt(sos, mpx)
    audio = filtered[::5] * SCALE
    return np.clip(signal.lfilter(deemphasis_b, deemphasis_a, audio), -1, 1).astype(np.float32)


def band_power(freq: np.ndarray, psd: np.ndarray, low: float, high: float) -> float:
    mask = (freq >= low) & (freq < high)
    return float(np.sum(psd[mask]) * (freq[1] - freq[0]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iq-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.iq_file.is_file():
        parser.error(f"Missing IQ file: {args.iq_file}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    receiver = WbfmMonoDemodulator()
    mpx = np.concatenate(list(discriminator_stream(args.iq_file, receiver)))
    # Analyze the positive-frequency side of the real FM multiplex spectrum.
    frequency, psd = signal.welch(mpx, fs=RF_RATE, nperseg=32768,
                                 scaling="density")
    bands = {
        "mono_0_15k": (0, 15_000),
        "pilot_18_20k": (18_000, 20_000),
        "stereo_23_53k": (23_000, 53_000),
        "rds_56_58k": (56_000, 58_000),
        "upper_60_100k": (60_000, 100_000),
    }
    power = {name: band_power(frequency, psd, *limits)
             for name, limits in bands.items()}
    peak_mask = (frequency >= 18_000) & (frequency <= 20_000)
    pilot_peak_hz = float(frequency[peak_mask][np.argmax(psd[peak_mask])])
    baseline = receiver._audio_sos
    # Narrow transition explicitly rejects the 19 kHz pilot, trading some
    # high-frequency audio bandwidth for attenuation.
    strict = signal.iirdesign(13_500, 17_500, 1, 70, fs=RF_RATE, output="sos")
    # A gentler audio-bandwidth alternative with a strong 19 kHz stopband.
    balanced = signal.iirdesign(15_000, 18_000, 1, 70, fs=RF_RATE, output="sos")
    variants = {"original": baseline, "balanced": balanced, "strict": strict}
    report = {"rf_samples": len(mpx), "pilot_peak_hz": pilot_peak_hz,
              "multiplex_band_power_db": {
                  name: float(10*np.log10(max(value, 1e-30)))
                  for name, value in power.items()
              }, "filters": {}}
    for name, sos in variants.items():
        w, h = signal.sosfreqz(sos, worN=np.array([1000., 10000., 15000., 19000., 38000., 57000.]),
                              fs=RF_RATE)
        attenuation = {str(int(f)): float(20*np.log10(max(abs(value), 1e-15)))
                       for f, value in zip(w, h)}
        pcm = filter_audio(mpx, sos, receiver._deemphasis_b, receiver._deemphasis_a)
        wav_path = args.output_dir / f"{name}.wav"
        with wave.open(str(wav_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(AUDIO_RATE)
            wav.writeframes(np.rint(pcm * 32767).astype("<i2").tobytes())
        report["filters"][name] = {
            "response_db": attenuation,
            "pcm_samples": len(pcm),
            "audio_rms": float(np.sqrt(np.mean(pcm.astype(np.float64)**2))),
        }
        print(f"{name}: RMS={report['filters'][name]['audio_rms']:.6f}, "
              f"19kHz response={attenuation['19000']:.1f} dB")
    (args.output_dir / "multiplex_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Pilot-region peak: {pilot_peak_hz:.1f} Hz")
    for name, value in report["multiplex_band_power_db"].items():
        print(f"{name}: {value:.2f} dB")
    print(f"Files: {args.output_dir.resolve()}")
    print("Pilot peak and band powers are diagnostic; they do not prove audible leakage.")


if __name__ == "__main__":
    main()
