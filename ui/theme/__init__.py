# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Frontend-neutral UI theme contracts."""

from .theme_bundle import ThemeBundle
from .theme_mode import ThemeMode
from .theme_ui_if import ThemeUiIf
from .ui_theme import Color, UiTheme
from .vehicle_gauges import (
    VEHICLE_GAUGE_REDLINE_THEME,
    VEHICLE_GAUGE_THEME,
    VehicleGaugeRedlineTheme,
    VehicleGaugeTheme,
)

__all__ = [
    "VEHICLE_GAUGE_REDLINE_THEME",
    "VEHICLE_GAUGE_THEME",
    "VehicleGaugeRedlineTheme",
    "VehicleGaugeTheme",
    "Color",
    "StyleSheet",
    "ThemeBundle",
    "ThemeMode",
    "ThemeUiIf",
    "UiTheme",
    "load_style_sheet",
    "load_theme_bundle",
    "load_ui_theme",
]


def __getattr__(name: str):
    """Load CSS helpers only when requested. @param name Export. @return Exported helper."""
    if name in {"StyleSheet", "load_style_sheet", "load_theme_bundle", "load_ui_theme"}:
        from . import style_sheet
        value = getattr(style_sheet, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
