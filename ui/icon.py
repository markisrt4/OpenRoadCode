# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent semantic icon identifiers."""

from __future__ import annotations

from enum import Enum


class IconId(str, Enum):
    """Semantic icon names that any frontend may render in its native style."""

    RADIO = "radio"
    AIRCRAFT = "aircraft"
    AIRBAND_AM = "airband-am"
    GAUGES = "gauges"
    WEATHER = "weather"
    WEATHER_RADIO = "weather-radio"
    LIGHTING = "lighting"
    MEDIA = "media"
    FM_RADIO = "fm-radio"
    SCANNER_RADIO = "scanner-radio"
    SPOTIFY = "spotify"
    NETFLIX = "netflix"
    YOUTUBE = "youtube"
    POWER = "power"
    MICROPHONE = "microphone"
    CAMERA = "camera"
    DISPLAY = "display"
    BRIGHTNESS = "brightness"
    VOLUME = "volume"
    VOLUME_MUTED = "volume-muted"
