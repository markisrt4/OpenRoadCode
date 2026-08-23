# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AudioFrame:
    """A mono PCM analysis window and the amount newly captured in it.

    ``new_sample_count`` distinguishes fresh PCM from samples retained for an
    overlapping FFT window. Sources that do not overlap may leave it unset.
    """

    samples: tuple[float, ...]
    sample_rate_hz: int
    new_sample_count: int | None = None


class AudioCaptureIf(ABC):
    """Interface for capturing PCM audio independently of the audio backend."""

    @abstractmethod
    def start(self) -> None:
        """Start capturing audio."""

    @abstractmethod
    def read(self) -> AudioFrame:
        """Return the next block of captured PCM samples.

        @return Analysis window with fresh-sample metadata.
        """

    @abstractmethod
    def stop(self) -> None:
        """Stop capturing audio and release resources."""
