# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Parse ELM327 ATMA monitor output without trusting damaged records."""

from __future__ import annotations

from dataclasses import dataclass

from protocols.can.can_frame import CanFrame
from protocols.can.compact_frame_parser import parse_compact_can_frame


@dataclass(frozen=True, slots=True)
class ElmMonitorParseResult:
    frames: tuple[CanFrame, ...]
    buffer_full_count: int
    data_error_count: int
    malformed_count: int


def parse_elm_monitor_output(raw: str) -> ElmMonitorParseResult:
    """Parse complete, space-separated CAN records from an ELM monitor dump.

    The KW905 may append '<DATA ERROR' to otherwise plausible lines. Those
    lines are rejected rather than being interpreted as valid CAN traffic.
    A final line without a line terminator is considered incomplete.
    """
    frames: list[CanFrame] = []
    buffer_full = data_errors = malformed = 0
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for index, original in enumerate(lines):
        line = original.strip()
        if not line:
            continue
        upper = line.upper()
        if "BUFFER FULL" in upper:
            buffer_full += 1
            continue
        if "DATA ERROR" in upper:
            data_errors += 1
            continue
        if upper in {">", "STOPPED", "ATMA", "OK"}:
            continue
        if index == len(lines) - 1 and not raw.endswith(("\r", "\n")):
            malformed += 1
            continue
        if upper.startswith(">"):
            upper = upper[1:].strip()
        parts = upper.split()
        if len(parts) < 2 or len(parts[0]) not in (3, 8):
            malformed += 1
            continue
        if any(len(part) != 2 for part in parts[1:]):
            malformed += 1
            continue
        try:
            frames.append(parse_compact_can_frame(
                "".join(parts), extended_id=len(parts[0]) == 8,
                includes_data_length=False,
            ))
        except ValueError:
            malformed += 1
    return ElmMonitorParseResult(tuple(frames), buffer_full, data_errors, malformed)
