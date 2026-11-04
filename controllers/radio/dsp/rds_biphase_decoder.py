# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Streaming RDS biphase polarity and differential bit decoding."""

from __future__ import annotations

import numpy as np


class RdsBiphaseDecoder:
    """Decode aligned pairs of half-bit BPSK symbols.

    The caller must establish the half-bit pair phase. A valid biphase pair
    contains opposite signs. Invalid pairs are reported as erasures and
    reset differential history, rather than being silently decoded.
    The decoded data convention is: differential 1 means a transition.
    """

    def __init__(self, *, pair_phase: int = 0, invert: bool = False) -> None:
        if pair_phase not in (0, 1):
            raise ValueError("pair_phase must be 0 or 1")
        self._pair_phase = pair_phase
        self._invert = bool(invert)
        self.reset()

    def reset(self) -> None:
        self._skip = self._pair_phase
        self._pending: int | None = None
        self._previous: int | None = None
        self.invalid_pairs = 0

    def process(self, half_bits: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return (decoded_bits, valid_mask), one entry per complete pair.

        A first valid pair following reset or an erasure has no preceding
        differential reference and is marked invalid.
        """
        samples = np.asarray(half_bits)
        if samples.ndim != 1 or not np.issubdtype(samples.dtype, np.number):
            raise ValueError("expected one-dimensional numeric half-bit samples")
        if not np.all(np.isfinite(samples)):
            raise ValueError("half-bit samples must be finite")
        bits: list[int] = []
        valid: list[bool] = []
        for sample in samples:
            if self._skip:
                self._skip -= 1
                continue
            sign = int(np.real(sample) >= 0)
            if self._pending is None:
                self._pending = sign
                continue
            first = self._pending
            self._pending = None
            if first == sign:
                self.invalid_pairs += 1
                self._previous = None
                bits.append(0)
                valid.append(False)
                continue
            # Differential encoding is applied to the biphase bit stream.
            encoded = first ^ int(self._invert)
            if self._previous is None:
                bits.append(0)
                valid.append(False)
            else:
                bits.append(encoded ^ self._previous)
                valid.append(True)
            self._previous = encoded
        return np.asarray(bits, dtype=np.uint8), np.asarray(valid, dtype=np.bool_)
