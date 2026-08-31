# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic requests emitted by an interactive map UI."""

from abc import ABC, abstractmethod

from ui.navigation.map_ui_if import GeoPoint


class MapRequestHandlerIf(ABC):
    """Handle map camera and style requests without renderer coupling."""

    @abstractmethod
    def request_follow(self, enabled: bool) -> None:
        """Request whether the map camera follows current position.

        @param enabled True to follow the vehicle; False for manual camera mode.
        """
        ...

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
    def request_pan(self, north_m: float, east_m: float) -> None:
        """Request a geographic camera pan.

        @param north_m Distance north in metres.
        @param east_m Distance east in metres.
        """
        ...

    @abstractmethod
    def request_pan_screen(self, right_px: float, up_px: float) -> None:
        """Request a camera pan in screen-relative pixels.

        The handler owns conversion from viewport-relative movement to geographic
        movement so UI implementations do not duplicate zoom, latitude, or
        bearing math.

        @param right_px Positive pixels move the camera toward screen-right.
        @param up_px Positive pixels move the camera toward screen-up.
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
