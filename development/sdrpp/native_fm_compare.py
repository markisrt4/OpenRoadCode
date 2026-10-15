# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Capture one RTL-SDR IQ recording and compare WBFM DSP variants offline.

Requires numpy and scipy; recording additionally requires librtlsdr and a dongle.
Each WAV is generated from the same IQ data, without live audio playback.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import time

import numpy as np
from scipy.io import wavfile
from scipy import signal

from controllers.radio.dsp.wbfm_mono_demodulator import WbfmMonoDemodulator
from hardware_io.sdr import IqBlock, RtlSdrSource

RATE = 2_400_000
AUDIO_RATE = 48_000
VARIANTS = ("original", "current", "no_dc", "limited", "limited_dc")


class ConfigurableDemodulator(WbfmMonoDemodulator):
    """Use the production filter chain, with switchable DC and FM limiting."""

    def __init__(self, *, dc: bool, limiter: bool) -> None:
        super().__init__()
        self.dc_enabled = dc
        self.limiter_enabled = limiter

    def process(self, block: IqBlock) -> np.ndarray:
        if block.sample_rate_hz != RATE or len(block.samples) % 2:
            raise ValueError("Expected complete 2.4 MSPS IQ")
        raw = np.frombuffer(block.samples, dtype=np.uint8).astype(np.float32)
        samples = (((raw[::2] - 127.5) + 1j * (raw[1::2] - 127.5)) / 127.5).astype(np.complex64)
        for stage, (factor, sos) in enumerate(self._rf_stages):
            samples, self._rf_states[stage] = signal.sosfilt(
                sos, samples, zi=self._rf_states[stage]
            )
            count = len(samples)
            samples = samples[self._rf_phases[stage]::factor]
            self._rf_phases[stage] = (self._rf_phases[stage] - count) % factor
        if not len(samples):
            return np.empty(0, dtype=np.float32)
        if self.dc_enabled:
            dc, _ = signal.lfilter(
                [self._dc_alpha], [1, -(1 - self._dc_alpha)],
                samples, zi=[self._dc_state * (1 - self._dc_alpha)]
            )
            self._dc_state = complex(dc[-1])
            samples = samples - dc
        if self.limiter_enabled:
            samples = samples / np.maximum(np.abs(samples), 1e-6)
        previous = np.concatenate((
            np.asarray([self._previous_iq if self._previous_iq is not None else samples[0]]),
            samples[:-1],
        ))
        self._previous_iq = complex(samples[-1])
        discriminator = np.angle(samples * np.conj(previous))
        audio, self._audio_state = signal.sosfilt(
            self._audio_sos, discriminator, zi=self._audio_state
        )
        count = len(audio)
        audio = audio[self._audio_phase::5]
        self._audio_phase = (self._audio_phase - count) % 5
        audio *= 240_000 / (2 * np.pi * 75_000)
        audio, self._deemphasis_state = signal.lfilter(
            self._deemphasis_b, self._deemphasis_a, audio,
            zi=self._deemphasis_state,
        )
        return np.clip(audio, -1, 1).astype(np.float32)


