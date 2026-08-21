# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Common Unix-epoch timestamp wire representation."""

from __future__ import annotations

from datetime import datetime, timezone

NANOSECONDS_PER_SECOND = 1_000_000_000
NANOSECONDS_PER_MICROSECOND = 1_000


def encode_timestamp(timestamp: datetime) -> dict[str, int]:
    """Encode a datetime as unsigned Unix epoch seconds plus nanoseconds.

    Wire contract:
      * seconds: uint64 whole seconds since 1970-01-01T00:00:00 UTC
      * nanoseconds: uint32 fractional nanoseconds, range 0..999,999,999

    Python's datetime has microsecond resolution, so nanoseconds produced from a
    datetime are currently multiples of 1,000. The wire contract intentionally
    preserves nanosecond capacity for future higher-resolution sources.
    """
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)

    epoch_seconds = int(timestamp.timestamp())
    if epoch_seconds < 0:
        raise ValueError("OpenRoadCode wire timestamps cannot precede Unix epoch")

    nanoseconds = timestamp.microsecond * NANOSECONDS_PER_MICROSECOND
    if not 0 <= nanoseconds < NANOSECONDS_PER_SECOND:
        raise ValueError("timestamp nanoseconds are outside the uint32 contract range")

    return {
        "seconds": epoch_seconds,
        "nanoseconds": nanoseconds,
    }
