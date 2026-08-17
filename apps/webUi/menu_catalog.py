# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Menu models assembled for the OpenRoadCode web application."""

from ui.menu import MenuPage, MenuTile


def create_web_ui_menu_pages() -> dict[str, MenuPage]:
    """Return browser-safe menu pages with no hardware dependencies."""
    return {
        "main": MenuPage(
            title="OpenRoadCode",
            tiles=(
                MenuTile("radio", "RADIO", "FM / Scanner / NOAA", "Broadcast and monitoring"),
                MenuTile("aircraft", "AIRCRAFT", "ADS-B + Airband", "Traffic and chatter"),
                MenuTile("gauges", "GAUGES", "OBD-II / telemetry", "Vehicle dashboard"),
                MenuTile("weather", "WEATHER", "Forecast + alerts", "Conditions and warnings"),
                MenuTile("lighting", "LIGHTING", "Cabin / accent", "Lighting controls"),
                MenuTile("media", "MEDIA", "Spotify / audio", "Music and playback"),
            ),
            columns=3,
        ),
        "radio": MenuPage(
            title="Radio",
            tiles=(
                MenuTile("fm_radio", "FM RADIO", "FM broadcast radio", "Web radio screen"),
                MenuTile("scanner_radio", "SCANNER", "Radio monitoring", "Police / Fire / HAM / GMRS"),
                MenuTile("weather_radio", "NOAA WX", "Weather radio", "NOAA and alerts"),
            ),
            columns=3,
        ),
        "media": MenuPage(
            title="Media",
            tiles=(
                MenuTile("spotify", "SPOTIFY", "Streaming control", "Spotify integration"),
                MenuTile("netflix", "NETFLIX", "Streaming video", "Browser integration"),
                MenuTile("youtube", "YOUTUBE", "Video and search", "Browser integration"),
            ),
            columns=3,
        ),
        "gauges": MenuPage(
            title="Gauges",
            tiles=(
                MenuTile("vehicle_gauges", "VEHICLE", "Performance gauges", "OBD-II instruments"),
                MenuTile("offroad_dashboard", "OFF-ROAD", "Pitch / roll / trail", "Inclinometer and navigation"),
            ),
            columns=3,
        ),
    }
