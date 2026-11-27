# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Choose display symbols and theme accents for normalized weather conditions."""

from __future__ import annotations

from ui.theme import ThemeBundle


def weather_symbol(condition: str, *, nighttime: bool = False) -> str:
    """Return a compact Unicode symbol for a normalized condition label."""
    text = condition.lower()
    if "thunder" in text:
        return "ϟ"
    if "snow" in text or "sleet" in text:
        return "✣"
    if "rain" in text or "drizzle" in text or "shower" in text:
        return "●≋"
    if "fog" in text or "mist" in text:
        return "≋≋"
    if "clear" in text or "sun" in text:
        return "◒" if nighttime else "✹"
    if "partly" in text:
        return "◒☁" if nighttime else "✹☁"
    if "cloud" in text or "overcast" in text:
        return "☁"
    return "◌"


def weather_accent(condition: str, theme: ThemeBundle) -> str:
    """Choose a semantic accent while staying inside the ORC theme palette."""
    text = condition.lower()
    ui = theme.ui
    if "thunder" in text:
        return ui.accent_danger
    if "rain" in text or "drizzle" in text or "shower" in text:
        return ui.accent_primary
    if "snow" in text or "sleet" in text:
        return ui.text
    if "fog" in text or "mist" in text:
        return ui.text_muted
    if "clear" in text or "sun" in text:
        return "#e5a100"
    if "partly" in text:
        return "#d39a20"
    if "cloud" in text or "overcast" in text:
        return "#70869a"
    return ui.text_muted
