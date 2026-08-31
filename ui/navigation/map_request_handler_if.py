# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic requests emitted by an interactive map UI."""

from abc import ABC, abstractmethod

from ui.navigation.map_ui_if import GeoPoint


class MapRequestHandlerIf(ABC):
    """Handle map camera, POI, and style requests without renderer coupling."""

    @abstractmethod
    def request_follow(self, enabled: bool) -> None:
        """Enable or disable automatic map following.

        @param enabled True to follow the current position; False for manual camera control.
        """
        ...

    @abstractmethod
    def request_recenter(self) -> None:
        """Recenter the map on the latest known follow position."""
        ...

    @abstractmethod
    def request_center_on(self, position: GeoPoint) -> None:
        """Center the map on a geographic position.

        @param position Geographic position to place at the map center.
        """
        ...

    @abstractmethod
    def request_pan(self, north_m: float, east_m: float) -> None:
        """Pan the map by geographic offsets.

        @param north_m Northward offset in meters.
        @param east_m Eastward offset in meters.
        """
        ...

    @abstractmethod
    def request_pan_screen(self, right_px: float, up_px: float) -> None:
        """Request a camera pan in screen-relative pixels.

        @param right_px Horizontal screen offset in pixels, positive to the right.
        @param up_px Vertical screen offset in pixels, positive upward.
        """
        ...

    @abstractmethod
    def request_zoom(self, zoom_level: float) -> None:
        """Set the requested map zoom level.

        @param zoom_level MapLibre-compatible zoom level.
        """
        ...

    @abstractmethod
    def request_bearing(self, bearing_rad: float) -> None:
        """Set the requested map bearing.

        @param bearing_rad Clockwise map bearing in radians.
        """
        ...

    @abstractmethod
    def request_pitch(self, pitch_rad: float) -> None:
        """Set the requested map camera pitch.

        @param pitch_rad Camera pitch in radians.
        """
        ...

    @abstractmethod
    def request_poi_focus(self, category: str | None) -> None:
        """Highlight a semantic POI category or clear the focus.

        @param category Semantic POI category to highlight, or None to clear focus.
        """
        ...

    @abstractmethod
    def request_style(self, style_id: str) -> None:
        """Select the active map style.

        @param style_id Identifier of the map style to activate.
        """
        ...
