# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent icon selection for menu tiles."""

from __future__ import annotations

from ui.icon import IconId


_MENU_ICONS: dict[str, IconId] = {
    "radio": IconId.RADIO,
    "aircraft": IconId.AIRCRAFT,
    "adsb": IconId.AIRCRAFT,
    "airband_am": IconId.AIRBAND_AM,
    "gauges": IconId.GAUGES,
    "gauges_placeholder": IconId.GAUGES,
    "weather": IconId.WEATHER,
    "weather_dashboard": IconId.WEATHER,
    "noaa_weather_radio": IconId.WEATHER_RADIO,
    "lighting": IconId.LIGHTING,
    "media": IconId.MEDIA,
    "fm_radio": IconId.FM_RADIO,
    "scanner_radio": IconId.SCANNER_RADIO,
    "spotify": IconId.SPOTIFY,
    "netflix": IconId.NETFLIX,
    "youtube": IconId.YOUTUBE,
}


def menu_icon_for_key(key: str) -> IconId | None:
    """Return the semantic icon for a menu tile key, when one is known."""
    return _MENU_ICONS.get(key)
