# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility aliases for the generalized position-source contract."""

from controllers.navigation.position_source_if import (
    PositionSourceIf,
    PositionStateCallback,
)

GpsStateCallback = PositionStateCallback
NavigationGpsSourceIf = PositionSourceIf

__all__ = ["GpsStateCallback", "NavigationGpsSourceIf"]
