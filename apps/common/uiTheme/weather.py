# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from apps.common.uiTheme.uiTheme import COLORS


WEATHER_PANEL_THEME = {
    "colors": {
        "background": COLORS["app_bg"],
    },
    "layout": {
        "columns": 2,
        "row": 0,
        "dashboard_column": 0,
        "noaa_column": 1,
        "fill_weight": 1,
        "column_uniform": "weather_column",
        "row_uniform": "weather_row",
        "fill_both": "both",
        "sticky": "nsew",
        "dashboard_key": "weather_dashboard",
        "dashboard_title": "WEATHER DASHBOARD",
        "dashboard_subtitle": "Forecast display",
        "dashboard_detail": "Toggle Streamlit kiosk",
        "noaa_key": "noaa_weather_radio",
        "noaa_title": "NOAA WEATHER RADIO",
        "noaa_subtitle": "Weather band SDR",
        "noaa_detail": "Toggle SDR++ at NOAA preset",
    },
    "profiles": {
        "default": {
            "tile_padx": 10,
            "tile_pady": 10,
        },
    },
}
