# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Presentation unit systems supported by terminal automotive views."""

from enum import StrEnum


class UnitSystem(StrEnum):
    """Select presentation units while keeping domain telemetry in SI."""

    IMPERIAL = "imperial"
    METRIC = "metric"
