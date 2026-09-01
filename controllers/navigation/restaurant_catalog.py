# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility imports for the POI restaurant catalog.

New code should import from ``controllers.poi.restaurant_catalog``.
"""

from controllers.poi.restaurant_catalog import (
    RESTAURANTS,
    RestaurantDestination,
    resolve_restaurant_poi,
)

__all__ = ["RESTAURANTS", "RestaurantDestination", "resolve_restaurant_poi"]
