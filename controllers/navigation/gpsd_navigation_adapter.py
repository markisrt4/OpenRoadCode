# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility import for the renamed gpsd position source."""

from controllers.navigation.gpsd_position_source import GpsdPositionSource

GpsdNavigationAdapter = GpsdPositionSource

__all__ = ["GpsdNavigationAdapter"]
