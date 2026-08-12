# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from apps.common.uiTheme.uiTheme import COLORS

AIRCRAFT_PANEL_THEME = {
    "colors": {
        "background": COLORS["app_bg"],
    },
    "layout": {
        "columns": 2,
        "row": 0,
        "fill_weight": 1,
        "column_uniform": "aircraft_column",
        "row_uniform": "aircraft_row",
        "fill_both": "both",
        "sticky": "nsew",
    },
    "profiles": {
        "default": {
            "tile_padx": 10,
            "tile_pady": 10,
        },
    },
    "tiles": (
        {
            "key": "adsb",
            "action": "adsb",
            "title": "ADS-B",
            "subtitle": "Aircraft tracking",
            "detail": "Launch tar1090 web UI",
        },
        {
            "key": "airband_am",
            "action": "airband",
            "title": "AIRBAND AM",
            "subtitle": "Aircraft chatter",
            "detail": "Launch SDR++ airband receiver",
        },
    ),
}