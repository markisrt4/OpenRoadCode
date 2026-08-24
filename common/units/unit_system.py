# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Presentation unit-system selection shared by OpenRoadCode frontends."""

from enum import StrEnum


class UnitSystem(StrEnum):
    """Select presentation units while domain and contract data remain SI."""

    IMPERIAL = "imperial"
    METRIC = "metric"
