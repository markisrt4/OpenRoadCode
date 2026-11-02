# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Offline WBFM low-magnitude phase-protection listening comparison.

Uses production RF and audio filters; changes only the discriminator input/output.
Experimental variants are NOT production fixes. A complex limiter should be
mathematically phase-invariant and acts as a negative control.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import wave

import numpy as np
from scipy import signal

from controllers.radio.dsp.wbfm_mono_demodulator import WbfmMonoDemodulator
from hardware_io.sdr import IqBlock, IqSampleFormat


class ExperimentalReceiver(WbfmMonoDemodulator):
    def __init__(self, variant: str):
        super().__init__()
        self.variant = variant
        self.modified = 0
        self.total = 0
        self._previous_phase = 0.0

    def process(self, block: IqBlock) -> np.ndarray:
        if block.sample_format != IqSampleFormat.U8_INTERLEAVED:
            raise ValueError("Expected U8 interleaved IQ")
        if block.sample_rate_hz != self.sample_rate_hz or len(block.samples) % 2:
            raise ValueError("Unexpected sample rate or incomplete IQ pair")
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
        dc, _ = signal.lfilter(
            [self._dc_alpha], [1, -(1 - self._dc_alpha)],
            samples, zi=[self._dc_state * (1 - self._dc_alpha)]
        )
        self._dc_state = complex(dc[-1])
        samples = samples - dc
        magnitude = np.abs(samples)

        if self.variant == "limiter":
            # Normalizing the complex amplitude should not change its phase.
            samples = samples / np.maximum(magnitude, 1e-9)

        if self._previous_iq is None:
            previous = np.concatenate((samples[:1], samples[:-1]))
        else:
            previous = np.concatenate(([self._previous_iq], samples[:-1]))
        self._previous_iq = complex(samples[-1])
        discriminator = np.angle(samples * np.conj(previous))

        if self.variant in ("soft", "strong"):
            threshold = 0.1215 if self.variant == "soft" else 0.1408
            low = magnitude < threshold
            suspicious = low & (np.abs(discriminator) >= 1.0)
            self.modified += int(np.count_nonzero(suspicious))
            # Hold the preceding discriminator value for suspicious samples.
            # This deliberately simple strategy is diagnostic, not production DSP.
            # Avoid carrying an unmodified high-jump sample across a chunk boundary.
            replacement = self._previous_phase
            for idx in np.flatnonzero(suspicious):
                if idx > 0:
                    replacement = float(discriminator[idx - 1])
                discriminator[idx] = replacement
            self._previous_phase = float(discriminator[-1])
        self.total += len(discriminator)

        filtered, self._audio_state = signal.sosfilt(
            self._audio_sos, discriminator, zi=self._audio_state
        )
        length = len(filtered)
        audio = filtered[self._audio_phase::5]
        self._audio_phase = (self._audio_phase - length) % 5
        audio = audio * (240_000 / (2 * np.pi * 75_000))
        output, self._deemphasis_state = signal.lfilter(
            self._deemphasis_b, self._deemphasis_a, audio,
            zi=self._deemphasis_state
        )
        return np.clip(output, -1, 1).astype(np.float32)


def write_wav(path: Path, pcm: np.ndarray) -> None:
    data = np.rint(np.clip(pcm, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(48_000)
        wav.writeframes(data.tobytes())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iq-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("wbfm-protection"))
    parser.add_argument("--block-bytes", type=int, default=262_144)
    args = parser.parse_args()
    if args.block_bytes <= 0 or args.block_bytes % 2:
        parser.error("--block-bytes must be positive and even")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if not args.iq_file.is_file():
        parser.error(f"Missing IQ recording: {args.iq_file}")
    if args.iq_file.stat().st_size % 2:
        parser.error("IQ file has incomplete IQ pair")

    baseline = None
    for variant in ("original", "limiter", "soft", "strong"):
        receiver = ExperimentalReceiver(variant)
        outputs = []
        with args.iq_file.open("rb") as source:
            while block_bytes := source.read(args.block_bytes):
                block = IqBlock(
                    samples=block_bytes,
                    center_frequency_hz=104_300_000,
                    sample_rate_hz=2_400_000,
                    timestamp_ns=0,
                )
                outputs.append(receiver.process(block))
        pcm = np.concatenate(outputs) if outputs else np.empty(0, dtype=np.float32)
        if not len(pcm):
            parser.error("Recording was empty")
        write_wav(args.output_dir / f"{variant}.wav", pcm)
        if baseline is None:
            baseline = pcm
            print(f"{variant}: {len(pcm)} PCM samples (reference)")
        else:
            delta = pcm.astype(np.float64) - baseline.astype(np.float64)
            print(f"{variant}: RMS delta={np.sqrt(np.mean(delta**2)):.8g}, "
                  f"max delta={np.max(np.abs(delta)):.8g}, "
                  f"modified={receiver.modified}/{receiver.total} RF samples")
    print(f"WAV files: {args.output_dir.resolve()}")
    print("Compare at the same playback volume; differences do not prove improvement.")


if __name__ == "__main__":
    main()
