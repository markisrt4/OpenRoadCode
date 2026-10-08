# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Immutable radio presentation values shared by frontends and backends."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RadioProfileState:
    label: str
    frequency_hz: int
    mode_name: str
    profile_key: str
    profile_label: str
    rds: str | None = None