class OriginalDemodulator:
    """Original full-rate FIR implementation, retained for A/B testing."""

    def __init__(self) -> None:
        self.rf_taps = signal.firwin(129, 100_000, fs=RATE)
        self.audio_taps = signal.firwin(129, 15_000, fs=240_000)
        self.rf_state = np.zeros(128, dtype=np.complex128)
        self.audio_state = np.zeros(128)
        self.rf_phase = 0
        self.audio_phase = 0
        self.previous = None
        alpha = 1 - np.exp(-1 / (AUDIO_RATE * 75e-6))
        self.deemphasis_b = [alpha]
        self.deemphasis_a = [1, -(1 - alpha)]
        self.deemphasis_state = np.zeros(1)

    def process(self, block: IqBlock) -> np.ndarray:
        raw = np.frombuffer(block.samples, dtype=np.uint8).astype(np.float32)
        iq = ((raw[::2] - 127.5) + 1j * (raw[1::2] - 127.5)) / 127.5
        rf, self.rf_state = signal.lfilter(self.rf_taps, [1], iq, zi=self.rf_state)
        count = len(rf)
        rf = rf[self.rf_phase::10]
        self.rf_phase = (self.rf_phase - count) % 10
        if not len(rf):
            return np.empty(0, dtype=np.float32)
        previous = np.concatenate((
            np.asarray([self.previous if self.previous is not None else rf[0]]),
            rf[:-1],
        ))
        self.previous = complex(rf[-1])
        discriminator = np.angle(rf * np.conj(previous))
        audio, self.audio_state = signal.lfilter(
            self.audio_taps, [1], discriminator, zi=self.audio_state
        )
        count = len(audio)
        audio = audio[self.audio_phase::5]
        self.audio_phase = (self.audio_phase - count) % 5
        audio *= 240_000 / (2 * np.pi * 75_000)
        audio, self.deemphasis_state = signal.lfilter(
            self.deemphasis_b, self.deemphasis_a, audio,
            zi=self.deemphasis_state,
        )
        return np.clip(audio, -1, 1).astype(np.float32)



class WideDemodulator:
    """480 kSPS discriminator to retain a wider broadcast FM channel."""

    def __init__(self):
        self.rf = signal.iirdesign(180_000, 240_000, 1, 65, fs=RATE, output="sos")
        self.rf_zi = np.zeros((len(self.rf), 2), dtype=complex)
        self.rf_phase = 0
        self.audio = signal.iirdesign(15_000, 24_000, 1, 70, fs=480_000, output="sos")
        self.audio_zi = np.zeros((len(self.audio), 2))
        self.audio_phase = 0
        self.prev = None
        a = 1 - np.exp(-1 / (AUDIO_RATE * 75e-6))
        self.de_b, self.de_a, self.de_zi = [a], [1, -(1-a)], np.zeros(1)

    def process(self, block):
        raw = np.frombuffer(block.samples, dtype=np.uint8).astype(np.float32)
        iq = (raw[::2] - 127.5 + 1j * (raw[1::2] - 127.5)) / 127.5
        rf, self.rf_zi = signal.sosfilt(self.rf, iq, zi=self.rf_zi)
        n = len(rf)
        rf = rf[self.rf_phase::5]
        self.rf_phase = (self.rf_phase - n) % 5
        if not len(rf):
            return np.empty(0, dtype=np.float32)
        prev = np.concatenate(([self.prev if self.prev is not None else rf[0]], rf[:-1]))
        self.prev = complex(rf[-1])
        fm = np.angle(rf * np.conj(prev))
        audio, self.audio_zi = signal.sosfilt(self.audio, fm, zi=self.audio_zi)
        n = len(audio)
        audio = audio[self.audio_phase::10]
        self.audio_phase = (self.audio_phase - n) % 10
        audio *= 480_000 / (2 * np.pi * 75_000)
        audio, self.de_zi = signal.lfilter(self.de_b, self.de_a, audio, zi=self.de_zi)
        return np.clip(audio, -1, 1).astype(np.float32)


class OffsetDemodulator:
    """Mix the station to DC before running the selected demodulator."""

    def __init__(self, decoder, station_offset_hz):
        self.decoder = decoder
        self.station_offset_hz = station_offset_hz
        self.index = 0

    def process(self, block):
        raw = np.frombuffer(block.samples, dtype=np.uint8).astype(np.float32)
        iq = (raw[::2] - 127.5) + 1j * (raw[1::2] - 127.5)
        n = len(iq)
        phase = -2j * np.pi * self.station_offset_hz / RATE
        iq *= np.exp(phase * (np.arange(n) + self.index))
        self.index += n
        packed = np.empty(n * 2, dtype=np.uint8)
        packed[::2] = np.clip(np.rint(127.5 + iq.real), 0, 255)
        packed[1::2] = np.clip(np.rint(127.5 + iq.imag), 0, 255)
        return self.decoder.process(IqBlock(packed.tobytes(), block.center_frequency_hz, RATE, 0))


