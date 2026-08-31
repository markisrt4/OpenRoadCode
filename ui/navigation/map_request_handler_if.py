# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic requests emitted by an interactive map UI."""

from abc import ABC, abstractmethod

from ui.navigation.map_ui_if import GeoPoint


class MapRequestHandlerIf(ABC):
    """Handle map camera, POI, and style requests without renderer coupling."""

    @abstractmethod
    def request_follow(self, enabled: bool) -> None: ...

    @abstractmethod
    def request_recenter(self) -> None: ...

    @abstractmethod
    def request_center_on(self, position: GeoPoint) -> None: ...

    @abstractmethod
    def request_pan(self, north_m: float, east_m: float) -> None: ...

    @abstractmethod
    def request_pan_screen(self, right_px: float, up_px: float) -> None:
        """Request a camera pan in screen-relative pixels."""
        ...

    @abstractmethod
    def request_zoom(self, zoom_level: float) -> None: ...

    @abstractmethod
    def request_bearing(self, bearing_rad: float) -> None: ...

    @abstractmethod
    def request_pitch(self, pitch_rad: float) -> None: ...

    @abstractmethod
    def request_poi_focus(self, category: str | None) -> None:
        """Highlight a semantic POI category, or clear focus with None."""
        ...

    @abstractmethod
    def request_style(self, style_id: str) -> None: ...
