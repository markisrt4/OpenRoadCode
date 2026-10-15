# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Compare liquid-dsp's native FM discriminator against ORC on saved IQ.

Requires libliquid (e.g. libliquid-dev on Debian), numpy and scipy.
This is a diagnostic A/B experiment, not a production dependency.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

from controllers.radio.dsp.wbfm_mono_demodulator import WbfmMonoDemodulator
from hardware_io.sdr import IqBlock

IQ_RATE = 2_400_000
RF_RATE = 240_000
AUDIO_RATE = 48_000


def liquid_library():
    name = ctypes.util.find_library("liquid")
    if not name:
        raise RuntimeError("libliquid not found; install libliquid-dev")
    lib = ctypes.CDLL(name)
    lib.freqdem_create.argtypes = [ctypes.c_float]
    lib.freqdem_create.restype = ctypes.c_void_p
    lib.freqdem_demodulate_block.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p
    ]
    lib.freqdem_demodulate_block.restype = ctypes.c_int
    lib.freqdem_destroy.argtypes = [ctypes.c_void_p]
    lib.freqdem_destroy.restype = ctypes.c_int
    return lib


class LiquidReceiver:
    """Existing ORC RF/audio filters, replacing only the FM discriminator."""

    def __init__(self):
        self.lib = liquid_library()
        # liquid-dsp frequency demodulator returns phase difference / kf.
        self.kf = 2 * np.pi * 75_000 / RF_RATE
        self.handle = self.lib.freqdem_create(float(self.kf))
        if not self.handle:
            raise RuntimeError("freqdem_create failed")
        self.rf_stages = (
            (5, signal.iirdesign(180_000, 240_000, 1, 65, fs=IQ_RATE, output="sos")),
            (2, signal.iirdesign(95_000, 120_000, 1, 65, fs=480_000, output="sos")),
        )
        self.rf_zi = [np.zeros((len(sos), 2), dtype=np.complex128)
                      for _, sos in self.rf_stages]
        self.rf_phase = [0, 0]
        self.audio_sos = signal.iirdesign(15_000, 24_000, 1, 70,
                                         fs=RF_RATE, output="sos")
        self.audio_zi = np.zeros((len(self.audio_sos), 2))
        self.audio_phase = 0
        alpha = 1 - np.exp(-1 / (AUDIO_RATE * 75e-6))
        self.de_b = [alpha]
        self.de_a = [1, -(1 - alpha)]
        self.de_zi = np.zeros(1)

    def close(self):
        if self.handle:
            self.lib.freqdem_destroy(self.handle)
            self.handle = None

    def process(self, block):
        raw = np.frombuffer(block.samples, dtype=np.uint8).astype(np.float32)
        samples = ((raw[::2] - 127.5) + 1j * (raw[1::2] - 127.5)) / 127.5
        for stage, (factor, sos) in enumerate(self.rf_stages):
            samples, self.rf_zi[stage] = signal.sosfilt(
                sos, samples, zi=self.rf_zi[stage]
            )
            length = len(samples)
            samples = samples[self.rf_phase[stage]::factor]
            self.rf_phase[stage] = (self.rf_phase[stage] - length) % factor
        if not len(samples):
            return np.empty(0, dtype=np.float32)
        iq = np.ascontiguousarray(samples, dtype=np.complex64)
        fm = np.empty(len(iq), dtype=np.float32)
        status = self.lib.freqdem_demodulate_block(
            self.handle, ctypes.c_void_p(iq.ctypes.data),
            len(iq), ctypes.c_void_p(fm.ctypes.data)
        )
        if status != 0:
            raise RuntimeError(f"freqdem_demodulate_block failed: {status}")
        audio, self.audio_zi = signal.sosfilt(
            self.audio_sos, fm, zi=self.audio_zi
        )
        length = len(audio)
        audio = audio[self.audio_phase::5]
        self.audio_phase = (self.audio_phase - length) % 5
        audio, self.de_zi = signal.lfilter(
            self.de_b, self.de_a, audio, zi=self.de_zi
        )
        return np.clip(audio, -1, 1).astype(np.float32)


def render(path, decoder):
    parts = []
    with path.open("rb") as source:
        while chunk := source.read(262_144):
            if len(chunk) % 2:
                raise ValueError("IQ file has an incomplete sample")
            parts.append(decoder.process(IqBlock(chunk, 104_300_000, IQ_RATE, 0)))
    return np.concatenate(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iq-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("/tmp/orc-liquid"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    liquid = LiquidReceiver()
    try:
        wavfile.write(str(args.output / "liquid.wav"), AUDIO_RATE,
                      render(args.iq_file, liquid))
    finally:
        liquid.close()
    wavfile.write(str(args.output / "orc.wav"), AUDIO_RATE,
                  render(args.iq_file, WbfmMonoDemodulator()))
    print(f"Compare {args.output / 'orc.wav'} and {args.output / 'liquid.wav'}")
    print("Both use identical ORC RF/audio filters; only the FM discriminator differs.")


if __name__ == "__main__":
    main()
