# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Immutable radio presentation values shared by frontends and backends."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RadioProfilePreset:
    label: str
    frequency_hz: int
    mode_name: str
    bandwidth: int
    step_hz: int
    user_defined: bool = False


@dataclass(frozen=True)
class RadioProfile:
    key: str
    label: str
    group: str
    config_path: Path
    presets: tuple[RadioProfilePreset, ...]
