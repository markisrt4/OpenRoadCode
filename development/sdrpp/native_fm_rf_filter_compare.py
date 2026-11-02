# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Offline RF filter A/B comparison from recorded IQ; production unchanged."""

from __future__ import annotations

import argparse
from pathlib import Path
import wave

import numpy as np
from scipy import signal

from controllers.radio.dsp.wbfm_mono_demodulator import WbfmMonoDemodulator
from hardware_io.sdr import IqBlock


class Receiver(WbfmMonoDemodulator):
    def __init__(self, variant: str):
        super().__init__()
        self.fir = None
        if variant == "narrow":
            sos = signal.iirdesign(75_000, 115_000, 1, 65, fs=480_000, output="sos")
        elif variant == "wide":
            sos = signal.iirdesign(105_000, 118_000, 1, 65, fs=480_000, output="sos")
        elif variant == "fir":
            self.fir = signal.firwin(161, 95_000, fs=480_000, window=("kaiser", 8.6))
            self.fir_state = np.zeros(160, dtype=np.complex128)
            sos = self._rf_stages[1][1]
        else:
            sos = self._rf_stages[1][1]
        self._rf_stages = (self._rf_stages[0], (2, sos))
        self._rf_states[1] = np.zeros((len(sos), 2), dtype=np.complex128)

    def process(self, block: IqBlock) -> np.ndarray:
        raw = np.frombuffer(block.samples, dtype=np.uint8).astype(np.float32)
        samples = ((raw[::2] - 127.5) + 1j * (raw[1::2] - 127.5)) / 127.5
        for stage, (factor, sos) in enumerate(self._rf_stages):
            if stage == 1 and self.fir is not None:
                samples, self.fir_state = signal.lfilter(
                    self.fir, [1.0], samples, zi=self.fir_state
                )
            else:
                samples, self._rf_states[stage] = signal.sosfilt(
                    sos, samples, zi=self._rf_states[stage]
                )
            n = len(samples)
            samples = samples[self._rf_phases[stage]::factor]
            self._rf_phases[stage] = (self._rf_phases[stage] - n) % factor
        if not len(samples):
            return np.empty(0, dtype=np.float32)
        dc, _ = signal.lfilter(
            [self._dc_alpha], [1, -(1 - self._dc_alpha)],
            samples, zi=[self._dc_state * (1 - self._dc_alpha)]
        )
        self._dc_state = complex(dc[-1])
        samples = samples - dc
        previous = (np.concatenate((samples[:1], samples[:-1]))
                    if self._previous_iq is None else
                    np.concatenate(([self._previous_iq], samples[:-1])))
        self._previous_iq = complex(samples[-1])
        phase = np.angle(samples * np.conj(previous))
        filtered, self._audio_state = signal.sosfilt(
            self._audio_sos, phase, zi=self._audio_state
        )
        n = len(filtered)
        audio = filtered[self._audio_phase::5]
        self._audio_phase = (self._audio_phase - n) % 5
        audio *= 240_000 / (2 * np.pi * 75_000)
        output, self._deemphasis_state = signal.lfilter(
            self._deemphasis_b, self._deemphasis_a, audio,
            zi=self._deemphasis_state
        )
        return np.clip(output, -1, 1).astype(np.float32)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iq-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("rf-filter-compare"))
    args = parser.parse_args()
    if not args.iq_file.is_file():
        parser.error(f"Missing IQ file: {args.iq_file}")
    if args.iq_file.stat().st_size % 2:
        parser.error("Incomplete IQ pair")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with args.iq_file.open("rb") as source:
        raw = np.frombuffer(source.read(2 * 1_310_720), dtype=np.uint8).astype(np.float32)
    iq = ((raw[::2] - 127.5) + 1j * (raw[1::2] - 127.5)) / 127.5
    frequency, psd = signal.welch(iq, fs=2_400_000, nperseg=16384,
                                 return_onesided=False)
    print("RF band powers (relative dB):")
    for low, high in ((-100, 100), (-200, -100), (100, 200),
                      (-400, -200), (200, 400)):
        selected = (frequency >= low * 1000) & (frequency < high * 1000)
        power = np.sum(psd[selected]) * 2_400_000 / 16384
        print(f"  {low:+} to {high:+} kHz: {10*np.log10(max(power,1e-30)):.2f}")
    for name in ("original", "narrow", "wide", "fir"):
        receiver = Receiver(name)
        audio = []
        with args.iq_file.open("rb") as source:
            while data := source.read(262_144):
                audio.append(receiver.process(IqBlock(
                    samples=data, center_frequency_hz=104_300_000,
                    sample_rate_hz=2_400_000, timestamp_ns=0
                )))
        pcm = np.concatenate(audio)
        samples = np.rint(pcm * 32767).astype("<i2")
        with wave.open(str(args.output_dir / f"{name}.wav"), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(48_000)
            wav.writeframes(samples.tobytes())
        print(f"{name}: {len(pcm)} samples; RMS={np.sqrt(np.mean(pcm.astype(np.float64)**2)):.6f}")
    print(f"WAV files: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
