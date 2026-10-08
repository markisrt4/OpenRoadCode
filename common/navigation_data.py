# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Resolve the navigation dataset consistently for runtime and data tools."""
from __future__ import annotations

import os
from pathlib import Path


def navigation_data_root() -> Path:
    configured = os.environ.get('OPENROADCODE_DATA_ROOT')
    if configured:
        return Path(configured).expanduser()
    from common.xdg_paths import openroadcode_data_dir
    if os.environ.get('TERMUX_VERSION') or 'com.termux' in os.environ.get('PREFIX', ''):
        return openroadcode_data_dir()
    if Path('/srv/openroadcode/maps/search/openroadcode-search.sqlite').is_file():
        return Path('/srv/openroadcode')
    return openroadcode_data_dir()


def search_database_path() -> Path:
    return navigation_data_root() / 'maps/search/openroadcode-search.sqlite'
