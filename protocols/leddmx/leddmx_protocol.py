# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol


class RgbColorValue(Protocol):
    """Structural RGB value accepted by the LEDDMX encoder."""

    red: int
    green: int
    blue: int


class PatternModeValue(Protocol):
    """Structural pattern mode exposing its protocol byte value."""

    value: int


class LedDmxProtocol:
    """Build packets for LEDDMX-00 and LEDDMX-03 controllers."""

    @staticmethod
    def power(enabled: bool) -> bytes:
        return bytes(
            [0x7B, 0xFF, 0x04, 0x03 if enabled else 0x02,
             0xFF, 0xFF, 0xFF, 0xFF, 0xBF]
        )

    @staticmethod
    def color(color: RgbColorValue) -> bytes:
        return bytes(
            [0x7B, 0xFF, 0x07, color.red, color.green,
             color.blue, 0x00, 0xFF, 0xBF]
        )

    @staticmethod
    def brightness(percent: int) -> bytes:
        value = _clamp(percent, 0, 100)
        adjusted = value * 32 // 100
        return bytes(
            [0x7B, 0xFF, 0x01, adjusted, value,
             0x00, 0xFF, 0xFF, 0xBF]
        )

    @staticmethod
    def color_temperature(percent: int) -> bytes:
        value = _clamp(percent, 0, 100)
        adjusted = value * 32 // 100
        return bytes(
            [0x7B, 0xFF, 0x09, adjusted, value,
             0xFF, 0xFF, 0xFF, 0xBF]
        )

    @staticmethod
    def pattern(index: int) -> bytes:
        value = _clamp(index, 0, 210)
        return bytes(
            [0x7B, 0xFF, 0x03, value,
             0xFF, 0xFF, 0xFF, 0xFF, 0xBF]
        )

    @staticmethod
    def mic_eq(eq_mode: int) -> bytes:
        value = _clamp(eq_mode, 0, 255)
        return bytes(
            [0x7B, 0xFF, 0x0B, value,
             0x00, 0xFF, 0xFF, 0xBF]
        )

    @staticmethod
    def custom_pattern_color(
        color: RgbColorValue,
        list_position: int,
        list_size: int,
    ) -> bytes:
        position = _clamp(list_position, 1, 255)
        size = _clamp(list_size, 1, 255)
        return bytes(
            [0x7B, position, 0x0E, 0xFD, color.red,
             color.green, color.blue, size, 0xBF]
        )

    @staticmethod
    def custom_pattern_mode(mode: PatternModeValue) -> bytes:
        return bytes(
            [0x7B, 0xFF, 0x13, mode.value,
             0xFF, 0xFF, 0xFF, 0xFF, 0xBF]
        )

    @staticmethod
    def custom_pattern_direction(is_forward: bool) -> bytes:
        direction = 0x00 if is_forward else 0x01
        return bytes(
            [0x7B, 0xFF, 0x0D, direction,
             0xFF, 0xFF, 0xFF, 0xFF, 0xBF]
        )

    @staticmethod
    def timing(
        *,
        hour: int,
        minute: int,
        mode: int,
        weekdays: Sequence[bool],
        list_position: int,
        now: datetime | None = None,
    ) -> bytes:
        if len(weekdays) != 7:
            raise ValueError(
                "weekdays must contain seven values, Monday first"
            )

        current = now or datetime.now()
        current_day = current.isoweekday()
        packed_day_and_position = (
            current_day << 4
        ) | _clamp(list_position, 0, 15)

        packed_weekdays = 0
        for index, enabled in enumerate(weekdays):
            if enabled:
                packed_weekdays |= 1 << index

        return bytes(
            [
                0x8B,
                packed_day_and_position,
                _clamp(mode, 0, 255),
                packed_weekdays,
                _clamp(hour, 0, 24),
                _clamp(minute, 0, 59),
                current.hour,
                current.minute,
                0xBF,
            ]
        )

    @staticmethod
    def timing_termination(
        list_size: int,
        now: datetime | None = None,
    ) -> bytes:
        current = now or datetime.now()
        return bytes(
            [
                0x7B,
                0xFF,
                0x10,
                current.isoweekday(),
                _clamp(list_size, 0, 255),
                0xFF,
                current.hour,
                current.minute,
                0xBF,
            ]
        )


def _clamp(value: int, lower: int, upper: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("protocol values must be integers")
    return max(lower, min(value, upper))
