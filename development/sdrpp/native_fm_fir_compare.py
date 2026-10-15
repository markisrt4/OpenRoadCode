# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""A/B test ORC IIR channel filtering against liquid-dsp FIR decimation.

Both paths use liquid-dsp freqdem, identical ORC audio filtering, and the
same recorded IQ. Optional offset tuning mixes before either RF filter.
Requires libliquid-dev, numpy, scipy. Experimental, not production code.
"""

from __future__ import annotations

import argparse
import ctypes as C
from pathlib import Path
import time

import numpy as np
from scipy import signal
from scipy.io import wavfile

from development.sdrpp.native_fm_liquid_compare import LiquidReceiver, liquid_library
from hardware_io.sdr import IqBlock

RATE = 2_400_000
CHUNK_SAMPLES = 131_072


class FirDecimator:
    """Stateful complex FIR decimator using liquid-dsp firdecim_crcf."""

    def __init__(self, lib, factor, taps):
        self.lib = lib
        self.factor = factor
        self.pending = np.empty(0, dtype=np.complex64)
        self.lib.firdecim_crcf_create.argtypes = [C.c_uint, C.c_void_p, C.c_uint]
        self.lib.firdecim_crcf_create.restype = C.c_void_p
        self.lib.firdecim_crcf_execute_block.argtypes = [
            C.c_void_p, C.c_void_p, C.c_uint, C.c_void_p
        ]
        self.lib.firdecim_crcf_execute_block.restype = C.c_int
        self.lib.firdecim_crcf_destroy.argtypes = [C.c_void_p]
        self.lib.firdecim_crcf_destroy.restype = C.c_int
        # liquid complex-float is two interleaved float32 values.
        coefficients = np.ascontiguousarray(taps, dtype=np.float32)
        self.handle = self.lib.firdecim_crcf_create(
            factor, C.c_void_p(coefficients.ctypes.data), len(coefficients)
        )
        if not self.handle:
            raise RuntimeError("firdecim_crcf_create failed")

    def process(self, samples):
        samples = np.concatenate((self.pending, np.asarray(samples, dtype=np.complex64)))
        count = len(samples) // self.factor
        consumed = count * self.factor
        self.pending = samples[consumed:].copy()
        if not count:
            return np.empty(0, dtype=np.complex64)
        source = np.ascontiguousarray(samples[:consumed])
        output = np.empty(count, dtype=np.complex64)
        status = self.lib.firdecim_crcf_execute_block(
            self.handle, C.c_void_p(source.ctypes.data),
            count, C.c_void_p(output.ctypes.data)
        )
        if status != 0:
            raise RuntimeError(f"firdecim_crcf_execute_block failed: {status}")
        return output

    def close(self):
        if self.handle:
            self.lib.firdecim_crcf_destroy(self.handle)
            self.handle = None


class LiquidFirReceiver(LiquidReceiver):
    """Use liquid FIR decimators instead of ORC's RF IIR filters."""

    def __init__(self):
        super().__init__()
        try:
            self.decimators = [
                FirDecimator(self.lib, 5, signal.firwin(
                    321, 185_000, fs=RATE, window=("kaiser", 8.6)
                )),
                FirDecimator(self.lib, 2, signal.firwin(
                    161, 95_000, fs=480_000, window=("kaiser", 8.6)
                )),
            ]
        except Exception:
            self.close()
            raise

    def close(self):
        for stage in getattr(self, "decimators", []):
            stage.close()
        super().close()

    def process(self, block):
        raw = np.frombuffer(block.samples, dtype=np.uint8).astype(np.float32)
        samples = ((raw[::2] - 127.5) + 1j * (raw[1::2] - 127.5)) / 127.5
        return self.process_complex(samples)

    def process_complex(self, samples):
        for stage in self.decimators:
            samples = stage.process(samples)
        if not len(samples):
            return np.empty(0, dtype=np.float32)
        iq = np.ascontiguousarray(samples, dtype=np.complex64)
        fm = np.empty(len(iq), dtype=np.float32)
        status = self.lib.freqdem_demodulate_block(
            self.handle, C.c_void_p(iq.ctypes.data), len(iq),
            C.c_void_p(fm.ctypes.data)
        )
        if status != 0:
            raise RuntimeError(f"freqdem_demodulate_block failed: {status}")
        audio, self.audio_zi = signal.sosfilt(self.audio_sos, fm, zi=self.audio_zi)
        n = len(audio)
        audio = audio[self.audio_phase::5]
        self.audio_phase = (self.audio_phase - n) % 5
        audio, self.de_zi = signal.lfilter(self.de_b, self.de_a, audio, zi=self.de_zi)
        return np.clip(audio, -1, 1).astype(np.float32)


