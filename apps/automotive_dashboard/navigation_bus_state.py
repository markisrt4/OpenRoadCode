# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility export for standalone automotive dashboard clients."""

from common.telemetry.navigation_bus_state import NavigationBusSnapshot, NavigationBusState

__all__ = ["NavigationBusSnapshot", "NavigationBusState"]
