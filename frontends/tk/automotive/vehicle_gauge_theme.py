# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Resolve automotive gauge rendering colors from an ORC stylesheet."""

from __future__ import annotations

from dataclasses import replace

from apps.common.uiTheme import VEHICLE_GAUGE_THEME, VehicleGaugeTheme
from ui.theme import StyleSheet


def vehicle_gauge_theme_from_style_sheet(
    sheet: StyleSheet,
) -> VehicleGaugeTheme:
    """Build a gauge theme from the .automotive-gauge CSS rule."""

    values = sheet.declarations(".automotive-gauge")
    root = sheet.declarations(":root")

    background = values.get("background", root["--background"])
    foreground = values.get("color", root["--text"])
    face = values.get("--gauge-face", VEHICLE_GAUGE_THEME.face_color)
    bezel = values.get("--gauge-bezel", VEHICLE_GAUGE_THEME.bezel_mid)
    tick = values.get("--gauge-tick", foreground)
    needle = values.get("--gauge-needle", VEHICLE_GAUGE_THEME.needle_body)

    return replace(
        VEHICLE_GAUGE_THEME,
        background_color=background,
        panel_foreground=foreground,
        face_color=face,
        foreground_color=tick,
        primary_text=foreground,
        normal_value=foreground,
        endpoint_text=tick,
        performance_label=tick,
        bezel_mid=bezel,
        bezel_midlight=bezel,
        needle_body=needle,
        needle_outline=needle,
    )
