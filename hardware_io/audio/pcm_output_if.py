# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Hardware-independent mono PCM output contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class PcmOutputIf(ABC):
    """Consumer of float32 mono PCM at a configured sample rate."""

    @abstractmethod
    def open(self, sample_rate_hz: int = 48_000) -> None:
        """Initialize output resources."""

    @abstractmethod
    def write(self, samples: np.ndarray) -> None:
        """Write one contiguous block of mono PCM; may block."""

    @abstractmethod
    def drain(self) -> None:
        """Wait until previously written PCM has finished playing."""

    @abstractmethod
    def close(self) -> None:
        """Release output resources; safe to call repeatedly."""