class IirComplexReceiver(LiquidReceiver):
    """Original IIR RF stages with complex input to avoid re-quantizing mixer."""

    def process_complex(self, samples):
        for index, (factor, sos) in enumerate(self.rf_stages):
            samples, self.rf_zi[index] = signal.sosfilt(
                sos, samples, zi=self.rf_zi[index]
            )
            n = len(samples)
            samples = samples[self.rf_phase[index]::factor]
            self.rf_phase[index] = (self.rf_phase[index] - n) % factor
        if not len(samples):
            return np.empty(0, dtype=np.float32)
        iq = np.ascontiguousarray(samples, dtype=np.complex64)
        fm = np.empty(len(iq), dtype=np.float32)
        status = self.lib.freqdem_demodulate_block(
            self.handle, C.c_void_p(iq.ctypes.data), len(iq),
            C.c_void_p(fm.ctypes.data)
        )
        if status != 0:
            raise RuntimeError(f"freqdem_demodulate_block failed: {status}")
        audio, self.audio_zi = signal.sosfilt(self.audio_sos, fm, zi=self.audio_zi)
        n = len(audio)
        audio = audio[self.audio_phase::5]
        self.audio_phase = (self.audio_phase - n) % 5
        audio, self.de_zi = signal.lfilter(self.de_b, self.de_a, audio, zi=self.de_zi)
        return np.clip(audio, -1, 1).astype(np.float32)


def compare(recording, output, offset_hz):
    decoders = {"iir_liquid": IirComplexReceiver(), "fir_liquid": LiquidFirReceiver()}
    try:
        for name, decoder in decoders.items():
            index = 0
            audio = []
            start = time.perf_counter()
            with recording.open("rb") as source:
                while chunk := source.read(CHUNK_SAMPLES * 2):
                    if len(chunk) % 2:
                        raise ValueError("Incomplete IQ sample")
                    raw = np.frombuffer(chunk, dtype=np.uint8).astype(np.float32)
                    iq = ((raw[::2] - 127.5) + 1j * (raw[1::2] - 127.5)) / 127.5
                    n = len(iq)
                    if offset_hz:
                        phase = -2j * np.pi * offset_hz / RATE
                        iq = iq * np.exp(phase * (np.arange(n) + index))
                    index += n
                    audio.append(decoder.process_complex(iq))
            samples = np.concatenate(audio)
            wavfile.write(str(output / f"{name}.wav"), 48_000, samples)
            print(f"{name}: {len(samples) / 48000:.2f}s audio; "
                  f"{time.perf_counter() - start:.2f}s processing; "
                  f"rms={np.sqrt(np.mean(samples ** 2)):.4f}")
    finally:
        for decoder in decoders.values():
            decoder.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iq-file", type=Path, required=True)
    parser.add_argument("--station-offset-khz", type=float, default=0,
                        help="Station minus hardware center; -200 for 104.3 at 104.5")
    parser.add_argument("--output", type=Path, default=Path("/tmp/orc-fir-compare"))
    args = parser.parse_args()
    if not args.iq_file.is_file():
        parser.error(f"IQ file not found: {args.iq_file}")
    args.output.mkdir(parents=True, exist_ok=True)
    compare(args.iq_file, args.output, args.station_offset_khz * 1000)
    print("Compare iir_liquid.wav vs fir_liquid.wav at matched playback volume.")


if __name__ == "__main__":
    main()
