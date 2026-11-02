# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compare WBFM decoding of identical IQ with different block boundaries."""

from __future__ import annotations

import argparse
from pathlib import Path
import wave

import numpy as np

from controllers.radio.dsp.wbfm_mono_demodulator import WbfmMonoDemodulator
from hardware_io.sdr import IqBlock


def decode(raw: bytes, block_bytes: int) -> np.ndarray:
    receiver = WbfmMonoDemodulator()
    chunks = []
    for offset in range(0, len(raw), block_bytes):
        chunk = raw[offset:offset + block_bytes]
        if not chunk:
            break
        block = IqBlock(
            samples=chunk,
            center_frequency_hz=104_300_000,
            sample_rate_hz=2_400_000,
            timestamp_ns=0,
        )
        chunks.append(receiver.process(block))
    return np.concatenate(chunks) if chunks else np.empty(0, dtype=np.float32)


def write_wav(path: Path, samples: np.ndarray) -> None:
    pcm = np.rint(np.clip(samples, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(48_000)
        output.writeframes(pcm.tobytes())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iq-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("wbfm-block-check"))
    args = parser.parse_args()
    raw = args.iq_file.read_bytes()
    if not raw or len(raw) % 2:
        parser.error("IQ file must contain complete nonempty interleaved U8 IQ pairs")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Reference is a single contiguous call. Every other decode starts fresh.
    sizes = (len(raw), 262_144, 65_536, 1_048_576)
    reference = None
    for size in sizes:
        label = "whole" if size == len(raw) else str(size)
        pcm = decode(raw, size)
        write_wav(args.output_dir / f"{label}.wav", pcm)
        if reference is None:
            reference = pcm
            print(f"{label}: {len(pcm)} PCM samples (reference)")
            continue
        if len(pcm) != len(reference):
            print(f"{label}: LENGTH MISMATCH {len(pcm)} vs {len(reference)}")
            continue
        delta = pcm.astype(np.float64) - reference.astype(np.float64)
        print(f"{label}: RMS error={np.sqrt(np.mean(delta ** 2)):.9g} "
              f"max error={np.max(np.abs(delta)):.9g} "
              f"samples >1e-4={np.count_nonzero(np.abs(delta) > 1e-4)}")
    print(f"WAV files: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
