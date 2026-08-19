# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import colorsys

from common.color.color_types import HsvColor, RgbColor


def rgb_to_hex(color: RgbColor) -> str:
    """Return the canonical upper-case ``#RRGGBB`` representation."""
    return f"#{color.red:02X}{color.green:02X}{color.blue:02X}"


def hex_to_rgb(value: str) -> RgbColor:
    """Parse ``#RRGGBB`` or ``RRGGBB`` text into an RGB color."""
    if not isinstance(value, str):
        raise TypeError("hex color must be a string")
    normalized = value.strip().removeprefix("#")
    if len(normalized) != 6:
        raise ValueError("hex color must contain exactly 6 hexadecimal digits")
    try:
        packed = int(normalized, 16)
    except ValueError as exc:
        raise ValueError("hex color contains non-hexadecimal characters") from exc
    return RgbColor(
        red=(packed >> 16) & 0xFF,
        green=(packed >> 8) & 0xFF,
        blue=packed & 0xFF,
    )


def rgb_to_hsv(color: RgbColor) -> HsvColor:
    """Convert an RGB color to HSV."""
    hue, saturation, value = colorsys.rgb_to_hsv(
        color.red / 255.0,
        color.green / 255.0,
        color.blue / 255.0,
    )
    return HsvColor(
        hue_degrees=hue * 360.0,
        saturation=saturation,
        value=value,
    )


def hsv_to_rgb(color: HsvColor) -> RgbColor:
    """Convert an HSV color to RGB."""
    hue = (float(color.hue_degrees) % 360.0) / 360.0
    red, green, blue = colorsys.hsv_to_rgb(
        hue,
        float(color.saturation),
        float(color.value),
    )
    return RgbColor(
        red=round(red * 255),
        green=round(green * 255),
        blue=round(blue * 255),
    )