def capture(path: Path, frequency: int, gain: float | None, seconds: float) -> None:
    source = RtlSdrSource()
    remaining = round(seconds * RATE)
    try:
        source.open()
        source.set_sample_rate(RATE)
        source.set_center_frequency(frequency)
        source.set_gain(gain)
        source.start()
        with path.open("wb") as destination:
            while remaining > 0:
                block = source.read_iq()
                samples = min(remaining, len(block.samples) // 2)
                destination.write(block.samples[:samples * 2])
                remaining -= samples
    finally:
        source.close()


def run_variant(path: Path, decoder: object, recording: Path, frequency: int) -> dict:
    audio_blocks = []
    started = time.perf_counter()
    with recording.open("rb") as source:
        while chunk := source.read(262_144):
            if len(chunk) % 2:
                raise ValueError("IQ recording has an incomplete sample")
            audio_blocks.append(decoder.process(IqBlock(chunk, frequency, RATE, 0)))
    elapsed = time.perf_counter() - started
    audio = np.concatenate(audio_blocks)
    # Fixed amplitude across all variants: do not normalize individual WAVs.
    wavfile.write(str(path), AUDIO_RATE, audio)
    return {
        "variant": path.stem,
        "audio_seconds": round(len(audio) / AUDIO_RATE, 3),
        "processing_seconds": round(elapsed, 3),
        "realtime_ratio": round(elapsed / (len(audio) / AUDIO_RATE), 3),
        "rms": round(float(np.sqrt(np.mean(audio ** 2))), 5),
        "peak": round(float(np.max(np.abs(audio))), 5),
        "clipped_percent": round(float(np.mean(np.abs(audio) >= 0.999) * 100), 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frequency", type=int, default=104_300_000)
    parser.add_argument("--gain", type=float, default=None)
    parser.add_argument("--offset-khz", type=int, default=0)
    parser.add_argument("--seconds", type=float, default=5.0)
    parser.add_argument("--output", type=Path, default=Path("fm_comparison"))
    parser.add_argument("--iq-file", type=Path, help="Reuse existing raw unsigned 8-bit interleaved IQ")
    args = parser.parse_args()
    if abs(args.offset_khz) > 900:
        parser.error("offset must be within 900 kHz")
    if args.seconds <= 0:
        parser.error("--seconds must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    recording = args.iq_file or args.output / "capture.u8"
    if args.iq_file is None:
        print(f"Capturing {args.seconds:g}s at {(args.frequency + args.offset_khz * 1000) / 1e6:.3f} MHz, gain={args.gain} dB")
        capture(recording, args.frequency + args.offset_khz * 1000, args.gain, args.seconds)
    decoders = {
        "original": OriginalDemodulator(),
        "current": WbfmMonoDemodulator(),
        "no_dc": ConfigurableDemodulator(dc=False, limiter=False),
        "limited": ConfigurableDemodulator(dc=False, limiter=True),
        "limited_dc": ConfigurableDemodulator(dc=True, limiter=True),
        "wide": WideDemodulator(),
    }
    if args.offset_khz:
        decoders["offset_current"] = OffsetDemodulator(WbfmMonoDemodulator(), -args.offset_khz * 1000)
        decoders["offset_wide"] = OffsetDemodulator(WideDemodulator(), -args.offset_khz * 1000)
    results = []
    for name, decoder in decoders.items():
        result = run_variant(args.output / f"{name}.wav", decoder, recording, args.frequency)
        results.append(result)
        print(result)
    with (args.output / "results.csv").open("w", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"Compare WAV files in {args.output}; all use identical recorded IQ.")


if __name__ == "__main__":
    main()
