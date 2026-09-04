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

    # Component-specific card colors are optional. When a stylesheet does not
    # provide them, inherit the active application surface instead of falling
    # back to the legacy dark-only gauge palette. This keeps linear gauges and
    # the spaces between performance gauges correct in light mode.
    card_background = values.get("--linear-card-background", background)
    card_inner = values.get("--linear-card-inner", background)
    card_border = values.get(
        "--linear-card-border",
        root.get("--border", tick),
    )
    card_highlight = values.get(
        "--linear-card-highlight",
        root.get("--border", tick),
    )
    card_text = values.get("--linear-card-text", foreground)
    card_muted = values.get("--linear-card-muted", tick)

    return replace(
        VEHICLE_GAUGE_THEME,
        background_color=background,
        panel_background=background,
        panel_foreground=foreground,
        panel_inner=background,
        panel_border=root.get("--border", tick),
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
        linear_card_background=card_background,
        linear_card_inner=card_inner,
        linear_card_border=card_border,
        linear_card_highlight=card_highlight,
        linear_card_text=card_text,
        linear_card_muted=card_muted,
    )
