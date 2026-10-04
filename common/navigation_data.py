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
    if os.environ.get('PREFIX', '').startswith('/data/data/com.termux/'):
        return Path.home() / '.local/share/openroadcode'
    return Path('/srv/openroadcode')


def search_database_path() -> Path:
    return navigation_data_root() / 'maps/search/openroadcode-search.sqlite'
