# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Common types for software-defined radio IQ sources."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SdrCapabilities:
    """Describe tuning and sampling capabilities exposed by an SDR source."""

    min_frequency_hz: int
    max_frequency_hz: int
    supported_sample_rates_hz: tuple[int, ...] = ()
    min_sample_rate_hz: int | None = None
    max_sample_rate_hz: int | None = None
    supports_manual_gain: bool = False


@dataclass(frozen=True)
class IqBlock:
    """A block of interleaved raw I/Q sample bytes plus capture metadata."""

    samples: bytes
    center_frequency_hz: int
    sample_rate_hz: int
    timestamp_ns: int
