# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from enum import Enum


class AutomotiveTelemetryProfile(str, Enum):
    """Semantic telemetry-priority hint for the automotive producer."""

    NORMAL = "normal"
    PERFORMANCE = "performance"
    ENGINE = "engine"
    ECU = "ecu"
    TRIP = "trip"
