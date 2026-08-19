# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AudioFrame:
    """A block of mono floating-point PCM samples."""

    samples: tuple[float, ...]
    sample_rate_hz: int


class AudioCaptureIf(ABC):
    """Interface for capturing PCM audio independently of the audio backend."""

    @abstractmethod
    def start(self) -> None:
        """Start capturing audio."""

    @abstractmethod
    def read(self) -> AudioFrame:
        """Return the next block of captured PCM samples."""

    @abstractmethod
    def stop(self) -> None:
        """Stop capturing audio and release resources."""
