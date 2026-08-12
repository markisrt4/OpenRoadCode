"""Adapt normalized position reports to map-renderer commands."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from controllers.navigation.navigation_state import PositionState
from protocols.map_renderer.map_renderer_client import (
    MapRendererClient,
    MapRendererUnavailableError,
)


LOGGER = logging.getLogger(__name__)


class MapPositionAdapter:
    """Display live position fixes with an optional follow camera."""

    def __init__(
        self,
        map_renderer: MapRendererClient,
        *,
        follow: bool = True,
        zoom: float = 16.5,
        pitch: float = 45.0,
        minimum_camera_interval_s: float = 0.25,
        minimum_course_speed_mps: float = 1.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if minimum_camera_interval_s < 0.0:
            raise ValueError("minimum_camera_interval_s must not be negative")
        if minimum_course_speed_mps < 0.0:
            raise ValueError("minimum_course_speed_mps must not be negative")

        self._map_renderer = map_renderer
        self._follow = follow
        self._zoom = zoom
        self._pitch = pitch
        self._minimum_camera_interval_s = minimum_camera_interval_s
        self._minimum_course_speed_mps = minimum_course_speed_mps
        self._clock = clock
        self._last_camera_update: float | None = None
        self._bearing = 0.0

    def update(self, state: PositionState) -> None:
        """Send one usable position report to the renderer.

        Reports without a 2D/3D fix are ignored. Renderer connection failures
        are logged instead of escaping into the GPS reader thread.
        """
        if (
            not state.has_fix
            or state.latitude_deg is None
            or state.longitude_deg is None
        ):
            return

        try:
            self._map_renderer.set_position(
                latitude=state.latitude_deg,
                longitude=state.longitude_deg,
            )

            if not self._follow or not self._camera_update_due():
                return

            if (
                state.course_deg is not None
                and state.speed_mps is not None
                and state.speed_mps >= self._minimum_course_speed_mps
            ):
                self._bearing = state.course_deg % 360.0

            self._map_renderer.set_camera(
                latitude=state.latitude_deg,
                longitude=state.longitude_deg,
                zoom=self._zoom,
                bearing=self._bearing,
                pitch=self._pitch,
            )
            self._last_camera_update = self._clock()
        except MapRendererUnavailableError as error:
            LOGGER.warning("%s", error)

    def _camera_update_due(self) -> bool:
        if self._last_camera_update is None:
            return True
        return (
            self._clock() - self._last_camera_update
            >= self._minimum_camera_interval_s
        )
