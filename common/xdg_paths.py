# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Shared XDG base-directory resolution without filesystem side effects."""

from __future__ import annotations

import os
from pathlib import Path


def _home(variable: str, default: str) -> Path:
    value = os.environ.get(variable, "")
    if value and Path(value).is_absolute():
        return Path(value)
    return Path.home() / default


def xdg_config_home() -> Path:
    return _home("XDG_CONFIG_HOME", ".config")


def xdg_data_home() -> Path:
    return _home("XDG_DATA_HOME", ".local/share")


def xdg_cache_home() -> Path:
    return _home("XDG_CACHE_HOME", ".cache")


def xdg_state_home() -> Path:
    return _home("XDG_STATE_HOME", ".local/state")


def openroadcode_config_dir(*parts: str) -> Path:
    return xdg_config_home().joinpath("openroadcode", *parts)


def openroadcode_data_dir(*parts: str) -> Path:
    return xdg_data_home().joinpath("openroadcode", *parts)


def openroadcode_cache_dir(*parts: str) -> Path:
    return xdg_cache_home().joinpath("openroadcode", *parts)


def openroadcode_state_dir(*parts: str) -> Path:
    return xdg_state_home().joinpath("openroadcode", *parts)
