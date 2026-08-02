"""gpsd adapter for the navigation controller."""

from __future__ import annotations

from typing import TYPE_CHECKING

from controllers.navigation.navigation_gps_source_if import (
    GpsStateCallback,
    NavigationGpsSourceIf,
)
from controllers.navigation.navigation_state import GpsState

if TYPE_CHECKING:
    from hardware_io.gps import GpsData, GpsReader


class GpsdNavigationAdapter(NavigationGpsSourceIf):
    """Translate gpsd reports into normalized navigation GPS state."""

    def __init__(self, reader: GpsReader | None = None) -> None:
        if reader is None:
            from hardware_io.gps import GpsReader

            reader = GpsReader()

        self._reader = reader
        self._callback: GpsStateCallback | None = None

    def start(self, callback: GpsStateCallback) -> None:
        self._callback = callback
        self._reader.start(callback=self._gps_data_received)

    def stop(self) -> None:
        self._reader.stop()
        self._callback = None

    def _gps_data_received(self, data: GpsData) -> None:
        callback = self._callback
        if callback is None:
            return

        callback(
            GpsState(
                latitude_deg=data.latitude,
                longitude_deg=data.longitude,
                altitude_m=data.altitude,
                speed_mps=data.speed,
                course_deg=data.track,
                fix_mode=data.mode,
                satellites_visible=data.satellites_visible,
                satellites_used=data.satellites_used,
            )
        )
