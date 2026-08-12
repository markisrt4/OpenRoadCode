# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic requests emitted by an interactive map UI."""

from abc import ABC, abstractmethod

from ui.navigation.map_ui_if import GeoPoint


class MapRequestHandlerIf(ABC):
    """Handle map camera and style requests without renderer coupling."""

    @abstractmethod
    def request_recenter(self) -> None:
        """Request that the map follow the current position again."""
        ...

    @abstractmethod
    def request_center_on(self, position: GeoPoint) -> None:
        """Request that the map center on a geographic position.

        @param position Requested viewport center.
        """
        ...

    @abstractmethod
    def request_zoom(self, zoom_level: float) -> None:
        """Request an absolute renderer-neutral zoom level.

        @param zoom_level Requested map zoom level.
        """
        ...

    @abstractmethod
    def request_bearing(self, bearing_rad: float) -> None:
        """Request a clockwise map bearing from true north.

        @param bearing_rad Requested bearing in radians.
        """
        ...

    @abstractmethod
    def request_pitch(self, pitch_rad: float) -> None:
        """Request map camera pitch from nadir.

        @param pitch_rad Requested pitch in radians.
        """
        ...

    @abstractmethod
    def request_style(self, style_id: str) -> None:
        """Request an application-defined map style.

        @param style_id Stable map style identifier.
        """
        ...
