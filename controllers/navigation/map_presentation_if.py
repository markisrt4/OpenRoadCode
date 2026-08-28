# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Public interface for presenting geographic locations on a map."""

from __future__ import annotations

from abc import ABC, abstractmethod


class MapPresentationIf(ABC):
    """Present geographic navigation context without prescribing a map backend."""

    @abstractmethod
    def focus_location(
        self,
        latitude: float,
        longitude: float,
        *,
        altitude_m: float | None = None,
    ) -> None:
        """Center the presentation on a geographic location.

        @param latitude Geographic latitude in degrees.
        @param longitude Geographic longitude in degrees.
        @param altitude_m Optional altitude above mean sea level in meters.
        """
        ...
