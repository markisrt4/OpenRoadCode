# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""UI Theme module providing color schemes and fonts for the application."""

from .uiTheme import (
    COLORS, 
    FONT_FAMILY,
    FONTS,
    MENU_TILE_STYLE,
    CAR_UI_THEME,
    TOP_BAR_THEME,
    STATUS_BAR_THEME,
)

from .aircraft import AIRCRAFT_PANEL_THEME
from .lighting import LIGHTING_PANEL_THEME
from .radio import RADIO_PANEL_THEME
from .spotify import SPOTIFY_PANEL_THEME
from .weather import WEATHER_PANEL_THEME


__all__ = [
    "COLORS",
    "FONT_FAMILY",
    "FONTS",
    "MENU_TILE_STYLE",
    "CAR_UI_THEME",
    "TOP_BAR_THEME",
    "STATUS_BAR_THEME",
    "AIRCRAFT_PANEL_THEME",
    "LIGHTING_PANEL_THEME",
    "RADIO_PANEL_THEME",
    "SPOTIFY_PANEL_THEME",
    "WEATHER_PANEL_THEME",
]
