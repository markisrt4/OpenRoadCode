# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""gpsd-backed geographic position source."""

from __future__ import annotations

from typing import TYPE_CHECKING

from controllers.navigation.position_source_if import (
    PositionSourceIf,
    PositionStateCallback,
)
from controllers.navigation.navigation_state import PositionState

if TYPE_CHECKING:
    from hardware_io.gps import GpsData, GpsReader


class GpsdPositionSource(PositionSourceIf):
    """Translate gpsd reports into normalized position state."""

    def __init__(self, reader: GpsReader | None = None) -> None:
        if reader is None:
            from hardware_io.gps import GpsReader

            reader = GpsReader()

        self._reader = reader
        self._callback: PositionStateCallback | None = None

    def start(self, callback: PositionStateCallback) -> None:
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
            PositionState(
                latitude_deg=data.latitude,
                longitude_deg=data.longitude,
                altitude_m=data.altitude,
                speed_mps=data.speed,
                course_deg=data.track,
                fix_mode=data.mode,
                satellites_visible=data.satellites_visible,
                satellites_used=data.satellites_used,
                source="gpsd",
            )
        )
