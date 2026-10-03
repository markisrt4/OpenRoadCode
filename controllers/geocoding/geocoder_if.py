# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility exports for the canonical navigation geocoding contract."""

from controllers.navigation.geocoding import GeocodedLocation, GeocoderIf

__all__ = ["GeocodedLocation", "GeocoderIf"]
