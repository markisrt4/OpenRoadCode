# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Common Unix-epoch timestamp wire representation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

NANOSECONDS_PER_SECOND = 1_000_000_000
NANOSECONDS_PER_MICROSECOND = 1_000
UINT64_MAX = (1 << 64) - 1
UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class Timestamp:
    """Decoded OpenRoadCode wire timestamp."""

    seconds: int
    nanoseconds: int


def validate_timestamp(payload: Mapping[str, Any]) -> None:
    """Validate the common timestamp wire contract."""
    if set(payload) != {"seconds", "nanoseconds"}:
        raise ValueError("timestamp must contain exactly seconds and nanoseconds")

    seconds = payload["seconds"]
    nanoseconds = payload["nanoseconds"]

    if isinstance(seconds, bool) or not isinstance(seconds, int):
        raise ValueError("timestamp.seconds must be a uint64 integer")
    if not 0 <= seconds <= UINT64_MAX:
        raise ValueError("timestamp.seconds is outside uint64 range")

    if isinstance(nanoseconds, bool) or not isinstance(nanoseconds, int):
        raise ValueError("timestamp.nanoseconds must be a uint32 integer")
    if not 0 <= nanoseconds < NANOSECONDS_PER_SECOND:
        raise ValueError("timestamp.nanoseconds must be in range 0..999999999")


def decode_timestamp(payload: Mapping[str, Any]) -> Timestamp:
    """Validate and decode a common wire timestamp."""
    validate_timestamp(payload)
    return Timestamp(
        seconds=payload["seconds"],
        nanoseconds=payload["nanoseconds"],
    )


def encode_timestamp(timestamp: datetime) -> dict[str, int]:
    """Encode a datetime as unsigned Unix epoch seconds plus nanoseconds.

    Wire contract:
      * seconds: uint64 whole seconds since 1970-01-01T00:00:00 UTC
      * nanoseconds: uint32 fractional nanoseconds, range 0..999,999,999

    Naive datetimes are interpreted as UTC. Python's datetime has microsecond
    resolution, so nanoseconds produced from a datetime are currently multiples
    of 1,000. The wire contract intentionally preserves nanosecond capacity for
    future higher-resolution sources.
    """
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)

    if timestamp < UNIX_EPOCH:
        raise ValueError("OpenRoadCode wire timestamps cannot precede Unix epoch")

    delta = timestamp - UNIX_EPOCH
    epoch_seconds = delta.days * 86_400 + delta.seconds
    nanoseconds = timestamp.microsecond * NANOSECONDS_PER_MICROSECOND

    payload = {
        "seconds": epoch_seconds,
        "nanoseconds": nanoseconds,
    }
    validate_timestamp(payload)
    return payload
